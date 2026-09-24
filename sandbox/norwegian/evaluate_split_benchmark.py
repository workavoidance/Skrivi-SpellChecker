"""Generate and rank exact one-word-to-two-word boundary candidates."""
from __future__ import annotations

import json
from pathlib import Path

from engine import Lexicon, Norbert
from experimental_inference import fast_whole
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
ROOT = HERE / "split-benchmark"
LOCK = ROOT / "policy-lock.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def recognised(word: str, lexicon: Lexicon, ordbank: OrdbankResources) -> bool:
    return word.casefold() in lexicon.vocab or bool(ordbank.lookup(word))


def split_candidates(word: str, lexicon: Lexicon, ordbank: OrdbankResources) -> list[str]:
    lower = word.casefold()
    if not (lower.isalpha() and lower.islower() and len(lower) >= 4):
        return []
    candidates = list(ordbank.splits(lower))
    for position in range(1, len(lower) - 1):
        left, right = lower[:position], lower[position:]
        if recognised(left, lexicon, ordbank) and recognised(right, lexicon, ordbank):
            candidates.append(left + " " + right)
    return list(dict.fromkeys(candidates))[:24]


def score_cases(split: str, model: Norbert, lexicon: Lexicon,
                ordbank: OrdbankResources) -> list[dict]:
    output = []
    for number, case in enumerate(read(ROOT / f"{split}.json"), 1):
        target = case["target"]
        candidates = split_candidates(target["typed"], lexicon, ordbank)
        span = {"word": target["typed"], "start": target["start"], "end": target["end"]}
        ranked = []
        if candidates:
            values, _ = fast_whole(model, case["text"], span,
                                   [target["typed"], *candidates])
            original = values[target["typed"]]
            ranked = sorted(
                ({"candidate": candidate, "margin": values[candidate] - original}
                 for candidate in candidates),
                key=lambda row: row["margin"], reverse=True,
            )
        output.append({
            "id": case["id"], "category": case["category"],
            "typed": target["typed"], "answer": target["answer"],
            "candidate_available": target["answer"] in candidates,
            "ranked": ranked,
        })
        if number % 20 == 0:
            print(f"{split} {number}/100", flush=True)
    return output


def metrics(rows: list[dict], threshold: float) -> dict:
    positives = [row for row in rows if row["category"] == "joined_error"]
    negatives = [row for row in rows if row["category"] == "legitimate_compound"]
    shown = [row for row in rows if row["ranked"] and
             row["ranked"][0]["margin"] > threshold]
    correct = [row for row in shown if row["category"] == "joined_error" and
               row["ranked"][0]["candidate"] == row["answer"]]
    return {
        "threshold": threshold, "positive_cases": len(positives),
        "candidate_available": sum(row["candidate_available"] for row in positives),
        "correct_top1": sum(bool(row["ranked"]) and
                            row["ranked"][0]["candidate"] == row["answer"]
                            for row in positives),
        "correct_shown": len(correct),
        "wrong_positive_splits": sum(row in shown and
                                     row["ranked"][0]["candidate"] != row["answer"]
                                     for row in positives),
        "negative_cases": len(negatives),
        "false_splits": sum(row in shown for row in negatives),
    }


def select_threshold(rows: list[dict]) -> tuple[float, list[dict]]:
    margins = sorted({item["margin"] for row in rows for item in row["ranked"]})
    trials = [metrics(rows, threshold) for threshold in [-100.0, *margins, 100.0]]
    eligible = [trial for trial in trials
                if trial["false_splits"] <= 2 and trial["wrong_positive_splits"] <= 2]
    chosen = max(eligible, key=lambda trial: (
        trial["correct_shown"], -trial["false_splits"],
        -trial["wrong_positive_splits"], trial["threshold"]
    ))
    return chosen["threshold"], trials


def main():
    model, lexicon, ordbank = Norbert(), Lexicon(revised=True), OrdbankResources()
    development = score_cases("development", model, lexicon, ordbank)
    threshold, trials = select_threshold(development)
    lock = {
        "threshold": threshold,
        "selection": "Maximise correct development splits with at most two false legitimate-compound splits and two wrong positive splits.",
        "development": metrics(development, threshold),
        "evaluation_not_used_for_selection": True,
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "development-results.json").write_text(json.dumps({
        "metrics": lock["development"], "rows": development,
        "threshold_trials": trials,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Policy locked before reserved evaluation", flush=True)
    evaluation = score_cases("evaluation", model, lexicon, ordbank)
    evaluation_metrics = metrics(evaluation, threshold)
    (ROOT / "evaluation-results.json").write_text(json.dumps({
        "metrics": evaluation_metrics, "rows": evaluation,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"development": lock["development"], "evaluation": evaluation_metrics}
    (ROOT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
