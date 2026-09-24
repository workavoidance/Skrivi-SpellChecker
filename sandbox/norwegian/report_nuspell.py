"""Summarize saved local results without re-running models."""
import json
from pathlib import Path
from evaluate import expected

HERE=Path(__file__).parent
OUT=HERE/'nuspell-experiments'
NAMES={'nuspell':'Nuspell alone','nuspell_rank':'Nuspell + candidate ranking',
       'nuspell_context':'Nuspell + broad context','nuspell_confusions':'Nuspell + fixed confusions'}
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    lines=['# Nuspell and local Norwegian context: measured results','',
        '6 September 2026. Native Nuspell 5.1.8 uses the existing Bokmål dictionary and affix/compound rules. All model inference used cached NorBERT3-small on CPU. No training, new model download or external submission of writing.', '',
        'These are the previously used 127 development and 60 source-based regression cases. The latter were fresh in the previous round, but are not a new blind test now. Labels remain provisional; source restoration does not establish Norwegian dyslexia effectiveness. No policy was tuned on these results.','']
    details={}
    for suite in ['development','fresh']:
        cases=read(HERE/'iteration-2026-09-05'/f'{suite}.json'); by_id={c['id']:c for c in cases}
        lines += ['## '+suite,'','| Approach | Errors caught | Intended first | Intended top 3 | Intended in candidates | Other-word flags | Clean sentences untouched |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        old=read(HERE/'iteration-2026-09-05'/f'{suite}-baseline.json')
        all_reports=[('Previous v4/v5', [{'case':r['id'], 'kind':r['kind'],'metrics':r['metrics'],'result':r['result']} for r in old['rows']])]
        for mode,name in NAMES.items():
            all_reports.append((name,read(OUT/f'{suite}-{mode}.json')['runs']))
        details[suite]={}
        for name,rows in all_reports:
            total={k:sum(r['metrics'][k] for r in rows) for k in rows[0]['metrics']}
            clean=[r for r in rows if r['kind']=='clean']
            untouched=sum(r['metrics']['false_alarms']==0 for r in clean)
            lines.append(f"| {name} | {total['detected']}/{total['errors']} | {total['top1']} | {total['top3']} | {total['candidate_recall']} | {total['false_alarms']} | {untouched}/{len(clean)} |")
            details[suite][name]={'totals':total, 'clean_untouched':untouched, 'cases':len(rows)}
        native=read(OUT/f'{suite}-nuspell.json')['runs']
        native_by_id={r['case']:r for r in native}
        categories={}
        for name,rows in all_reports:
            counts={k:dict(targets=0, detected=0, top1=0,top3=0,candidate_present=0) for k in ['native_recognised','native_unrecognised']}
            for row in rows:
                gold=expected(by_id[row['case']])
                native_words={w['id']:w for w in native_by_id[row['case']]['result']['words']}
                for w in row['result']['words']:
                    if w['id'] not in gold:continue
                    c=counts['native_recognised' if native_words[w['id']]['native_known'] else 'native_unrecognised']
                    answers=set(gold[w['id']]); suggestions=w['suggestions']
                    c['targets']+=1;c['detected']+=w['status']!='OK'
                    c['top1']+=bool(suggestions) and suggestions[0] in answers
                    c['top3']+=bool(answers.intersection(suggestions))
                    c['candidate_present']+=bool(answers.intersection(w['candidates']))
            categories[name]=counts
        details[suite]['by_native_recognition']=categories
        lines+=['','Native recognition is an engine decision, not an independently verified linguistic label. Other-word flags include unadjudicated names/source issues and punctuation-containing tokens that the CLI cannot safely check as a unit.','']
    lines+=['## Local authentic paragraph','',
        '16 scored error occurrences. Ambiguous intent, the school name, boundary changes and language-variety conversion remain unscored. No grammar or punctuation rewriting.','',
        '| Approach | Caught /16 | Intended first | Intended top 3 | Other-word flags |',
        '|---|---:|---:|---:|---:|']
    for mode,name in NAMES.items():
        row=next(r for r in read(OUT/f'development-{mode}.json')['runs'] if r['case']=='natural-paragraph01')
        m=row['metrics']
        lines.append(f"| {name} | {m['detected']} | {m['top1']} | {m['top3']} | {m['false_alarms']} |")
    timing=OUT/'integration-timing.json'
    if timing.exists():
        lines+=['','## Full-request timing on the authentic paragraph','',
            'Each mode has a fresh checker. First request includes native dictionary startup and model load where required; warm figures are medians of three later requests with the native word cache populated. No GPU or concurrent model benchmark was used.','',
            '| Approach | First request, seconds | Warm median, seconds |','|---|---:|---:|']
        for mode,r in read(timing)['modes'].items():
            lines.append(f"| {NAMES[mode]} | {r['first_request_seconds']:.3f} | {r['median_warm_seconds']:.3f} |")
    lines+=['','## Interpretation and next work','',
        '**Recommendation: use Nuspell + broad context as the next optional user trial, keeping the existing default unchanged.** The candidate-ranking-only mode is a useful faster comparison that avoids introducing recognised-word context flags.',
        'On the source-based regression set, native top-three recovery is 63/72, candidate ranking reaches 68/72 without extra flags, and broad context reaches 70/72 with two more other-word flags. Previous v4/v5 recovered 51/72. On development, broad context improves top-three recovery from 79/105 to 87/105, with one additional other-word flag.',
        'On the authentic paragraph, broad context improves from the previous 9/16 top-three and 7/16 first-choice recoveries to 11/16 for both. It still raises the scored hei false alarm and misses several contextual targets. The one false-alarm count excludes the previously unscored school name, ambiguous intent and boundary/variety cases; it is not the total number of questionable suggestions a user sees.',
        'The fixed-confusion alternative has lower development coverage (61/105 top-three) and does not improve the source-based or authentic-paragraph totals over candidate-only ranking. Retain it for comparison; do not prefer it as the main contextual mode.',
        '- Nuspell alone cannot detect recognised words used accidentally. Its suggestion order is a useful baseline rather than a final answer.',
        '- Candidate-only ranking measures model value without adding known-word flags. Broad context trades additional coverage against interference; fixed confusion checks restrict that coverage.',
        '- Default v2 is unchanged. All four Nuspell modes are explicitly experimental and selectable after restarting the sandbox.',
        '- No fine-tuning or Qwen comparison was performed in this round. No evidence of superiority to Lingdys is claimed.',
        '- Proper names, legal variants, realistic severe errors and a larger independently reviewed real-word confusion set still need evaluation.',
        '- Word-boundary repairs are excluded. Suggestions containing whitespace are rejected. CLI-segmented punctuation-containing words receive manual-review status with no replacement.',
        '- Verification: 16 Python tests passed in the actual cached environment; existing simulated-DOM meaning/accept/undo tests passed. All four selectable backends matched saved paragraph outputs over four runs each, and 12 invalid-input checks passed. Local HTTP tests verified all four modes, unchanged default, Unicode offsets and single-word suggestion constraints. No full visual/accessibility browser audit was performed.',
        '- See PLAN.md, LOG.md, raw per-case JSON, http-integration.json and integration-timing.json for protocol, checkpoints and evidence.','']
    (OUT/'SUMMARY.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'category-summary.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':main()
