"""Evaluate SCARRIE candidate rescue and a Bokmal unigram ranking prior.

This remains separate from the application.  It reuses frozen Nuspell results,
scores only genuinely new candidates, and omits private sentence text from the
saved report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from engine import Lexicon, Norbert, recase, words
from evaluate import expected, score
from experimental_inference import fast_whole
from nuspell_backend import NativeNuspell
from traditional_resources import TraditionalResources


HERE = Path(__file__).parent
OUT = HERE / "traditional-experiment"
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
WEIGHTS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def gold_by_id(case: dict) -> dict[int, list[str]]:
    return expected(case)


def original_token(case: dict, run: dict, token_id: int) -> dict:
    return next(token for token in run["result"]["words"] if token["id"] == token_id)


def gather_packets() -> list[dict]:
    resources = TraditionalResources()
    packets = []
    for suite, (case_path, result_path) in SUITES.items():
        cases = {case["id"]: case for case in read(case_path)}
        for run in read(result_path)["runs"]:
            case = cases[run["case"]]
            private = case["id"] == "natural-paragraph01"
            gold = gold_by_id(case)
            for token in run["result"]["words"]:
                score_pairs = token.get("scores") or []
                existing = [candidate for candidate, _ in score_pairs]
                mapped = resources.corrections(token["word"])
                # SCARRIE is old and contains historical variants.  Restrict its
                # correction table to words the current Nuspell dictionary rejects.
                proposed = mapped if not token.get("native_known") else []
                options = list(dict.fromkeys([*existing, token["word"], *proposed]))
                packets.append(
                    {
                        "id": f"{suite}:{case['id']}:{token['id']}",
                        "suite": suite,
                        "private": private,
                        "case_id": case["id"],
                        "kind": case["kind"],
                        "text": case["text"],
                        "token": {key: token[key] for key in ("id", "word", "start", "end")},
                        "native_known": bool(token.get("native_known")),
                        "baseline": token,
                        "answers": gold.get(token["id"], []),
                        "mapped": proposed,
                        "options": options,
                        "existing_scores": {word: float(value) for word, value in score_pairs},
                    }
                )
    resources.close()
    return packets


def score_new_candidates(packets: list[dict]) -> tuple[list[dict], dict]:
    native = NativeNuspell()
    candidates = list(
        dict.fromkeys(candidate for packet in packets for candidate in packet["mapped"])
    )
    validity = native.lookup(candidates) if candidates else {}
    needed = 0
    for packet in packets:
        packet["mapped"] = [
            recase(candidate, packet["token"]["word"])
            for candidate in packet["mapped"]
            if validity.get(candidate, {}).get("known")
        ]
        packet["options"] = list(
            dict.fromkeys(
                [*packet["existing_scores"], packet["token"]["word"], *packet["mapped"]]
            )
        )
        if any(candidate not in packet["existing_scores"] for candidate in packet["options"]):
            needed += 1
    model = Norbert() if needed else None
    lexicon = Lexicon(revised=True)
    seconds = []
    for index, packet in enumerate(packets, 1):
        missing = [candidate for candidate in packet["options"] if candidate not in packet["existing_scores"]]
        if not missing:
            packet["scores"] = packet["existing_scores"]
            continue
        started = time.perf_counter()
        values, _ = fast_whole(model, packet["text"], packet["token"], packet["options"])
        if not packet["native_known"]:
            typed = packet["token"]["word"].casefold()
            values = {
                word: value - 1.5 * max(0, lexicon.distance(typed, word.casefold()) - 1)
                for word, value in values.items()
            }
        packet["scores"] = values
        seconds.append(time.perf_counter() - started)
        if index % 100 == 0:
            print(f"Scored {index}/{len(packets)} packets", flush=True)
    return packets, {
        "packets_with_new_candidates": needed,
        "new_candidate_score_seconds": sum(seconds),
        "median_new_candidate_score_seconds": statistics.median(seconds) if seconds else 0,
    }


def result_for_weight(packet: dict, resources: TraditionalResources, weight: float) -> dict:
    baseline = packet["baseline"]
    original = packet["token"]["word"]
    scores = packet["scores"]
    frequencies = resources.frequencies(scores)
    adjusted = {
        word: score
        + (0 if packet["native_known"] else weight * math.log10(1 + frequencies[word.casefold()]))
        for word, score in scores.items()
    }
    ranked = sorted(adjusted, key=adjusted.get, reverse=True)
    alternatives = [word for word in ranked if word != original]
    if packet["native_known"]:
        suggestions = [word for word in alternatives if adjusted[word] - adjusted[original] > 4][:3]
        status = "UNCERTAIN" if suggestions else "OK"
    else:
        suggestions = alternatives[:3]
        gap = adjusted[alternatives[0]] - adjusted[original] if alternatives else -math.inf
        status = "LIKELY_ERROR" if gap > 3 else "UNCERTAIN"
    return {
        **baseline,
        "status": status,
        "suggestions": suggestions,
        "candidates": [word for word in packet["options"] if word != original],
        "scores": [[word, adjusted[word]] for word in ranked],
        "scarrie_candidates": packet["mapped"],
    }


def evaluate_weight(packets: list[dict], resources: TraditionalResources, weight: float) -> dict:
    totals = {key: 0 for key in ("errors", "detected", "top1", "top3", "candidate_recall", "false_alarms")}
    cases = {}
    for packet in packets:
        key = (packet["suite"], packet["case_id"])
        cases.setdefault(key, []).append(packet)
    suite_totals = {}
    for (suite, case_id), members in cases.items():
        case_path = SUITES[suite][0]
        case = next(item for item in read(case_path) if item["id"] == case_id)
        result = {
            "text": case["text"],
            "words": [result_for_weight(packet, resources, weight) for packet in members],
        }
        metrics = score(case, result)
        target = suite_totals.setdefault(
            suite,
            {key: 0 for key in totals},
        )
        for name, value in metrics.items():
            totals[name] += value
            target[name] += value
    return {"weight": weight, "all": totals, "suites": suite_totals}


def candidate_rescue(packets: list[dict]) -> dict:
    summary = {}
    rows = []
    for suite in SUITES:
        targets = [packet for packet in packets if packet["suite"] == suite and packet["answers"]]
        base = sum(any(answer in packet["baseline"].get("candidates", []) for answer in packet["answers"]) for packet in targets)
        augmented = sum(any(answer in packet["options"] for answer in packet["answers"]) for packet in targets)
        mapped_targets = sum(bool(packet["mapped"]) for packet in targets)
        summary[suite] = {
            "targets": len(targets),
            "baseline_candidate_recall": base,
            "augmented_candidate_recall": augmented,
            "targets_with_valid_scarrie_candidate": mapped_targets,
        }
        for packet in targets:
            if packet["mapped"] and not packet["private"]:
                rows.append(
                    {
                        "suite": suite,
                        "case": packet["case_id"],
                        "typed": packet["token"]["word"],
                        "answers": packet["answers"],
                        "scarrie_candidates": packet["mapped"],
                        "rescued": any(answer in packet["mapped"] for answer in packet["answers"]),
                    }
                )
    return {"summary": summary, "non_private_details": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT / "results.json"))
    args = parser.parse_args()
    packets = gather_packets()
    packets, timing = score_new_candidates(packets)
    resources = TraditionalResources()
    curves = [evaluate_weight(packets, resources, weight) for weight in WEIGHTS]
    resources.close()
    development = [point for point in curves]
    chosen = max(
        development,
        key=lambda point: (
            point["suites"]["development"]["top3"],
            -point["suites"]["development"]["false_alarms"],
            point["suites"]["development"]["top1"],
            -point["weight"],
        ),
    )["weight"]
    resource_reader = TraditionalResources()
    resource_meta = resource_reader.metadata()
    resource_reader.close()
    report = {
        "protocol": (
            "SCARRIE explicit replacements only for current-Nuspell unknown words; "
            "replacement candidates revalidated with current Nuspell; frequency prior "
            "applied only to unknown-word ranking; NorBERT3 Small context retained"
        ),
        "private_data": "Private sentence text and token-level details are omitted.",
        "inputs": {
            suite: {
                "cases_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                "frozen_results_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest(),
            }
            for suite, paths in SUITES.items()
        },
        "resource_manifest": resource_meta,
        "timing": timing,
        "candidate_rescue": candidate_rescue(packets),
        "weight_curve": curves,
        "chosen_on_development": chosen,
        "fresh_result_at_chosen_weight": next(
            point["suites"]["fresh"] for point in curves if point["weight"] == chosen
        ),
    }
    save(Path(args.output), report)
    print(json.dumps({
        "candidate_rescue": report["candidate_rescue"]["summary"],
        "chosen_on_development": chosen,
        "fresh_result_at_chosen_weight": report["fresh_result_at_chosen_weight"],
        "weight_curve": curves,
        "timing": timing,
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
