"""Build source-backed joined-error and legitimate-compound split cases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).parent
SOURCE = HERE / "compound-benchmark"
OUT = HERE / "split-benchmark"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def replace(text: str, start: int, end: int, value: str) -> str:
    return text[:start] + value + text[end:]


def build(split: str) -> list[dict]:
    source = read(SOURCE / f"{split}.json")
    rows = []
    positive = [case for case in source if case["category"] == "clean_separate_phrase"]
    negative = [case for case in source if case["category"] in
                {"established_boundary", "obt_boundary_probe"}]
    for number, case in enumerate(positive, 1):
        target = case["target"]
        joined = target["typed"].replace(" ", "")
        text = replace(case["text"], target["start"], target["end"], joined)
        rows.append({
            "id": f"{split}-joined_error-{number:03d}", "split": split,
            "category": "joined_error", "text": text,
            "target": {"start": target["start"], "end": target["start"] + len(joined),
                       "typed": joined, "answer": target["typed"], "action": "replace"},
            "source": case["source"],
            "mutation": {"operation": "remove_phrase_space",
                         "original": target["typed"], "injected": joined},
            "evidence": case["evidence"],
        })
    for number, case in enumerate(negative, 1):
        answer = case["target"]["answer"]
        start = case["target"]["start"]
        text = case["source"]["original_text"]
        assert text[start:start + len(answer)].casefold() == answer.casefold()
        rows.append({
            "id": f"{split}-legitimate_compound-{number:03d}", "split": split,
            "category": "legitimate_compound", "text": text,
            "target": {"start": start, "end": start + len(answer),
                       "typed": answer, "answer": answer, "action": "keep",
                       "tempting_split": case["target"]["typed"]},
            "source": case["source"],
            "evidence": case["evidence"],
        })
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    manifest = {
        "title": "Skrivi exact split benchmark v1",
        "derived_from": "compound-benchmark",
        "positive_definition": "A space from a source-attested phrase is removed.",
        "negative_definition": "A source-attested compound remains unchanged.",
        "private_writing_included": False,
        "license": "Derived from UD Norwegian-Bokmaal, CC BY-SA 4.0.",
        "splits": {},
    }
    for split in ("development", "evaluation"):
        rows = build(split)
        payload = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
        (OUT / f"{split}.json").write_bytes(payload)
        manifest["splits"][split] = {
            "cases": len(rows),
            "joined_errors": sum(row["category"] == "joined_error" for row in rows),
            "legitimate_compounds": sum(row["category"] == "legitimate_compound" for row in rows),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["splits"], indent=2))


if __name__ == "__main__":
    main()
