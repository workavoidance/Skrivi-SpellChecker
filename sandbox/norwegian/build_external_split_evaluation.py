"""Freeze a source-disjoint split/context and collision-control benchmark."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from split_resources import SplitResources


HERE = Path(__file__).parent
ROOT = HERE / "external-split-evaluation"
SOURCE = ROOT / "source" / "no_bokmaal-ud-train.conllu"
REVISION = "396d11f0c2bd290a2a2711015c04ac25bc3dcc06"
WORD = re.compile(r"^[A-Za-zÆØÅæøå]+$")
LIMIT = 80


def records():
    for block in SOURCE.read_text(encoding="utf-8").strip().split("\n\n"):
        sent_id = text = None
        forms = []
        for line in block.splitlines():
            if line.startswith("# sent_id = "):
                sent_id = line.removeprefix("# sent_id = ")
            elif line.startswith("# text = "):
                text = line.removeprefix("# text = ")
            elif line and not line.startswith("#"):
                columns = line.split("\t")
                if columns[0].isdigit():
                    forms.append((int(columns[0]), columns[1]))
        if not sent_id or not text:
            continue
        aligned, cursor = [], 0
        for token_id, form in forms:
            start = text.find(form, cursor)
            if start < 0:
                aligned = []
                break
            aligned.append({"id": token_id, "word": form,
                            "start": start, "end": start + len(form)})
            cursor = start + len(form)
        if aligned:
            yield {"sent_id": sent_id, "text": text, "tokens": aligned}


def stable_key(value: str) -> str:
    return hashlib.sha256(("skrivi-external-split-v1|" + value).encode()).hexdigest()


def source(record: dict) -> dict:
    return {
        "corpus": "UD Norwegian-Bokmaal / Norwegian Dependency Treebank",
        "revision": REVISION,
        "file": "no_bokmaal-ud-train.conllu",
        "sent_id": record["sent_id"],
        "source_url": ("https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal/"
                       f"blob/{REVISION}/no_bokmaal-ud-train.conllu"),
        "license": "CC BY-SA 4.0",
        "original_text": record["text"],
    }


def main():
    resources = SplitResources()
    positives, controls, all_controls = [], [], []
    occurrence_total = occurrence_covered = 0
    unique_phrases, covered_phrases = set(), set()
    seen_positive, seen_control = set(), set()
    for record in records():
        tokens = record["tokens"]
        for left, right in zip(tokens, tokens[1:]):
            if (right["id"] != left["id"] + 1
                    or record["text"][left["end"]:right["start"]] != " "
                    or not WORD.fullmatch(left["word"])
                    or not WORD.fullmatch(right["word"])
                    or not left["word"].islower() or not right["word"].islower()):
                continue
            phrase = (left["word"] + " " + right["word"]).casefold()
            joined = phrase.replace(" ", "")
            if len(joined) < 4 or len(joined) > 32:
                continue
            occurrence_total += 1
            unique_phrases.add(phrase)
            available = {row["phrase"] for row in resources.exact(joined)}
            if phrase not in available:
                continue
            occurrence_covered += 1
            covered_phrases.add(phrase)
            if phrase in seen_positive:
                continue
            seen_positive.add(phrase)
            changed = (record["text"][:left["start"]] + joined
                       + record["text"][right["end"]:])
            positives.append({
                "id": f"train-split-{record['sent_id']}-{left['id']}",
                "category": "joined_error", "text": changed,
                "target": {"start": left["start"],
                           "end": left["start"] + len(joined),
                           "typed": joined, "answer": phrase, "action": "replace"},
                "source": source(record),
                "mutation": {"operation": "remove_phrase_space",
                             "original": phrase, "injected": joined},
            })
        for token in tokens:
            word = token["word"].casefold()
            if (not WORD.fullmatch(token["word"]) or not token["word"].islower()
                    or len(word) < 4 or not resources.exact(word)):
                continue
            item = {
                "id": f"train-control-{record['sent_id']}-{token['id']}",
                "category": "legitimate_token", "text": record["text"],
                "target": {"start": token["start"], "end": token["end"],
                           "typed": token["word"], "answer": token["word"],
                           "action": "keep",
                           "tempting_splits": [row["phrase"]
                                               for row in resources.exact(word)]},
                "source": source(record),
            }
            all_controls.append(item)
            if word not in seen_control:
                seen_control.add(word)
                controls.append(item)
    positives.sort(key=lambda row: stable_key(row["id"]))
    controls.sort(key=lambda row: stable_key(row["id"]))
    all_controls.sort(key=lambda row: stable_key(row["id"]))
    cases = [*positives[:LIMIT], *controls[:LIMIT]]
    diagnostic_ids = {row["id"] for row in cases}
    reserved_controls = [row for row in all_controls if row["id"] not in diagnostic_ids]
    reserved = [*positives[LIMIT:2 * LIMIT], *reserved_controls[:LIMIT]]
    if len(positives) < 2 * LIMIT or len(reserved_controls) < LIMIT:
        raise RuntimeError(f"Insufficient cases: {len(positives)} positives, "
                           f"{len(reserved_controls)} reserved controls")
    payload = json.dumps(cases, ensure_ascii=False, indent=2).encode("utf-8")
    reserved_payload = json.dumps(reserved, ensure_ascii=False, indent=2).encode("utf-8")
    (ROOT / "cases.json").write_bytes(payload)
    (ROOT / "reserved-cases.json").write_bytes(reserved_payload)
    manifest = {
        "title": "Skrivi source-disjoint split evaluation v1",
        "frozen_before_scoring": True,
        "selection": ("Stable SHA-256 order; diagnostic targets use unique phrases/tokens; "
                      "reserved positives use new phrases and controls use different sentence occurrences."),
        "source_revision": REVISION,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "cases_sha256": hashlib.sha256(payload).hexdigest(),
        "reserved_cases_sha256": hashlib.sha256(reserved_payload).hexdigest(),
        "license": "Source and derived cases: CC BY-SA 4.0",
        "counts": {"diagnostic_joined_errors": LIMIT,
                   "diagnostic_legitimate_tokens": LIMIT,
                   "reserved_joined_errors": LIMIT,
                   "reserved_legitimate_tokens": LIMIT},
        "coverage": {
            "eligible_train_pair_occurrences": occurrence_total,
            "covered_pair_occurrences": occurrence_covered,
            "eligible_unique_phrases": len(unique_phrases),
            "covered_unique_phrases": len(covered_phrases),
            "conditional_note": "Positive accuracy is conditional on phrase-resource coverage.",
        },
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
