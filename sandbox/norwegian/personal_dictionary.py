"""A tiny local-only allow-list for words the writer wants Skrivi to remember."""
from __future__ import annotations

import json
from pathlib import Path
import threading

from engine import single
from setup_assets import ROOT


DEFAULT_PATH = ROOT / "personal" / "bokmal-keep.json"


class PersonalDictionary:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self.lock = threading.Lock()
        self.words = self._read()

    def _read(self) -> set[str]:
        if not self.path.exists():
            return set()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("words"), list):
            raise RuntimeError("The local remembered-word file is invalid.")
        return {word.casefold() for word in data["words"] if single(word)}

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".partial.json")
        temporary.write_text(
            json.dumps({"version": 1, "words": sorted(self.words)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def add(self, word: str) -> int:
        if not single(word):
            raise ValueError("Only one ordinary word can be remembered at a time.")
        with self.lock:
            self.words.add(word.casefold())
            self._write()
            return len(self.words)

    def clear(self) -> int:
        with self.lock:
            removed = len(self.words)
            self.words.clear()
            self._write()
            return removed

    def apply(self, result: dict) -> dict:
        for token in result.get("words", []):
            if token.get("word", "").casefold() in self.words:
                token["status"] = "OK"
                token["suggestions"] = []
                token["reason"] = "Dette ordet er husket på denne PC-en."
                token["remembered"] = True
        return result

