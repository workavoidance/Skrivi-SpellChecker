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

## 2026-09-24: targeted coverage and opt-in integration

Authored and ran 19 synthetic error targets plus 20 correct controls in fresh baseline/proposal-only processes. Top-three 11 to 19; control flags 8 to 0. Median subsequent check +0.079 seconds; peak working set +108.6 MiB. Single-run timing; targeted synthetic evidence, not independent learner performance. Saved each case locally and aggregate summaries in docs/benchmarks/2026-09-24-coverage-integration.json.

Integrated only the previously frozen proposal-only policy as optional `nuspell_coverage`, leaving default unchanged. No downloads. Read-only database connections support sequential HTTP request threads. Seven coverage tests, 14 sandbox regression tests and a real localhost HTTP test passed. HTTP checks include unchanged default before/after, repeat requests, Unicode offsets and single-word replacement. Broader usability and fresh-machine setup remain untested.

## 2026-09-24: larger frozen comparison

Reviewed 1,000 new isolated ASK pairs; froze 311 pairs plus 120 synthetic pairs and 24 artificial paragraph stress cases before inference. Dictionary label audit during baseline identified 14 ambiguous normative originals; one pair also failed token alignment. Original data/results preserved, conservative analysis applies symmetric exclusions. Main learner top-three 274 to 277/297, first-choice 245 to 247, corrected-target warnings 4 to 4. No top-three losses. Synthetic top-three 60 to 118/120; stress 98 to 191/192 (reused targets). Two synthetic and three stress first-choice losses despite positive net totals.

Baseline 886 attempts, two invalid spans; coverage 241 reruns plus 643 equivalent-case reuses, with ten successful unchanged-case spot checks. No code/default/model changes. 27 evaluator tests pass. Report: docs/benchmarks/2026-09-24-expanded-evaluation.md; private checkpoints: results/expanded-20260924/. Next candidate narrowing/generation experiment should use separate future evaluation data.

## 2026-09-24: API reference ranking comparison

User authorized existing tutor-project credential reuse under a USD 5 cap. Frozen 168 synthetic-only cases before API calls; opaque IDs and randomized candidate order, no answer key/local predictions sent. GPT-6 Astra medium: 82/84 top-three and first-choice; NorBERT3 Small: 81/84 top-three, 78/84 first-choice; traditional candidate ordering: 40/84 and 29/84. All 84 controls kept. Both models reach the 22/24 candidate-availability ceiling on contextual examples.

42 main requests plus 12 isolated reruns from three paired batches, with identical scored outcomes on all reruns. Estimated token cost USD 0.74632, conservative ledger USD 0.86639. No application changes or private learner text exported. Five new evaluator tests; full lightweight suite 32 passed, seven resource skips. Report: docs/benchmarks/2026-09-24-cloud-reference.md. Evidence favors retaining the small model; broader real-writing validation remains separate.
