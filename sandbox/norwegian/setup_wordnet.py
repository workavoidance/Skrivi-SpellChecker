"""One-time, persistent-cache setup for the Norwegian WordNet experiment."""

from pathlib import Path

from setup_assets import ROOT, fetch
from wordnet_help import build_index, DATASET_SHA256, DATASET_URL, DATASET_VERSION


def main():
    folder = ROOT / "lexical" / ("norsk-ordvev-" + DATASET_VERSION)
    archive = folder / "norsk-ordvev.zip"
    database = folder / "wordnet-help.sqlite3"
    fetch(DATASET_URL, archive, DATASET_SHA256)
    if not database.exists():
        print("Building compact local meaning index …", flush=True)
        stats = build_index(archive, database)
        print(f"Indexed {stats['senses']:,} useful senses ({stats['bytes'] / 1_000_000:.1f} MB).", flush=True)
    else:
        print("Reusing compact local meaning index.", flush=True)
    print("Norsk ordvev help is ready. Normal launches are offline.", flush=True)


if __name__ == "__main__":
    main()

