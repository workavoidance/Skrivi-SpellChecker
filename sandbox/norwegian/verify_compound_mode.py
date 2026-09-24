"""Verify that the optional UI mode reproduces the locked boundary policy."""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import time

from engine import Checker


HERE = Path(__file__).parent
ROOT = HERE / "compound-benchmark"
CATEGORIES = {"established_boundary", "obt_boundary_probe", "clean_separate_phrase"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    cases = [row for row in read(ROOT / "evaluation.json") if row["category"] in CATEGORIES]
    score_rows = {row["id"]: row for row in read(ROOT / "boundary-scores-evaluation.json")["rows"]}
    lock = read(ROOT / "boundary-policy-lock.json")
    checker = Checker()
    results = []
    for index, case in enumerate(cases, 1):
        score = score_rows[case["id"]]
        threshold = (lock["ordbank_threshold"]
                     if score["provenance"]["source_class"] == "ordbank"
                     else lock["obt_threshold"])
        expected_flag = score["join_margin"] > threshold
        started = time.perf_counter()
        checked = checker.check(case["text"], "nuspell_compounds")
        target = case["target"]
        actual = next((row for row in checked["words"]
                       if row["start"] == target["start"] and row["end"] == target["end"]
                       and row.get("operation") == "join"), None)
        actual_flag = actual is not None
        results.append({
            "id": case["id"], "category": case["category"],
            "expected_flag": expected_flag, "actual_flag": actual_flag,
            "matches_locked_policy": expected_flag == actual_flag,
            "elapsed_seconds": time.perf_counter() - started,
        })
        if index % 10 == 0:
            print(f"integration {index}/{len(cases)}", flush=True)
    groups = {}
    for category in sorted(CATEGORIES):
        rows = [row for row in results if row["category"] == category]
        positive = category != "clean_separate_phrase"
        groups[category] = {
            "targets": len(rows),
            "policy_matches": sum(row["matches_locked_policy"] for row in rows),
            "correct": sum(row["actual_flag"] == positive for row in rows),
            "join_flags": sum(row["actual_flag"] for row in rows),
        }
    output = {
        "mode": "nuspell_compounds", "groups": groups,
        "policy_matches": sum(row["matches_locked_policy"] for row in results),
        "targets": len(results),
        "median_full_check_seconds": statistics.median(row["elapsed_seconds"] for row in results),
        "mismatches": [row for row in results if not row["matches_locked_policy"]],
    }
    (ROOT / "boundary-mode-integration.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
