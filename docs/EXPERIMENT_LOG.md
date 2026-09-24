# Spell-checker experiment log

## 2026-09-24 — recovered default baseline

Question: where are errors lost between dictionary detection, candidate generation, ranking, UI display and word help?

Protocol: unchanged application; Nuspell, Nuspell + ranking, and Nuspell + context with cached NorBERT3 Small. Three frozen local suites, 387 cases and 277 scored targets; raw text remains local. CPU, one pass, checkpoint after each case; no tuning or repeated timing runs. About 14 minutes of evaluation wall time. Input and code hashes recorded.

Result: 1,161 checks completed without failures. The hybrid wins all three groups; the major remaining labelled failure stage is detection (15 targets), while four targets lack the intended candidate. Actual definitions/examples cover 1.5% of displayed suggestions; optional WordNet raises any-hint coverage to 38.6%, not definition coverage. Five choices would add only two scored corrections across these suites under the same detection policy.

Decision: retain current defaults and the small model. Next investigate keep/change decisions with separate paired cases; separately integrate richer lexical explanations with verified distribution rights. Human review of non-target flags and help usefulness remains necessary. Do not interpret the synthetic source-restoration 100/100 as general accuracy.

[Full aggregate report](benchmarks/2026-09-24-baseline.md). Private traces: `results/baseline-20260924/`. Functional validation: 20 tests pass. No application algorithm or threshold changes.

## 2026-09-24 — ASK source preparation (not a benchmark result)

Prepared offline candidate selection and target/control evaluation tools. The public training split contains 36,404 rows; the deterministic isolated-edit filter yields 2,184 unique pairs. This is a provisional review queue, not verified spelling truth. Source hash and revision are in STATUS.md and ignored local preparation metadata. Five additional tests cover exact edit isolation, target offsets, target-only controls, paired reservation and mechanical error categorization; all 25 tests pass.

The review stage is pending user permission after automatic approval review blocked exposing corpus sentences and a bulk error-pair list. No model predictions were run and no application changes were made. Full source data remains in ignored data/local/ask-reviewed-20260924/. Source validation/test splits remain untouched. The intended reviewed subset will preserve original sentence context locally but will not claim whole-sentence correctness based only on pair review.


## 2026-09-24 — ASK evaluation completed after public-pair review permission

Reviewed 350 isolated pairs; accepted 120 before scoring. Tested 100 pairs (error plus corrected-target control), reserved 20 pairs without inference. Fresh sample has no exact sentence overlap with historical sets, but is spelling-selected L2 writing and may overlap upstream model training. Full sentences were not independently adjudicated.

600 checks completed without failures. Top-three dictionary/ranking/default: 92/95/95 of 100. Top-one: 72/87/87. Corrected-target warnings: 3/3/3 of 100. Default remaining failures are three missing candidates and two detection misses; same-policy five options add zero successes. Engine hashes unchanged from the recovered baseline. Keep current defaults; focus next on candidate coverage and separate contextual adjudication, not a bigger suggestion list. Twenty-five tests pass.

[Full report](benchmarks/2026-09-24-ask-spelling.md). Raw data/traces and review decisions remain ignored and local. Aggregate-only exporter rejects incomplete runs, changed sample hashes and any scored reserved cases.


## 2026-09-24 — Lexical coverage experiments and frozen validation

Ran four cumulative/separated policies over ASK and three historical suites: 2,348 logical sentence comparisons, 284 affected-sentence reruns and 2,064 cached unchanged results. Genitives help; corpus-attested compound acceptance silently accepts a misspelling. Revising compounds to candidate proposals only gives ASK 98/100 top-three versus 95 baseline, warnings 2/100 versus 3, and historical top-three 258/277 versus 257, with no paired losses. Private paragraph stays 11/16. Defaults unchanged.

Lower score-gap thresholds 3 and 2 were assessed from cached scores; both recover targets but increase warnings on labelled-clean historical cases, so neither was adopted. No source sentence was displayed or submitted to a hosted model.

Selected proposal-only policy hash frozen before reserved evaluation. Eighty new checks on 20 error/control pairs give 18/20 top-three and no corrected-target warnings for both versions. No tuning after reserve; it is now consumed. Six cached-runtime tests plus 25 lightweight evaluation tests pass. See [report and aggregate files](benchmarks/2026-09-24-lexical-coverage.md). Continue with targeted independent coverage/performance validation before UI integration.
