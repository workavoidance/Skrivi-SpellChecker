# Softer hyphen suggestion policy — 25 September 2026

## Decision

Prefer the extended soft policy for a future optional UI trial. It stably puts supported suggestions first and retains every eligible candidate, instead of deleting uncertain hyphen constructions. This is an experimental replay, not an app/default change. The first three are returned in `shown`; the remainder in `more`. The app does not yet expose that additional list.

## Measured results

Reused the existing saved NorBERT scores and candidate pools, including the wider local Norwegian learner suite. No pupil text left the machine. Counts below are intended-answer matches, not general spelling accuracy. Groups overlap and must not be added together.

| Group | Targets | Correct first: before → after | Correct in top three: before → after |
|---|---:|---:|---:|
| Historical | 277 | 246 → 248 | 257 → 257 |
| Learner default | 297 | 245 → 261 | 274 → 274 |
| Learner optional coverage | 297 | 247 → 263 | 277 → 277 |
| Synthetic default | 120 | 58 → 58 | 60 → 60 |
| Synthetic optional coverage | 120 | 108 → 108 | 118 → 118 |
| Stress default | 192 | 89 → 90 | 98 → 98 |
| Stress optional coverage | 192 | 169 → 172 | 191 → 191 |

No individual first-choice or top-three losses versus the existing baseline in these groups. Detection is deliberately unchanged: four learner control warnings remain. Historical displayed hyphen suggestions drop from 118 to 21; this is not a count of verified incorrect suggestions. Total displayed choices remain 1,068.

The narrower soft variant earns one extra learner first-choice success in each mode, but recognizes fewer legitimate constructions. We prefer the extended evidence despite that tradeoff.

## Legitimate constructions and limitations

The previous 20-form diagnostic now recognizes 18; a further 20 constructed legitimate examples recognizes all 20. All 40 remain eligible. Unknown brand `Office-programmene` and optional readability spelling `skole-elev` remain demoted when enough supported alternatives exist. Twelve previously observed suspect splits all move below the first three in constructed four-candidate probes, but remain available.

These are synthetic gate tests with constructed scores, not end-to-end accuracy tests. During development, adjective combinations exposed a data issue: the compact Ordbank table retains one analysis per spelling. The policy now uses all adjective analyses in the existing base-form index. Consequently these diagnostics are development examples, not an untouched validation set. Recorded adjective/name status is supporting evidence, not proof a compound is correct.

The linguistic basis includes [Språkrådet’s hyphen guidance](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/tegn/bindestrek/). Our lexical heuristics do not implement every permitted construction.

## Reproduction and next step

Run `tools/evaluate_soft_hyphen_policy.py` with the existing cached Ordbank, base-form index and Nuspell word list. It replays saved local scores, records input hashes in the adjacent aggregate JSON and keeps raw outputs in ignored `results/soft-hyphen-policy-20260925/`. No downloads or model calls. Existing score threshold, detection, already-hyphenated input and special paths are preserved.

Validation: 51 lightweight tests passed, seven resource-dependent tests skipped. Tests cover ordering, candidate retention, input immutability, legitimate evidence and preserved thresholds/special paths.

Next: optional UI integration with an explicit more-suggestions action, followed by fresh end-to-end cases. No need for the user to run technical tests; human feedback is useful later for whether the resulting choices are easier to understand. No new definition coverage or latency measurement was made.
