"""Targeted end-to-end verification for the isolated component-join result."""
from __future__ import annotations

import json
from pathlib import Path

from engine import Checker
from evaluate_local_compound_mode import PRIVATE_ID, score


HERE = Path(__file__).parent
OUT = HERE / "component-join-experiment" / "integration.json"
TARGETS = {
    "development": {"profile-Moderate", "profile-Bad", PRIVATE_ID},
    "fresh": {"session-016349-mutated"},
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    checker = Checker()
    report = {"public": [], "private": {}}
    for suite, ids in TARGETS.items():
        cases = {case["id"]: case for case in read(
            HERE / "iteration-2026-09-05" / f"{suite}.json"
        )}
        baselines = {run["case"]: run["result"] for run in read(
            HERE / "nuspell-experiments" / f"{suite}-nuspell_context.json"
        )["runs"] if "result" in run}
        for case_id in ids:
            case = cases[case_id]
            result = checker.check(case["text"], "nuspell_compounds")
            baseline_metrics = score(case, baselines[case_id])
            metrics = score(case, result)
            joins = [token for token in result["words"] if token.get("operation") == "join"]
            if case_id == PRIVATE_ID:
                report["private"][case_id] = {
                    "baseline": baseline_metrics,
                    "component_mode": metrics,
                    "join_reviews": len(joins),
                    "component_join_reviews": sum(
                        token.get("boundary_source") == "ordbank_component" for token in joins
                    ),
                    "text_and_join_details_redacted": True,
                }
            else:
                report["public"].append({
                    "suite": suite, "id": case_id,
                    "baseline": baseline_metrics, "component_mode": metrics,
                    "joins": [{
                        "typed": token["word"],
                        "suggestion": token["suggestions"][0],
                        "source": token.get("boundary_source"),
                    } for token in joins],
                })
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "public_cases": len(report["public"]),
        "private": report["private"],
        "output": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
