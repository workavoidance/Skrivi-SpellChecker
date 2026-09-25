# Hyphen candidate policies — 25 September 2026

## Findings

Three isolated policies were replayed over existing scored candidate pools. No model calls, downloads, learner-text uploads or app/default changes. Filtering preserves detection/status and the known-word score-gap rule; removed suggestions are backfilled from already scored eligible candidates. This is an exact output-policy replay, not a rerun of candidate generation or scoring.

| Set / mode | First choice before -> guarded | Top-three before -> guarded | First/top-three losses |
|---|---:|---:|---:|
| Historical default, 277 targets | 246 -> 248 | 257 -> 257 | 0 / 0 |
| Conservative learner default, 297 targets | 245 -> 262 | 274 -> 274 | 0 / 0 |
| Conservative learner optional coverage, 297 targets | 247 -> 264 | 277 -> 277 | 0 / 0 |
| Synthetic default, 120 targets | 58 -> 58 | 60 -> 60 | 0 / 0 |
| Synthetic optional coverage, 120 targets | 108 -> 108 | 118 -> 118 | 0 / 0 |
| Stress default, 192 targets | 89 -> 90 | 98 -> 98 | 0 / 0 |
| Stress optional coverage, 192 targets | 169 -> 172 | 191 -> 191 | 0 / 0 |

Historical displayed hyphenated occurrences fall 118 -> 5; default learner outputs 134 -> 1 (counts include suggestions on non-target words). These are hyphen counts, not human-adjudicated bad-word counts. Historical suggestion count falls only 1,068 -> 1,058 because most removed candidates are replaced by lower-ranked unhyphenated ones. Their semantic quality is not established merely by lacking a hyphen. Corrected-target warnings stay unchanged by construction.

## Policies

1. **guard:** A newly introduced hyphen must be present in an explicitly listed Nuspell/Ordbank form, or match a narrow initial single-letter/numeric/uppercase-abbreviation pattern with a recorded right-hand word. Existing hyphens in the original token and special non-native paths are left unchanged. No general confidence threshold.
2. **guard_native_tiebreak:** Additionally subtract 0.15 per native rank position (unlisted candidates use position 24) from ranking scores. This is a fixed exploratory blend, not a calibrated confidence. It adds two learner top-three successes but creates first-choice regressions: two learner targets and 22 optional synthetic targets, among others. Do not promote this variant; its treatment of added candidates is particularly unfavorable.
3. **guard_gap:** Additionally suppress candidates more than 2 score units below the best retained alternative. First choice is unchanged, but correct top-three answers are lost: one historical target and three optional synthetic targets. Do not promote this arbitrary cutoff; no calibration is claimed.

No parameter sweep or test-set threshold tuning was performed.

## Legitimate hyphens: blocking limitation

A separate 20-form acceptance diagnostic retained 16 and rejected four valid constructions: Oslo-jente, Office-programmene, skole-elev and norsk-engelsk. This probes the gate directly, not whether Nuspell would generate those forms in a real sentence. The examples were checked after the initial benchmark and are now development examples, not a holdout.

[Språkrådet's hyphen guidance](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/tegn/bindestrek/) describes required and optional uses including proper-name compounds and readability hyphens. Consequently a hard gate based on whole-form membership plus a narrow acronym rule is incomplete. It must not be enabled by default based only on the favorable existing spelling benchmark. The rule is a proposal-admission heuristic, not a complete Norwegian spelling validator.

## Interpretation and next work

The current ranker still adds value overall. Its handling of these native hyphen candidates is a specific weakness. The guard improves first-choice selection substantially in the reused learner sample while retaining all observed top-three successes, but legitimate-hyphen rejection is demonstrated outside that sample. Keep this experiment separate.

Next extend source-backed recognition of valid hyphen constructions, with a frozen acceptance/rejection diagnostic that includes new examples beyond the four observed failures. Compare a guarded fallback/demotion policy if broad exceptions weaken the benefit. Only then integrate as an opt-in mode. Tokenization/mean-subtoken scoring bias remains a hypothesis; this experiment did not compare alternative model likelihood normalizations. Lower-ranked nonhyphen candidate quality also needs review before claiming cleaner overall choices.

## Reproduction

`python tools/evaluate_hyphen_policy.py` uses existing local historical and expanded-suite outputs, cached Nuspell dictionary and Ordbank. `docs/benchmarks/2026-09-25-hyphen-policy.json` contains aggregate results, resource/input hashes and the public synthetic legitimate-form probe. Per-target regressions remain in ignored `results/hyphen-policy-20260925/regressions.json`; no source sentences or learner-specific examples are published.

47 lightweight tests pass, seven resource-dependent tests skip. Four new tests verify filtering/backfill without mutation, listed/rule-supported forms, unchanged detection and strict known-word thresholds, special-path preservation and separation of the gap experiment. Results are on reused, nonrepresentative benchmarks; stress targets reuse synthetic material and modes share cases. Do not sum them as independent samples. No production source was changed.
