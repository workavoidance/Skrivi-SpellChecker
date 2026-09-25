# Lexical coverage follow-up — 24 September 2026

## Aim

Investigate three missing ASK correction candidates and two dictionary-recognized detection misses. No application/default changes; all policies live in tools/experimental_lexical_coverage.py and are used only by the experiment runner. Cached resources only. Twenty reserved ASK pairs were kept untouched during development; the selected policy is subsequently frozen for one final validation.

## Diagnosis

The three missing answers expose unlisted compound forms and an unlisted noun possessive. Case-folding alone does not solve the latter: the lowercase possessive is also absent. The cached full-form dictionary accepts the constituent nouns, but not the required derived words.

For the two detection misses, the intended alternatives already exist in the default context candidate pool. Their model score advantages are approximately 3.26 and 2.18 against the current strict greater-than-4 threshold. Both source strings have entries in the cached Ordbank. The dictionary accepts one as a verb form and the other as a noun form. These are not ordinary unknown-word misses.

Public lexical checks: [Bokmalsordboka die](https://ordbokene.no/bm/die) confirms the verb's nursing/breastfeeding meaning. The [innehold query](https://ordbokene.no/bm/innehold) returned no headword, despite the cached Ordbank entry. A missing headword is not sufficient evidence to delete a cached form. This discrepancy needs lexical-resource review. Only public isolated words were queried; no corpus sentence was uploaded. The ASK sentence contexts have not been independently adjudicated.

## Cumulative coverage policies

1. **Genitive:** recognize an s-ending when its base is a cached, normative common noun, excluding bases already ending s/x/z; for misspelled s-endings, repair the base with Nuspell and reattach s. Preserve capitalization. No target-specific exception list.
2. **Attested compound:** add the genitive policy plus nearby words occurring at least five times in the cached corpus frequency table, within two adjacent-transposition-aware edits, with a matching first letter and a decomposition into cached common nouns (optionally with linking s). This is a heuristic, not a definitive compound grammar. Recognize exact attested compounds under the same decomposition gate.
3. **Productive compound:** add a narrower linking-s proposal/recognition rule for common-noun combinations whose first noun ends in -sjon, without requiring whole-compound corpus attestation. This is explicitly a more permissive experiment.

Additions occupy at most eight of 24 candidate slots, preserving the first 16 native suggestions. Existing NorBERT ranking and detection thresholds remain unchanged. Recognition can still be followed by normal contextual checking.

## Evaluation

The fixed ASK evaluation partition supplies 100 errors plus 100 target-only controls. The three historical suites supply 387 sentences and 277 labelled error targets, including the private natural paragraph. They are reused development evidence, not independent accuracy estimates. Whole sentences and raw results stay local.

The runner first compares original versus experimental native dictionary responses. Sentences with identical recognition/candidate responses reuse their cached baseline output. Affected sentences are checked again in full using the same cached NorBERT3 Small model. This permits accuracy comparisons, not wall-clock speed comparisons. Results checkpoint after every sentence. No reserved ASK pair is run in development. The later validation has its own explicit runner and frozen-policy record.

Separately, thresholds 4, 3 and 2 are evaluated against the already saved default candidate scores, leaving candidate generation/ranking unchanged. This sensitivity analysis does not retrain or rerun the model, and does not establish semantic correctness of an ASK answer key.

## Threshold result

| Strict score-gap threshold | ASK top-three / 100 | ASK corrected-target warnings / 100 | Historical top-three / 277 | Historical clean cases flagged / 208 |
|---|---:|---:|---:|---:|
| 4 (default) | 95 | 3 | 257 | 65 |
| 3 | 96 | 3 | 263 | 73 |
| 2 | 97 | 3 | 266 | 87 |

Lower thresholds recover the two ASK targets in stages, but increase warnings on historical cases labelled clean. Counts of non-target flags across all historical sentences rise from 189 to 218 to 269; these are not all adjudicated false positives. Reject a blanket threshold decrease based on these results. Local context adjudication of the two ASK cases remains unfinished; no permission to display full corpus sentences was inferred from permission to inspect isolated pairs.

## Coverage results

A fourth policy was added after the attested-compound policies lost a previously successful correction. The misspelling appeared often enough in the frequency table to be accepted. Frequency is evidence of usage, not correctness.

**Proposal-only compounds** retain genitive recognition but use compound/frequency evidence only to propose candidates, never to accept a compound as correctly spelled. The thresholds and candidate limits of the first three policies are unchanged. Their first-run source is archived locally with its hash in the manifest.

| Policy | ASK top-three / 100 | ASK corrected-target warnings / 100 | ASK gains / losses versus default | Historical top-three / 277 | Historical clean cases flagged / 208 |
|---|---:|---:|---:|---:|---:|
| Unchanged default | 95 | 3 | — | 257 | 65 |
| Genitive | 96 | 2 | +1 / 0 | 257 | 61 |
| Genitive + attested compounds | 96 | 1 | +2 / -1 | 258 | 57 |
| Above + productive linking s | 97 | 0 | +3 / -1 | 258 | 57 |
| Genitive + proposal-only compounds | **98** | **2** | **+3 / 0** | **258** | **61** |

Paired checks show no lost historical top-three corrections for any policy. The proposal-only policy gains one historical correction and three ASK corrections without losing any previous success. Teo's private paragraph remains 11/16 scored targets in the top three. Non-target warnings over all historical sentences fall from 189 to 176 with the proposal-only policy; these are not all adjudicated false positives.

The proposal-only policy contains the intended answer in every ASK candidate pool (100/100). Two recognized-word targets remain unflagged, so top-three remains 98/100. The same-policy top-five also reaches 98, providing no additional benefit. Two correctly spelled compounds still attract warnings: proposing compounds successfully does not establish a safe general acceptance rule.

The four policies produce 2,348 sentence-level comparisons. Only 284 affected sentences require new checks; 2,064 reuse unchanged baseline results. This is not 2,348 independent inferences or a timing benchmark. Native-only candidate-hit fields are omitted from the exported experimental metrics because the wrapper augments the backend suggestions.

## Decision and remaining work

Prefer the genitive plus proposal-only compound policy for further integration. Reject accepting compounds based on corpus frequency alone, and reject blanket context-threshold reductions. These are small development-set gains, not general Norwegian accuracy estimates.

No default, UI, launcher, downloaded resource or model changed. The experimental code uses the existing Ordbank and corpus-frequency caches, so an eventual application integration must handle their availability explicitly and measure startup/memory/latency. Candidate generation and recognition must remain separate.

The two detection misses still need independent sentence-context adjudication before threshold work. The discrepancy between cached noun coverage and the current public dictionary deserves a separate resource audit. A better targeted compound/possessive acceptance test is needed beyond these small samples.

Six cached-runtime unit tests pass, covering genitives, casing, existing acceptance, optional linking s, and the candidate-only/recognition distinction. The lightweight evaluator suite has 25 passing tests; its six resource-dependent tests are skipped there and run successfully with the cached runtime.

Aggregate data: [lexical comparison](2026-09-24-lexical-summary.json). Private outputs: `results/lexical-coverage-20260924/` and `results/lexical-proposal-only-20260924/`. No source sentences or spelling pairs are published.

## Frozen-policy reserved validation

The proposal-only source hash was frozen before reserved inference. Both unchanged default and frozen policy scored 18/20 top-three corrections, 16/20 first-choice corrections, and 0/20 corrected-target warnings. There were no paired gains, losses or new control flags. All 80 checks completed. No tuning followed.

This small validation shows no observed regression, but no additional gain either. Two reserved candidate-generation misses remain. The reserve has now been consumed and must not be presented as untouched in later experiments. [Frozen-policy validation and hashes](2026-09-24-lexical-reserved.json). Raw traces remain in ignored `results/lexical-reserved-20260924/`.
