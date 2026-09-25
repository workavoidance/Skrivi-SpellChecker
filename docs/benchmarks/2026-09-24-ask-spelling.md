# ASK spelling evaluation — 24 September 2026

## Question and scope

Does the recovered spelling pipeline offer the intended correction among its first three suggestions for new, authentic Norwegian learner misspellings, and does it leave the corresponding corrected word alone?

This is an exploratory, assistant-reviewed spelling sample. It is not a clinically representative dyslexia benchmark, a Norwegian-human-reviewed answer key, or a whole-sentence grammar assessment. No application code or settings were changed for this experiment.

## Source and selection

Source: [University of Oslo LTG ASK-GEC](https://huggingface.co/datasets/ltg/ask-gec), training split, revision `9871205efddb575e77c4b49443ff75e28e25deae`. The release card declares CC BY 4.0 and identifies Jentoft's 2023 ASK-RAW conversion. Source texts, pairs, decisions and traces remain local; none are included in this repository.

The 7,716,969-byte file contains 36,404 rows. Source SHA-256: `51046c28cda51a91f0501ddcd2be91f2b98a553736b446a86246b0b48472ade9`.

Preparation selected rows with exactly one changed alphabetic token and no other text changes, 5–35 punctuation/word tokens, at least three letters on each side, and character-sequence similarity of at least 0.60. It excluded case-only changes and deduplicated case-folded error/correction pairs, retaining the first occurrence. The resulting 2,184 candidates were shuffled with seed 20260924.

The assistant inspected the first 350 isolated pairs, accepting 120 reasonably clear orthographic repairs and excluding 230 grammatical, lexical, variant or ambiguous changes. Full sentences were not displayed or independently adjudicated. The source's correction is not automatically treated as correct elsewhere in the sentence. Labels were fixed before running the checker.

The accepted pairs were shuffled with seed 24092026. Twenty pairs were reserved and never passed to the checker. The other 100 form 200 cases: one original sentence and one sentence with its target spelling corrected. Only the target word is scored on controls; unrelated flags are not called false positives. Evaluation and reserve share no selected error/correction pair, but may share lexical targets or authors: the release does not supply essay/writer identifiers here.

This selection excludes split/join errors, most real-word confusions, very short words, capitalization-only errors and many severely corrupted words. It favors isolated, recognizable misspellings. Do not generalize its scores to every spelling task. The public source may have appeared in model training.

## Local reproduction

Inputs and decisions are in ignored `data/local/ask-reviewed-20260924/`. The source validation and test splits remain undownloaded.

```powershell
.venv\Scripts\python.exe tools/prepare_ask_spelling.py --directory data/local/ask-reviewed-20260924 --reviews data/local/ask-reviewed-20260924/reviews.json --reserve 20
```

Use the existing cached Norwegian Python runtime for `tools/audit_ask_spelling.py`, supplying `--data data/local/ask-reviewed-20260924/reviewed-cases.json` and a new output directory under `results/`. The runner refuses exact sentence overlap with the three recovered historical suites and does not run reserved cases. It saves a checkpoint after every sentence. It does not download assets.

Review-set SHA-256: `83a4ef37a0a7eb74e168dc93aeaffc192a19a151cd282e500e82dd8d119346e0`.

## Measurement conventions

- Compare dictionary mode, dictionary with model ranking, and the default context mode using cached Nuspell/NorBERT3 Small.
- Count detection, candidate-pool inclusion, visible top-one/top-three success and corrected-target false flags separately.
- Top-five is a counterfactual using existing detection and score thresholds, not a five-option UI trial.
- Exact intended spellings are used. Ambiguous/variant pairs were excluded during review, but independent Norwegian review could still revise labels.
- CPU, one pass per mode, new Checker per mode. Model loading is recorded separately. Original and corrected sentences run consecutively and share caches, so timing is descriptive rather than a randomized performance comparison.

## Results

All 600 checks completed successfully: 200 cases in each of three modes. No exact sentence overlap with the three recovered historical suites was found. Engine file hashes match the previous baseline. Twenty reserved pairs (40 cases) remain unrun.

| Measure | Dictionary | Model ranking | Default context |
|---|---:|---:|---:|
| Errors flagged / 100 | 98 | 98 | 98 |
| Intended answer in candidate pool / 100 | 95 | 95 | 97 |
| Intended answer first / 100 | 72 | 87 | 87 |
| Intended answer in visible top three / 100 | 92 | 95 | 95 |
| Hypothetical same-policy top five / 100 | 93 | 95 | 95 |
| Corrected target words flagged / 100 | 3 | 3 | 3 |
| Median check seconds, excluding load | 0.44 | 0.47 | 0.98 |

The ranking model adds three top-three successes and loses none relative to the dictionary. It also raises first-choice success by 15 targets. Default context adds two intended candidates to its pool but does not flag those targets, so visible success is unchanged from ranking-only. Both model modes have the same top-three successes and corrected-target flags here.

Five default failures remain: three flagged errors whose intended answer is absent from the candidate pool, and two dictionary-recognized strings that are not flagged despite an intended candidate being available. The latter are particularly important to validate in sentence context before changing thresholds: isolated-pair review cannot establish their intended meaning independently of the source correction.

All three corrected-target flags concern the same targets as the dictionary mode. This run therefore provides no evidence of additional target-control warnings from model ranking or default context. It does not assess every flag elsewhere in the sentences.

The evaluated error categories are 54 omitted-letter cases, 24 extra-letter cases, 16 substitutions, five multiple-edit cases and one adjacent transposition. These are mechanical categories, not diagnoses or estimates of real-world error prevalence.

## Decision

Retain the small model and existing default for now. This sample supports the value of model ranking, but supplies no added visible benefit for the broader default context mode; that mode should be assessed on a separate contextual-error set before any decision to remove it. The observed timing difference is descriptive, with paired cache reuse and no repeated performance measurement.

Next investigate the three candidate-generation failures, including compound and capitalized inflected-form handling. Separately adjudicate paired sentence context for the two detection misses before testing a keep/change adjustment. Keep changes experimental and use the reserved pairs only after development decisions are frozen. Do not enlarge the UI to five options based on these results: it would recover no additional targets in either model mode.

## Saved outputs

Aggregate results and source-code hashes: [JSON report](2026-09-24-ask-summary.json). Raw results: ignored `results/ask-reviewed-20260924/`. Accepted and excluded review decisions: ignored `data/local/ask-reviewed-20260924/reviews.json`. No corpus text or isolated source pairs are published in this report.

Twenty-five evaluation tests pass. No application code, thresholds, models, audio or UI were changed. This is fresh evaluation of the selected examples, not proof of general 95% Norwegian spelling accuracy.
