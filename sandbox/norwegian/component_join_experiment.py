"""Isolated trial: repair one misspelled component while joining two words."""
from __future__ import annotations

import json
from pathlib import Path

from engine import single
from experimental_inference import fast_whole
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
OUT = HERE / "component-join-experiment"
PRIVATE_ID = "natural-paragraph01"
MAX_COMPONENT_CHOICES = 12


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def component_choices(row: dict) -> list[str]:
    original = row["word"].casefold()
    candidates = [
        word.casefold() for word in row.get("native_suggestions", [])
        if single(word) and word.isalpha()
    ]
    return list(dict.fromkeys([original, *candidates]))[:MAX_COMPONENT_CHOICES + 1]


def generate(text: str, rows: list[dict], ordbank: OrdbankResources) -> list[dict]:
    """Return attested joins where only an unrecognised component is repaired."""
    proposals = []
    for index, (left, right) in enumerate(zip(rows, rows[1:])):
        gap = text[left["end"]:right["start"]]
        if not (gap and all(character in " \t" for character in gap)
                and left["word"].islower() and right["word"].islower()
                and left["word"].isalpha() and right["word"].isalpha()):
            continue
        left_unknown = left.get("native_known") is False
        right_unknown = right.get("native_known") is False
        if left_unknown == right_unknown:
            continue
        left_choices = component_choices(left) if left_unknown else [left["word"].casefold()]
        right_choices = component_choices(right) if right_unknown else [right["word"].casefold()]
        candidates = ordbank.compounds(left_choices, right_choices)
        typed_join = left["word"].casefold() + right["word"].casefold()
        candidates = [candidate for candidate in candidates if candidate != typed_join]
        alternatives = []
        for candidate in candidates:
            decompositions = ordbank.decompositions(candidate)
            spaced = [
                item["first"] + item["linking"] + " " + item["second"]
                for item in decompositions
                if item["first"] + item["linking"] in left_choices
                and item["second"] in right_choices
            ]
            if spaced:
                alternatives.append({"joined": candidate, "spaced": spaced[0],
                                     "retrieval": "nuspell_to_ordbank"})
        repair_side = "left" if left_unknown else "right"
        alternatives.extend({
            "joined": match["form"],
            "spaced": match["left"] + " " + match["right"],
            "retrieval": "ordbank_component_distance",
        } for match in ordbank.repair_compounds(
            left["word"], right["word"], repair_side
        ) if match["form"] != typed_join)
        alternatives = list({
            (item["joined"], item["spaced"]): item for item in alternatives
        }.values())
        if not alternatives:
            continue
        proposals.append({
            "index": index,
            "start": left["start"],
            "end": right["end"],
            "typed": text[left["start"]:right["end"]],
            "alternatives": alternatives,
            "repaired_side": "left" if left_unknown else "right",
        })
    return proposals


def rank(text: str, rows: list[dict], proposals: list[dict], model) -> list[dict]:
    ranked = []
    for proposal in proposals:
        left = rows[proposal["index"]]
        right = rows[proposal["index"] + 1]
        span = {**left, "word": proposal["typed"], "end": right["end"]}
        choices = list(dict.fromkeys([
            proposal["typed"],
            *(alternative["joined"] for alternative in proposal["alternatives"]),
            *(alternative["spaced"] for alternative in proposal["alternatives"]),
        ]))
        values, _ = fast_whole(model, text, span, choices)
        alternatives = sorted(
            ({
                **alternative,
                "repair_margin": values[alternative["joined"]] - values[proposal["typed"]],
                "boundary_margin": values[alternative["joined"]] - values[alternative["spaced"]],
            } for alternative in proposal["alternatives"]),
            key=lambda item: item["boundary_margin"], reverse=True,
        )
        ranked.append({**proposal, "best": alternatives[0]})
    return ranked


def main():
    OUT.mkdir(exist_ok=True)
    ordbank = OrdbankResources()
    from engine import Norbert
    model = Norbert()
    complete = {}
    for suite in ("development", "fresh"):
        source = read(HERE / "nuspell-experiments" / f"{suite}-nuspell_context.json")
        rows = []
        private_count = 0
        private_margins = []
        for run in source["runs"]:
            result = run.get("result")
            if not result:
                continue
            proposals = rank(result["text"], result["words"],
                             generate(result["text"], result["words"], ordbank), model)
            if run["case"] == PRIVATE_ID:
                private_count = len(proposals)
                private_margins = [proposal["best"]["boundary_margin"] for proposal in proposals]
                continue
            if proposals:
                rows.append({"id": run["case"], "proposals": proposals})
        report = {
            "suite": suite,
            "policy": {
                "component_choices": MAX_COMPONENT_CHOICES,
                "exactly_one_component_must_be_unknown_to_nuspell": True,
                "candidate_must_be_an_attested_ordbank_compound": True,
                "ordbank_component_distance": 1,
                "context_ranking_applied": True,
            },
            "cases_with_candidates": len(rows),
            "proposal_count": sum(len(row["proposals"]) for row in rows),
            "rows": rows,
            "private": {
                "case_present": any(run["case"] == PRIVATE_ID for run in source["runs"]),
                "proposal_count": private_count,
                "positive_margin_count": sum(margin > 0 for margin in private_margins),
                "margins": private_margins,
                "text_and_proposals_redacted": True,
            },
        }
        (OUT / f"{suite}-candidates.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        complete[suite] = {
            "cases_with_candidates": report["cases_with_candidates"],
            "proposal_count": report["proposal_count"],
            "private_proposal_count": private_count,
        }
    (OUT / "candidate-summary.json").write_text(
        json.dumps(complete, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(complete, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
