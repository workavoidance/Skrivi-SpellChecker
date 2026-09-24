"""Validate and score provenance-aware spell-checker benchmark data.

This tool deliberately uses only the Python standard library. It is kept outside
the shipped dictation application while the spell-checker concept is evaluated.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WRITER_GROUPS = {
    "diagnosed_dyslexia",
    "poor_speller",
    "general_pupil",
    "norwegian_l2",
    "synthetic",
}
LANGUAGE_STANDARDS = {"bokmal", "nynorsk", "mixed", "unknown"}
CORRECTION_KINDS = {"keep", "replace", "contextual_replace", "split", "join"}

REQUIRED_STRING_FIELDS = (
    "id",
    "source",
    "original_sentence",
    "original_token",
    "corrected_token",
    "corrected_sentence",
    "error_type",
    "collection_method",
    "licence",
)
REQUIRED_FIELDS = set(REQUIRED_STRING_FIELDS) | {
    "source_record_id",
    "writer_group",
    "formal_dyslexia_diagnosis",
    "age_or_grade",
    "language_standard",
    "norwegian_first_language",
    "correction_kind",
    "contextual_real_word_error",
    "redistributable",
    "notes",
}


class BenchmarkValidationError(ValueError):
    """Raised when a JSONL benchmark or prediction file is invalid."""


@dataclass(frozen=True)
class ScoreCounts:
    total: int = 0
    changes: int = 0
    keeps: int = 0
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0
    top1: int = 0
    top3: int = 0
    top5: int = 0
    reciprocal_rank: float = 0.0

    def add(self, **values: int | float) -> ScoreCounts:
        current = self.__dict__ | values
        for name in self.__dict__:
            if name in values:
                current[name] = getattr(self, name) + values[name]
        return ScoreCounts(**current)


def _normalise(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise BenchmarkValidationError(
                f"{path}:{line_number}: invalid JSON: {error.msg}"
            ) from error
        if not isinstance(record, dict):
            raise BenchmarkValidationError(
                f"{path}:{line_number}: each line must be a JSON object"
            )
        record["_line_number"] = line_number
        records.append(record)
    return records


def _location(path: Path, record: dict[str, Any]) -> str:
    return f"{path}:{record.get('_line_number', '?')}"


def validate_benchmark(
    records: Iterable[dict[str, Any]], path: Path = Path("<benchmark>")
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for record in records:
        location = _location(path, record)
        for field in sorted(REQUIRED_FIELDS - record.keys()):
            errors.append(f"{location}: missing required field {field}")
        for field in REQUIRED_STRING_FIELDS:
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{location}: {field} must be a non-empty string")

        for field in ("source_record_id", "age_or_grade"):
            if record.get(field) is not None and not isinstance(record.get(field), str):
                errors.append(f"{location}: {field} must be a string or null")
        if not isinstance(record.get("notes"), str):
            errors.append(f"{location}: notes must be a string")

        identifier = record.get("id")
        if isinstance(identifier, str):
            if identifier in seen_ids:
                errors.append(f"{location}: duplicate id {identifier!r}")
            seen_ids.add(identifier)

        writer_group = record.get("writer_group")
        if writer_group not in WRITER_GROUPS:
            errors.append(
                f"{location}: writer_group must be one of {sorted(WRITER_GROUPS)}"
            )

        language_standard = record.get("language_standard")
        if language_standard not in LANGUAGE_STANDARDS:
            errors.append(
                f"{location}: language_standard must be one of "
                f"{sorted(LANGUAGE_STANDARDS)}"
            )

        correction_kind = record.get("correction_kind")
        if correction_kind not in CORRECTION_KINDS:
            errors.append(
                f"{location}: correction_kind must be one of {sorted(CORRECTION_KINDS)}"
            )

        for field in ("formal_dyslexia_diagnosis", "norwegian_first_language"):
            if record.get(field) not in (True, False, None):
                errors.append(f"{location}: {field} must be true, false, or null")

        for field in ("contextual_real_word_error", "redistributable"):
            if not isinstance(record.get(field), bool):
                errors.append(f"{location}: {field} must be a boolean")

        diagnosis = record.get("formal_dyslexia_diagnosis")
        if writer_group == "diagnosed_dyslexia" and diagnosis is not True:
            errors.append(
                f"{location}: diagnosed_dyslexia records require a confirmed diagnosis"
            )
        if writer_group in {"general_pupil", "norwegian_l2", "synthetic"}:
            if diagnosis is True:
                errors.append(
                    f"{location}: {writer_group} records cannot claim a diagnosis"
                )
        if (
            writer_group == "norwegian_l2"
            and record.get("norwegian_first_language") is not False
        ):
            errors.append(
                f"{location}: norwegian_l2 records require "
                "norwegian_first_language=false"
            )

        original = record.get("original_token")
        corrected = record.get("corrected_token")
        if isinstance(original, str) and isinstance(corrected, str):
            changed = _normalise(original) != _normalise(corrected)
            if correction_kind == "keep" and changed:
                errors.append(
                    f"{location}: keep records must have identical original and "
                    "corrected tokens"
                )
            if correction_kind != "keep" and not changed:
                errors.append(
                    f"{location}: {correction_kind} records must change the token"
                )

    return errors


def validate_predictions(
    records: Iterable[dict[str, Any]], path: Path = Path("<predictions>")
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for record in records:
        location = _location(path, record)
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{location}: id must be a non-empty string")
        elif identifier in seen_ids:
            errors.append(f"{location}: duplicate id {identifier!r}")
        else:
            seen_ids.add(identifier)

        if not isinstance(record.get("flagged"), bool):
            errors.append(f"{location}: flagged must be a boolean")

        suggestions = record.get("suggestions")
        if not isinstance(suggestions, list):
            errors.append(f"{location}: suggestions must be a list")
            continue
        if len(suggestions) > 5:
            errors.append(f"{location}: suggestions must contain at most 5 items")
        normalised: list[str] = []
        for suggestion in suggestions:
            if not isinstance(suggestion, str) or not suggestion.strip():
                errors.append(
                    f"{location}: every suggestion must be a non-empty string"
                )
                continue
            normalised.append(_normalise(suggestion.strip()))
        if len(normalised) != len(set(normalised)):
            errors.append(f"{location}: suggestions must not contain duplicates")
    return errors


def _safe_ratio(numerator: int | float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _score_group(counts: ScoreCounts) -> dict[str, int | float | None]:
    precision_denominator = counts.true_positive + counts.false_positive
    recall_denominator = counts.true_positive + counts.false_negative
    precision = _safe_ratio(counts.true_positive, precision_denominator)
    recall = _safe_ratio(counts.true_positive, recall_denominator)
    f1 = None
    if precision is not None and recall is not None and precision + recall:
        f1 = round(2 * precision * recall / (precision + recall), 4)
    return {
        "total": counts.total,
        "changes": counts.changes,
        "keeps": counts.keeps,
        "detection_precision": precision,
        "detection_recall": recall,
        "detection_f1": f1,
        "top1_recall": _safe_ratio(counts.top1, counts.changes),
        "top3_recall": _safe_ratio(counts.top3, counts.changes),
        "top5_recall": _safe_ratio(counts.top5, counts.changes),
        "mean_reciprocal_rank_at_5": _safe_ratio(
            counts.reciprocal_rank, counts.changes
        ),
    }


def score(
    benchmark: Iterable[dict[str, Any]], predictions: Iterable[dict[str, Any]]
) -> dict[str, dict[str, int | float | None]]:
    prediction_by_id = {record["id"]: record for record in predictions}
    counts_by_group: dict[str, ScoreCounts] = defaultdict(ScoreCounts)
    counts_by_group["all"] = ScoreCounts()

    for item in benchmark:
        prediction = prediction_by_id.get(
            item["id"], {"flagged": False, "suggestions": []}
        )
        changed = _normalise(item["original_token"]) != _normalise(
            item["corrected_token"]
        )
        flagged = prediction["flagged"]
        suggestions = [
            _normalise(suggestion.strip()) for suggestion in prediction["suggestions"]
        ]
        target = _normalise(item["corrected_token"])
        rank = suggestions.index(target) + 1 if target in suggestions else None
        values: dict[str, int | float] = {
            "total": 1,
            "changes": int(changed),
            "keeps": int(not changed),
            "true_positive": int(changed and flagged),
            "false_positive": int(not changed and flagged),
            "false_negative": int(changed and not flagged),
            "true_negative": int(not changed and not flagged),
            "top1": int(changed and rank == 1),
            "top3": int(changed and rank is not None and rank <= 3),
            "top5": int(changed and rank is not None and rank <= 5),
            "reciprocal_rank": 1 / rank if changed and rank else 0.0,
        }
        for group in ("all", item["writer_group"]):
            counts_by_group[group] = counts_by_group[group].add(**values)

    return {
        group: _score_group(counts) for group, counts in sorted(counts_by_group.items())
    }


def _fail_if_invalid(errors: list[str]) -> None:
    if errors:
        raise BenchmarkValidationError("\n".join(errors))


def _write_metrics(metrics: dict[str, Any]) -> None:
    print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("benchmark", type=Path)

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("benchmark", type=Path)
    score_parser.add_argument("predictions", type=Path)

    args = parser.parse_args(argv)
    try:
        benchmark = read_jsonl(args.benchmark)
        _fail_if_invalid(validate_benchmark(benchmark, args.benchmark))
        if args.command == "validate":
            print(f"Valid benchmark: {len(benchmark)} records")
            return 0

        predictions = read_jsonl(args.predictions)
        _fail_if_invalid(validate_predictions(predictions, args.predictions))
        benchmark_ids = {record["id"] for record in benchmark}
        unknown = sorted(
            record["id"] for record in predictions if record["id"] not in benchmark_ids
        )
        if unknown:
            raise BenchmarkValidationError(
                "Predictions contain unknown benchmark ids: " + ", ".join(unknown)
            )
        _write_metrics(score(benchmark, predictions))
        return 0
    except (OSError, BenchmarkValidationError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

