import json
from pathlib import Path
HERE=Path(__file__).parent
comparisons=[('Development','extended-results.json','candidate-v2-development.json'),
             ('Published source','sourced-results.json','candidate-v2-sourced.json'),
             ('Reserved sentences','candidate-v2-reserved.json','candidate-v2-reserved.json')]
lines=['# Candidate revision comparison','',
'The baseline remains available as norbert; the revision is norbert_v2. Both use the same cached NorBERT weights and context thresholds. Changes: Optimal String Alignment edit distance (adjacent swaps cost one edit), up to 24 candidates rather than eight, no introduced hyphen for an unhyphenated input, and a 1.5-point penalty per edit beyond the first when ranking unknown words. Known-word confusion groups are unchanged. There is no new model download.', '',
'The revision was fixed before evaluating reserved-regression.json. Those 24 synthetic sentences are now used evaluation data, no longer an unused holdout. The developer/source sets were already inspected and therefore are development evidence, not independent evaluation.', '',
'| Set | Version | Errors | Flagged | Expected first | Expected top 3 | Expected in candidates | Non-target flags | Median seconds |',
'|---|---|---:|---:|---:|---:|---:|---:|---:|']
for title,oldfile,newfile in comparisons:
    for label,filename,mode in [('Original',oldfile,'norbert'),('Revised',newfile,'norbert_v2')]:
        data=json.loads((HERE/filename).read_text(encoding='utf-8'))
        s=data['summary'][mode]
        assert s['failed']==0
        lines.append(f"| {title} | {label} | {s['errors']} | {s['detected']} | {s['top1']} | {s['top3']} | {s['candidate_recall']} | {s['false_alarms']} | {s['median_check_seconds']:.3f} |")
lines+=['','Non-target flags include both original and altered corpus copies, so source totals count repeated occurrences. They are not adjudicated false positives: source material contains names, foreign words and possible pre-existing errors. Expected correction means exact answer-key/source restoration; another accepted spelling may be valid. Timings are single runs, include different mixes of model work and exclude lazy loading. More candidates generally mean more processing.', '',
'## Per-case improvements and regressions','']
for title,oldfile,newfile in comparisons:
    old=json.loads((HERE/oldfile).read_text(encoding='utf-8'))
    new=json.loads((HERE/newfile).read_text(encoding='utf-8'))
    oldrows={r['case']:r for r in old['runs'] if r['mode']=='norbert'}
    lines+=['### '+title,'','| Case | Change in first suggestion | Change in top three |','|---|---:|---:|']
    for r in new['runs']:
        if r['mode']!='norbert_v2':continue
        b=oldrows[r['case']]
        d1=r['metrics']['top1']-b['metrics']['top1'];d3=r['metrics']['top3']-b['metrics']['top3']
        if d1 or d3:lines.append(f"| {r['case']} | {d1:+d} | {d3:+d} |")
lines+=['','## Remaining limits','',
'This change improves spelling-repair choices, not name recognition or compound analysis. Unknown names/compounds remain uncertain; they are not silently marked correct. The viste/visste and skule/skulle coverage gaps remain. The earlier Gjem/Hjem false alarm remains possible. These need separate paired correct/incorrect tests. Candidate ranking is heuristic and still makes mistakes; no automatic text changes are made. Original model/checker behavior is preserved for comparison.']
(HERE/'CANDIDATE-REVISION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:16]))
