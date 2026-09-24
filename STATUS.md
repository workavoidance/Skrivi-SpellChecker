# Verified status — 2026-09-24

**The original Norwegian sandbox has been recovered.**

GitHub source of truth: https://github.com/workavoidance/Skrivi-SpellChecker

Application: sandbox/norwegian/. Launcher: sandbox/Start-Skrivi.cmd. Optional word help: sandbox/Start-Wordnet-Experiment.cmd. All further work should use this Git checkout.

## Recovery

116 source/notice files copied without algorithm changes. Hashes are in docs/RECOVERY-MANIFEST.json. Launcher wrappers were reconstructed from the original packaging script. The complete 543-file original is preserved in ignored data/local/recovered-original/, including historical datasets and results. Those files must not be published without data review. The source in Codex project storage was left untouched.

The historical release is Skrivi-Responsive-POC.zip. Recovered editable source includes later experimental modules; recovery does not imply every experiment is active or improves accuracy. The older English/Qwen prototype is preserved locally, not published here.

Recent dictionary downloads remain in the parent workspace's output/spell-checker-research directory. Models/runtime remain in the persistent user cache. No models or external datasets were downloaded during migration.

## Validation

- 16 evaluator/diagnostic tests passed during initial setup.
- 16 recovered sandbox tests passed with the cached Python runtime: engine contracts, Nuspell protocol, candidate handling, context scoring, personal dictionary and WordNet help.
- These are functional tests, not a new accuracy benchmark. Browser operation and fresh-machine setup have not yet been revalidated after migration.

## Next work

Run the app from this checkout and establish the unchanged baseline using reviewed local test data. Diagnose candidate absence, ranking/pruning failures and false alarms before changing algorithms. Keep raw writing local; publish suitable aggregates and reproducible methods.

Historical provenance: research merged through Skrivi-STT PR 53; evaluator copied from commit 1fc51e4e8d1350f78a820a748b98aa87346631a8 in open PR 54. Neither old PR was changed by this migration.
