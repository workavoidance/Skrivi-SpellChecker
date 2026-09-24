"""Offline access to a compact index derived from Norsk Ordbank."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from setup_assets import ROOT


RESOURCE_ROOT = ROOT / "lexical" / "ordbank-20220201"
DATABASE = RESOURCE_ROOT / "ordbank.sqlite3"
MANIFEST = RESOURCE_ROOT / "manifest.json"


class OrdbankResources:
    def __init__(self, database: Path = DATABASE):
        if not database.exists():
            raise RuntimeError("Run Setup-Ordbank.cmd once to enable this experiment.")
        self.database = database
        self.connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)

    def close(self):
        self.connection.close()

    def lookup(self, word: str) -> dict | None:
        row = self.connection.execute(
            "SELECT display, proper, tag FROM form WHERE word = ?", (word.casefold(),)
        ).fetchone()
        return {"display": row[0], "proper": bool(row[1]), "tag": row[2]} if row else None

    def all_forms(self) -> list[str]:
        return [row[0] for row in self.connection.execute("SELECT word FROM form ORDER BY word")]

    def display(self, word: str) -> str:
        row = self.connection.execute("SELECT display FROM form WHERE word = ?", (word.casefold(),)).fetchone()
        return row[0] if row else word

    def compounds(self, first_words, second_words) -> list[str]:
        first = list(dict.fromkeys(word.casefold().strip("-") for word in first_words))
        second = list(dict.fromkeys(word.casefold().strip("-") for word in second_words))
        if not first or not second:
            return []
        first_marks = ",".join("?" for _ in first)
        second_marks = ",".join("?" for _ in second)
        rows = self.connection.execute(
            f"SELECT DISTINCT form FROM compound WHERE first IN ({first_marks}) "
            f"AND second IN ({second_marks}) ORDER BY form",
            [*first, *second],
        )
        return [row[0] for row in rows]

    def splits(self, word: str) -> list[str]:
        rows = self.connection.execute(
            "SELECT first, second FROM compound WHERE form = ? ORDER BY first, second",
            (word.casefold(),),
        )
        return list(dict.fromkeys(f"{first} {second}" for first, second in rows))

    def decompositions(self, word: str) -> list[dict[str, str]]:
        """Return the recorded compound boundary, including any linking letters."""
        rows = self.connection.execute(
            "SELECT first, fugue, second FROM compound "
            "WHERE form = ? ORDER BY first, fugue, second",
            (word.casefold(),),
        )
        return [
            {"first": first, "linking": linking or "", "second": second}
            for first, linking, second in rows
        ]

    def repair_compounds(self, left: str, right: str, repair_side: str,
                         max_distance: int = 1, limit: int = 24) -> list[dict]:
        """Find nearby recorded components while holding the other side exact."""
        from rapidfuzz.distance import OSA

        left, right = left.casefold(), right.casefold()
        if repair_side == "left":
            rows = self.connection.execute(
                "SELECT DISTINCT form, first, fugue, second FROM compound WHERE second = ?",
                (right,),
            )
            typed = left
        elif repair_side == "right":
            rows = self.connection.execute(
                "SELECT DISTINCT form, first, fugue, second FROM compound "
                "WHERE first || COALESCE(fugue, '') = ?",
                (left,),
            )
            typed = right
        else:
            raise ValueError("repair_side must be 'left' or 'right'")
        matches = []
        for form, first, linking, second in rows:
            corrected_left = first + (linking or "")
            corrected = corrected_left if repair_side == "left" else second
            distance = OSA.distance(typed, corrected)
            if 0 < distance <= max_distance:
                matches.append({
                    "form": form, "left": corrected_left, "right": second,
                    "distance": distance,
                })
        matches.sort(key=lambda item: (item["distance"], item["form"]))
        return matches[:limit]

    def repair_splits(self, word: str, max_distance: int = 3,
                      max_sound_distance: int = 2, limit: int = 24) -> list[dict]:
        """Find nearby Ordbank forms that have a recorded two-part split."""
        from rapidfuzz import process
        from rapidfuzz.distance import OSA

        if not hasattr(self, "_split_forms"):
            rows = self.connection.execute(
                "SELECT DISTINCT form, first, fugue, second FROM compound ORDER BY form"
            )
            self._split_map = {}
            for form, first, linking, second in rows:
                self._split_map.setdefault(form, []).append(
                    first + (linking or "") + " " + second
                )
            self._split_forms = sorted(self._split_map)
        typed = word.casefold()
        sound = str.maketrans({"å": "o", "æ": "e", "ø": "o"})
        typed_sound = typed.translate(sound)
        raw = process.extract(
            typed, self._split_forms, scorer=OSA.distance,
            score_cutoff=max_distance, limit=100,
        )
        matches = []
        for form, distance, _ in raw:
            if (not form or form == typed or form[0] != typed[0]
                    or form[-1] != typed[-1]
                    or OSA.distance(typed_sound, form.translate(sound)) > max_sound_distance):
                continue
            for split in self._split_map[form]:
                matches.append({"form": form, "split": split, "distance": distance})
        matches.sort(key=lambda item: (item["distance"], item["form"], item["split"]))
        return matches[:limit]

    def metadata(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
