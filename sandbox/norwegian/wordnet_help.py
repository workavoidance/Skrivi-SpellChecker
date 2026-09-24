"""Build and query a small, local help index from Norsk ordvev.

The data provides semantic relations rather than learner-friendly definitions.
Skrivi therefore labels every result as a meaning clue and keeps curated help
ahead of these fallbacks in the UI.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
import io
import json
from pathlib import Path
import re
import sqlite3
import zipfile


DATASET_URL = "https://www.nb.no/sbfil/leksikalske_databaser/norsk_ordvev_nob_1.1.2.zip"
DATASET_SHA256 = "8e99f5bcc0e3c9cb805a4f3bedc0705dee7060b4568dca0a4e2df297c7b9356f"
DATASET_VERSION = "1.1.2"
DATASET_PAGE = "https://data.norge.no/en/datasets/f479d8ff-03aa-3af5-a8d5-03854a9ba190/norwegian-wordnet-bokmal"
INDEX_VERSION = 1
WORD_RE = re.compile(r"^[^\W\d_][\w -]*$", re.UNICODE)


@contextmanager
def _rows(source: Path, member: str):
    """Yield tab-separated rows from either an extracted tree or the ZIP."""
    if source.is_dir():
        path = source / "dat" / member
        with path.open("r", encoding="utf-8") as stream:
            yield (line.rstrip("\r\n").split("\t") for line in stream)
    else:
        with zipfile.ZipFile(source) as archive:
            matches = [name for name in archive.namelist()
                       if name == "dat/" + member or name.endswith("/dat/" + member)]
            if len(matches) != 1:
                raise RuntimeError(f"Norsk ordvev archive is missing dat/{member}.")
            with archive.open(matches[0]) as raw, io.TextIOWrapper(raw, encoding="utf-8") as stream:
                yield (line.rstrip("\r\n").split("\t") for line in stream)


def _usable_label(value: str | None) -> bool:
    if not value or len(value) > 48 or "�" in value or value[0].isupper():
        return False
    if len(value.split()) > 4 or not WORD_RE.fullmatch(value):
        return False
    return True


def _unique(values, original: str, limit=6):
    seen = {original.casefold()}
    result = []
    for value in values:
        if not _usable_label(value) or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        result.append(value)
        if len(result) == limit:
            break
    return result


def build_index(source: Path, target: Path) -> dict:
    """Create a compact SQLite index without extracting the source archive."""
    source, target = Path(source), Path(target)
    words = {}
    with _rows(source, "words.tab") as rows:
        for row in rows:
            if len(row) >= 3:
                words[row[0]] = (row[1], row[2])

    synset_words = defaultdict(list)
    word_synsets = defaultdict(list)
    with _rows(source, "wordsenses.tab") as rows:
        for row in rows:
            if len(row) < 3 or row[1] not in words:
                continue
            form, pos = words[row[1]]
            synset_words[row[2]].append(form)
            if _usable_label(form):
                word_synsets[(form.casefold(), pos)].append(row[2])

    relations = defaultdict(lambda: defaultdict(list))
    wanted = {"hyponymOf": "broader", "nearSynonymOf": "related",
              "xposNearSynonymOf": "related", "eqSynonymOf": "related"}
    with _rows(source, "relations.tab") as rows:
        for row in rows:
            if len(row) < 4 or row[1] not in wanted or row[3] not in synset_words:
                continue
            relations[row[0]][wanted[row[1]]].append(row[3])

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    partial.unlink(missing_ok=True)
    connection = sqlite3.connect(partial)
    try:
        connection.executescript("""
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE senses (
                lemma TEXT NOT NULL,
                pos TEXT NOT NULL,
                rank INTEGER NOT NULL,
                synonyms TEXT NOT NULL,
                broader TEXT NOT NULL,
                related TEXT NOT NULL,
                PRIMARY KEY (lemma, pos, rank)
            ) WITHOUT ROWID;
            CREATE INDEX senses_lemma ON senses(lemma);
        """)
        metadata = {
            "index_version": str(INDEX_VERSION), "dataset_version": DATASET_VERSION,
            "dataset_url": DATASET_PAGE, "license": "CC BY 4.0; source archive also includes the DanNet 1.0 notice",
        }
        connection.executemany("INSERT INTO metadata VALUES (?, ?)", metadata.items())
        inserted = 0
        for (lemma, pos), synsets in sorted(word_synsets.items()):
            seen_senses = set()
            rank = 0
            for synset in dict.fromkeys(synsets):
                synonyms = _unique(synset_words[synset], lemma)
                broader = _unique(
                    (word for target_synset in relations[synset]["broader"]
                     for word in synset_words[target_synset]), lemma
                )
                related = _unique(
                    (word for target_synset in relations[synset]["related"]
                     for word in synset_words[target_synset]), lemma
                )
                signature = (tuple(synonyms), tuple(broader), tuple(related))
                if not any(signature) or signature in seen_senses:
                    continue
                seen_senses.add(signature)
                connection.execute(
                    "INSERT INTO senses VALUES (?, ?, ?, ?, ?, ?)",
                    (lemma, pos, rank, json.dumps(synonyms, ensure_ascii=False),
                     json.dumps(broader, ensure_ascii=False), json.dumps(related, ensure_ascii=False)),
                )
                rank += 1
                inserted += 1
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()
    partial.replace(target)
    return {"entries": len(word_synsets), "senses": inserted, "bytes": target.stat().st_size}


def _lemma_candidates(word: str):
    word = word.casefold()
    yield word
    rules = [
        ("hetene", ("het",)), ("heter", ("het",)), ("ende", ("e", "")),
        ("ene", ("", "e")), ("ane", ("", "e")), ("ers", ("", "e")),
        ("er", ("", "e")), ("en", ("",)), ("et", ("",)),
        ("a", ("",)), ("e", ("",)), ("r", ("",)),
    ]
    seen = {word}
    for suffix, endings in rules:
        if len(word) <= len(suffix) + 2 or not word.endswith(suffix):
            continue
        stem = word[:-len(suffix)]
        for ending in endings:
            candidate = stem + ending
            if candidate not in seen:
                seen.add(candidate)
                yield candidate


class WordnetHelp:
    def __init__(self, database: Path | None):
        self.database = Path(database) if database else None
        self.available = bool(self.database and self.database.is_file())

    def lookup(self, word: str) -> dict | None:
        if not self.available or not isinstance(word, str) or len(word) > 80:
            return None
        connection = sqlite3.connect(self.database)
        try:
            connection.row_factory = sqlite3.Row
            for lemma in _lemma_candidates(word):
                rows = connection.execute(
                    "SELECT pos, rank, synonyms, broader, related FROM senses WHERE lemma=? ORDER BY pos, rank LIMIT 5",
                    (lemma,),
                ).fetchall()
                if rows:
                    return {
                        "word": word, "lemma": lemma, "source": "Norsk ordvev",
                        "source_url": DATASET_PAGE,
                        "senses": [{
                            "pos": row["pos"],
                            "synonyms": json.loads(row["synonyms"]),
                            "broader": json.loads(row["broader"]),
                            "related": json.loads(row["related"]),
                        } for row in rows],
                    }
        finally:
            connection.close()
        return None

    def lookup_many(self, words) -> dict:
        clean = []
        for word in words if isinstance(words, list) else []:
            if isinstance(word, str) and word not in clean and len(clean) < 60:
                clean.append(word)
        return {word: help_data for word in clean if (help_data := self.lookup(word))}
