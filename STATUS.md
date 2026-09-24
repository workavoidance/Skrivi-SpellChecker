# Verified status — 2026-09-24

**The original Norwegian sandbox has been recovered.**

GitHub source of truth: https://github.com/workavoidance/Skrivi-SpellChecker

Application: sandbox/norwegian/. Launcher: sandbox/Start-Skrivi.cmd. Optional word help: sandbox/Start-Wordnet-Experiment.cmd. All further work should use this Git checkout.

## Recovery

116 source/notice files copied without algorithm changes. Hashes are in docs/RECOVERY-MANIFEST.json. Launcher wrappers were reconstructed from the original packaging script. The complete 543-file original is preserved in ignored data/local/recovered-original/, including historical datasets and results. Those files must not be published without data review. The source in Codex project storage was left untouched.

The historical release is Skrivi-Responsive-POC.zip. Recovered editable source includes later experimental modules; recovery does not imply every experiment is active or improves accuracy. The older English/Qwen prototype is preserved locally, not published here.

Recent dictionary downloads are in the local Documents/Skrivi/Research/Dictionary-Exploration folder after the OneDrive migration. Models/runtime remain in the persistent user cache. No models or external datasets were downloaded during migration.

## Validation

- 16 evaluator/diagnostic tests passed during initial setup.
- 16 recovered sandbox tests passed with the cached Python runtime: engine contracts, Nuspell protocol, candidate handling, context scoring, personal dictionary and WordNet help.
- These are functional tests, not a new accuracy benchmark. The relocated sandbox served its page successfully during migration; fresh-machine setup has not been revalidated.

## Next work

The unchanged baseline was rerun on 24 September: 387 cases, 277 scored targets, three modes, 1,161 successful checks. See [the measured report](docs/benchmarks/2026-09-24-baseline.md) and [experiment log](docs/EXPERIMENT_LOG.md). Default top-three counts are 87/105 development, 70/72 previously used fresh, and 100/100 source-restoration targets. These are reused exploratory sets, not independent accuracy claims.

Next scoring experiment: inspect the 15 default detection misses using the private traces, and build separate paired correct/incorrect tests before changing keep/change thresholds. Separately improve actual definition/example coverage; only 16/1,068 displayed default suggestions have curated help, with optional WordNet increasing any-hint coverage to 412/1,068. Keep raw writing local. Do not change defaults based only on reused cases.

## Current audit verification

- Application source and defaults unchanged; cached Nuspell and NorBERT3 Small used offline.
- 20 evaluation/audit tests pass (including four stage/coverage checks).
- Six old development/fresh mode score summaries reproduced exactly.
- Raw results: ignored `results/baseline-20260924/`, checkpointed after each case. Corpus/code hashes and aggregate metrics are in `docs/benchmarks/2026-09-24-summary.json`.
- Personal remembered-word overrides bypassed for reproducible scoring; user settings untouched. No new models, audio or cloud inference.
- Larger models, split/join behaviour, human-rated word-help usefulness and independent evaluation remain untested in this run.

Historical provenance: research merged through Skrivi-STT PR 53; evaluator copied from commit 1fc51e4e8d1350f78a820a748b98aa87346631a8 in open PR 54. Neither old PR was changed by this migration.
