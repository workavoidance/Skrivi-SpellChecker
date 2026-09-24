"""Small, offline Norwegian lexical resources used by isolated experiments.

The source archives and derived SQLite index live in Skrivi's persistent user
cache.  Normal checking never downloads data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sqlite3

from setup_assets import ROOT


RESOURCE_VERSION = "traditional-v1"
RESOURCE_ROOT = ROOT / "lexical" / RESOURCE_VERSION
DATABASE = RESOURCE_ROOT / "traditional.sqlite3"
MANIFEST = RESOURCE_ROOT / "manifest.json"


class TraditionalResources:
    def __init__(self, database: Path = DATABASE):
        if not database.exists():
            raise RuntimeError("Run Setup-Traditional.cmd once to enable this experiment.")
        self.database = database
        self.connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)

    def close(self):
        self.connection.close()

    def corrections(self, word: str, limit: int = 16) -> list[str]:
        rows = self.connection.execute(
            "SELECT replacement FROM scarrie_correction "
            "WHERE typed = ? ORDER BY replacement LIMIT ?",
            (word.casefold(), limit),
        )
        return [row[0] for row in rows]

    def frequencies(self, candidates) -> dict[str, int]:
        unique = list(dict.fromkeys(candidate.casefold() for candidate in candidates))
        if not unique:
            return {}
        result = {candidate: 0 for candidate in unique}
        # Candidate sets are deliberately small, but stay below SQLite's
        # parameter limit if this helper is reused for a larger diagnostic.
        for offset in range(0, len(unique), 500):
            batch = unique[offset : offset + 500]
            marks = ",".join("?" for _ in batch)
            rows = self.connection.execute(
                f"SELECT word, count FROM unigram WHERE word IN ({marks})", batch
            )
            result.update({word: count for word, count in rows})
        return result

    def adjusted_scores(self, scores: dict[str, float], weight: float) -> dict[str, float]:
        frequencies = self.frequencies(scores)
        return {
            word: score + weight * math.log10(1 + frequencies[word.casefold()])
            for word, score in scores.items()
        }

    def metadata(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

