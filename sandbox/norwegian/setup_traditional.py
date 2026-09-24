"""Download once and index compact traditional Bokmal spell resources."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from engine import single
from setup_assets import digest
from traditional_resources import DATABASE, MANIFEST, RESOURCE_ROOT


SOURCES = {
    "scarrie-lex-lmf.zip": {
        "url": "https://www.nb.no/sbfil/leksikalske_databaser/leksikon/scarrie-lex-lmf.zip",
        "sha256": "5af2b1b28a2b6b392591f9d7ced33a71db16e12efb0b3c2e48f4a138b95056d7",
        "license": "CC BY 3.0",
    },
    "1gram_nob_f1_freq.zip": {
        "url": "https://www.nb.no/sbfil/tekst/1gram_nob_f1_freq.zip",
        "sha256": "cda1477a11fc98bcf61e8152fe1a09a4d5f9ae04b16c4ed9dc86ee224c2284e3",
        "license": "CC0",
    },
}
SCHEMA_VERSION = 2


def fetch(name: str, details: dict) -> Path:
    target = RESOURCE_ROOT / name
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) == details["sha256"]:
        print(f"Reusing {name}", flush=True)
        return target
    if target.exists():
        raise RuntimeError(f"Cached file failed its checksum: {target}. Remove only that file and retry.")
    partial = target.with_suffix(target.suffix + ".partial")
    print(f"Downloading {name}", flush=True)
    request = urllib.request.Request(details["url"], headers={"User-Agent": "Skrivi-POC/1"})
    with urllib.request.urlopen(request, timeout=90) as source, partial.open("wb") as output:
        while block := source.read(1024 * 1024):
            output.write(block)
    if digest(partial) != details["sha256"]:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded checksum did not match for {name}")
    partial.replace(target)
    return target


def scarrie_rows(archive: Path):
    with zipfile.ZipFile(archive) as bundle:
        with bundle.open("scarrie-lex-lmf.xml") as source:
            # Like the unigram file, this XML is distributed as ISO-8859-1 and
            # has no XML encoding declaration.
            text_source = io.TextIOWrapper(source, encoding="latin-1")
            for _, element in ET.iterparse(text_source, events=("end",)):
                if element.tag != "WordForm":
                    continue
                features = {
                    feature.get("att"): feature.get("val", "")
                    for feature in element.findall("feat")
                }
                typed = features.get("writtenForm", "").casefold().strip()
                replacement = features.get("replacement", "").casefold().strip()
                if (
                    typed
                    and replacement
                    and typed != replacement
                    and single(typed)
                    and single(replacement)
                ):
                    yield typed, replacement, features.get("corrStyle", "")
                element.clear()


def unigram_rows(archive: Path):
    with zipfile.ZipFile(archive) as bundle:
        with bundle.open("1gram_nob_f1_freq.frk") as raw:
            # The published file is ISO-8859-1, not UTF-8.
            for binary in raw:
                line = binary.decode("latin-1").strip()
                try:
                    count_text, word = line.split(maxsplit=1)
                    count = int(count_text)
                except (ValueError, TypeError):
                    continue
                word = word.casefold()
                if single(word):
                    yield word, count


def build_database(scarrie: Path, unigram: Path) -> dict:
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = DATABASE.with_suffix(".partial.sqlite3")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE scarrie_correction (
            typed TEXT NOT NULL,
            replacement TEXT NOT NULL,
            style TEXT NOT NULL,
            PRIMARY KEY (typed, replacement)
        ) WITHOUT ROWID;
        CREATE TABLE unigram (
            word TEXT PRIMARY KEY,
            count INTEGER NOT NULL
        ) WITHOUT ROWID;
        """
    )
    correction_count = 0
    batch = []
    for row in scarrie_rows(scarrie):
        batch.append(row)
        if len(batch) >= 5000:
            before = connection.total_changes
            connection.executemany("INSERT OR IGNORE INTO scarrie_correction VALUES (?, ?, ?)", batch)
            correction_count += connection.total_changes - before
            batch.clear()
    before = connection.total_changes
    connection.executemany("INSERT OR IGNORE INTO scarrie_correction VALUES (?, ?, ?)", batch)
    correction_count += connection.total_changes - before

    unigram_count = 0
    batch = []
    for row in unigram_rows(unigram):
        batch.append(row)
        if len(batch) >= 20000:
            connection.executemany(
                "INSERT INTO unigram VALUES (?, ?) "
                "ON CONFLICT(word) DO UPDATE SET count = MAX(count, excluded.count)",
                batch,
            )
            unigram_count += len(batch)
            batch.clear()
    connection.executemany(
        "INSERT INTO unigram VALUES (?, ?) "
        "ON CONFLICT(word) DO UPDATE SET count = MAX(count, excluded.count)",
        batch,
    )
    unigram_count += len(batch)
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    temporary.replace(DATABASE)
    return {"scarrie_corrections": correction_count, "unigram_rows_read": unigram_count}


def main():
    archives = {name: fetch(name, details) for name, details in SOURCES.items()}
    existing = None
    if MANIFEST.exists() and DATABASE.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_hashes = {name: digest(path) for name, path in archives.items()}
    if existing and existing.get("schema_version") == SCHEMA_VERSION and existing.get("source_hashes") == source_hashes:
        print(f"Reusing {DATABASE.name}", flush=True)
        return
    counts = build_database(archives["scarrie-lex-lmf.zip"], archives["1gram_nob_f1_freq.zip"])
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "database": str(DATABASE),
        "database_bytes": DATABASE.stat().st_size,
        "database_sha256": digest(DATABASE),
        "source_hashes": source_hashes,
        "sources": SOURCES,
        "counts": counts,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    print("Traditional Norwegian resources ready. Normal use is offline.", flush=True)


if __name__ == "__main__":
    main()
