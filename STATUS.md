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

## Additional error-source research

Online source inspection on 24 September identified ASK-GEC as a practical source of authentic learner spelling examples and Sprakradet's 2026 appendix as expert-designed error/control material. See [source assessment and next experiment](docs/research/NORWEGIAN_ERROR_SOURCES_2026-09-24.md). No dataset was imported and no new accuracy claim follows from this research. Next data action: curate a local, reviewed spelling-only subset with separate learner/constructed provenance and untouched evaluation cases.

## ASK sample preparation — historical checkpoint (now completed below)

- Downloaded only the public ASK-GEC training split (7,716,969 bytes) and source card into ignored `data/local/ask-reviewed-20260924/`.
- Source revision: `9871205efddb575e77c4b49443ff75e28e25deae`; SHA-256: `51046c28cda51a91f0501ddcd2be91f2b98a553736b446a86246b0b48472ade9`.
- `tools/prepare_ask_spelling.py` finds 2,184 distinct isolated edit pairs among 36,404 training rows. This automated shortlist includes grammatical/lexical changes and is NOT a reviewed spelling benchmark.
- Local preparation metadata records the deterministic seed and mechanical edit categories. Validation/test source splits were not downloaded or inspected.
- `tools/audit_ask_spelling.py` scores precise target spans, pairs each accepted error with its corrected target, keeps reserved pairs unrun, checks exact historical sentence overlap, and saves raw traces only in ignored results. Other words in each sentence are not counted as false positives without adjudication.
- 25 tests pass. Pytest could not write its optional cache, which does not affect the passing tests.
- No reviewed sample or new spell-checker accuracy results yet. Automatic approval review rejected displaying full learner sentences and then a bulk list of isolated pairs in tool output. User permission to inspect public spelling pairs is pending. Until then, no labels are asserted as reviewed and no evaluation has been run.
- Next action: obtain that review permission, review spelling-only pairs while excluding context-dependent/grammatical edits, finalize approximately 100 evaluation pairs plus a separate reserve, and run the unchanged three baseline modes offline. Application defaults remain unchanged.


## ASK reviewed sample — completed

User permission to inspect public isolated pairs was granted. Reviewed 350 pairs, accepted 120, froze labels before inference, tested 100 paired error/control examples, and kept 20 pairs unrun. This is assistant pair review, not Norwegian-human or whole-sentence adjudication. Source text stays local.

All 600 offline checks passed. Dictionary / model ranking / default top-three scores: 92 / 95 / 95 out of 100; first-choice scores: 72 / 87 / 87. Each mode flagged 3 of 100 corrected targets. Default misses: three missing candidates and two unflagged dictionary-recognized targets. Top-five would add no model-mode successes. Defaults unchanged.

See [ASK evaluation report](docs/benchmarks/2026-09-24-ask-spelling.md) and aggregate JSON alongside it. Private traces: `results/ask-reviewed-20260924/`. Next: investigate candidate-generation failures, then separately verify the two detection misses in context before threshold changes. Keep the 20 reserved pairs untouched until development decisions are frozen.
