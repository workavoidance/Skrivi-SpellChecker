# Spell-checker benchmark format

The benchmark is stored as UTF-8 JSON Lines: one independent JSON object per
line. The format keeps the source and writer population attached to every item
so results from general pupils, second-language writers, synthetic tests and
children with a confirmed diagnosis cannot be accidentally combined.

No pupil text or derived corpus data should be committed unless its licence and
consent explicitly permit redistribution. Private benchmark files should live
outside the repository.

## Benchmark record

Required fields:

| Field | Meaning |
|---|---|
| `id` | Stable, pseudonymous record identifier |
| `source` | Dataset or collection name |
| `source_record_id` | Pseudonymous source identifier, or `null` |
| `writer_group` | `diagnosed_dyslexia`, `poor_speller`, `general_pupil`, `norwegian_l2`, or `synthetic` |
| `formal_dyslexia_diagnosis` | `true`, `false`, or `null` when unknown |
| `age_or_grade` | Non-identifying age band or grade, or `null` |
| `language_standard` | `bokmal`, `nynorsk`, `mixed`, or `unknown` |
| `norwegian_first_language` | `true`, `false`, or `null` |
| `original_sentence` | Sentence containing the writer's original form |
| `original_token` | Original token or span being assessed |
| `corrected_token` | Intended token or span |
| `corrected_sentence` | Sentence with only the relevant correction applied |
| `error_type` | Source label or documented project taxonomy |
| `correction_kind` | `keep`, `replace`, `contextual_replace`, `split`, or `join` |
| `contextual_real_word_error` | Whether the original is a valid word but wrong in context |
| `collection_method` | How the writing and correction were obtained |
| `licence` | Licence or permission applying to this item |
| `redistributable` | Whether this exact record may be published |
| `notes` | Relevant non-identifying qualifications; use an empty string if none |

The benchmark deliberately allows spaces in `original_token` and
`corrected_token`. Real writing contains split and join errors, even if an early
application prototype only offers single-word replacements.

Example synthetic record:

```json
{"id":"synthetic-001","source":"synthetic","source_record_id":null,"writer_group":"synthetic","formal_dyslexia_diagnosis":null,"age_or_grade":null,"language_standard":"bokmal","norwegian_first_language":null,"original_sentence":"I morgen skal vi gå til skolen.","original_token":"skolen","corrected_token":"skolen","corrected_sentence":"I morgen skal vi gå til skolen.","error_type":"none","correction_kind":"keep","contextual_real_word_error":false,"collection_method":"hand-authored regression case","licence":"CC0-1.0","redistributable":true,"notes":"Correct control item."}
```

## Prediction record

System output is a second JSONL file keyed by the benchmark `id`:

```json
{"id":"synthetic-001","flagged":false,"suggestions":[]}
```

`suggestions` is ordered best-first and may contain at most five unique values.
The evaluator reports top-1, top-3 and top-5 correction recall. Application UI
limits, such as rejecting suggestions containing whitespace, belong in the
application output adapter rather than the benchmark: otherwise split and join
errors would disappear from evaluation.

## Commands

```powershell
python tools/spell_checker_benchmark.py validate path\to\benchmark.jsonl
python tools/spell_checker_benchmark.py score path\to\benchmark.jsonl path\to\predictions.jsonl
```

Missing predictions count as unflagged with no suggestions. Predictions for
unknown benchmark IDs fail validation. Metrics are reported overall and by
writer group, including detection precision, recall and F1; correction recall
at ranks 1, 3 and 5; and mean reciprocal rank at 5.

