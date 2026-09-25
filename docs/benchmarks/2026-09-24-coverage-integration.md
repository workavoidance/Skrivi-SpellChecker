# Optional candidate coverage: targeted diagnostic and integration

The validated proposal-only policy is now available as an opt-in mode in both responsive interfaces. The default remains Nuspell plus NorBERT3 Small. No model downloads or external inference were used.

## New diagnostic

A newly authored synthetic set contains 19 misspellings focused on noun possessives and compounds, paired with correct targets plus one additional compound control. It is a diagnostic tailored to these rules, not an independent learner-writing benchmark. Targets are assistant-authored, not Norwegian-human adjudicated; lexical overlap with earlier sets was not excluded. Raw cases and traces remain in ignored `data/local/coverage-targeted-20260924/` and `results/coverage-targeted-20260924/`.

| Measurement | Default | Proposal-only |
| --- | ---: | ---: |
| Correct suggestion in top three | 11/19 | 19/19 |
| Correct suggestion first | 8/19 | 13/19 |
| Correct targets incorrectly flagged | 8/20 | 0/20 |
| Median subsequent check | 0.732 s | 0.811 s |
| Subsequent check p95 | 0.914 s | 1.420 s |
| First check, excluding setup | 5.960 s | 6.548 s |
| Setup | 0.804 s | 1.535 s |
| Peak process working set | 855.7 MiB | 964.3 MiB |

Timing is one fresh process per mode, with identical sentence order and shared caches between paired checks. It measures the frozen experimental wrapper before UI integration. These are indicative timings, not repeated performance estimates or machine memory requirements. Private committed memory was 1469.9 versus 1568.0 MiB. Detailed aggregate measurements and dataset hash are in the adjacent JSON.

Earlier evidence remains relevant: ASK top-three 95 to 98/100, historical 257 to 258/277, and consumed reserve unchanged at 18/20. Teo's historical score remains 11/16; no improvement on his paragraph is claimed.

## Integration and validation

`lexical_coverage.py` implements only the selected proposal-only policy. It recognizes supported noun possessives and adds compound candidates, but frequency never establishes correctness. Context ranking and thresholds remain unchanged. Native raw suggestions remain separate from added coverage candidates.

Cached Ordbank and frequency databases are required. When absent, the interface disables the option and the API returns a clear error without loading the model. It never downloads resources. SQLite connections are read-only and support sequential requests from different server threads; checks are serialized.

A real localhost HTTP smoke test verified the optional selector, unchanged default selection, two successive optional requests, unchanged source text, single-word replacement, Unicode offsets, at most three single-word suggestions, and identical default results before/after. Its own server was stopped afterwards. Seven coverage contract/parity tests and 14 sandbox regression tests passed; the lightweight suite passed 25 tests with resource-dependent tests skipped.

## Use and next work

Restart `sandbox/Start-Skrivi.cmd` and choose the extra-word-suggestions experiment in the control selector (Norwegian label: Flere ordforslag, utproving). The normal default remains selected. Both responsive variants support it.

Keep this optional while gathering independent examples. Definition/example coverage and the two ASK detection misses remain unresolved. Do not lower detection thresholds based on this diagnostic. Fresh-machine installation and broad human usability are not validated here.
