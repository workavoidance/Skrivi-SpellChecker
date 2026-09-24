"""Build a reproducible Bokmål compound benchmark from official UD splits.

The source sentences are naturally occurring corpus text.  Errors are synthetic
and exactly reversible.  No model score is used to decide the correct answer.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import random
import re

from engine import words
from nuspell_backend import NativeNuspell
from obt_resources import ObtResources
from ordbank_resources import OrdbankResources


HERE = Path(__file__).parent
SOURCE = HERE / "corpus-source"
OUTPUT = HERE / "compound-benchmark"
SEED = 20260907
REVISION = (SOURCE / "revision.txt").read_text(encoding="utf-8-sig").strip()
FILES = {
    "development": SOURCE / "no_bokmaal-ud-dev.conllu",
    "evaluation": SOURCE / "no_bokmaal-ud-test.conllu",
}
QUOTAS = {
    "established_boundary": 30,
    "obt_boundary_probe": 30,
    "clean_separate_phrase": 40,
    "compound_internal_typo": 25,
    "proper_name_control": 15,
}
HEAD_POS = {"subst", "adj"}
WORD_RE = re.compile(r"^[A-Za-zÆØÅæøå]+$")


def read_conllu(path: Path) -> list[dict]:
    rows = []
    raw = path.read_text(encoding="utf-8")
    for block in raw.strip().split("\n\n"):
        metadata = {}
        annotations = []
        for line in block.splitlines():
            if line.startswith("# ") and " = " in line:
                key, value = line[2:].split(" = ", 1)
                metadata[key] = value
            elif line and not line.startswith("#"):
                columns = line.split("\t")
                if columns[0].isdigit():
                    annotations.append({
                        "id": int(columns[0]), "form": columns[1], "lemma": columns[2],
                        "upos": columns[3], "xpos": columns[4], "feats": columns[5],
                        "head": int(columns[6]) if columns[6].isdigit() else 0,
                        "deprel": columns[7],
                    })
        text = metadata.get("text", "")
        engine_tokens = words(text)
        lexical_annotations = [a for a in annotations if WORD_RE.fullmatch(a["form"])]
        lexical_tokens = [t for t in engine_tokens if WORD_RE.fullmatch(t["word"])]
        aligned = len(lexical_annotations) == len(lexical_tokens) and all(
            a["form"].casefold() == t["word"].casefold()
            for a, t in zip(lexical_annotations, lexical_tokens)
        )
        if (aligned and 7 <= len(engine_tokens) <= 30 and text.endswith((".", "!", "?"))
                and "Typo=Yes" not in block):
            for annotation, token in zip(lexical_annotations, lexical_tokens):
                annotation["token"] = token
            rows.append({"meta": metadata, "annotations": lexical_annotations,
                         "tokens": engine_tokens, "text": text})
    return rows


def source_info(path: Path, record: dict) -> dict:
    text = record["text"]
    return {
        "corpus": "UD Norwegian-Bokmaal / Norwegian Dependency Treebank",
        "revision": REVISION,
        "file": path.name,
        "sent_id": record["meta"]["sent_id"],
        "source_url": (
            "https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal/blob/"
            f"{REVISION}/{path.name}"
        ),
        "license": "CC BY-SA 4.0",
        "original_text": text,
        "original_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def replace_span(text: str, start: int, end: int, replacement: str) -> str:
    assert text[start:end]
    return text[:start] + replacement + text[end:]


def safe_obt_rows(info: dict) -> list[dict]:
    return [row for row in info.get("strict", [])
            if row["trusted"] and row["suffix_pos"] in HEAD_POS]


def nominal_component(ordbank: OrdbankResources, word: str) -> bool:
    info = ordbank.lookup(word)
    return bool(info and "subst" in info["tag"])


def nuspell_batched(nuspell: NativeNuspell, values, batch_size: int = 400) -> dict:
    unique = list(dict.fromkeys(values))
    result = {}
    for offset in range(0, len(unique), batch_size):
        result.update(nuspell.lookup(unique[offset:offset + batch_size]))
    return result


def case(split: str, category: str, number: int, text: str, start: int, end: int,
         typed: str, answer: str, source: dict, evidence: dict,
         mutation: dict | None = None) -> dict:
    value = {
        "id": f"{split}-{category}-{number:03d}",
        "split": split,
        "category": category,
        "text": text,
        "target": {
            "start": start, "end": end, "typed": typed, "answer": answer,
            "action": "keep" if typed == answer else "replace",
        },
        "source": source,
        "evidence": evidence,
    }
    if mutation:
        value["mutation"] = mutation
    return value


def mutate_component(word: str, component_start: int, component_end: int,
                     operation: str, rng: random.Random) -> tuple[str, dict] | None:
    if component_end - component_start < 4:
        return None
    positions = list(range(component_start + 1, component_end - 1))
    rng.shuffle(positions)
    vowels = "aeiouyæøå"
    for position in positions:
        if operation == "delete_letter":
            changed = word[:position] + word[position + 1:]
        elif operation == "duplicate_letter":
            changed = word[:position] + word[position] + word[position:]
        elif operation == "transpose_letters":
            if position + 1 >= component_end or word[position] == word[position + 1]:
                continue
            changed = word[:position] + word[position + 1] + word[position] + word[position + 2:]
        else:
            replacements = [letter for letter in vowels if letter != word[position]]
            changed = word[:position] + rng.choice(replacements) + word[position + 1:]
        if changed != word and WORD_RE.fullmatch(changed):
            return changed, {"operation": operation, "position": position,
                             "original_character": word[position]}
    return None


def build_split(split: str, path: Path, ordbank: OrdbankResources,
                obt: ObtResources, nuspell: NativeNuspell) -> list[dict]:
    rng = random.Random(f"{SEED}:{split}")
    records = read_conllu(path)
    rng.shuffle(records)
    all_word_forms = list(dict.fromkeys(
        annotation["form"].casefold() for record in records
        for annotation in record["annotations"]
        if annotation["form"].islower() and len(annotation["form"]) >= 6
    ))
    all_joined = list(dict.fromkeys(
        (left["form"] + right["form"]).casefold()
        for record in records
        for left, right in zip(record["annotations"], record["annotations"][1:])
        if left["token"]["end"] + 1 == right["token"]["start"]
        and left["form"].islower() and right["form"].islower()
        and len(left["form"]) >= 2 and len(right["form"]) >= 3
    ))
    obt_analysis = obt.analyse([*all_word_forms, *all_joined])
    used_sentences = set()
    selected: list[dict] = []

    def add(value: dict) -> None:
        selected.append(value)
        used_sentences.add(value["source"]["sent_id"])

    # Recorded lexical compounds. Linking letters stay on the first typed part.
    count = 0
    established_pool = []
    for record in records:
        for annotation in record["annotations"]:
            original = annotation["form"]
            if (not original.islower() or not WORD_RE.fullmatch(original)
                    or annotation["upos"] != "NOUN"):
                continue
            for decomposition in ordbank.decompositions(original):
                left = decomposition["first"] + decomposition["linking"]
                right = decomposition["second"]
                if (len(left) >= 3 and len(right) >= 3 and left + right == original.casefold()
                        and nominal_component(ordbank, decomposition["first"])
                        and nominal_component(ordbank, decomposition["second"])):
                    established_pool.append((record, annotation, decomposition, left, right))
                    break
    rng.shuffle(established_pool)
    for record, annotation, decomposition, left, right in established_pool:
        if record["meta"]["sent_id"] in used_sentences:
            continue
        token = annotation["token"]
        typed = f"{left} {right}"
        altered = replace_span(record["text"], token["start"], token["end"], typed)
        add(case(split, "established_boundary", count + 1, altered, token["start"],
                 token["start"] + len(typed), typed, token["word"], source_info(path, record),
                 {"authority": "Norsk Ordbank", "decomposition": decomposition},
                 {"operation": "insert_compound_space", "original": token["word"],
                  "injected": typed}))
        count += 1
        if count == QUOTAS["established_boundary"]:
            break

    # OBT boundary probes. The source word is the exact restoration target, but
    # these are not labelled as certified linguistic compounds: even conservative
    # OBT can find accidental decompositions in ordinary inflected words.
    count = 0
    productive_raw = []
    for record in records:
        for annotation in record["annotations"]:
            original = annotation["form"]
            if (not original.islower() or annotation["upos"] != "NOUN"
                    or len(original) < 7 or ordbank.decompositions(original)):
                continue
            for row in safe_obt_rows(obt_analysis.get(original.casefold(), {})):
                left = row["prefix"] + row["linking"]
                right = row["suffix"]
                if (row["suffix_pos"] == "subst" and len(left) >= 3 and len(right) >= 3
                        and left + right == original.casefold()
                        and nominal_component(ordbank, row["prefix"])
                        and nominal_component(ordbank, row["suffix"])):
                    productive_raw.append((record, annotation, row, left, right))
                    break
    component_lookup = nuspell_batched(nuspell, (
        component for _, _, row, _, _ in productive_raw
        for component in (row["prefix"], row["suffix"])
    ))
    productive_pool = [item for item in productive_raw
                       if component_lookup[item[2]["prefix"]]["known"]
                       and component_lookup[item[2]["suffix"]]["known"]]
    rng.shuffle(productive_pool)
    for record, annotation, row, left, right in productive_pool:
        if record["meta"]["sent_id"] in used_sentences:
            continue
        token = annotation["token"]
        typed = f"{left} {right}"
        altered = replace_span(record["text"], token["start"], token["end"], typed)
        add(case(split, "obt_boundary_probe", count + 1, altered, token["start"],
                 token["start"] + len(typed), typed, token["word"], source_info(path, record),
                 {"authority": "OBT conservative component analysis", "analysis": row,
                  "ordbank_entry": False},
                 {"operation": "insert_compound_space", "original": token["word"],
                  "injected": typed}))
        count += 1
        if count == QUOTAS["obt_boundary_probe"]:
            break

    # Real, syntactically connected phrases that a surface-only analyser can
    # mistake for compounds. These are the main false-join controls.
    count = 0
    clean_pool = []
    for record in records:
        annotations = record["annotations"]
        for left, right in zip(annotations, annotations[1:]):
            if left["token"]["end"] + 1 != right["token"]["start"]:
                continue
            if not left["form"].islower() or not right["form"].islower():
                continue
            joined = (left["form"] + right["form"]).casefold()
            relation = (
                (left["head"] == right["id"] and left["deprel"] in {"amod", "det", "nmod", "advmod"})
                or (right["head"] == left["id"] and right["deprel"] in {"obj", "obl", "advmod", "xcomp"})
            )
            if relation and safe_obt_rows(obt_analysis.get(joined, {})):
                clean_pool.append((record, left, right, joined))
    rng.shuffle(clean_pool)
    for record, left, right, joined in clean_pool:
        if record["meta"]["sent_id"] in used_sentences:
            continue
        start, end = left["token"]["start"], right["token"]["end"]
        typed = record["text"][start:end]
        add(case(split, "clean_separate_phrase", count + 1, record["text"], start, end,
                 typed, typed, source_info(path, record),
                 {"authority": "UD source text and dependency annotation",
                  "joined_form_accepted_by_obt": joined,
                  "left": {k: left[k] for k in ("form", "upos", "head", "deprel")},
                  "right": {k: right[k] for k in ("form", "upos", "head", "deprel")}}))
        count += 1
        if count == QUOTAS["clean_separate_phrase"]:
            break

    # One controlled character error inside a source-attested compound.
    count = 0
    operations = ["delete_letter", "duplicate_letter", "transpose_letters", "substitute_vowel"]
    internal_pool = []
    for record, annotation, decomposition, left, right in established_pool:
        original = annotation["form"]
        boundary = len(left)
        internal_pool.append((record, annotation, {"authority": "Norsk Ordbank",
                              "decomposition": decomposition}, boundary))
    rng.shuffle(internal_pool)
    typo_pool = []
    for index, (record, annotation, evidence, boundary) in enumerate(internal_pool):
        if record["meta"]["sent_id"] in used_sentences:
            continue
        original = annotation["form"]
        operation = operations[index % len(operations)]
        component = (0, boundary) if boundary >= 4 else (boundary, len(original))
        result = mutate_component(original, *component, operation, rng)
        if not result:
            continue
        changed, mutation = result
        if ordbank.lookup(changed):
            continue
        typo_pool.append((record, annotation, evidence, changed, mutation))
        if len(typo_pool) >= 250:
            break
    typo_lookup = nuspell_batched(nuspell, (row[3] for row in typo_pool))
    for record, annotation, evidence, changed, mutation in typo_pool:
        if record["meta"]["sent_id"] in used_sentences or typo_lookup[changed]["known"]:
            continue
        token = annotation["token"]
        altered = replace_span(record["text"], token["start"], token["end"], changed)
        add(case(split, "compound_internal_typo", count + 1, altered, token["start"],
                 token["start"] + len(changed), changed, token["word"], source_info(path, record),
                 evidence, {**mutation, "original": token["word"], "injected": changed,
                            "inside_compound": True}))
        count += 1
        if count == QUOTAS["compound_internal_typo"]:
            break

    # Correct source-attested proper names, preferring names unknown to Nuspell.
    count = 0
    name_rows = []
    for record in records:
        for annotation in record["annotations"]:
            word = annotation["form"]
            if annotation["upos"] == "PROPN" and WORD_RE.fullmatch(word) and len(word) >= 3:
                name_rows.append((record, annotation))
    rng.shuffle(name_rows)
    # A modest batch is enough to find fifteen controls and avoids checking the
    # treebank's entire proper-name vocabulary during every reproducible build.
    name_rows = name_rows[:400]
    name_lookup = nuspell_batched(nuspell, (
        annotation["form"] for _, annotation in name_rows
    ))
    names = [(name_lookup[annotation["form"]]["known"], record, annotation)
             for record, annotation in name_rows]
    names.sort(key=lambda row: row[0])
    for known, record, annotation in names:
        if record["meta"]["sent_id"] in used_sentences:
            continue
        token = annotation["token"]
        add(case(split, "proper_name_control", count + 1, record["text"], token["start"],
                 token["end"], token["word"], token["word"], source_info(path, record),
                 {"authority": "UD UPOS=PROPN annotation", "nuspell_known": known}))
        count += 1
        if count == QUOTAS["proper_name_control"]:
            break

    counts = {category: sum(row["category"] == category for row in selected) for category in QUOTAS}
    if counts != QUOTAS:
        raise RuntimeError(f"Could not fill {split} quotas: {counts}")
    return selected


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ordbank, obt, nuspell = OrdbankResources(), ObtResources(), NativeNuspell()
    outputs = {}
    try:
        for split, path in FILES.items():
            outputs[split] = build_split(split, path, ordbank, obt, nuspell)
            (OUTPUT / f"{split}.json").write_text(
                json.dumps(outputs[split], ensure_ascii=False, indent=2), encoding="utf-8"
            )
    finally:
        ordbank.close()
    manifest = {
        "title": "Skrivi Bokmål compound benchmark v1",
        "seed": SEED,
        "corpus_revision": REVISION,
        "splits": {},
        "quotas_per_split": QUOTAS,
        "selection_note": (
            "Official UD development and test files remain separate. Positive boundaries require "
            "Ordbank evidence. OBT probes test exact source restoration without claiming a certified "
            "compound analysis. Clean phrases require source and dependency evidence."
        ),
        "limitations": [
            "The source is edited corpus text, not a certified error-free gold standard.",
            "Injected errors are synthetic and are not claimed to represent dyslexia prevalence.",
            "Clean phrase cases should receive a small native-speaker ambiguity review before publication.",
        ],
        "license": "Derived from UD Norwegian-Bokmaal, CC BY-SA 4.0.",
    }
    for split, path in FILES.items():
        output_path = OUTPUT / f"{split}.json"
        manifest["splits"][split] = {
            "source_file": path.name,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "cases": len(outputs[split]),
            "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUTPUT / "review.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "split", "id", "category", "source_sentence", "typed", "answer",
            "review_status", "review_note",
        ])
        writer.writeheader()
        for split in FILES:
            for row in outputs[split]:
                writer.writerow({
                    "split": split, "id": row["id"], "category": row["category"],
                    "source_sentence": row["source"]["original_text"],
                    "typed": row["target"]["typed"], "answer": row["target"]["answer"],
                    "review_status": "unreviewed", "review_note": "",
                })
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
