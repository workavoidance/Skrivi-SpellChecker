# Strong API reference versus local Norwegian ranking

## Finding

On a constrained synthetic benchmark, NorBERT3 Small captured most of the benefit of contextual ranking. GPT-6 Astra improved four first choices and one top-three result, with no scored regressions. This supports retaining the small local model; it does not establish equivalence between these models on general Norwegian writing.

| Synthetic error group | Traditional candidate order | NorBERT3 Small | GPT-6 Astra |
| --- | ---: | ---: | ---: |
| Possessive/compound: first correct | 28/60 | 56/60 | 60/60 |
| Possessive/compound: correct in top three | 39/60 | 59/60 | 60/60 |
| Contextual: first correct | 1/24 | 22/24 | 22/24 |
| Contextual: correct in top three | 1/24 | 22/24 | 22/24 |
| Correct controls unnecessarily reviewed | 0/84 | 0/84 | 0/84 |

Combined top-three results: 40, 81 and 82 out of 84 errors. Combined first-choice results: 29, 78 and 82. These totals describe this deliberately constructed mixture, not everyday spelling accuracy. The no-model comparator retains our traditional coverage rules; it is not bare Nuspell without those additions.

The correct candidate was present for all 60 morphology errors and 22 of 24 contextual errors. Both models chose it first on all 22 available contextual cases. Two contextual cases lacked the intended alternative, so neither ranker could select it. Improving the candidate pool remains a distinct task from improving ranking.

## Protocol

User authorized reuse of the existing tutor-project API setup under a proposed USD 5 cap. Only synthetic text was exported. No learner corpus, pupil writing, answer key, local scores or conversation history was sent. Existing application defaults and model weights were unchanged. The tutor credential was read into memory, not copied, printed, edited or committed.

Selected 30 existing synthetic possessive pairs and 30 compound pairs, balanced between misspelled targets and correct controls (120 cases), then added 24 newly authored contextual/error pairs and their controls (48 cases). The contextual examples include similar-sounding words, single/double letters, function-word confusions and two nonword misspellings. Gold labels are assistant-authored, not independently human-adjudicated. Earlier morphology examples derive from cached lexical resources used by the application. Most of their local outputs were reused; 48 new contextual cases were run locally before API inference.

Each API input contains only a neutral case identifier, sentence, target span, original option ID, and the exact candidate pool available to the local system. Candidate order was randomized with a fixed seed. Error/control labels were replaced by opaque IDs before the first API call. The original word is an available keep choice. The model cannot add candidates or rewrite sentences. It returns keep/change/unsure and at most three candidate IDs; the runner rejects invalid IDs, duplicate choices and inconsistent keep decisions.

The frozen dataset SHA-256 is `d201c8b4d00df7d626ba9cb5b4edcde38fd2da682c0b1d504b7b031f6f321a96`. Prompt SHA-256 is `9f54b64d59c9b8b3784262e8387e858e0bdc1b41291d845c5ad041e69a26eb42`. Exact prompt and request construction are in `tools/run_cloud_reference.py`.

Used Responses API model `gpt-6-astra`, medium reasoning, standard service tier, `store=false`, strict structured output and a 2,048-token output cap. The API returned model name `gpt-6-astra`; no dated snapshot was exposed by that alias. No prompt tuning occurred after outcomes. This compares the existing NorBERT scoring/threshold policy against a prompted strong-model selection policy, not neural weights in isolation. All methods receive a preselected target; whole-document error detection is not evaluated here.

The initial 42 requests contained four cases each. A post-run audit found three batches containing both members of a paired error/control example. All 12 cases from those batches were rerun as fresh single-case requests under the same prompt. All 12 retained the same decision and scored outcome. This reduces the specific paired-batch concern but is not a general repeated-run variance estimate.

## Cost, timing and validation

54 requests completed successfully: 42 main batches and 12 isolated audit cases. Total usage was 48,027 input tokens and 5,321 output tokens, including 709 reasoning tokens. Estimated standard token cost, before any cached-input discount, is USD 0.74632. The conservative budget ledger accounts for USD 0.86639 against the USD 5 cap. These are estimates from token usage, not a billing statement or a check of the project's prepaid balance. Main four-case batch median response time was 3.35 seconds; this is not single-word application latency.

Model and price references: [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [API pricing](https://developers.openai.com/api/docs/pricing), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Standard short-context rates used for the estimate are USD 10 per million input tokens and USD 50 per million output tokens. The guard conservatively reserves USD 12.50 per million input bytes plus framing margin and the full output-token allowance before each request, persisting reservations before network access. Incomplete/error requests retain accounting; no blind network retries.

Five added evaluator tests cover opaque ID mapping, invalid selections, keep semantics, budget reservation and conditional candidate availability. The full lightweight suite passes 32 tests, with seven existing resource-dependent tests skipped. All main and audit responses passed schema/application validation.

## Interpretation and next work

This test demonstrates useful contextual-model assistance within the selected artificial examples. It gives little evidence that a bigger ranking model is a priority for the current app. It does not show that small models match strong models on arbitrary sentences, heavy dyslexic writing, definitions, candidate generation, or a different prompt. The 168 cases are now consumed exploratory material.

Retain the local small model and existing optional mode. Improve missing-candidate coverage and word explanations when practical use justifies it. Any later API test on real writing needs appropriate permission; no permission to export the local learner corpus or pupil writing is implied by this synthetic test.

Private inputs: `data/local/cloud-reference-20260924/`. Private predictions and cumulative cost ledger: `results/cloud-reference-20260924/`. Public adjacent JSON contains aggregates only. `prepare_cloud_reference.py` requires local synthetic fixtures and frozen local results. `run_cloud_reference.py` reads the explicitly supplied credential file and resumes completed cases; run it serially. It refuses a budget above USD 5. `summarize_cloud_reference.py` generates the aggregate report.
