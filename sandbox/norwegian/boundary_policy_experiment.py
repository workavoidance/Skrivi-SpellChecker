"""Tune a provenance-aware compound boundary policy on development only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from engine import Norbert
from experimental_inference import fast_whole
from obt_resources import ObtResources
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
ROOT = HERE / "compound-benchmark"
CATEGORIES = {"established_boundary", "obt_boundary_probe", "clean_separate_phrase"}
HEAD_POS = {"subst", "adj"}
MODEL_REVISION = "f84759ddd3e628afcabb561253d80bbb845e3c8b"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def accepted(info: dict) -> bool:
    if info.get("lexical_compound"):
        return True
    return any(row["trusted"] and row["suffix_pos"] in HEAD_POS
               for row in info.get("strict", []))


def refresh_ordbank_provenance(report: dict) -> None:
    """Credit stored compounds correctly when the visible left part has a linker."""
    ordbank = OrdbankResources()
    try:
        for row in report["rows"]:
            parts = row["typed"].split()
            stored = len(parts) == 2 and any(
                decomposition["first"] + decomposition["linking"] == parts[0].casefold()
                and decomposition["second"] == parts[1].casefold()
                for decomposition in ordbank.decompositions(row["joined"])
            )
            row["provenance"]["ordbank"] = stored
            row["provenance"]["source_class"] = "ordbank" if stored else "obt"
    finally:
        ordbank.close()


def score_split(split: str) -> dict:
    benchmark_path = ROOT / f"{split}.json"
    rows = [row for row in read(benchmark_path) if row["category"] in CATEGORIES]
    digest = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
    output = ROOT / f"boundary-scores-{split}.json"
    report = read(output) if output.exists() else {
        "split": split, "benchmark_sha256": digest,
        "model": "NorBERT3 Small", "model_revision": MODEL_REVISION,
        "rows": [],
    }
    if report["benchmark_sha256"] != digest:
        raise RuntimeError(f"{split} benchmark changed; archive the old score file")
    complete = {row["id"] for row in report["rows"]}
    pending = [row for row in rows if row["id"] not in complete]
    refresh_ordbank_provenance(report)
    save(output, report)
    if not pending:
        return report
    joins = {row["id"]: "".join(row["target"]["typed"].split()) for row in pending}
    obt = ObtResources()
    analyses = obt.analyse(joins.values())
    ordbank = OrdbankResources()
    provenance = {}
    try:
        for row in pending:
            parts = row["target"]["typed"].split()
            joined = joins[row["id"]]
            stored = any(
                decomposition["first"] + decomposition["linking"] == parts[0].casefold()
                and decomposition["second"] == parts[1].casefold()
                for decomposition in ordbank.decompositions(joined)
            )
            analysed = accepted(analyses.get(joined.casefold(), {}))
            provenance[row["id"]] = {
                "ordbank": stored, "obt": analysed,
                "source_class": "ordbank" if stored else "obt",
            }
    finally:
        ordbank.close()
    model = Norbert()
    for index, row in enumerate(pending, 1):
        typed = row["target"]["typed"]
        joined = joins[row["id"]]
        token = {"id": 0, "word": typed, "start": row["target"]["start"],
                 "end": row["target"]["end"]}
        started = time.perf_counter()
        values, _ = fast_whole(model, row["text"], token, [typed, joined])
        report["rows"].append({
            "id": row["id"], "category": row["category"],
            "typed": typed, "joined": joined,
            "correct_action": "keep" if row["category"] == "clean_separate_phrase" else "join",
            "provenance": provenance[row["id"]],
            "typed_score": values[typed], "joined_score": values[joined],
            "join_margin": values[joined] - values[typed],
            "elapsed_seconds": time.perf_counter() - started,
        })
        if index % 20 == 0:
            save(output, report)
            print(f"{split} {index}/{len(pending)}", flush=True)
    save(output, report)
    return report


def metrics(rows: list[dict], ordbank_threshold: float, obt_threshold: float) -> dict:
    decisions = []
    for row in rows:
        threshold = ordbank_threshold if row["provenance"]["source_class"] == "ordbank" else obt_threshold
        flagged = row["join_margin"] > threshold
        decisions.append((row, flagged))
    groups = {}
    for category in sorted(CATEGORIES):
        category_rows = [(row, flag) for row, flag in decisions if row["category"] == category]
        groups[category] = {
            "targets": len(category_rows),
            "correct": sum((flag if row["correct_action"] == "join" else not flag)
                           for row, flag in category_rows),
            "join_flags": sum(flag for _, flag in category_rows),
        }
    positives = [(row, flag) for row, flag in decisions if row["correct_action"] == "join"]
    controls = [(row, flag) for row, flag in decisions if row["correct_action"] == "keep"]
    return {
        "ordbank_threshold": ordbank_threshold,
        "obt_threshold": obt_threshold,
        "positive_recall": sum(flag for _, flag in positives) / len(positives),
        "false_join_rate": sum(flag for _, flag in controls) / len(controls),
        "groups": groups,
    }


def candidate_thresholds(rows: list[dict], source_class: str) -> list[float]:
    values = sorted({row["join_margin"] for row in rows
                     if row["provenance"]["source_class"] == source_class})
    if not values:
        return [0.0]
    return [values[0] - 1.0,
            *[(left + right) / 2 for left, right in zip(values, values[1:])],
            values[-1] + 1.0]


def tune() -> dict:
    report = score_split("development")
    rows = report["rows"]
    fixed = {
        "context_only": (0.0, 0.0),
        "ordbank_always": (-1_000_000.0, 0.0),
        "light_asymmetry": (-1.0, 1.0),
        "strong_asymmetry": (-1_000_000.0, 1.0),
    }
    comparisons = {name: metrics(rows, *thresholds) for name, thresholds in fixed.items()}
    current_false_joins = comparisons["context_only"]["groups"]["clean_separate_phrase"]["join_flags"]
    # Preserve the existing development false-positive count. Established
    # Ordbank errors count twice in the objective because their label is stronger
    # than the exact-restoration OBT probes.
    eligible = []
    for left in candidate_thresholds(rows, "ordbank"):
        for right in candidate_thresholds(rows, "obt"):
            result = metrics(rows, left, right)
            false_joins = result["groups"]["clean_separate_phrase"]["join_flags"]
            if false_joins <= current_false_joins:
                established = result["groups"]["established_boundary"]["join_flags"]
                probes = result["groups"]["obt_boundary_probe"]["join_flags"]
                eligible.append((2 * established + probes, -false_joins,
                                 left + right, result))
    selected = max(eligible, key=lambda item: item[:3])[3]
    comparisons["development_selected"] = selected
    lock = {
        "name": "development_selected",
        "development_benchmark_sha256": report["benchmark_sha256"],
        "model_revision": MODEL_REVISION,
        "selection_rule": (
            "Maximise 2× established joins + OBT-probe joins while allowing no more "
            "clean false joins than context-only on development."
        ),
        "ordbank_threshold": selected["ordbank_threshold"],
        "obt_threshold": selected["obt_threshold"],
        "development_metrics": selected,
        "comparisons": comparisons,
    }
    save(ROOT / "boundary-policy-lock.json", lock)
    print(json.dumps(lock, ensure_ascii=False, indent=2))
    return lock


def evaluate_locked() -> dict:
    lock_path = ROOT / "boundary-policy-lock.json"
    if not lock_path.exists():
        raise RuntimeError("Run the development command first to lock a policy")
    lock = read(lock_path)
    report = score_split("evaluation")
    result = {
        "policy": {key: lock[key] for key in (
            "name", "selection_rule", "ordbank_threshold", "obt_threshold"
        )},
        "evaluation_benchmark_sha256": report["benchmark_sha256"],
        "metrics": metrics(report["rows"], lock["ordbank_threshold"], lock["obt_threshold"]),
        "context_only_comparison": metrics(report["rows"], 0.0, 0.0),
        "median_scoring_seconds": statistics.median(row["elapsed_seconds"] for row in report["rows"]),
    }
    save(ROOT / "boundary-policy-evaluation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("development", "evaluation"))
    arguments = parser.parse_args()
    tune() if arguments.command == "development" else evaluate_locked()


if __name__ == "__main__":
    main()
