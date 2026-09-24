"""Evaluate exact and spelling-repaired split suggestions on the wider suites."""
from __future__ import annotations

import json
from pathlib import Path

from engine import Norbert
from split_resources import SplitResources, rank_split_token, SPLIT_THRESHOLD


HERE = Path(__file__).parent
OUT = HERE / "split-local-evaluation"
THRESHOLD = SPLIT_THRESHOLD
PRIVATE_ID = "natural-paragraph01"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def boundary_targets(case: dict) -> list[dict]:
    return [item for item in case.get("boundary_expectations", [])
            if " " not in item["source"] and " " in item["target"]]


def proposals(text: str, rows: list[dict], model: Norbert,
              resources: SplitResources) -> tuple[list[dict], int]:
    shown, evaluated = [], 0
    for row in rows:
        word = row["word"]
        if not (word.islower() and word.isalpha()):
            continue
        has_candidates = bool(resources.exact(word) or resources.override(word)
                              or (row.get("native_known") is False
                                  and resources.repaired(word)))
        if not has_candidates:
            continue
        evaluated += 1
        best = rank_split_token(text, row, model, resources, THRESHOLD)
        if best:
            best.pop("scores", None)
            shown.append({"start": row["start"], "end": row["end"],
                          "typed": word, **best})
    return shown, evaluated


def main():
    OUT.mkdir(exist_ok=True)
    model, resources = Norbert(), SplitResources()
    summary = {}
    for suite in ("development", "fresh"):
        cases = {case["id"]: case for case in read(
            HERE / "iteration-2026-09-05" / f"{suite}.json"
        )}
        runs = read(HERE / "nuspell-experiments" / f"{suite}-nuspell_context.json")["runs"]
        public, private = [], {}
        evaluated = 0
        for number, run in enumerate(runs, 1):
            if "result" not in run:
                continue
            case = cases[run["case"]]
            found, count = proposals(case["text"], run["result"]["words"],
                                     model, resources)
            evaluated += count
            targets = boundary_targets(case)
            correct = sum(any(
                item["typed"] == target["source"] and
                item["suggestion"] == target["target"] for item in found
            ) for target in targets)
            if run["case"] == PRIVATE_ID:
                private[run["case"]] = {
                    "split_targets": len(targets), "correct_shown": correct,
                    "split_reviews": len(found), "text_and_details_redacted": True,
                }
            elif found:
                public.append({
                    "id": run["case"], "kind": case["kind"],
                    "proposals": found,
                })
            if number % 20 == 0:
                print(f"{suite} {number}/{len(runs)}", flush=True)
        report = {
            "suite": suite, "threshold": THRESHOLD,
            "tokens_with_candidates": evaluated,
            "public_cases_with_split_reviews": len(public),
            "public_split_reviews": sum(len(row["proposals"]) for row in public),
            "public": public, "private": private,
        }
        (OUT / f"{suite}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[suite] = {key: report[key] for key in (
            "tokens_with_candidates", "public_cases_with_split_reviews",
            "public_split_reviews", "private")}
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
