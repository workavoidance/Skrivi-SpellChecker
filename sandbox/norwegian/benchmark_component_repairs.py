"""Source-backed benchmark for a typo inside a spaced Norwegian compound."""
from __future__ import annotations

import json
from pathlib import Path

from engine import Norbert, single
from experimental_inference import fast_whole
from nuspell_backend import NativeNuspell
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
OUT = HERE / "component-join-experiment"
THRESHOLD = -1.0
MAX_COMPONENT_CHOICES = 12
VOWELS = {"a": "e", "e": "i", "i": "o", "o": "u", "u": "y",
          "y": "i", "æ": "e", "ø": "o", "å": "a"}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(word: str, variant: int) -> tuple[str, str]:
    operations = ["deletion", "duplication", "transposition", "vowel_change"]
    for offset in range(len(operations)):
        operation = operations[(variant + offset) % len(operations)]
        middle = max(1, min(len(word) - 2, len(word) // 2))
        if operation == "deletion" and len(word) >= 4:
            changed = word[:middle] + word[middle + 1:]
        elif operation == "duplication" and len(word) >= 3:
            changed = word[:middle] + word[middle] + word[middle:]
        elif operation == "transposition" and len(word) >= 4 and word[middle] != word[middle + 1]:
            changed = word[:middle] + word[middle + 1] + word[middle] + word[middle + 2:]
        elif operation == "vowel_change":
            position = next((index for index, character in enumerate(word)
                             if character in VOWELS), None)
            changed = (word[:position] + VOWELS[word[position]] + word[position + 1:]
                       if position is not None else word)
        else:
            continue
        if changed != word:
            return changed, operation
    raise ValueError(f"No controlled mutation for {word!r}")


def build_case(case: dict, variant: int) -> dict:
    left, right = case["target"]["typed"].split(" ", 1)
    side = 0 if len(left) >= len(right) else 1
    component = (left, right)[side]
    typo, operation = mutate(component, variant)
    parts = [left, right]
    parts[side] = typo
    altered = " ".join(parts)
    start, old_end = case["target"]["start"], case["target"]["end"]
    text = case["text"][:start] + altered + case["text"][old_end:]
    return {
        "id": case["id"], "text": text, "start": start,
        "end": start + len(altered), "typed": altered,
        "corrected_spaced": case["target"]["typed"],
        "answer": case["target"]["answer"], "parts": parts,
        "correct_parts": [left, right], "mutated_side": side,
        "typo": typo, "correct_component": component, "operation": operation,
    }


def run_split(split: str, native: NativeNuspell, ordbank: OrdbankResources,
              model: Norbert) -> dict:
    source = [case for case in read(HERE / "compound-benchmark" / f"{split}.json")
              if case["category"] == "established_boundary"]
    cases = [build_case(case, index) for index, case in enumerate(source)]
    requested = [word for case in cases for word in case["parts"]]
    lookup = native.lookup(requested)
    rows = []
    for case in cases:
        side = case["mutated_side"]
        typo_info = lookup[case["typo"]]
        other_info = lookup[case["parts"][1 - side]]
        suggestions = [word.casefold() for word in typo_info["raw_suggestions"]
                       if single(word) and word.isalpha()][:MAX_COMPONENT_CHOICES]
        choices = list(dict.fromkeys([case["typo"], *suggestions]))
        left_choices = choices if side == 0 else [case["correct_parts"][0]]
        right_choices = choices if side == 1 else [case["correct_parts"][1]]
        compounds = ordbank.compounds(left_choices, right_choices)
        repair_side = "left" if side == 0 else "right"
        fuzzy = ordbank.repair_compounds(
            case["parts"][0], case["parts"][1], repair_side
        )
        fuzzy_forms = [match["form"] for match in fuzzy]
        available = (not typo_info["known"] and other_info["known"] and
                     case["answer"] in {*compounds, *fuzzy_forms})
        retrieval = (
            "nuspell_to_ordbank" if case["answer"] in compounds else
            "ordbank_component_distance" if case["answer"] in fuzzy_forms else None
        )
        margin = None
        shown = False
        if available:
            span = {"word": case["typed"], "start": case["start"], "end": case["end"]}
            values, _ = fast_whole(model, case["text"], span,
                                   [case["typed"], case["corrected_spaced"], case["answer"]])
            margin = values[case["answer"]] - values[case["corrected_spaced"]]
            shown = margin > THRESHOLD
        rows.append({
            "id": case["id"], "operation": case["operation"],
            "typed": case["typed"], "corrected_spaced": case["corrected_spaced"],
            "answer": case["answer"], "candidate_available": available,
            "retrieval": retrieval, "boundary_margin": margin, "shown": shown,
        })
    return {
        "split": split, "threshold": THRESHOLD, "cases": len(rows),
        "candidate_available": sum(row["candidate_available"] for row in rows),
        "shown": sum(row["shown"] for row in rows), "rows": rows,
    }


def main():
    OUT.mkdir(exist_ok=True)
    native, ordbank, model = NativeNuspell(), OrdbankResources(), Norbert()
    reports = {}
    for split in ("development", "evaluation"):
        report = run_split(split, native, ordbank, model)
        reports[split] = report
        (OUT / f"source-backed-{split}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    summary = {
        split: {key: report[key] for key in
                ("cases", "candidate_available", "shown", "threshold")}
        for split, report in reports.items()
    }
    (OUT / "source-backed-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
