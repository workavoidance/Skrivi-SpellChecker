# Importer recovery and remaining gaps — 25 September 2026

## Completed change

The importer can now index embedded sub-articles under their own complete headwords and retain explicit parent-to-expression links. `--include-embedded` enables this addition. Exact lookup never treats an expression definition as a definition of its individual words. `lookup_expressions` returns separately labelled related expressions, including their complete wording, source and sense/example pairs. Existing top-level copies take precedence over embedded duplicates.

A separate `dictionary-expanded.sqlite3` was built in the existing persistent Bokmål cache. The installed `dictionary.sqlite3`, app defaults and UI remain untouched. No additional downloads, model calls or private-text uploads.

Source inspection found 10,660 embedded occurrences / 9,129 distinct article IDs; 173 were absent from the top-level export map. All 173 were recovered, adding 192 senses and 166 distinct indexed form strings. Total index: 92,837 usable articles, 119,808 senses, 393,262 forms, 59,316 form-to-expression links, 57,634,816 bytes. Zero placeholder rendering errors in the imported sense traversal. Editorial statuses still require verification under the existing local-testing assumption.

## Measured outcome

On the same 1,068 saved suggestion occurrences, direct definition coverage remains 775 (72.6%). With the previous recorded base/compound POC: 12 additional whole-word definitions and 49 component explanations, unchanged total 836 (78.3%). There are **no new whole-word matches in this benchmark** from the 173 recovered entries. This is a useful negative result: embedded-entry recovery does not explain most current gaps.

Three still-uncovered occurrences can now be associated with separately labelled related-expression help. These remain excluded from whole-word and component coverage. For example, the explanation for an expression containing a word must not be shown as the meaning of that standalone word.

The prior ten direct-lookup failures which had a form in the export were not ten omitted definitions: inspected entries include empty definition lists, and entries containing only embedded expressions. No definition can be recovered from an empty source record.

## Remaining gap analysis

These categories are mutually exclusive, mechanically assigned in the order shown by `tools/audit_importer_gaps.py`. Counts are occurrences, not distinct words; 232 occurrences correspond to 152 distinct strings.

| Remaining gap | Occurrences |
|---|---:|
| Contains hyphen/space; removing separators still gives no definition or complete component help | 113 |
| Contains hyphen/space; joined spelling has help | 5 |
| Only a related expression has help | 3 |
| Current source form exists, but contains no usable standalone definition | 2 |
| Ordbank marks the word as a proper name | 11 |
| Ordbank provides a base-form link, but no usable whole-word/component help follows | 53 |
| No recorded base-form link in the filtered Ordbank index | 45 |
| Total | 232 |

These are lookup-routing categories, not judgments that words are invalid, or that every recorded form is a good suggestion. Names can also occur in other categories. Arbitrarily stripping hyphens has NOT been enabled: it would change the proposed word, and only five of 118 separator-bearing occurrences gain help from even that diagnostic. This count differs from the earlier grouping, which gave recorded compound analyses priority over separator detection.

## Recommendation

A complementary definition source is now a reasonable next coverage experiment for the legitimate dictionary gaps. First keep separator-bearing alternatives identifiable in that assessment: otherwise they dominate the missing count and may obscure gains for ordinary words. Do not delete such suggestions merely to improve coverage. Candidate-quality review is a separate task, and neither dictionary presence nor absence proves correctness.

No more unrestricted flattening of nested dictionary text is warranted. The recovered expressions can be surfaced as related-expression help later, but must retain their complete wording and separate label. Coverage does not establish user usefulness or intended-answer coverage.

## Reproduction and validation

Build with `python tools/import_bokmaal.py --source <cached-articles.gz> --concepts <cached-concepts.json> --output <cache>/dictionary-expanded.sqlite3 --include-embedded`, then `python tools/audit_importer_gaps.py`. The audit uses the installed original index, expanded index, existing Ordbank/base-form caches and saved baseline outputs. Hashes are recorded in `2026-09-25-importer-gaps.json`.

Private per-word routing audit: ignored `results/importer-gaps-20260925/word-audit.json`. Source dictionary data and private writing are not in Git. 43 lightweight tests pass; seven resource tests skip. Added regression verifies standalone expression lookup, parent-link lookup, no automatic meaning transfer to individual words, no inferred reverse links and top-level precedence.
