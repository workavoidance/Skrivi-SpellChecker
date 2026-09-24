# Larger evaluation of optional Norwegian candidate coverage

## Conclusion

The unchanged optional mode makes a modest improvement on new learner-writing examples and a large improvement on constructed possessive/compound diagnostics. Keep it available as an experiment; this does not establish general dyslexia accuracy or justify changing the default solely from synthetic results. Application code and defaults were not changed during this evaluation.

| Measure | Default | Optional coverage |
| --- | ---: | ---: |
| Learner corrections in top three | 274/297 (92.3%) | 277/297 (93.3%) |
| Learner corrections first | 245/297 | 247/297 |
| Corrected learner targets flagged | 4/297 | 4/297 |
| Synthetic corrections in top three | 60/120 | 118/120 |
| Correct synthetic targets flagged | 60/120 | 1/120 |
| Stress-paragraph target corrections in top three | 98/192 | 191/192 |

No previously successful top-three target was lost in any group. Learner first-choice results had two gains and no losses. Synthetic first-choice results had 52 gains and two losses (58 to 108/120 overall); stress results had 83 gains and three losses (89 to 169/192). Stress targets reuse synthetic words, so these are not five independent first-choice regressions. The correct replacements remain in the top three in those cases.

## Sample and label audit

Reviewed 1,000 previously unused isolated ASK-GEC training pairs (candidate indices 350-1349), selecting 311 plausible spelling pairs. Each is paired with its source-corrected target. There is no exact sentence overlap with the recovered historical sets, earlier ASK review, or the preceding targeted diagnostic. This is assistant word-pair review, not full-sentence or Norwegian-human adjudication. ASK is second-language learner writing, not a diagnosed-dyslexia dataset. Writer-level independence and absence from model training cannot be established.

The 886-case input was frozen before model evaluation, SHA-256 `bec72fec6041558486b82af796b1cb7fd2de7e22047e4296d18b5d1d2b5edd8a`. During the baseline run, a separate dictionary-based label audit identified 14 pairs whose originals have normative entries and therefore need context or variant adjudication. This audit did not use individual model predictions and was recorded before the optional comparison, but it was not part of the initial freeze. The conservative main analysis excludes those pairs symmetrically; original frozen results remain intact. For example, the official dictionary lists both [handball and håndball](https://ordbokene.no/eng/search?dict=bm&q=h%C3%A5ndball&scope=eif), illustrating why a source substitution is not automatically a spelling error.

One of those 14 pairs also has a target boundary incompatible with the app tokenizer. Its error/control cases produced two scoring ValueErrors; both are excluded as invalid benchmark spans, not counted as spelling failures. The reusable preparation tool now records this preflight audit. Of the original 311 pairs, 310 are technically scorable; full unfiltered source-key top-three results are 276 to 279/310, with warnings 4/310 in both modes. The conservative set contains 297 errors plus 297 corrected-target controls.

Controls score only the target word; they are not 297 independently verified, entirely clean sentences. A fully adjudicated clean-sentence benchmark remains unfinished.

The additional 120 synthetic pairs contain 60 noun possessives and 60 recorded compounds, sampled deterministically from existing cached lexical resources, excluding previously used target words. Four mechanical corruptions are cycled: deletion, adjacent transposition, substitution and insertion. These are structural diagnostics, not representative dyslexic error rates. In particular, substitution uses an artificial letter replacement. Gold words use resources also used by the experiment, so the large synthetic gain must not be treated as independent evidence of general accuracy.

The 24 stress paragraphs combine eight synthetic targets each with comma-separated surrounding template text. They are artificial, reuse targets, and test a denser/longer input; they are not authentic paragraphs from dyslexic writers. Teo's paragraph was not rerun because neither mode changed; its previously measured result remains 11/16.

## Execution and performance

All data and inference stayed local. Existing cached Nuspell, NorBERT3 Small, Ordbank and frequency resources were used; no downloads or paid services. The baseline used the application at commit `690ce768b50d7429fd832051d560c07baa958b04`; source hashes are retained with private run metadata and checked before comparison.

The default attempted all 886 cases: 884 scored successfully plus the two invalid spans. The comparison reran 241 cases (77 learner, 140 synthetic, 24 stress). The other 643 valid cases reused predictions only after every word's native acceptance, segmentation and first 24 candidates matched. Ten unchanged-case spot checks (five learner, five synthetic) were rerun and matched word/status/candidate/suggestion output exactly. All 24 stress cases were affected, so there were no unchanged stress cases to spot-check. There are 1,768 validated logical outputs, not 1,768 independent full inference runs.

Default median checks: learner 0.94 s, synthetic 0.89 s, stress paragraph 3.75 s. Optional affected/spot medians: learner 1.18 s, synthetic 1.14 s, stress 4.64 s. The first two optional populations differ from the full baseline and must not be used as a whole-mode speed comparison. All 24 stress cases were run in both modes; their single-pass median comparison is informative but not a repeated timing estimate. Dictionary equivalence-check overhead is not included in application check timings. No new comparative memory estimate was made.

Every successful logical output preserved the input text and token spans and returned at most three whitespace-free suggestions per word. Evaluation tests: 27 passed, seven existing resource-dependent tests skipped in the lightweight environment. No application changes required new runtime regression testing.

## What to investigate next

The optional mode's 20 remaining conservative learner misses partition into 11 absent from the scored candidate pool, six ranking/threshold misses and three unflagged targets. Of those 11 absent candidates, two already exist in the longer native suggestion list. Next, investigate candidate narrowing separately from generation: preserve useful native alternatives, then target the nine genuinely absent suggestions. Keep held-out evaluation separate from these now-consumed development examples.

A hypothetical top-five list recovers four additional learner corrections (277 to 281/297). That modest gain should be weighed against making the user assess more choices; the UI remains at three. Definitions/examples and independently adjudicated clean sentences remain important separate work.

## Local artifacts and reproduction

Private inputs/reviews: `data/local/expanded-20260924/`. Private per-case traces and code hashes: `results/expanded-20260924/`. Adjacent public JSON contains aggregates only. Source corpus revision and hashes are in that JSON. Raw writing and per-case identifiers are not published.

With the existing cached Windows runtime and privately reviewed inputs, run `tools/prepare_expanded_evaluation.py`, then `tools/run_expanded_evaluation.py nuspell_context`, `tools/compare_expanded_evaluation.py`, and `tools/summarize_expanded_evaluation.py`. Preparation and run tools refuse to overwrite frozen data/results. The review file requires deliberate review; no automatic correctness labels are implied.
