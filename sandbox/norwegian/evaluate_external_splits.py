"""Run the frozen source-disjoint split evaluation through the product mode."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import argparse

from engine import Checker


HERE = Path(__file__).parent
ROOT = HERE / "external-split-evaluation"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserved", action="store_true")
    args = parser.parse_args()
    case_path = ROOT / ("reserved-cases.json" if args.reserved else "cases.json")
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    hash_key = "reserved_cases_sha256" if args.reserved else "cases_sha256"
    if hashlib.sha256(case_path.read_bytes()).hexdigest() != manifest[hash_key]:
        raise RuntimeError("Cases changed after freezing")
    cases = json.loads(case_path.read_text(encoding="utf-8"))
    checker, rows = Checker(), []
    for number, case in enumerate(cases, 1):
        started = time.perf_counter()
        result = checker.check(case["text"], "nuspell_compounds")
        target = case["target"]
        exact = next((row for row in result["words"]
                      if row["start"] == target["start"]
                      and row["end"] == target["end"]), None)
        split_rows = [row for row in result["words"]
                      if row.get("operation") == "split"]
        correct = bool(exact and exact.get("suggestions")
                       and exact["suggestions"][0] == target["answer"])
        rows.append({
            "id": case["id"], "category": case["category"],
            "target_split_shown": bool(exact and exact.get("operation") == "split"),
            "target_correct_top1": correct,
            "split_reviews_in_sentence": len(split_rows),
            "target_proposal": None if not exact or exact.get("operation") != "split" else {
                "suggestions": exact["suggestions"],
                "comparison": exact.get("boundary_comparison"),
                "retrieval": exact.get("boundary_retrieval"),
                "margin": exact.get("split_margin"),
            },
            "elapsed_seconds": time.perf_counter() - started,
        })
        if number % 20 == 0:
            print(f"{number}/{len(cases)}", flush=True)
    positives = [row for row in rows if row["category"] == "joined_error"]
    controls = [row for row in rows if row["category"] == "legitimate_token"]
    summary = {
        "cases_sha256": manifest[hash_key],
        "split": "reserved" if args.reserved else "diagnostic",
        "source_disjoint_from_phrase_resource": True,
        "coverage": manifest["coverage"],
        "joined_errors": len(positives),
        "target_split_shown": sum(row["target_split_shown"] for row in positives),
        "target_correct_top1": sum(row["target_correct_top1"] for row in positives),
        "wrong_target_splits": sum(row["target_split_shown"]
                                   and not row["target_correct_top1"] for row in positives),
        "legitimate_token_controls": len(controls),
        "false_target_splits": sum(row["target_split_shown"] for row in controls),
        "control_sentences_with_any_split": sum(
            row["split_reviews_in_sentence"] > 0 for row in controls),
        "control_split_reviews": sum(row["split_reviews_in_sentence"] for row in controls),
    }
    result_name = "reserved-results.json" if args.reserved else "results.json"
    summary_name = "reserved-summary.json" if args.reserved else "summary.json"
    (ROOT / result_name).write_text(
        json.dumps({"summary": summary, "rows": rows},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / summary_name).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
