# Strong-model candidate-generation pilot — 24 September 2026

Question: can a prompted strong model add intended corrections that the existing dictionary-based candidate pool misses, and can unchanged NorBERT rank the combined pool?

## Frozen protocol

Reused the synthetic-only 168-case reference benchmark: 84 spelling errors and 84 paired correct controls. Inputs are short, 4–8 words. These are previously consumed, assistant-authored/constructed examples, not independent or authentic dyslexia evaluation. Only two error cases initially lacked the intended candidate. The real learner corpus and pupil writing remained local and were not used in cloud requests.

GPT-6 Astra, medium reasoning, supplied zero to five single-word alternatives using the original spelling and sentence. Instructions required spelling or phonetic resemblance, no synonyms, style changes or grammar rewriting, and empty output for a correct original. The API did not receive dictionary candidates, gold answers, prior predictions or error/control labels. Forty-two independent requests, four cases per request, with paired error/control cases separated into different requests. Structured output and local validation enforced identity and single-word constraints; phonetic/semantic relevance was instructed, not mechanically certified. No output repairs, prompt tuning or automatic retries were performed.

Locally reran the optional nuspell_coverage baseline on all cases and checked decisions and displayed corrections against the frozen prior predictions. Added AI candidates without deleting existing candidates or imposing a dictionary-recognition gate. Rescored changed pools with cached NorBERT3 Small and the existing edit-distance penalty and confidence thresholds. Only six pools gained a new candidate. No app/default/UI changes or new model downloads.

## Results

| Metric | Existing optional engine | AI candidates for every supplied target | AI candidates only when already flagged |
|---|---:|---:|---:|
| Intended answer first /84 | 78 | 79 | 78 |
| Intended answer top three /84 | 81 | 83 | 82 |
| Correct controls flagged /84 | 0 | 0 | 0 |

The AI proposed the intended correction for 84/84 errors and returned no alternatives for 84/84 controls. Candidate availability increased from 82/84 to 84/84. Both missing candidates became top-three successes when all supplied targets were eligible. One had not originally been flagged, so the proposed flagged-only workflow recovers only one of those two. The flagged-only result is a post-hoc application of the pre-existing detection gate, not a separate API run or a measured cost-saving deployment.

No top-three regressions. One first-choice regression in the possessive group offsets one of the two contextual first-choice gains. One existing error remains outside the top three despite the correct answer being available. Thus perfect candidate-generation coverage on this small set does not mean perfect end-to-end correction.

## Cost and latency

42 API requests; estimated standard token cost USD 0.53955, conservative accounted cost USD 0.5879625. Including the previous benchmark, conservative cumulative spending USD 1.45435, below the previously authorized USD 5 ceiling. These are token-based estimates using the previous run's recorded rates, not invoice totals. Median four-case API request 4.064 seconds; this is not single-word production latency. Store=false; credential used in memory, never copied or printed.

## Interpretation and next step

The proposal passes a narrow feasibility test. Strong AI can recover missing candidates, and NorBERT can use them. It is not yet a case for deploying cloud generation or assuming a small local generator will reproduce it. The modest end-to-end gain reflects the strong existing baseline and only two initial candidate omissions.

Next: freeze a broader synthetic challenge set with substantially more candidate omissions, longer sentences and multiple errors. Compare AI additions against simply retaining/widening traditional suggestions. Include clean controls and successful cases, measure first-choice as well as top-three regressions, and keep prompt/ranking fixed. Genuine learner and pupil text must remain local unless separately authorized. No conclusion about paragraph-wide context follows from this pilot.

## Reproduction and records

Tools: tools/test_cloud_candidates.py (generate/evaluate), tools/summarize_cloud_candidates.py. Generation requires explicit --key-file; source digest and synthetic provenance are checked before transmission; combined budget guard includes the prior reference ledger. Re-running evaluation resumes local checkpoints. Three output-validation tests pass; full lightweight suite: 35 passed, 7 cached-resource-dependent skips. An initial local runner reference to the wrong checker attribute was corrected before successful evaluation; no API requests were repeated for that fix.

Private inputs: data/local/cloud-reference-20260924/frozen.json. Private proposals, per-case ranks, ledger and aggregate: results/cloud-candidates-20260924/. Public aggregate: 2026-09-24-cloud-candidates.json.

Source SHA-256: d201c8b4d00df7d626ba9cb5b4edcde38fd2da682c0b1d504b7b031f6f321a96.
Prompt SHA-256: 19365e54ea7d1c8cca24449733e65633c174084b25cef4fda624a49b57d7267b.
