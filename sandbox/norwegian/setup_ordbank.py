"""One-time download and compact indexing of Norsk Ordbank Bokmal 2005."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import tarfile
import urllib.request

from engine import single
from setup_assets import digest
from ordbank_resources import DATABASE, MANIFEST, RESOURCE_ROOT


ARCHIVE_NAME = "20220201_norsk_ordbank_nob_2005.tar.gz"
URL = "https://www.nb.no/sbfil/leksikalske_databaser/ordbank/20220201_norsk_ordbank_nob_2005.tar.gz"
SHA256 = "57d91cb3f17b85befa50a3b56fcaed9800ca665b39486fe97b668add914d5f60"
SCHEMA_VERSION = 2


def fetch():
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    target = RESOURCE_ROOT / ARCHIVE_NAME
    if target.exists() and digest(target) == SHA256:
        print(f"Reusing {ARCHIVE_NAME}", flush=True)
        return target
    if target.exists():
        raise RuntimeError(f"Cached archive failed its checksum: {target}. Remove only that file and retry.")
    partial = target.with_suffix(target.suffix + ".partial")
    request = urllib.request.Request(URL, headers={"User-Agent": "Skrivi-POC/1"})
    print(f"Downloading {ARCHIVE_NAME}", flush=True)
    with urllib.request.urlopen(request, timeout=90) as source, partial.open("wb") as output:
        while block := source.read(1024 * 1024):
            output.write(block)
    if digest(partial) != SHA256:
        partial.unlink(missing_ok=True)
        raise RuntimeError("Downloaded Ordbank checksum did not match.")
    partial.replace(target)
    return target


def rows(bundle: tarfile.TarFile, name: str):
    source = bundle.extractfile(name)
    if source is None:
        raise RuntimeError(f"Ordbank archive is missing {name}")
    # The 2022 dump is ISO-8859-1.
    with io.TextIOWrapper(source, encoding="latin-1", newline="") as text:
        yield from csv.DictReader(text, delimiter="\t")


def build(archive):
    temporary = DATABASE.with_suffix(".partial.sqlite3")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE form (
            word TEXT PRIMARY KEY,
            display TEXT NOT NULL,
            proper INTEGER NOT NULL,
            tag TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE compound (
            form TEXT NOT NULL,
            first TEXT NOT NULL,
            fugue TEXT NOT NULL,
            second TEXT NOT NULL,
            PRIMARY KEY (form, first, fugue, second)
        ) WITHOUT ROWID;
        CREATE INDEX compound_parts ON compound(first, second);
        """
    )
    form_rows = compound_rows = 0
    with tarfile.open(archive, "r:gz") as bundle:
        batch = []
        for row in rows(bundle, "fullformsliste.txt"):
            display = row["OPPSLAG"].strip()
            word = display.casefold()
            tag = row["TAG"].strip()
            if row["NORMERING"].casefold() != "normert" or not single(word):
                continue
            proper = int(" prop " in f" {tag.casefold()} ")
            batch.append((word, display, proper, tag))
            if len(batch) >= 10000:
                connection.executemany(
                    "INSERT INTO form VALUES (?, ?, ?, ?) ON CONFLICT(word) DO UPDATE SET "
                    "display = CASE WHEN excluded.proper > proper THEN excluded.display ELSE display END, "
                    "proper = MAX(proper, excluded.proper)", batch
                )
                form_rows += len(batch); batch.clear()
        connection.executemany(
            "INSERT INTO form VALUES (?, ?, ?, ?) ON CONFLICT(word) DO UPDATE SET "
            "display = CASE WHEN excluded.proper > proper THEN excluded.display ELSE display END, "
            "proper = MAX(proper, excluded.proper)", batch
        )
        form_rows += len(batch)

        batch = []
        for row in rows(bundle, "leddanalyse.txt"):
            form = row["OPPSLAG"].casefold().strip()
            first = row["FORLEDD"].casefold().strip().strip("-")
            second = row["ETTERLEDD"].casefold().strip().strip("-")
            fugue = row["FUGE"].casefold().strip()
            if row["LEDDMARKERT_BOB"].casefold() != "ok":
                continue
            if not all(single(value) for value in (form, first, second)):
                continue
            batch.append((form, first, fugue, second))
            if len(batch) >= 10000:
                connection.executemany("INSERT OR IGNORE INTO compound VALUES (?, ?, ?, ?)", batch)
                compound_rows += len(batch); batch.clear()
        connection.executemany("INSERT OR IGNORE INTO compound VALUES (?, ?, ?, ?)", batch)
        compound_rows += len(batch)
    connection.commit()
    unique_forms = connection.execute("SELECT COUNT(*) FROM form").fetchone()[0]
    unique_compounds = connection.execute("SELECT COUNT(*) FROM compound").fetchone()[0]
    connection.execute("VACUUM")
    connection.close()
    temporary.replace(DATABASE)
    return {
        "form_rows_read": form_rows,
        "unique_forms": unique_forms,
        "compound_rows_read": compound_rows,
        "unique_compound_analyses": unique_compounds,
    }


def main():
    archive = fetch()
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() and DATABASE.exists() else {}
    if existing.get("schema_version") == SCHEMA_VERSION and existing.get("archive_sha256") == SHA256:
        print(f"Reusing {DATABASE.name}", flush=True)
        return
    counts = build(archive)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source": URL,
        "license": "CC BY 4.0",
        "archive_sha256": SHA256,
        "archive_bytes": archive.stat().st_size,
        "database_bytes": DATABASE.stat().st_size,
        "database_sha256": digest(DATABASE),
        "counts": counts,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    print("Norsk Ordbank index ready. Normal use is offline.", flush=True)


if __name__ == "__main__":
    main()
