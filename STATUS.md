# Verified status — 2026-09-24

**The original Norwegian sandbox has been recovered.**

GitHub source of truth: https://github.com/workavoidance/Skrivi-SpellChecker

Application: sandbox/norwegian/. Launcher: sandbox/Start-Skrivi.cmd. Optional word help: sandbox/Start-Wordnet-Experiment.cmd. All further work should use this Git checkout.

## Recovery

116 source/notice files copied without algorithm changes. Hashes are in docs/RECOVERY-MANIFEST.json. Launcher wrappers were reconstructed from the original packaging script. The complete 543-file original is preserved in ignored data/local/recovered-original/, including historical datasets and results. Those files must not be published without data review. The source in Codex project storage was left untouched.

The historical release is Skrivi-Responsive-POC.zip. Recovered editable source includes later experimental modules; recovery does not imply every experiment is active or improves accuracy. The older English/Qwen prototype is preserved locally, not published here.

Recent dictionary downloads are in the local Documents/Skrivi/Research/Dictionary-Exploration folder after the OneDrive migration. Models/runtime remain in the persistent user cache. No models or external datasets were downloaded during migration.

## Validation

- 16 evaluator/diagnostic tests passed during initial setup.
- 16 recovered sandbox tests passed with the cached Python runtime: engine contracts, Nuspell protocol, candidate handling, context scoring, personal dictionary and WordNet help.
- These are functional tests, not a new accuracy benchmark. The relocated sandbox served its page successfully during migration; fresh-machine setup has not been revalidated.

## Next work

The unchanged baseline was rerun on 24 September: 387 cases, 277 scored targets, three modes, 1,161 successful checks. See [the measured report](docs/benchmarks/2026-09-24-baseline.md) and [experiment log](docs/EXPERIMENT_LOG.md). Default top-three counts are 87/105 development, 70/72 previously used fresh, and 100/100 source-restoration targets. These are reused exploratory sets, not independent accuracy claims.

Next scoring experiment: inspect the 15 default detection misses using the private traces, and build separate paired correct/incorrect tests before changing keep/change thresholds. Separately improve actual definition/example coverage; only 16/1,068 displayed default suggestions have curated help, with optional WordNet increasing any-hint coverage to 412/1,068. Keep raw writing local. Do not change defaults based only on reused cases.

## Current audit verification

- Application source and defaults unchanged; cached Nuspell and NorBERT3 Small used offline.
- 20 evaluation/audit tests pass (including four stage/coverage checks).
- Six old development/fresh mode score summaries reproduced exactly.
- Raw results: ignored `results/baseline-20260924/`, checkpointed after each case. Corpus/code hashes and aggregate metrics are in `docs/benchmarks/2026-09-24-summary.json`.
- Personal remembered-word overrides bypassed for reproducible scoring; user settings untouched. No new models, audio or cloud inference.
- Larger models, split/join behaviour, human-rated word-help usefulness and independent evaluation remain untested in this run.

Historical provenance: research merged through Skrivi-STT PR 53; evaluator copied from commit 1fc51e4e8d1350f78a820a748b98aa87346631a8 in open PR 54. Neither old PR was changed by this migration.

## Additional error-source research

Online source inspection on 24 September identified ASK-GEC as a practical source of authentic learner spelling examples and Sprakradet's 2026 appendix as expert-designed error/control material. See [source assessment and next experiment](docs/research/NORWEGIAN_ERROR_SOURCES_2026-09-24.md). No dataset was imported and no new accuracy claim follows from this research. Next data action: curate a local, reviewed spelling-only subset with separate learner/constructed provenance and untouched evaluation cases.

## ASK sample preparation — historical checkpoint (now completed below)

