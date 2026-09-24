"""Constrained one-word-to-two-word candidates from a pinned Bokmål corpus."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
RESOURCE = HERE / "split-benchmark" / "split-phrases.json"
OVERRIDES = HERE / "split-overrides.json"
SPLIT_THRESHOLD = 3.0


def rank_split_token(text: str, row: dict, model, resources,
                     threshold: float = SPLIT_THRESHOLD) -> dict | None:
    """Return one tightly-gated one-token-to-two-word review proposal."""
    word = row["word"]
    if not (word.islower() and word.isalpha()):
        return None
    candidates = [{"suggestion": match["phrase"], "comparison": word,
                   "retrieval": "observed_phrase_exact"}
                  for match in resources.exact(word)]
    if row.get("native_known") is False:
        candidates.extend({
            "suggestion": match["phrase"], "comparison": match["joined"],
            "retrieval": "observed_phrase_repaired",
        } for match in resources.repaired(word))
    override = resources.override(word)
    if override:
        candidates.append({
            "suggestion": override["suggestion"], "comparison": word,
            "retrieval": "authority_override", "source_url": override["source_url"],
        })
    candidates = list({
        (item["suggestion"], item["comparison"]): item for item in candidates
    }.values())
    if not candidates:
        return None

    from experimental_inference import fast_whole
    span = {"word": word, "start": row["start"], "end": row["end"]}
    ordinary = [candidate for candidate in row.get("candidates", [])
                if isinstance(candidate, str) and candidate.isalpha()]
    choices = list(dict.fromkeys([
        word, *(item["comparison"] for item in candidates),
        *(item["suggestion"] for item in candidates), *ordinary,
    ]))
    values, _ = fast_whole(model, text, span, choices)
    spelling_choices = list(dict.fromkeys([
        word,
        *(item["comparison"] for item in candidates
          if item["retrieval"] == "observed_phrase_repaired"),
        *ordinary,
    ]))
    best_spelling = max(spelling_choices, key=lambda candidate: values[candidate])
    ranked = []
    for item in candidates:
        if (item["retrieval"] == "observed_phrase_repaired"
                and item["comparison"] != best_spelling):
            continue
        comparison = (item["comparison"]
                      if item["retrieval"] == "authority_override"
                      else best_spelling)
        margin = values[item["suggestion"]] - values[comparison]
        ranked.append({**item, "comparison": comparison, "margin": margin})
    if not ranked:
        return None
    best = max(ranked, key=lambda item: item["margin"])
    if best["retrieval"] != "authority_override" and best["margin"] <= threshold:
        return None
    return {**best, "scores": sorted(values.items(), key=lambda item: item[1],
                                      reverse=True)}


class SplitResources:
    def __init__(self, resource: Path = RESOURCE, overrides: Path = OVERRIDES,
                 ordbank=None):
        payload = json.loads(Path(resource).read_text(encoding="utf-8"))
        self.rows = payload["phrases"]
        self.by_joined = {}
        for row in self.rows:
            self.by_joined.setdefault(row["joined"], []).append(row)
        self.joined = sorted(self.by_joined)
        self.overrides = json.loads(Path(overrides).read_text(encoding="utf-8"))
        if ordbank is None:
            from ordbank_resources import OrdbankResources
            ordbank = OrdbankResources()
        self.ordbank = ordbank

    def exact(self, word: str) -> list[dict]:
        return [dict(row) for row in self.by_joined.get(word.casefold(), [])]

    def repaired(self, word: str, max_distance: int = 3,
                 max_sound_distance: int = 2, limit: int = 24) -> list[dict]:
        if not hasattr(self.ordbank, "repair_splits"):
            return []
        matches = []
        for repair in self.ordbank.repair_splits(
                word, max_distance=max_distance,
                max_sound_distance=max_sound_distance, limit=100):
            for row in self.by_joined.get(repair["form"], []):
                if row["phrase"] == repair["split"]:
                    matches.append({**row, "distance": repair["distance"]})
        matches.sort(key=lambda row: (-row["total_count"], row["distance"], row["phrase"]))
        return matches[:limit]

    def override(self, word: str) -> dict | None:
        value = self.overrides.get(word.casefold())
        return dict(value) if value else None
