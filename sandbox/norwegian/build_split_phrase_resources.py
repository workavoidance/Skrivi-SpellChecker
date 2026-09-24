"""Build a compact adjacent-word index from the pinned UD Bokmål corpus."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re


HERE = Path(__file__).parent
SOURCE = HERE / "corpus-source"
OUT = HERE / "split-benchmark" / "split-phrases.json"
WORD = re.compile(r"^[A-Za-zÆØÅæøå]+$")
FILES = {
    "development": SOURCE / "no_bokmaal-ud-dev.conllu",
    "evaluation": SOURCE / "no_bokmaal-ud-test.conllu",
}


def phrases(path: Path) -> Counter:
    counts = Counter()
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        tokens = []
        for line in block.splitlines():
            if not line or line.startswith("#"):
                continue
            columns = line.split("\t")
            if columns[0].isdigit() and WORD.fullmatch(columns[1]):
                tokens.append((int(columns[0]), columns[1].casefold()))
        for (left_id, left), (right_id, right) in zip(tokens, tokens[1:]):
            if right_id == left_id + 1 and len(left + right) >= 4:
                counts[left + " " + right] += 1
    return counts


def main():
    by_split = {split: phrases(path) for split, path in FILES.items()}
    all_phrases = sorted(set().union(*(counts for counts in by_split.values())))
    rows = [{
        "phrase": phrase,
        "joined": phrase.replace(" ", ""),
        "development_count": by_split["development"][phrase],
        "evaluation_count": by_split["evaluation"][phrase],
        "total_count": sum(counts[phrase] for counts in by_split.values()),
    } for phrase in all_phrases]
    payload = {
        "source": "UD Norwegian-Bokmaal / Norwegian Dependency Treebank",
        "revision": (SOURCE / "revision.txt").read_text(encoding="utf-8-sig").strip(),
        "license": "CC BY-SA 4.0",
        "private_writing_included": False,
        "candidate_gate": "Exact two-word phrase observed in the pinned corpus",
        "phrases": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(json.dumps({"phrases": len(rows), "bytes": OUT.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
