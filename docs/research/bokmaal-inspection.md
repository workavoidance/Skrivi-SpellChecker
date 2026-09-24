# Bokmålsordboka offline-data inspection

Downloaded 21 September 2026 from the [official UiB export](https://ord.uib.no/bm/fil/article.json.gz), linked by the [official download documentation](https://ord.uib.no/ord_1_Ordlister.html).

## Measured size

Sizes below are decimal MB, not MiB.

| Data | Compressed | Uncompressed JSON |
|---|---:|---:|
| Original export | 19.09 MB | 200.40 MB |
| Experimental reduced extract | 9.66 MB | 69.21 MB |

The extract retains article IDs, headwords, current STANDARD inflected forms and full definition trees, including examples, references and nested expressions. It removes much article/lemma metadata. It is a size experiment, not a production database: grammar tags, entity expansion tables, licence notices and lookup indexes still need consideration. Uncompressed JSON size is not a RAM measurement; Python objects may consume substantially more memory. An indexed database would avoid loading all content into memory.

## Structural coverage

Across all 94,110 top-level records in this export:

- 93,326 (99.2%) contain a nonempty definition/explanation element, including nested senses and expressions.
- 44,983 (47.8%) contain at least one example.
- There are 100,059 example occurrences in the traversed trees. This is not a deduplicated sentence count: examples can be phrases, and nested entries can repeat material.
- 102,873 distinct headword strings and 400,115 distinct headword/current-standard-form strings occur in the extracted mapping.

The export contains multiple numeric editorial statuses. No publication-status filter was inferred. Status 8 alone accounts for 91,593 records, with 90,851 containing definition elements and 44,310 containing examples. Status semantics and public/current eligibility must be confirmed for production.

These are structural counts, not proof of useful explanations for 99.2% of Skrivi suggestions. A definition can be a short synonym, a reference, or belong to a nested expression rather than the main sense. Coverage for actual correction suggestions remains unmeasured.

## Spot checks

The entries for gjerne, hjerne, bibliotek, nøkkel, lekse, budsjett, venninne, brettspill, sommerfugl and kompensere all contain definitions and examples. These are a small, deliberately selected set, not a random quality sample.

## Important implementation findings

Definitions and examples preserve their sense hierarchy. Keep them paired by sense instead of flattening everything into one unrelated list.

Many text fields contain dollar-sign placeholders whose values live in structured items. Of the nonempty explanation elements counted, 95,032 contain such placeholders. Some items refer to another article; others refer to shared entities. A naive text-only import would produce incomplete definitions. The full importer must render those items, resolve cross-references and handle cycles/missing targets.

Inflection information is already present. Link forms to article IDs instead of copying definitions for every form. Some forms lead to several articles; preserve that ambiguity.

## Recommendation

This looks small enough to bundle and promising as the primary definition source. It cannot supply an example for every entry by itself. Build a proper offline importer, confirm the exact release licence/publication policy, then measure useful definition/example coverage against the application's real candidate lists. Prefer dictionary content first and add reviewed gap-filling content only where needed.

No application code was changed. The original download, reduced size prototype, audit script, sample records and machine-readable metrics are retained beside this report. No user's writing was sent to the dictionary service.
