import json
from pathlib import Path
HERE=Path(__file__).parent
data=json.loads((HERE/'scoring-all-summary.json').read_text(encoding='utf-8'))
assert data['scoring-development-cache']['baseline']['cases']==41
assert data['scoring-validation-cache']['baseline']['cases']==60
names={'baseline':'Default v2','broad_v3':'Broad partial masking (reference)',
       'whole_mask':'1. Whole-word masking','agreement':'2. Agreement',
       'context_gain':'3. Context-vs-neutral adjustment','single_token':'4. Single-token restriction',
       'strict_margin':'5. Stricter partial-score margin'}
lines=['# Five contextual-scoring experiments','',
'## Fixed protocol','',
'All methods use the same cached NorBERT3-small, the same spelling candidates, and the default v2 result as a starting point. They add comparisons only for recognised lowercase alphabetic words of three or more letters. No compound joining is included: this experiment isolates real-word spelling errors. Unknown-word suggestions and existing v2 flags are retained. No answers are passed to model scoring.', '',
'1. **Whole-word masking:** mask every target subtoken simultaneously, then average the log probabilities of the candidate pieces. Other candidate letters are no longer visible. Require a score advantage above 4.',
'2. **Agreement:** whole-word and previous partial masking must favour the same best candidate, with both score gaps above 4.',
'3. **Context-vs-neutral adjustment:** subtract each candidate’s score with no surrounding sentence from its whole-mask contextual score; require a gain advantage above 4 and partial-mask advantage above 4.',
'4. **Single-token restriction:** whole-word masking, but only when the original and suggested candidate each occupy one tokenizer token. This tests a way to avoid comparisons across different segmentations.',
'5. **Stricter margin:** retain partial masking but require an advantage above 8 instead of 4.', '',
'All thresholds were fixed before validation. Whole-word masking was the leading method on development; no thresholds were retuned after viewing fresh-set results. These views share one model, so agreement is not independent-model confirmation. Whole masking still exposes candidate subtoken count and still uses mean scores: length/segmentation bias is reduced in one respect, not eliminated.', '',
'## Data','',
'Development: 41 previously used constructed sentences, 19 intended errors and 22 clean controls. Fresh validation: 60 inputs, with 20 source-word mutations, their 20 untouched originals, and 20 additional untouched originals. Source sentence IDs exclude the previous 100-sentence sourced benchmark. Both pair members remain in validation. Seed 92405. Error families were selected before model scoring, with at most three examples per source word. Actual original targets: vil (3), skulle (3), får (3), gjerne (2), vært (3), sammen (3), legge (3). The original words viste/visste and some other desired families were not selected, so fresh coverage is narrow.', '',
'Fresh text comes from [UD Norwegian-Bokmaal/NDT](https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal), with its revision, sentence IDs and original text retained in scoring-validation.json. Original and derived text are CC BY-SA 4.0; attribution and upstream license are in corpus-source. NDT was developed by the National Library of Norway with the University of Oslo; contributors are credited in corpus-source/README.md. These are source-restoration labels, not independently adjudicated Norwegian spelling errors. Newness here means disjoint from our earlier experiments, not exclusion from model pretraining.', '',
'Two model forwards on the same input need not be performed per policy: raw partial, whole and neutral scores were collected once and policies evaluated deterministically from that shared cache. Reported policy cases are not seven independent inference runs. Collection includes all scoring approaches, and its duration must not be reported as the latency of the winning approach.']
for key,title in [('scoring-development-cache','Development: 19 errors'),('scoring-validation-cache','Fresh validation: 20 errors')]:
    group=data[key]
    lines+=['','## '+title,'','| Method | Targets flagged | Expected first | Expected top 3 | Other-word flags | Clean sentences unflagged |','|---|---:|---:|---:|---:|---:|']
    for mode,row in group.items():
        lines.append(f"| {names[mode]} | {row['detected']} | {row['top1']} | {row['top3']} | {row['false_alarms']} | {row['clean_unflagged']}/{row['clean']} |")
lines+=['','Other-word flags in published text are not verified false alarms. Some are names, foreign text, or possible source errors. Counts include both members of each pair. A better exact-source score also does not prove every alternative correction is invalid.', '',
'## Verification and reproduction','',
'Eight Python tests passed, including a test that all target letters are masked, context remains visible, same-length candidates produce identical masked inputs, and agreement abstains when scorers disagree. Existing occurrence, whitespace and candidate contracts passed. No automatic corrections are performed.', '',
'Run context_experiments.py --cases scoring-development.json --output scoring-development-cache.json; repeat for scoring-validation.json. Then summarize both cache files with --summarize and output scoring-all-summary.json. report_context_experiments.py creates this report. Source SHA-256 hashes and collection-script hashes are recorded in cache files. The existing model cache is reused.']
lines+=['','## Decision and app integration','',
'Whole-word masking is exposed as Helordskontekst (nytt eksperiment), mode norbert_v4. The default stays v2 because whole masking adds three non-target flags on fresh validation: one inappropriate tilsi replacement in an altered sentence, and trinnet in both versions of a source pair. Those are two distinct word locations across three inputs. The context-adjusted method is a useful more conservative research alternative: it restores 19/20 fresh targets with the baseline flag count, but added flags on development. No method is established as universally safest.', '',
'verify_whole_integration.py reran all 41 development texts through the app engine and verified exact status/suggestion equality with the frozen offline policy. Eight Python contract tests passed. No model or dependency download was needed. This is integration/logic verification, not a fresh browser accessibility audit.', '',
'A final check used the previously generated Very bad paragraph and its clean counterpart (whole-profile-check.json). v4 adds the intended huske and legge corrections; the number of flagged units rises from 12 to 14. Both modes leave the clean counterpart unflagged. Other intended errors remain, including the split compound, which v4 intentionally does not handle. Many severe unknown-word suggestions remain poor because those still use v2 scoring. Context recovery also remains difficult when surrounding words are damaged; this check is exploratory rather than proof of that causal explanation.']
(HERE/'CONTEXT-EXPERIMENTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[-28:]))
