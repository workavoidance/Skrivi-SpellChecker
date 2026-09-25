# Skrivi SpellChecker

An independent, Windows-first Norwegian spelling project: **write freely, check afterwards, choose your own corrections**.

## Current status

This repository now contains the **recovered runnable Norwegian Nuspell/NorBERT sandbox**, research and evaluation tools. Run **sandbox/Start-Skrivi.cmd** to reuse the existing cache. The recovered baseline has now been rerun locally; see [measured results and limitations](docs/benchmarks/2026-09-24-baseline.md). See [STATUS.md](STATUS.md) for the verified inventory and next work.

The intended baseline combines traditional Norwegian candidate generation with a small local contextual model. Definitions and examples should help the writer distinguish suggestions. Corrections must preserve wording and meaning, with no silent sentence rewriting.

## Layout

- `sandbox/`: recovered application and experiment source; see sandbox/README.md.
- `tools/`: benchmark scoring, candidate-stage diagnostics and dictionary inspection.
- `tests/`: tests of evaluation logic, not evidence of spelling accuracy.
- `docs/research/`: dataset, spell-checker architecture and dictionary research.
- `docs/BENCHMARK_FORMAT.md`: existing provenance-aware benchmark contract.

## Run the evaluation tools

Python 3.10+ is required. The tools use the standard library. Tests additionally need pytest:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/spell_checker_benchmark.py validate data/local/benchmark.jsonl
python tools/spell_checker_benchmark.py score data/local/benchmark.jsonl data/local/predictions.jsonl
python tools/candidate_audit.py data/local/traces.jsonl results/audit.json
```

Create the local input/output folders as needed. Private datasets are not bundled. Recovered sandbox tests require its cached runtime; evaluator tests use the environment described above.

## Local data and privacy

Keep private writing, dataset downloads and results in the ignored `data/` and `results/` folders. Never commit pupil text or derived records without explicit redistribution permission. Model weights belong in a persistent user cache outside the app, location `%LOCALAPPDATA%\Skrivi\models`; the recovered app reuses this cache.

For dictionary inspection, place the official Bokmål export at `data/local/dictionary/bokmaal-articles.json.gz` and run `python tools/inspect_dictionary.py`. It creates structural metrics and a reduced-size prototype in the same ignored directory; this is not a production importer. The script does not download anything.

## Origins and licensing

Research and benchmark tooling were carried over from [Skrivi-STT](https://github.com/workavoidance/Skrivi-STT). Benchmark source was copied from commit `1fc51e4e8d1350f78a820a748b98aa87346631a8` (PR 54); the original pull request is not merged. This repository does not alter that PR or the speech apps.

Project code retains the [MIT licence](LICENSE). External dictionaries, models and datasets retain their own licences and are not included here. The inspected dictionary extract is experimental and must not be treated as a cleared release package.


## Offline dictionary-help experiment

Run `sandbox/Start-Dictionary-Experiment.cmd` after building the index once. This is a separate experiment; the normal launcher and spelling/ranking logic are unchanged. Dictionary definitions and examples are shown beside suggestions, with other meanings expandable. Existing Windows speech can read the displayed help. Examples may be phrases, and the displayed sense is not selected automatically from the user's sentence.

One-time import, using already downloaded files (no network access):

```powershell
python tools/import_bokmaal.py --source "C:\path\bokmaal-articles.json.gz" --concepts "C:\path\bokmaal-concepts.json"
```

The original export is linked from https://ord.uib.no/ord_1_Ordlister.html; the small expansion table is https://ord.uib.no/bm/concepts.json. On this development PC both are in `C:\Users\jon\Documents\Skrivi\Research\Dictionary-Exploration`.

The generated database lives at `%LOCALAPPDATA%\Skrivi\lexical\bokmaal\dictionary.sqlite3` (or under `SKRIVI_CACHE_DIR`). It is reused across app updates. Re-run the importer to replace it atomically; close the experiment first. Delete that specific database to remove the installed dictionary. No source datasets or generated dictionaries are committed to GitHub.

Local testing proceeds under the user's acceptance of the official open-use wording. The exact licence document and editorial status meanings remain unresolved; the index retains source hashes, attribution and that qualification. See `docs/research/bokmaal-importer.md`. This does not assert that the dictionary is cleared for a general public release.