- Downloaded only the public ASK-GEC training split (7,716,969 bytes) and source card into ignored `data/local/ask-reviewed-20260924/`.
- Source revision: `9871205efddb575e77c4b49443ff75e28e25deae`; SHA-256: `51046c28cda51a91f0501ddcd2be91f2b98a553736b446a86246b0b48472ade9`.
- `tools/prepare_ask_spelling.py` finds 2,184 distinct isolated edit pairs among 36,404 training rows. This automated shortlist includes grammatical/lexical changes and is NOT a reviewed spelling benchmark.
- Local preparation metadata records the deterministic seed and mechanical edit categories. Validation/test source splits were not downloaded or inspected.
- `tools/audit_ask_spelling.py` scores precise target spans, pairs each accepted error with its corrected target, keeps reserved pairs unrun, checks exact historical sentence overlap, and saves raw traces only in ignored results. Other words in each sentence are not counted as false positives without adjudication.
- 25 tests pass. Pytest could not write its optional cache, which does not affect the passing tests.
- No reviewed sample or new spell-checker accuracy results yet. Automatic approval review rejected displaying full learner sentences and then a bulk list of isolated pairs in tool output. User permission to inspect public spelling pairs is pending. Until then, no labels are asserted as reviewed and no evaluation has been run.
- Next action: obtain that review permission, review spelling-only pairs while excluding context-dependent/grammatical edits, finalize approximately 100 evaluation pairs plus a separate reserve, and run the unchanged three baseline modes offline. Application defaults remain unchanged.


## ASK reviewed sample — completed

User permission to inspect public isolated pairs was granted. Reviewed 350 pairs, accepted 120, froze labels before inference, tested 100 paired error/control examples, and kept 20 pairs unrun. This is assistant pair review, not Norwegian-human or whole-sentence adjudication. Source text stays local.

All 600 offline checks passed. Dictionary / model ranking / default top-three scores: 92 / 95 / 95 out of 100; first-choice scores: 72 / 87 / 87. Each mode flagged 3 of 100 corrected targets. Default misses: three missing candidates and two unflagged dictionary-recognized targets. Top-five would add no model-mode successes. Defaults unchanged.

See [ASK evaluation report](docs/benchmarks/2026-09-24-ask-spelling.md) and aggregate JSON alongside it. Private traces: `results/ask-reviewed-20260924/`. Next: investigate candidate-generation failures, then separately verify the two detection misses in context before threshold changes. Keep the 20 reserved pairs untouched until development decisions are frozen.


## Lexical coverage follow-up — completed, defaults unchanged

Four isolated coverage policies and two lower context thresholds were tested. Preferred experiment: noun possessive recognition plus compound candidate proposals, without using word frequency as proof that a spelling is correct. ASK top-three improves from 95 to 98/100 and corrected-target warnings fall from 3 to 2. Historical top-three improves from 257 to 258/277; no previously successful target is lost. Teo's scored paragraph stays 11/16. Historical clean cases flagged fall from 65 to 61/208.

More permissive compound acceptance was rejected after it accepted a frequent misspelling and lost a correction. Lowering the context threshold was rejected: it increases warnings on historical clean cases. See [full experiment and limitations](docs/benchmarks/2026-09-24-lexical-coverage.md).

The preferred policy was frozen, then tested once on the 20 reserved pairs: both default and experiment score 18/20 top-three with 0/20 corrected-target warnings. No gains or regressions; reserve is now consumed. Do not tune on it or call it untouched again.

Experimental code is in `tools/experimental_lexical_coverage.py`; it is not imported by the app. Raw local traces: `results/lexical-coverage-20260924/`, `results/lexical-proposal-only-20260924/`, `results/lexical-reserved-20260924/`. Six resource-runtime tests and 25 lightweight tests pass. Next: targeted independent possessive/compound tests, resource availability and performance checks before opt-in UI integration. Context adjudication of the two ASK detection misses and dictionary-version discrepancy remain unresolved; do not lower thresholds from isolated-pair evidence.

## Optional coverage integration - latest checkpoint

The proposal-only policy is now an opt-in responsive UI mode; default selection and algorithm are unchanged. New targeted synthetic diagnostic: top-three 11 to 19/19, correct-target warnings 8 to 0/20. Median subsequent check 0.732 to 0.811 seconds, peak working set +108.6 MiB in one fresh-process run per mode. These tailored examples are not an independent accuracy estimate. See [integration report](docs/benchmarks/2026-09-24-coverage-integration.md).

Production mode `nuspell_coverage` uses cached Ordbank/frequency assets and NorBERT3 Small; missing assets disable the option, with no downloads. Private results: `results/coverage-targeted-20260924/`. Seven coverage tests, 14 sandbox tests and localhost HTTP integration pass. Raw native suggestions stay separate from added candidates. Earlier statements that all application source is unchanged describe historical checkpoints, not this integration.

Next: independent possessive/compound examples, better definition/example coverage, and contextual adjudication of the two ASK detection misses. The 20-pair reserve is consumed. Teo's previous score remains unchanged; no new claim about his paragraph.

