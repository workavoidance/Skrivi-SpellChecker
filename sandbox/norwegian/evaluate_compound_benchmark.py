"""Evaluate the current local candidate stack on the frozen compound benchmark."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import time

from engine import Norbert
from experimental_inference import fast_whole
from nuspell_backend import NativeNuspell
from obt_resources import ObtResources
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
BENCHMARK = HERE / "compound-benchmark" / "evaluation.json"
OUTPUT = HERE / "compound-benchmark" / "baseline-results.json"
ANALYSIS = HERE / "compound-benchmark" / "baseline-analysis.json"
HEAD_POS = {"subst", "adj"}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def accepted(info: dict) -> bool:
    if info.get("lexical_compound"):
        return True
    return any(row["trusted"] and row["suffix_pos"] in HEAD_POS
               for row in info.get("strict", []))


def target_token(row: dict) -> dict:
    target = row["target"]
    return {"id": 0, "word": target["typed"],
            "start": target["start"], "end": target["end"]}


def build_candidates(rows: list[dict], ordbank: OrdbankResources,
                     obt: ObtResources, nuspell: NativeNuspell) -> dict[str, list[str]]:
    joins = {}
    lexical_words = []
    for row in rows:
        target = row["target"]
        if row["category"] in {"established_boundary", "obt_boundary_probe",
                               "clean_separate_phrase"}:
            parts = target["typed"].split()
            if len(parts) == 2:
                joins[row["id"]] = (parts, "".join(parts))
        else:
            lexical_words.append(target["typed"])
    join_analysis = obt.analyse(joined for _, joined in joins.values())
    lexical = nuspell.lookup(lexical_words)
    output = {}
    for row in rows:
        typed = row["target"]["typed"]
        if row["id"] in joins:
            parts, joined = joins[row["id"]]
            candidates = ordbank.compounds([parts[0]], [parts[1]])
            if accepted(join_analysis.get(joined.casefold(), {})):
                candidates.append(joined)
            output[row["id"]] = list(dict.fromkeys([typed, *candidates]))
        else:
            output[row["id"]] = list(dict.fromkeys(
                [typed, *lexical[typed]["suggestions"][:24]]
            ))
    return output


def evaluate() -> dict:
    rows = read(BENCHMARK)
    digest = hashlib.sha256(BENCHMARK.read_bytes()).hexdigest()
    report = read(OUTPUT) if OUTPUT.exists() else {
        "benchmark_sha256": digest,
        "protocol": (
            "Ordbank/OBT generate boundary candidates; Nuspell generates one-word candidates; "
            "NorBERT3 Small ranks only those constrained alternatives."
        ),
        "rows": [],
    }
    if report["benchmark_sha256"] != digest:
        raise RuntimeError("Evaluation benchmark changed; archive or remove the old result file first.")
    ordbank, obt, nuspell = OrdbankResources(), ObtResources(), NativeNuspell()
    try:
        candidates = build_candidates(rows, ordbank, obt, nuspell)
    finally:
        ordbank.close()
    model = Norbert()
    complete = {row["id"] for row in report["rows"]}
    for index, row in enumerate(rows, 1):
        if row["id"] in complete:
            continue
        choices = candidates[row["id"]]
        started = time.perf_counter()
        if len(choices) > 1:
            values, _ = fast_whole(model, row["text"], target_token(row), choices)
            ranked = sorted(choices, key=values.get, reverse=True)
        else:
            values, ranked = {choices[0]: 0.0}, choices
        answer = row["target"]["answer"]
        answer_available = answer.casefold() in {value.casefold() for value in choices}
        answer_rank = next((position for position, value in enumerate(ranked, 1)
                            if value.casefold() == answer.casefold()), None)
        original_rank = ranked.index(row["target"]["typed"]) + 1
        report["rows"].append({
            "id": row["id"], "category": row["category"],
            "typed": row["target"]["typed"], "answer": answer,
            "candidate_count": len(choices) - 1,
            "answer_available": answer_available,
            "answer_rank": answer_rank,
            "answer_top1": answer_rank == 1,
            "answer_top3": answer_rank is not None and answer_rank <= 3,
            "original_rank": original_rank,
            "ranked": ranked[:5],
            "elapsed_seconds": time.perf_counter() - started,
        })
        if index % 10 == 0:
            save(OUTPUT, report)
            print(f"evaluation {index}/{len(rows)}", flush=True)
    save(OUTPUT, report)
    return report


def analyse(report: dict) -> dict:
    groups = {}
    for category in sorted({row["category"] for row in report["rows"]}):
        rows = [row for row in report["rows"] if row["category"] == category]
        for row in rows:
            row["answer_suggestion_rank"] = (
                row["answer_rank"] - int(row["original_rank"] < row["answer_rank"])
                if row["answer_rank"] is not None and row["answer"] != row["typed"] else None
            )
        groups[category] = {
            "targets": len(rows),
            "any_candidate": sum(row["candidate_count"] > 0 for row in rows),
            "answer_available": sum(row["answer_available"] for row in rows),
            "answer_top1": sum(row["answer_top1"] for row in rows),
            "answer_top3": sum(row["answer_top3"] for row in rows),
            "answer_first_suggestion": sum(row["answer_suggestion_rank"] == 1 for row in rows),
            "answer_in_three_suggestions": sum(
                row["answer_suggestion_rank"] is not None
                and row["answer_suggestion_rank"] <= 3 for row in rows
            ),
            "median_scoring_seconds": statistics.median(row["elapsed_seconds"] for row in rows),
        }
    result = {
        "benchmark_sha256": report["benchmark_sha256"],
        "groups": groups,
        "interpretation": {
            "boundary_errors": "answer_available measures candidate generation; answer_top1 measures NorBERT selection.",
            "clean_and_name_controls": "answer_top1 means the unchanged source span was retained.",
            "internal_typos": "answer_top3 measures whether the intended source word reaches the displayed shortlist.",
        },
    }
    save(ANALYSIS, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    analyse(evaluate())
