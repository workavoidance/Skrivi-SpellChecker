# Spell-checker experiment log

## 2026-09-24 — recovered default baseline

Question: where are errors lost between dictionary detection, candidate generation, ranking, UI display and word help?

Protocol: unchanged application; Nuspell, Nuspell + ranking, and Nuspell + context with cached NorBERT3 Small. Three frozen local suites, 387 cases and 277 scored targets; raw text remains local. CPU, one pass, checkpoint after each case; no tuning or repeated timing runs. About 14 minutes of evaluation wall time. Input and code hashes recorded.

Result: 1,161 checks completed without failures. The hybrid wins all three groups; the major remaining labelled failure stage is detection (15 targets), while four targets lack the intended candidate. Actual definitions/examples cover 1.5% of displayed suggestions; optional WordNet raises any-hint coverage to 38.6%, not definition coverage. Five choices would add only two scored corrections across these suites under the same detection policy.

Decision: retain current defaults and the small model. Next investigate keep/change decisions with separate paired cases; separately integrate richer lexical explanations with verified distribution rights. Human review of non-target flags and help usefulness remains necessary. Do not interpret the synthetic source-restoration 100/100 as general accuracy.

[Full aggregate report](benchmarks/2026-09-24-baseline.md). Private traces: `results/baseline-20260924/`. Functional validation: 20 tests pass. No application algorithm or threshold changes.
