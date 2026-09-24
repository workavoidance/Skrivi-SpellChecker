"""Measure OBT compound analysis without changing the default checker."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

from engine import Norbert, recase, words
from evaluate import expected
from experimental_inference import fast_whole
from nuspell_backend import NativeNuspell
from obt_resources import ObtResources


HERE = Path(__file__).parent
MODEL_BENCHMARK = HERE / "model-benchmark"
sys.path.insert(0, str(MODEL_BENCHMARK))
from boundary_experiments import clean_texts, packets as boundary_packets  # noqa: E402

OUT = HERE / "obt-experiment"
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
HEAD_POS = {"subst", "adj"}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def accepted(info: dict, policy: str = "trusted") -> bool:
    if info.get("lexical_compound"):
        return True
    rows = info.get("strict", [])
    if policy == "raw":
        return bool(rows)
    if policy == "trusted":
        return any(row["trusted"] for row in rows)
    if policy == "trusted_head":
        return any(row["trusted"] and row["suffix_pos"] in HEAD_POS for row in rows)
    raise ValueError(policy)


def spelling_options(native: NativeNuspell, values, limit: int = 6) -> dict[str, list[str]]:
    values = list(dict.fromkeys(value.casefold() for value in values if value))
    looked = native.lookup(values)
    return {value: [value, *looked[value]["suggestions"][:limit]] for value in values}


def boundary_experiment(resources: ObtResources, native: NativeNuspell) -> dict:
    items = boundary_packets()
    parts = [part.casefold() for item in items for part in item["token"]["word"].split()]
    options = spelling_options(native, parts, limit=8)
    candidate_sets = {}
    all_candidates = []
    for item in items:
        source_parts = item["token"]["word"].casefold().split()
        candidates = []
        if len(source_parts) == 2:
            left, right = source_parts
            candidates = list(dict.fromkeys(
                (first + second).casefold() for first in options[left] for second in options[right]
            ))
        candidate_sets[item["id"]] = candidates
        all_candidates.extend(candidates)
    analyses = resources.analyse(all_candidates)
    model = Norbert()
    scores = {}
    scoring_seconds = []
    for item in items:
        candidates = [candidate for candidate in candidate_sets[item["id"]]
                      if accepted(analyses[candidate], "raw")]
        if not candidates:
            scores[item["id"]] = {item["token"]["word"]: 0.0}
            continue
        started = time.perf_counter()
        values, _ = fast_whole(model, item["text"], item["token"],
                               [item["token"]["word"], *candidates])
        scoring_seconds.append(time.perf_counter() - started)
        scores[item["id"]] = values
    policies = {}
    for policy in ("raw", "trusted", "trusted_head"):
        groups = {}
        inspection = []
        for item in items:
            generated = [candidate for candidate in candidate_sets[item["id"]]
                         if accepted(analyses[candidate], policy)]
            answer = item["answer"].casefold()
            available = answer in generated
            values = scores[item["id"]]
            ranked = sorted(generated, key=values.get, reverse=True)
            top3 = available and answer in ranked[:3]
            top1 = available and bool(ranked) and ranked[0] == answer
            original_score = values[item["token"]["word"]]
            answer_preferred = available and values[answer] > original_score
            answer_selected = top1 and answer_preferred
            small_keeps_original = not ranked or values[ranked[0]] <= original_score
            group = groups.setdefault(item["kind"], {
                "targets": 0, "any_candidate_generated": 0,
                "answer_generated": 0, "answer_top3": 0, "answer_top1": 0,
                "answer_preferred_to_original": 0, "answer_selected_top1": 0,
                "small_keeps_original": 0,
            })
            group["targets"] += 1
            group["any_candidate_generated"] += bool(generated)
            group["answer_generated"] += available
            group["answer_top3"] += bool(top3)
            group["answer_top1"] += bool(top1)
            group["answer_preferred_to_original"] += bool(answer_preferred)
            group["answer_selected_top1"] += bool(answer_selected)
            group["small_keeps_original"] += small_keeps_original
            if not item["private"] and item["kind"] != "clean_phrase" and len(inspection) < 15:
                inspection.append({
                    "id": item["id"], "source": item["token"]["word"],
                    "answer": item["answer"], "answer_generated": available,
                    "top3": ranked[:3], "answer_top3": bool(top3),
                    "answer_selected": bool(answer_selected),
                })
        policies[policy] = {"groups": groups, "non_private_inspection": inspection}
    return {
        "candidate_protocol": "Join each two-word span after up to six Nuspell suggestions per component; OBT validates the joined result.",
        "policies": policies,
        "private_details": [
            {
                "answer_generated": item["answer"].casefold() in [
                    candidate for candidate in candidate_sets[item["id"]]
                    if accepted(analyses[candidate], "trusted_head")
                ],
                "answer_top3": item["answer"].casefold() in sorted(
                    [candidate for candidate in candidate_sets[item["id"]]
                     if accepted(analyses[candidate], "trusted_head")],
                    key=scores[item["id"]].get, reverse=True)[:3],
                "answer_preferred_to_original": (
                    scores[item["id"]].get(item["answer"].casefold(), float("-inf")) >
                    scores[item["id"]][item["token"]["word"]]
                ),
            }
            for item in items if item["private"]
        ],
        "unique_candidates_analysed": len(analyses),
        "median_small_scoring_seconds": statistics.median(scoring_seconds) if scoring_seconds else 0,
    }


def missing_packets() -> list[dict]:
    missing = []
    for suite, (case_path, result_path) in SUITES.items():
        cases = {case["id"]: case for case in read(case_path)}
        for run in read(result_path)["runs"]:
            case = cases[run["case"]]
            gold = expected(case)
            for token_id, answers in gold.items():
                token = next(token for token in run["result"]["words"] if token["id"] == token_id)
                candidates = {candidate.casefold() for candidate in token.get("candidates", [])}
                if any(answer.casefold() in candidates for answer in answers):
                    continue
                missing.append({
                    "id": f"{suite}:{case['id']}:{token_id}",
                    "private": case["id"] == "natural-paragraph01",
                    "text": case["text"], "token": token, "answers": answers,
                })
    return missing


def repair_from_analyses(resources: ObtResources, native: NativeNuspell,
                         typed_analyses: dict[str, dict]) -> dict[str, list[str]]:
    clues = {}
    prefixes = []
    for typed, info in typed_analyses.items():
        rows = [row for row in [*info.get("strict", []), *info.get("fallback", [])]
                if not row["trusted"] and row["suffix_pos"] in HEAD_POS
                and len(row["prefix"]) >= 3 and len(row["suffix"]) >= 4]
        clues[typed] = rows
        prefixes.extend(row["prefix"] for row in rows)
    prefix_options = spelling_options(native, prefixes, limit=8)
    proposed = {}
    all_proposals = []
    for typed, rows in clues.items():
        values = []
        for row in rows:
            for prefix in prefix_options[row["prefix"]][1:]:
                candidate = prefix.casefold() + row["linking"] + row["suffix"]
                if candidate != typed and candidate.isalpha():
                    values.append(candidate)
        proposed[typed] = list(dict.fromkeys(values))
        all_proposals.extend(proposed[typed])
    validated = resources.analyse(all_proposals)
    return {
        typed: [candidate for candidate in candidates
                if accepted(validated[candidate], "trusted_head")][:12]
        for typed, candidates in proposed.items()
    }


def missing_candidate_experiment(resources: ObtResources, native: NativeNuspell) -> dict:
    packets = missing_packets()
    analyses = resources.analyse(packet["token"]["word"] for packet in packets)
    candidates = repair_from_analyses(resources, native, analyses)
    model = Norbert() if any(candidates.values()) else None
    rows = []
    elapsed = []
    for packet in packets:
        typed = packet["token"]["word"]
        choices = [recase(candidate, typed) for candidate in candidates.get(typed.casefold(), [])]
        available = any(answer.casefold() in {candidate.casefold() for candidate in choices}
                        for answer in packet["answers"])
        top3 = False
        displayed = choices[:3]
        if choices:
            started = time.perf_counter()
            values, _ = fast_whole(model, packet["text"], packet["token"], [typed, *choices])
            elapsed.append(time.perf_counter() - started)
            ranked = sorted(choices, key=values.get, reverse=True)
            displayed = ranked[:3]
            top3 = any(answer.casefold() in {candidate.casefold() for candidate in displayed}
                       for answer in packet["answers"])
        row = {"id": packet["id"], "private": packet["private"],
               "answer_generated": available, "answer_top3": top3,
               "candidate_count": len(choices)}
        if not packet["private"]:
            row.update(typed=typed, answers=packet["answers"], suggestions=displayed)
        rows.append(row)
    return {
        "missing_baseline_targets": len(rows),
        "answer_generated": sum(row["answer_generated"] for row in rows),
        "answer_top3": sum(row["answer_top3"] for row in rows),
        "private_rows_redacted": sum(row["private"] for row in rows),
        "median_scoring_seconds": statistics.median(elapsed) if elapsed else 0,
        "rows": rows,
    }


def clean_unknown_risk(resources: ObtResources, native: NativeNuspell) -> dict:
    occurrences = []
    for key, text, _ in clean_texts():
        for token in words(text):
            if token["word"].isalpha():
                occurrences.append((key, text, token))
    native_rows = native.lookup([token["word"] for _, _, token in occurrences])
    unknown = [(key, text, token) for key, text, token in occurrences
               if not native_rows[token["word"]]["known"]]
    typed_analyses = resources.analyse(token["word"] for _, _, token in unknown)
    repairs = repair_from_analyses(resources, native, typed_analyses)
    affected = [(key, text, token, repairs.get(token["word"].casefold(), []))
                for key, text, token in unknown if repairs.get(token["word"].casefold())]
    model = Norbert() if affected else None
    preferred_change = 0
    inspections = []
    elapsed = []
    for key, text, token, candidates in affected:
        candidates = [recase(candidate, token["word"]) for candidate in candidates]
        started = time.perf_counter()
        values, _ = fast_whole(model, text, token, [token["word"], *candidates])
        elapsed.append(time.perf_counter() - started)
        ranked = sorted(candidates, key=values.get, reverse=True)
        changes = bool(ranked and values[ranked[0]] > values[token["word"]])
        preferred_change += changes
        if len(inspections) < 20:
            inspections.append({"case": key, "word": token["word"],
                                "suggestions": ranked[:3], "model_prefers_change": changes})
    return {
        "clean_word_occurrences": len(occurrences),
        "nuspell_unknown_occurrences": len(unknown),
        "obt_component_repair_occurrences": len(affected),
        "small_prefers_a_change": preferred_change,
        "median_scoring_seconds": statistics.median(elapsed) if elapsed else 0,
        "non_private_inspection": inspections,
        "caveat": "These untouched source sentences are treated as clean controls; flags are not individually adjudicated errors.",
    }


def probes(resources: ObtResources) -> dict:
    values = ["kulturkonservatisme", "kuturkonservatisme", "nordstrandskole", "bretspill"]
    rows = resources.analyse(values)
    return {
        word: {
            "lexical_compound": info["lexical_compound"],
            "raw_analysis": bool(info["strict"]),
            "trusted_head_analysis": accepted(info, "trusted_head"),
            "analyses": info["strict"],
        }
        for word, info in rows.items()
    }


def main() -> None:
    resources = ObtResources()
    native = NativeNuspell()
    report = {
        "protocol": "Pinned OBT multitagger compound analyser; raw and direct-component policies separated; Nuspell repairs components; NorBERT3 Small only ranks constrained alternatives.",
        "private_data": "The authentic paragraph is processed locally. Its sentence and token text are omitted from this report.",
        "resource": resources.metadata(),
        "inputs": {
            suite: {"cases_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                    "frozen_results_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest()}
            for suite, paths in SUITES.items()
        },
    }
    report["probes"] = probes(resources)
    report["boundaries"] = boundary_experiment(resources, native)
    report["missing_candidates"] = missing_candidate_experiment(resources, native)
    report["clean_unknown_risk"] = clean_unknown_risk(resources, native)
    save(OUT / "results.json", report)
    print(json.dumps({
        "boundaries": report["boundaries"]["policies"],
        "missing_candidates": {key: value for key, value in report["missing_candidates"].items() if key != "rows"},
        "clean_unknown_risk": {key: value for key, value in report["clean_unknown_risk"].items()
                               if key != "non_private_inspection"},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
