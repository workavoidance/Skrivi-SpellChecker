"""Small JSON bridge around the unmodified OBT multitagger source."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import warnings


def clean_result(word: str, result: dict, mtag, base_roots: frozenset[str]) -> dict:
    suffix = result["etterledd"].lstrip("-")
    linking = "s" if result.get("fuge-s") else ""
    boundary = len(word) - len(suffix) - len(linking)
    prefix = word[:max(0, boundary)]
    # analyserForledd memoizes recursively inferred roots in rootHash. Use the
    # immutable import-time key set so a speculative analysis cannot validate
    # itself as a known component.
    prefix_direct = prefix in mtag.fullformHash or prefix in base_roots
    suffix_direct = suffix in mtag.fullformHash or suffix in base_roots
    return {
        "prefix": prefix,
        "linking": linking,
        "suffix": suffix,
        "suffix_pos": result.get("etterleddOrdklasse"),
        "members": result.get("numLedd"),
        "first_is_compound": bool(result.get("forledd-samset")),
        "prefix_direct": prefix_direct,
        "suffix_direct": suffix_direct,
        "trusted": prefix_direct and suffix_direct,
    }


def unique(rows: list[dict]) -> list[dict]:
    found = []
    seen = set()
    for row in rows:
        key = (row["prefix"], row["linking"], row["suffix"], row["suffix_pos"])
        if key not in seen:
            found.append(row)
            seen.add(key)
    return found


def main() -> None:
    source_dir = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(source_dir))
    # mtag parses command-line arguments at import time. Hide bridge arguments.
    sys.argv = ["obt_worker"]
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    import mtag  # type: ignore

    requested = json.loads(sys.stdin.read())
    base_roots = frozenset(key for key, value in mtag.rootHash.items() if value)
    output = {}
    for raw in requested:
        word = str(raw).casefold()
        lexical = mtag.databaseSearch(word)
        strict_raw = mtag.analyserForleddOgEtterledd(word, False)
        fallback_raw = mtag.analyserBareEtterledd(word, False) if not strict_raw else []
        output[word] = {
            "lexical": bool(lexical),
            "lexical_compound": "samset-leks" in lexical,
            "strict": unique([clean_result(word, row, mtag, base_roots) for row in strict_raw]),
            "fallback": unique([clean_result(word, row, mtag, base_roots) for row in fallback_raw]),
        }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
