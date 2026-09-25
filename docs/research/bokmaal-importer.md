# Offline Bokmål importer — 25 September 2026

## Scope and licensing assumption

User explicitly accepted proceeding with local development/testing based on the official open-use statement while the exact licence document is pursued. https://ordbokene.no/about/open-data allows use for any purpose, including commercial, subject to conditions. Its linked UiB licence page failed or redirected during inspection. We have NOT verified that dictionary definitions/examples carry the same CC BY 4.0 terms explicitly stated for Norsk ordbank. Do not label the export conclusively CC BY 4.0. Find the current licence document or obtain UiB confirmation before a general release. No contact message has been sent.

Attribution, source URL and SHA-256 hashes are stored inside the SQLite metadata. Dictionary content stays in the user's cache, outside Git. Importer code uses the project's MIT licence; that does not relicense the data.

## Implementation

`tools/import_bokmaal.py` imports the cached full article export and official concepts table (https://ord.uib.no/bm/concepts.json; linked in https://ord.uib.no/ord_2_API.html). Standard library only. No model or article download; only the small concepts table was newly fetched for this experiment.

- Expands inline usages, entity labels, fractions and article-reference labels. References are displayed as labels, not recursively replaced by possibly unrelated definitions; no reference cycles arise.
- Retains sense IDs, parent explanations, sense-specific examples and example explanations. Sub-articles/idioms are excluded from the enclosing headword rather than falsely attributed to it; separate indexing of embedded expressions remains unfinished.
- Indexes headwords and current STANDARD inflections; preserves article ambiguity and grammatical tags. Unicode normalization and case-insensitive exact lookup; no suffix guessing.
- Drops affected senses when explanation placeholders cannot be resolved; does not fabricate content. Current imported top-level sense traversal had zero rendering errors. That does not validate skipped sub-articles or etymology.
- Preserves editorial status without a filter because the meanings of numeric statuses remain unverified.
- Atomic replacement, read-only lookup, no startup downloads, persistent cache.

The optional launcher displays real dictionary help in place of the small curated set when an entry exists; curated help remains a fallback. Multiple meanings remain accessible. Example mode prefers the first sense having an example; otherwise dictionary order is used. Neither policy claims contextual sense selection. Existing speech reads the displayed text; no new audio engine. The original-word help and practice panel still use curated content.

## Measured result

Index: 56,127,488 bytes (56.13 decimal MB), 92,664 articles, 119,616 senses, 393,096 distinct form strings. 44,260 indexed articles have an example. Original source: 94,110 articles. These are not all publication-verified entries.

On the unchanged saved default baseline outputs, 775/1,068 suggestion occurrences have a definition (72.6%), 640/1,068 have an example in at least one sense (59.9%). There are 757 distinct suggestion strings. Previous curated coverage was 16/1,068; optional WordNet provided any meaning hint for 412/1,068. These definitions are richer data, not proof of better human decisions. Reused predictions include incorrect suggestions, and examples include phrases. Median individual lookup was 0.816 ms in this run; not a cold-start or end-to-end app performance claim.

Reproduce with `python tools/measure_dictionary_help.py` using the private saved baseline outputs. Public aggregate: `docs/benchmarks/2026-09-25-dictionary-help.json`. No spelling inference or private text upload occurred.

## Validation and next work

39 lightweight tests passed, seven cached-model tests skipped in that runtime. Four importer tests cover expansion, unknown references, sense/example pairing, inflections, ambiguity, absent words and preservation of a previous index after a failed rebuild. Node DOM regression checks display order, other meanings, missing examples and explicit acceptance. Local HTTP integration verified optional page/script delivery, authenticated lookup, inflections, unknown words and shutdown. This is functional validation, not a visual user study.

Next: inspect the 293 uncovered suggestion occurrences locally, determine whether gaps are absent headwords, forms or embedded expressions, confirm publication statuses and licence terms, and test explanation usefulness with real users. Do not tune spelling rankings to improve a help-coverage metric.
