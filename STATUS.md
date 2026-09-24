# Verified project status

Updated: 2026-09-24.

Validation at repository setup: 16 evaluator/diagnostic tests passed. These verify accounting and validation only; they do not measure spelling accuracy.

This is the dedicated home for future spell-checker work. Each experiment should record its source revision, inputs, settings, results, and whether it changed the default.

| Component | Verified location/status |
|---|---|
| Dataset research | `docs/research/NORWEGIAN_DYSLEXIA_DATASET_RESEARCH.md`; originally merged through Skrivi-STT PR 53 |
| Architecture research | `docs/research/modern-norwegian-spell-checkers.md` |
| Dictionary inspection | `docs/research/bokmaal-inspection.md`, `tools/inspect_dictionary.py`; original downloads remain outside this repository |
| Existing evaluator | `tools/spell_checker_benchmark.py`; copied from unmerged Skrivi-STT PR 54 |
| Candidate-stage diagnostic scorer | `tools/candidate_audit.py`; tested with artificial traces, no sandbox adapter yet |
| Earlier runnable sandbox | Not located; no code recovered here |
| Wider Norwegian test suite | Not recovered here |
| Current model/dictionary versions and baseline | Not measured or verified in this repository |

## Next experiment

Recover the actual sandbox and test suite before claiming to benchmark the existing system. Inventory model/dictionary versions, candidate limits and scoring settings. Run the unchanged baseline locally. Then classify failures into candidate absence, ranking/pruning failure, detection/display suppression and false alarms. Choose generator versus ranker experiments based on those results.

The old repository name workavoidance/Skrivi now resolves to workavoidance/Skrivi-STT. Research is in [merged PR 53](https://github.com/workavoidance/Skrivi-STT/pull/53); evaluation tooling remains in [open PR 54](https://github.com/workavoidance/Skrivi-STT/pull/54). Neither establishes that the prior runnable app was committed.

## Candidate trace contract

One JSONL row per labelled target: `id`, explicit boolean `is_error` and `flagged`, `acceptable` reviewed answer list, `generated` complete candidate pool before context ranking, `ranked` ordered pool after ranking, and `displayed` actual visible suggestions (at most three). Optional `writer_group` and `error_type` retain stratification.

Capture all candidate sources. Ranked candidates must come from the captured pool. Do not feed gold answers to the checker. Check exported IDs against the frozen benchmark; the standalone scorer cannot detect omitted benchmark targets. Include correct tokens to measure false alarms; targeted-error tests alone cannot establish whole-text detection quality. Preserve ambiguity as multiple acceptable answers and keep unresolved cases out of scored claims.

Reports distinguish conditional ranking accuracy from end-to-end displayed-answer recovery. Keep private traces local. No new large models or external inference are required for this diagnostic step.
