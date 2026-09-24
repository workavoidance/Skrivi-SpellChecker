"""Measure useful roles for Norsk Ordbank before changing the default checker."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

from evaluate import expected, score
from engine import Lexicon, Norbert, recase, words
from experimental_inference import fast_whole
from nuspell_backend import NativeNuspell
from ordbank_resources import OrdbankResources
from traditional_resources import TraditionalResources


HERE = Path(__file__).parent
MODEL_BENCHMARK = HERE / "model-benchmark"
sys.path.insert(0, str(MODEL_BENCHMARK))
from boundary_experiments import packets as boundary_packets  # noqa: E402


OUT = HERE / "ordbank-experiment"
SUITES = {
    "development": (
        HERE / "iteration-2026-09-05" / "development.json",
        HERE / "nuspell-experiments" / "development-nuspell_context.json",
    ),
    "fresh": (
        HERE / "iteration-2026-09-05" / "fresh.json",
        HERE / "nuspell-experiments" / "fresh-nuspell_context.json",
    ),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_recognition(result: dict, resources: OrdbankResources, policy: str) -> dict:
    copied = json.loads(json.dumps(result, ensure_ascii=False))
    for token in copied["words"]:
        if token.get("native_known"):
            continue
        entry = resources.lookup(token["word"])
        accept = bool(entry) and (policy == "all" or entry["proper"])
        if accept:
            token["status"] = "OK"
            token["suggestions"] = []
            token["ordbank_recognised"] = True
    return copied


def recognition_experiment(resources: OrdbankResources) -> dict:
    report = {}
    for suite, (case_path, result_path) in SUITES.items():
        cases = {case["id"]: case for case in read(case_path)}
        runs = read(result_path)["runs"]
        policies = {}
        for policy in ("baseline", "proper_only", "all"):
            totals = {name: 0 for name in ("errors", "detected", "top1", "top3", "candidate_recall", "false_alarms")}
            recognised = harmed_targets = 0
            for run in runs:
                case = cases[run["case"]]
                result = run["result"] if policy == "baseline" else apply_recognition(run["result"], resources, policy.replace("_only", ""))
                metrics = score(case, result)
                for name, value in metrics.items():
                    totals[name] += value
                gold = expected(case)
                for token in result["words"]:
                    if token.get("ordbank_recognised"):
                        recognised += 1
                        harmed_targets += token["id"] in gold
            details = []
            if policy != "baseline":
                for run in runs:
                    case = cases[run["case"]]
                    if case["id"] == "natural-paragraph01":
                        continue
                    result = apply_recognition(run["result"], resources, policy.replace("_only", ""))
                    details.extend({"case": case["id"], "word": token["word"]}
                                   for token in result["words"] if token.get("ordbank_recognised"))
            policies[policy] = {**totals, "tokens_accepted_by_ordbank": recognised,
                                "labelled_errors_hidden": harmed_targets,
                                "non_private_accepted": details}
        report[suite] = policies
    return report


def candidate_experiment(resources: OrdbankResources) -> dict:
    from rapidfuzz import process
    from rapidfuzz.distance import OSA

    forms = resources.all_forms()
    missing = []
    for suite, (case_path, result_path) in SUITES.items():
        cases = {case["id"]: case for case in read(case_path)}
        for run in read(result_path)["runs"]:
            case = cases[run["case"]]
            for token_id, answers in expected(case).items():
                token = next(item for item in run["result"]["words"] if item["id"] == token_id)
                if any(answer in token.get("candidates", []) for answer in answers):
                    continue
                missing.append({
                    "id": f"{suite}:{case['id']}:{token_id}",
                    "suite": suite,
                    "private": case["id"] == "natural-paragraph01",
                    "text": case["text"],
                    "token": {key: token[key] for key in ("id", "word", "start", "end")},
                    "answers": answers,
                    "baseline_candidates": token.get("candidates", []),
                })
    model = Norbert() if missing else None
    lexicon = Lexicon(revised=True)
    rows = []
    for packet in missing:
        typed = packet["token"]["word"]
        maximum = 2 if len(typed) < 8 else 3
        matches = process.extract(typed.casefold(), forms, scorer=OSA.distance, score_cutoff=maximum, limit=80)
        retrieved = [resources.display(word) for word, _, _ in matches]
        options = list(dict.fromkeys([typed, *packet["baseline_candidates"], *retrieved]))
        started = time.perf_counter()
        values, _ = fast_whole(model, packet["text"], packet["token"], options)
        values = {
            word: value - 1.5 * max(0, lexicon.distance(typed.casefold(), word.casefold()) - 1)
            for word, value in values.items()
        }
        alternatives = [word for word in sorted(values, key=values.get, reverse=True) if word != typed]
        available = any(answer.casefold() in {word.casefold() for word in options} for answer in packet["answers"])
        top3 = any(answer.casefold() in {word.casefold() for word in alternatives[:3]} for answer in packet["answers"])
        row = {
            "id": packet["id"],
            "suite": packet["suite"],
            "private": packet["private"],
            "answer_available": available,
            "answer_top3": top3,
            "elapsed_seconds": time.perf_counter() - started,
        }
        if not packet["private"]:
            row.update(typed=typed, answers=packet["answers"], suggestions=alternatives[:3])
        rows.append(row)
    return {
        "missing_baseline_targets": len(missing),
        "answer_retrieved": sum(row["answer_available"] for row in rows),
        "answer_ranked_top3": sum(row["answer_top3"] for row in rows),
        "private_rows_redacted": sum(row["private"] for row in rows),
        "median_seconds": statistics.median(row["elapsed_seconds"] for row in rows) if rows else 0,
        "rows": rows,
    }


def full_candidate_pipeline(resources: OrdbankResources) -> dict:
    """Select a few Ordbank neighbours, using frequency only to break edit ties."""
    from rapidfuzz import process
    from rapidfuzz.distance import OSA

    forms_by_length = {}
    for form in resources.all_forms():
        forms_by_length.setdefault(len(form), []).append(form)
    retrieval_cache = {}
    model = Norbert()
    lexicon = Lexicon(revised=True)
    frequency = TraditionalResources()
    prepared = {suite: [] for suite in SUITES}
    scoring_seconds = []
    for suite, (case_path, result_path) in SUITES.items():
        cases = {case["id"]: case for case in read(case_path)}
        for run in read(result_path)["runs"]:
            case = cases[run["case"]]
            updates = {}
            for token in run["result"]["words"]:
                if token.get("native_known"):
                    continue
                typed = token["word"]
                lower = typed.casefold()
                maximum = 2 if len(lower) < 8 else 3
                if lower not in retrieval_cache:
                    choices = [form for length in range(max(1, len(lower)-maximum), len(lower)+maximum+1)
                               for form in forms_by_length.get(length, [])]
                    matches = process.extract(lower, choices, scorer=OSA.distance,
                                              score_cutoff=maximum, limit=200)
                    displays = [resources.display(word) for word, _, _ in matches]
                    counts = frequency.frequencies(displays)
                    retrieval_cache[lower] = [
                        display for display, distance in sorted(
                            ((resources.display(word), distance) for word, distance, _ in matches),
                            key=lambda row: (row[1], -counts[row[0].casefold()], row[0].casefold()),
                        )
                    ]
                baseline_scores = {word: float(value) for word, value in token.get("scores") or []}
                baseline_candidates = list(token.get("candidates", []))
                new_candidates = [candidate for candidate in retrieval_cache[lower]
                                  if candidate.casefold() != lower
                                  and candidate.casefold() not in {word.casefold() for word in baseline_scores}][:16]
                new_scores = {}
                if new_candidates:
                    started = time.perf_counter()
                    values, _ = fast_whole(model, case["text"], token, new_candidates)
                    scoring_seconds.append(time.perf_counter() - started)
                    new_scores = {
                        word: value - 1.5 * max(0, lexicon.distance(lower, word.casefold()) - 1)
                        for word, value in values.items()
                    }
                if typed not in baseline_scores:
                    values, _ = fast_whole(model, case["text"], token, [typed])
                    baseline_scores.update(values)
                updates[token["id"]] = {
                    "baseline_scores": baseline_scores,
                    "baseline_candidates": baseline_candidates,
                    "new_candidates": new_candidates,
                    "new_scores": new_scores,
                }
            prepared[suite].append((case, run["result"], updates))
    frequency.close()

    variants = {}
    for extra_limit in (0, 2, 4, 8, 16):
        suite_results = {}
        pool_sizes = []
        for suite, runs in prepared.items():
            totals = {name: 0 for name in ("errors", "detected", "top1", "top3", "candidate_recall", "false_alarms")}
            changed_targets = []
            for case, baseline_result, updates in runs:
                output = json.loads(json.dumps(baseline_result, ensure_ascii=False))
                gold = expected(case)
                private = case["id"] == "natural-paragraph01"
                for token in output["words"]:
                    update = updates.get(token["id"])
                    if not update:
                        continue
                    extras = update["new_candidates"][:extra_limit]
                    candidates = list(dict.fromkeys([*update["baseline_candidates"], *extras]))
                    values = {**update["baseline_scores"],
                              **{word: update["new_scores"][word] for word in extras}}
                    alternatives = [candidate for candidate in candidates if candidate in values]
                    alternatives.sort(key=values.get, reverse=True)
                    token["suggestions"] = alternatives[:3]
                    token["candidates"] = candidates
                    typed = token["word"]
                    gap = values[alternatives[0]] - values[typed] if alternatives else float("-inf")
                    token["status"] = "LIKELY_ERROR" if gap > 3 else "UNCERTAIN"
                    pool_sizes.append(len(candidates))
                    if token["id"] in gold and not private:
                        before = set(baseline_result["words"][token["id"]].get("suggestions", []))
                        after = set(token["suggestions"])
                        answers = set(gold[token["id"]])
                        if bool(after & answers) != bool(before & answers):
                            changed_targets.append({"case": case["id"], "word": typed,
                                                    "improved": bool(after & answers),
                                                    "suggestions": token["suggestions"]})
                metrics = score(case, output)
                for name, value in metrics.items():
                    totals[name] += value
            suite_results[suite] = {**totals, "non_private_changed_targets": changed_targets}
        variants[str(extra_limit)] = {
            "extra_candidates_per_unknown": extra_limit,
            "suites": suite_results,
            "median_candidate_pool": statistics.median(pool_sizes) if pool_sizes else 0,
            "maximum_candidate_pool": max(pool_sizes, default=0),
        }
    return {
        "selection": "OSA edit distance first; Bokmal unigram frequency breaks equal-distance ties",
        "variants": variants,
        "unique_unknown_spellings_retrieved": len(retrieval_cache),
        "new_candidate_scoring_seconds": sum(scoring_seconds),
        "median_affected_token_seconds": statistics.median(scoring_seconds) if scoring_seconds else 0,
    }


def boundary_experiment(resources: OrdbankResources) -> dict:
    native = NativeNuspell()
    items = boundary_packets()
    individual_words = [part for item in items for part in item["token"]["word"].split()]
    spelling = native.lookup(individual_words)
    small_rows = {row["id"]: row for row in read(MODEL_BENCHMARK / "capability-results" / "norbert3-small-boundaries.json")["rows"]}
    groups = {}
    private_details = []
    for item in items:
        source = item["token"]["word"]
        generated = []
        parts = source.split()
        if len(parts) == 1:
            generated.extend(resources.splits(parts[0]))
        elif len(parts) == 2:
            left, right = parts
            left_options = [left, *spelling[left]["suggestions"][:8]]
            right_options = [right, *spelling[right]["suggestions"][:8]]
            generated.extend(resources.compounds(left_options, right_options))
        answers = {item["answer"].casefold()}
        available = bool(answers & {candidate.casefold() for candidate in generated})
        model_correct = small_rows[item["id"]]["preferred_answer"] if available else None
        group = groups.setdefault(item["kind"], {"targets": 0, "answer_generated": 0, "model_correct_when_generated": 0})
        group["targets"] += 1
        group["answer_generated"] += available
        group["model_correct_when_generated"] += bool(model_correct)
        if item["private"]:
            private_details.append({"answer_generated": available, "model_correct_when_generated": model_correct})
    return {"groups": groups, "private_details_without_text": private_details}


def main():
    resources = OrdbankResources()
    report = {
        "protocol": "Current normed Ordbank forms; proper-name/all-form recognition policies; OSA retrieval only for four baseline misses; explicit compound decomposition with Nuspell component spelling; NorBERT3 Small remains the judge.",
        "private_data": "Private sentence text and token-level words are omitted from the saved report.",
        "inputs": {
            suite: {
                "cases_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                "frozen_results_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest(),
            }
            for suite, paths in SUITES.items()
        },
        "resource": resources.metadata(),
        "recognition": recognition_experiment(resources),
        "candidate_rescue": candidate_experiment(resources),
        "full_candidate_pipeline": full_candidate_pipeline(resources),
        "boundaries": boundary_experiment(resources),
    }
    resources.close()
    save(OUT / "results.json", report)
    compact = {key: report[key] for key in ("recognition", "candidate_rescue", "full_candidate_pipeline", "boundaries")}
    compact["candidate_rescue"] = {key: value for key, value in compact["candidate_rescue"].items() if key != "rows"}
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
