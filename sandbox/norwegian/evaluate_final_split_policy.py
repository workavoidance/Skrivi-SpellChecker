"""Evaluate the integrated split gate on source-backed positives and controls."""
from __future__ import annotations

import json
from pathlib import Path

from engine import GROUPS, Lexicon, Norbert, recase
from nuspell_backend import NativeNuspell
from split_resources import SplitResources, rank_split_token


HERE = Path(__file__).parent
ROOT = HERE / "split-benchmark"
OUT = ROOT / "final-policy-results.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ordinary_candidates(word: str, info: dict, lexicon: Lexicon) -> list[str]:
    if not info["known"]:
        return info["suggestions"][:24]
    lower = word.casefold()
    candidates = [recase(value, word) for group in GROUPS if lower in group
                  for value in group if value != lower]
    if word.islower() and word.isalpha() and len(word) >= 3:
        matches = lexicon.process.extract(
            word, lexicon.choices, scorer=lexicon.distance, score_cutoff=1, limit=64)
        doubled = [word[:position] + word[position] + word[position:]
                   for position in range(len(word))]
        candidates += [value for value in doubled if value in lexicon.vocab]
        candidates += [value for value, _, _ in matches
                       if value != word and value.isalpha()]
    return list(dict.fromkeys(candidates))[:24]


def main():
    cases = {split: read(ROOT / f"{split}.json")
             for split in ("development", "evaluation")}
    all_cases = [case for split in cases.values() for case in split]
    native, lexicon = NativeNuspell(), Lexicon(revised=True)
    lookup = native.lookup([case["target"]["typed"] for case in all_cases])
    model, resources = Norbert(), SplitResources()
    output, summary = {}, {}
    for split, suite in cases.items():
        rows = []
        for number, case in enumerate(suite, 1):
            target, word = case["target"], case["target"]["typed"]
            info = lookup[word]
            row = {"word": word, "start": target["start"], "end": target["end"],
                   "native_known": info["known"],
                   "candidates": ordinary_candidates(word, info, lexicon)}
            available = [item["phrase"] for item in resources.exact(word)]
            proposal = rank_split_token(case["text"], row, model, resources)
            correct = (target["action"] == "replace" and proposal is not None
                       and proposal["suggestion"] == target["answer"])
            cross_key = ("evaluation_count" if split == "development"
                         else "development_count")
            cross_observed = any(item["phrase"] == target["answer"]
                                 and item[cross_key] > 0
                                 for item in resources.exact(word))
            rows.append({
                "id": case["id"], "category": case["category"],
                "candidate_available": target["answer"] in available,
                "observed_in_opposite_corpus_split": cross_observed,
                "shown": proposal is not None,
                "correct": correct,
                "proposal": None if proposal is None else {
                    "suggestion": proposal["suggestion"],
                    "comparison": proposal["comparison"],
                    "retrieval": proposal["retrieval"],
                    "margin": proposal["margin"],
                },
            })
            if number % 20 == 0:
                print(f"{split} {number}/{len(suite)}", flush=True)
        positives = [row for row in rows if row["category"] == "joined_error"]
        negatives = [row for row in rows if row["category"] == "legitimate_compound"]
        summary[split] = {
            "positive_cases": len(positives),
            "candidate_available": sum(row["candidate_available"] for row in positives),
            "observed_in_opposite_corpus_split": sum(
                row["observed_in_opposite_corpus_split"] for row in positives),
            "correct_shown": sum(row["correct"] for row in positives),
            "missed": sum(not row["correct"] for row in positives),
            "negative_cases": len(negatives),
            "false_splits": sum(row["shown"] for row in negatives),
        }
        output[split] = rows
    OUT.write_text(json.dumps({"summary": summary, "rows": output},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "final-policy-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
