"""Compare the optional compound mode with saved Nuspell-context results."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import time

from engine import Checker, words


HERE = Path(__file__).parent
OUT = HERE / "compound-mode-split-evaluation"
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
PRIVATE_ID = "natural-paragraph01"
SCORING_VERSION = 6


def profile_boundaries() -> dict[str, list[dict]]:
    """Recover boundary labels omitted when the profile suite was assembled."""
    path = HERE / "error-profile-examples.json"
    profiles = json.loads(path.read_text(encoding="utf-8"))
    return {
        f"profile-{profile['level'].replace(' ', '-')}": [
            {"source": mutation["injected"], "target": mutation["original"]}
            for mutation in profile.get("changes", [])
            if mutation.get("family") == "word_boundary"
        ]
        for profile in profiles
    }


PROFILE_BOUNDARIES = profile_boundaries()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def occurrence(case: dict, entry: dict) -> dict:
    matches = [token for token in words(case["text"]) if token["word"] == entry["word"]]
    return matches[entry.get("occurrence", 0)]


def expectations(case: dict):
    singles = []
    for entry in case.get("errors", []):
        token = occurrence(case, entry)
        singles.append({"start": token["start"], "end": token["end"],
                        "answers": entry["suggestions"]})
    ignored = []
    for entry in case.get("unscored", []):
        token = occurrence(case, entry)
        ignored.append((token["start"], token["end"]))
    boundaries = []
    boundary_entries = [*case.get("boundary_expectations", []),
                        *PROFILE_BOUNDARIES.get(case["id"], [])]
    for entry in boundary_entries:
        start = case["text"].find(entry["source"])
        if start >= 0:
            boundaries.append({"start": start, "end": start + len(entry["source"]),
                               "answer": entry["target"]})
    return singles, set(ignored), boundaries


def migrate_saved_scoring(report: dict) -> None:
    """Apply the recovered public profile labels without rerunning the model."""
    if report.get("scoring_version", 1) >= SCORING_VERSION:
        return
    for row in report.get("rows", []):
        for mode in ("baseline", "compound"):
            row[mode].setdefault("composite_repairs", 0)
        expected = PROFILE_BOUNDARIES.get(row["id"], [])
        if not expected:
            continue
        for mode in ("baseline", "compound"):
            row[mode]["boundary_targets"] = len(expected)
        joins = row.get("joins", [])
        correct = sum(
            any(join["typed"] == item["source"] and
                join["suggestion"] == item["target"] for join in joins)
            for item in expected
        )
        row["compound"]["boundary_detected"] = correct
        row["compound"]["boundary_top1"] = correct
        row["compound"]["boundary_top3"] = correct
        row["compound"]["false_alarms"] -= correct
    report["scoring_version"] = SCORING_VERSION


def score(case: dict, result: dict) -> dict:
    singles, ignored, boundaries = expectations(case)
    output = {
        "errors": len(singles), "detected": 0, "top1": 0, "top3": 0,
        "candidate_recall": 0, "composite_repairs": 0,
        "swallowed_errors": 0, "false_alarms": 0,
        "review_items": sum(row["status"] != "OK" for row in result["words"]),
        "join_reviews": sum(row.get("operation") == "join" for row in result["words"]),
        "split_reviews": sum(row.get("operation") == "split" for row in result["words"]),
        "boundary_targets": len(boundaries), "boundary_detected": 0,
        "boundary_top1": 0, "boundary_top3": 0,
    }
    single_spans = {(entry["start"], entry["end"]): entry for entry in singles}
    boundary_spans = {(entry["start"], entry["end"]): entry for entry in boundaries}
    for entry in singles:
        exact = next((row for row in result["words"]
                      if row["start"] == entry["start"] and row["end"] == entry["end"]), None)
        covering = next((row for row in result["words"]
                         if row["start"] <= entry["start"] and row["end"] >= entry["end"]), None)
        if exact:
            output["detected"] += exact["status"] != "OK"
            output["top1"] += bool(exact["suggestions"]) and exact["suggestions"][0] in entry["answers"]
            output["top3"] += bool(set(exact["suggestions"]) & set(entry["answers"]))
            output["candidate_recall"] += bool(set(exact.get("candidates", [])) & set(entry["answers"]))
        elif covering:
            boundary = boundary_spans.get((covering["start"], covering["end"]))
            correct_composite = (boundary and
                                 boundary["answer"] in covering.get("suggestions", []))
            if correct_composite:
                output["detected"] += covering["status"] != "OK"
                output["top1"] += (bool(covering["suggestions"]) and
                                   covering["suggestions"][0] == boundary["answer"])
                output["top3"] += boundary["answer"] in covering["suggestions"]
                output["candidate_recall"] += boundary["answer"] in covering.get("candidates", [])
                output["composite_repairs"] += 1
            else:
                output["swallowed_errors"] += 1
    for entry in boundaries:
        exact = next((row for row in result["words"]
                      if row["start"] == entry["start"] and row["end"] == entry["end"]), None)
        if exact:
            output["boundary_detected"] += exact["status"] != "OK"
            output["boundary_top1"] += (bool(exact["suggestions"])
                                        and exact["suggestions"][0] == entry["answer"])
            output["boundary_top3"] += entry["answer"] in exact["suggestions"]
    for row in result["words"]:
        if row["status"] == "OK":
            continue
        span = (row["start"], row["end"])
        if span in single_spans or span in ignored:
            continue
        boundary = boundary_spans.get(span)
        if boundary and boundary["answer"] in row["suggestions"]:
            continue
        output["false_alarms"] += 1
    return output


def aggregate(rows: list[dict], mode: str) -> dict:
    scored = [row[mode] for row in rows]
    keys = ["errors", "detected", "top1", "top3", "candidate_recall", "composite_repairs",
            "swallowed_errors", "false_alarms", "review_items", "join_reviews", "split_reviews",
            "boundary_targets", "boundary_detected", "boundary_top1", "boundary_top3"]
    result = {key: sum(item[key] for item in scored) for key in keys}
    result["cases"] = len(rows)
    result["clean_cases"] = sum(row["kind"] == "clean" for row in rows)
    result["clean_unflagged"] = sum(
        row["kind"] == "clean" and row[mode]["review_items"] == 0 for row in rows
    )
    if mode == "compound":
        result["median_check_seconds"] = statistics.median(row["elapsed_seconds"] for row in rows)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checker = Checker()
    complete_report = {"suites": {}, "private": {}}
    for suite, (case_path, baseline_path) in SUITES.items():
        cases = read(case_path)
        baseline_runs = {row["case"]: row for row in read(baseline_path)["runs"]}
        output_path = OUT / f"{suite}.json"
        report = read(output_path) if output_path.exists() else {
            "suite": suite,
            "scoring_version": SCORING_VERSION,
            "cases_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
            "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
            "engine_sha256": hashlib.sha256((HERE / "engine.py").read_bytes()).hexdigest(),
            "rows": [],
        }
        migrate_saved_scoring(report)
        if report["engine_sha256"] != hashlib.sha256((HERE / "engine.py").read_bytes()).hexdigest():
            raise RuntimeError("Engine changed; archive the earlier local comparison before rerunning")
        done = {row["id"] for row in report["rows"]}
        for index, case in enumerate(cases, 1):
            if case["id"] in done:
                continue
            baseline = baseline_runs[case["id"]]
            if "result" not in baseline:
                raise RuntimeError(f"Missing baseline output for {case['id']}")
            started = time.perf_counter()
            result = checker.check(case["text"], "nuspell_compounds")
            private = case["id"] == PRIVATE_ID
            row = {
                "id": case["id"], "kind": case["kind"], "private": private,
                "baseline": score(case, baseline["result"]),
                "compound": score(case, result),
                "elapsed_seconds": time.perf_counter() - started,
            }
            if not private:
                row["boundary_reviews"] = [
                    {"typed": token["word"], "suggestion": token["suggestions"][0],
                     "operation": token.get("operation"),
                     "source": token.get("boundary_source")}
                    for token in result["words"] if token.get("operation") in {"join", "split"}
                ]
            report["rows"].append(row)
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            if index % 10 == 0:
                print(f"{suite} {index}/{len(cases)}", flush=True)
        public_rows = [row for row in report["rows"] if not row["private"]]
        report["summary"] = {
            "baseline": aggregate(public_rows, "baseline"),
            "compound": aggregate(public_rows, "compound"),
            "note": "Private supplied writing is excluded from public-suite totals.",
        }
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        complete_report["suites"][suite] = report["summary"]
        private_rows = [row for row in report["rows"] if row["private"]]
        for row in private_rows:
            complete_report["private"][row["id"]] = {
                "baseline": row["baseline"], "compound": row["compound"],
                "elapsed_seconds": row["elapsed_seconds"],
                "text_and_boundary_details_redacted": True,
            }
    (OUT / "summary.json").write_text(
        json.dumps(complete_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(complete_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