## Larger evaluation - latest checkpoint

Application remains at 690ce768b50d7429fd832051d560c07baa958b04, default unchanged. Frozen 886-case evaluation: 311 new reviewed ASK pairs, 120 synthetic pairs, 24 artificial stress paragraphs. A prediction-independent dictionary audit quarantined 14 ambiguous pairs; one pair also had invalid token boundaries. Main 297-pair learner results: top-three 274 to 277, first-choice 245 to 247, corrected-target warnings unchanged at 4. No top-three regressions. Synthetic top-three 60 to 118/120; stress 98 to 191/192 with reused synthetic targets. Some synthetic/stress first-choice regressions remain.

[Full report and limitations](docs/benchmarks/2026-09-24-expanded-evaluation.md); public aggregates alongside it. Private data/results: `data/local/expanded-20260924/`, `results/expanded-20260924/`. Input hash bec72fec6041558486b82af796b1cb7fd2de7e22047e4296d18b5d1d2b5edd8a. Baseline attempted 886; two invalid benchmark spans excluded. Optional mode reran 241 and reused 643 proven-unchanged valid cases; ten spot checks matched. All 1,768 logical outputs passed text/span/suggestion-contract checks. 27 evaluator tests pass, seven resource tests skip in lightweight runtime.

Next: investigate two useful native suggestions lost during narrowing and nine genuinely absent candidates. Preserve the optional status while seeking independent real-writing and whole-clean-sentence validation. The larger set is now consumed, not an untouched holdout; do not tune on it and claim independent accuracy. No new downloads, model changes or application changes.

## Strong API reference - latest checkpoint

Authorized synthetic-only comparison using the tutor project's existing API credential and USD 5 ceiling. GPT-6 Astra medium versus unchanged NorBERT3 Small and traditional candidate ordering: on 84 synthetic errors, top-three 82 versus 81 versus 40; first-choice 82 versus 78 versus 29. All three preserve 84/84 correct controls. Both models solve all 22 contextual errors whose correct answer is available; two lack the right candidate. No application/default changes.

[Full report](docs/benchmarks/2026-09-24-cloud-reference.md). Private inputs/results: `data/local/cloud-reference-20260924/`, `results/cloud-reference-20260924/`. Dataset hash d201c8b4d00df7d626ba9cb5b4edcde38fd2da682c0b1d504b7b031f6f321a96. Main run 168 cases in 42 requests; 12 single-case reruns checked three paired batches and reproduced all decisions/scored outcomes. Estimated total standard token cost USD 0.74632; conservative ledger USD 0.86639. No real learner or pupil writing exported, no key copied, no new models downloaded.

32 lightweight tests pass, seven resource-dependent tests skip. This is a small assistant-authored/constructed benchmark, not general dyslexia accuracy or a proof of model equivalence. Keep the small model; candidate availability and useful word explanations remain better-supported next priorities.


## Strong AI candidate generation — completed pilot

Synthetic-only GPT-6 Astra candidate generation plus unchanged optional NorBERT ranking: candidate availability 82 to 84/84, top-three 81 to 83/84 if every supplied target is eligible, or 82/84 restricted to already-flagged words. Correct controls unchanged at 0/84 flags; no top-three regressions, one first-choice regression. AI contained the gold answer on all 84 errors and proposed nothing for all 84 controls. This short, reused synthetic set contains only two candidate omissions and is a feasibility pilot, not general dyslexia accuracy. App/defaults unchanged. See [report](docs/benchmarks/2026-09-24-cloud-candidates.md). Private records: results/cloud-candidates-20260924/. Estimated incremental cost USD 0.54, combined conservative ledger USD 1.45 under USD 5. Next: broader frozen synthetic candidate-omission tests, longer contexts and a widened-traditional-pool comparator before local model selection.

## Offline dictionary help — 25 September 2026

Built the real offline importer and separate `sandbox/Start-Dictionary-Experiment.cmd` launcher. Default spelling/ranking unchanged. Persistent cache index is 56.13 MB. Saved baseline suggestion help improves from 16/1,068 curated definitions to 775/1,068 dictionary definitions and 640/1,068 with examples. Coverage only, not human usefulness or new spelling accuracy. 39 lightweight tests pass, seven resource skips; Node UI and localhost integration checks pass. See docs/research/bokmaal-importer.md and docs/benchmarks/2026-09-25-dictionary-help.json.

