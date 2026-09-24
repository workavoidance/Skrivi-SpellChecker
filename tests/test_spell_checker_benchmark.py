from __future__ import annotations

import pytest

from tools import spell_checker_benchmark as benchmark_tool


def item(**overrides):
    record = {
        "id": "case-1",
        "source": "synthetic",
        "source_record_id": None,
        "writer_group": "synthetic",
        "formal_dyslexia_diagnosis": None,
        "age_or_grade": None,
        "language_standard": "bokmal",
        "norwegian_first_language": None,
        "original_sentence": "Jeg jik hjem.",
        "original_token": "jik",
        "corrected_token": "gikk",
        "corrected_sentence": "Jeg gikk hjem.",
        "error_type": "phonological",
        "correction_kind": "replace",
        "contextual_real_word_error": False,
        "collection_method": "hand-authored regression case",
        "licence": "CC0-1.0",
        "redistributable": True,
        "notes": "",
    }
    record.update(overrides)
    return record


def test_validates_provenance_rules() -> None:
    record = item(
        writer_group="diagnosed_dyslexia",
        formal_dyslexia_diagnosis=None,
    )

    errors = benchmark_tool.validate_benchmark([record])

    assert any("require a confirmed diagnosis" in error for error in errors)


def test_rejects_missing_provenance_fields() -> None:
    record = item()
    del record["licence"]

    errors = benchmark_tool.validate_benchmark([record])

    assert any("missing required field licence" in error for error in errors)


def test_keeps_l2_data_separate() -> None:
    record = item(writer_group="norwegian_l2", norwegian_first_language=True)

    errors = benchmark_tool.validate_benchmark([record])

    assert any("norwegian_first_language=false" in error for error in errors)


def test_validates_keep_and_change_consistency() -> None:
    record = item(correction_kind="keep")

    errors = benchmark_tool.validate_benchmark([record])

    assert any("identical original and corrected" in error for error in errors)


def test_prediction_validation_rejects_more_than_five_candidates() -> None:
    predictions = [
        {
            "id": "case-1",
            "flagged": True,
            "suggestions": ["a", "b", "c", "d", "e", "f"],
        }
    ]

    errors = benchmark_tool.validate_predictions(predictions)

    assert any("at most 5" in error for error in errors)


def test_scores_detection_and_candidate_ranks_by_writer_group() -> None:
    records = [
        item(),
        item(
            id="case-2",
            original_sentence="Jeg gikk hjem.",
            original_token="gikk",
            corrected_token="gikk",
            corrected_sentence="Jeg gikk hjem.",
            error_type="none",
            correction_kind="keep",
        ),
    ]
    predictions = [
        {"id": "case-1", "flagged": True, "suggestions": ["gjekk", "gikk"]},
        {"id": "case-2", "flagged": False, "suggestions": []},
    ]

    result = benchmark_tool.score(records, predictions)

    assert result["all"] == {
        "total": 2,
        "changes": 1,
        "keeps": 1,
        "detection_precision": 1.0,
        "detection_recall": 1.0,
        "detection_f1": 1.0,
        "top1_recall": 0.0,
        "top3_recall": 1.0,
        "top5_recall": 1.0,
        "mean_reciprocal_rank_at_5": 0.5,
    }
    assert result["synthetic"] == result["all"]


def test_missing_prediction_counts_as_a_missed_error() -> None:
    result = benchmark_tool.score([item()], [])

    assert result["all"]["detection_recall"] == 0.0
    assert result["all"]["top3_recall"] == 0.0


@pytest.mark.parametrize("suggestion", ["", " "])
def test_prediction_suggestions_must_not_be_empty(suggestion: str) -> None:
    errors = benchmark_tool.validate_predictions(
        [{"id": "case-1", "flagged": True, "suggestions": [suggestion]}]
    )

    assert any("non-empty string" in error for error in errors)

