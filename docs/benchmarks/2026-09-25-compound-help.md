# Compound/base-form word-help POC — 25 September 2026

## Result

Saved baseline suggestions, 1,068 occurrences / 757 distinct strings; no new spelling inference. Same saved input hashes as the first dictionary audit (listed in aggregate JSON).

| Help type | Before | Conservative POC |
|---|---:|---:|
| Direct dictionary lookup | 775 | 775 |
| Additional whole-word definition via Ordbank base | 0 | 12 |
| Both recorded compound parts explained | 0 | 49 |
| No help | 293 | 232 |
| Any of the above help | 72.6% | 78.3% |

Whole-word definition coverage alone is 787/1,068 (73.7%). Do not describe the 78.3% as definition coverage. Component explanations are explicitly labelled as parts, with examples belonging to those parts, not the whole word. Unique-string coverage rises from 560/757 to 605/757; the 61 additional occurrences represent 45 distinct words.

First-choice coverage rises from 327/423 (77.3%) to 335/423 (79.2%). No first-choice gain comes from additional whole-word base lookup. Most gains occur in second/third alternatives. This does not establish intended-answer coverage, correction quality or human usefulness.

## Variants and review

A first version allowing all recorded decompositions adds 56 component-help occurrences, reaching 843/1,068 (78.9%). Inspection found analyses such as tilse -> til + se and oppgjennom -> opp + gjennom. These parts do not necessarily help explain the whole word. The preferred POC requires the final component to have a recorded noun analysis, reducing component gains to 49 and retaining all eight first-choice gains. This is a development heuristic, not a validated semantic guarantee.

Useful-looking synthetic illustrations: notatbok -> notat + bok; barnehagesektoren -> barnehagesektor -> barnehage + sektor; forskningsoppgaven -> forskningsoppgave -> forskning + linking s + oppgave. These demonstrate form mapping and component availability only. Multiple component senses remain unranked.

Base-form results also include unusual-looking forms recorded in Ordbank. A successful explanation lookup must never become evidence that a spelling suggestion is correct. Neither candidate generation nor ranking is changed.

## Implementation and reproduction

Run `python tools/evaluate_compound_help.py` from the checkout. Uses the existing dictionary index and cached 2022 Ordbank archive. No download or cloud inference. Builds a separate persistent `LOCALAPPDATA/Skrivi/lexical/ordbank-20220201/help-baseforms.sqlite3` index only if absent. SKRIVI_CACHE_DIR is respected. New index is 53,514,240 bytes (53.51 decimal MB), containing 866,720 form/lemma/tag rows. The existing 56.13 MB dictionary and 46.43 MB Ordbank index are reused; this POC has not optimized packaging size.

All recorded non-proper normert form/lemma links valid by year are retained, rather than guessing endings. Existing dictionary inflections already cover many forms, so extra base-form gains are limited. Compound boundaries must come from the cached Ordbank table and reconstruct the base exactly, including linking letters. Both components must have direct/base dictionary help. No recursive splits, arbitrary hyphen removal or guessed segmentation. Each SQLite connection is read-only and closed after use.

Public aggregate: `docs/benchmarks/2026-09-25-compound-help.json`. Private lookup payloads: ignored `results/compound-help-20260925/lookups.json`. No sentences or lexical payloads are published. The POC is not connected to either app launcher; defaults and dictionary UI remain unchanged.

42 lightweight tests pass; seven resource-dependent tests skip. Three new tests cover exact-before-base ordering, attested inflections, recorded linking letters, rejection of invented/invalid/incomplete splits, separate component semantics and the noun guard. Unique lookup median 0.81 ms, p95 4.70 ms in the final run; one warm local diagnostic, not a general performance guarantee.

## Recommendation

Keep base lookup and recorded noun-component help as an optional fallback candidate for UI integration. It addresses 61/293 missing occurrences (20.8%), leaving 232. Do not suppress suggestions merely for lacking help. Next measure coverage on intended correct answers and evaluate whether users understand component explanations before promoting them. Broad dictionary coverage, odd alternatives and source/import limitations still need separate investigation. Existing local dictionary licence assumption and outstanding verification remain unchanged.