User accepted local evaluation on published open-use wording despite missing detailed licence document. Attribution and hashes are retained; exact licence and editorial status filter remain unresolved. Sources remain in Documents/Skrivi/Research/Dictionary-Exploration; generated index in LOCALAPPDATA/Skrivi/lexical/bokmaal. Next: inspect 293 uncovered suggestion occurrences, resolve embedded expression support/publication statuses and licence documentation, and evaluate meaning usefulness. No new large model, paid service, or uploaded private writing.

## Compound and base-form help POC — 25 September 2026

Separate offline lookup experiment; app/defaults/UI unchanged. Whole-word definitions rise 775 to 787/1,068 suggestion occurrences; 49 more get both recorded noun-compound parts explained. Any help 72.6% to 78.3%; first-choice 77.3% to 79.2%. Unrestricted decomposition gave 78.9% but included less useful function-word splits; conservative noun-final variant retained all first-choice gains. This is help availability, not intended-answer coverage or usability. Full report: docs/benchmarks/2026-09-25-compound-help.md.

New cached base-form index 53.51 MB, derived from existing Ordbank archive; no downloads/cloud/inference. Raw lookup payloads remain in ignored results/compound-help-20260925. 42 lightweight tests pass, seven skips. Next: evaluate intended-answer coverage and usefulness, then optional UI integration; 232 suggestion occurrences still lack help. Licence documentation follow-up remains open.

## Expanded importer and residual gap audit — 25 September 2026

Recovered 173 embedded entries into separate dictionary-expanded.sqlite3 (57.63 MB); added explicit related-expression lookup without transferring expression definitions onto standalone words. Original app index/defaults unchanged. Same saved suggestions: direct 775/1,068 and base/compound any-help 836/1,068 remain unchanged. Three residual occurrences have related-expression help, counted separately. The embedded recovery adds dictionary content but does not solve these benchmark gaps.

Remaining 232 occurrences: 118 separator-bearing forms (only five gain help when joined), 53 Ordbank form/base links without usable help, 45 without a recorded base link, 11 recorded proper names, three expression-only and two source forms lacking standalone definitions. Mechanical classifications, not spelling judgments. Report: docs/benchmarks/2026-09-25-importer-gaps.md; private audit results/importer-gaps-20260925. 43 tests pass, seven skips. Next: complementary definition-source assessment, with separator alternatives analysed separately; no automatic candidate suppression. Licence/publication-status follow-up remains unresolved.

## Hyphen suggestion policy experiments — 25 September 2026

Three saved-score replay policies tested; app/defaults unchanged. Conservative new-hyphen guard improves learner default first-choice 245 -> 262/297, top-three unchanged 274; optional coverage first-choice 247 -> 264, top-three unchanged 277. No guard first/top-three losses across historical, learner, synthetic and stress targets. Historical displayed hyphens fall 118 -> 5, with most slots refilled by other scored candidates. Not a human-adjudicated bad-suggestion count.

Do not promote yet: separate legitimate-form gate probe retained 16/20, rejecting four valid constructions including proper-name and readability hyphens. Native-rank blend and fixed score-gap pruning caused regressions and were not adopted. Report docs/benchmarks/2026-09-25-hyphen-policy.md; aggregate JSON alongside; private per-target regressions results/hyphen-policy-20260925. 47 tests pass, seven skips. Next: improve legitimate-hyphen recognition and test new acceptance/rejection examples, then optional integration. Model tokenization bias remains untested. No downloads or model calls.

## 2026-09-25: Softer hyphen candidate ordering

Extended soft policy retains all eligible choices, demoting unsupported new hyphens. Saved-score replay: learner default first-choice 245 -> 261/297; optional coverage 247 -> 263; respective top-three 274 and 277 unchanged. No individual first/top-three losses across replayed groups. Historical displayed hyphens 118 -> 21. All-analysis adjective lookup fixes compact-table POS ambiguity. Synthetic legitimate gate diagnostics recognize 38/40, retain 40/40; 12 suspect splits demoted. These are development probes, not fresh model accuracy. 51 tests pass, seven skips. App/defaults unchanged; more-suggestions payload is not yet wired to UI. Report: docs/benchmarks/2026-09-25-soft-hyphen-policy.md; aggregates alongside; private results/soft-hyphen-policy-20260925/. Next: optional UI integration and fresh end-to-end examples. No downloads/cloud calls.
