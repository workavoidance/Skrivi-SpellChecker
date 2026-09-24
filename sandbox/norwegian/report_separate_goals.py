"""Post-hoc diagnostic categories; no new inference or tuning."""
import json
from pathlib import Path
from engine import words,single
from evaluate import expected
from setup_assets import ROOT,DICT_REV

HERE=Path(__file__).parent
DATA=HERE/'iteration-2026-09-05'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
lines=(ROOT/'models'/f'bokmal-lexicon-{DICT_REV[:12]}'/'nb_NO.dic').read_text(encoding='utf-8-sig').splitlines()[1:]
vocab={line.split('/')[0].split('\t')[0].strip().casefold() for line in lines}
vocab={w for w in vocab if single(w)}
report={}
for suite in ['development','fresh']:
    cases={c['id']:c for c in read(DATA/(suite+'.json'))}
    group={}
    for mode in ['default_v2','baseline','cleaner','cleaner_v4','short','phonetic','wide','agreement','fast_all']:
        path=DATA/(suite+'-'+('baseline' if mode=='default_v2' else mode)+'.json')
        if not path.exists():continue
        stats={k:dict(targets=0,flagged=0,candidate_present=0,first=0,top3=0) for k in ['unlisted_spelling','listed_context']}
        preservation=dict(other_tokens=0,other_flags=0,clean_tokens=0,clean_flags=0,clean_sentences=0,clean_sentences_untouched=0)
        examples={k:[] for k in stats}
        for row in read(path)['rows']:
            c=cases[row['id']];gold=expected(c)
            ignored=set(expected({'text':c['text'],'errors':[{**e,'suggestions':[]} for e in c.get('unscored',[])]}))
            result=row['base'] if mode=='default_v2' else row['result']
            clean_flags=0
            for w in result['words']:
                if w['id'] in ignored:continue
                if w['id'] in gold:
                    category='listed_context' if w['word'].casefold() in vocab else 'unlisted_spelling'
                    s=stats[category];answers=gold[w['id']]
                    s['targets']+=1;s['flagged']+=w['status']!='OK'
                    s['candidate_present']+=bool(set(answers)&set(w['candidates']))
                    s['first']+=bool(w['suggestions']) and w['suggestions'][0] in answers
                    s['top3']+=bool(set(answers)&set(w['suggestions']))
                    example={'word':w['word'],'intended':answers}
                    if example not in examples[category]:examples[category].append(example)
                else:
                    preservation['other_tokens']+=1;preservation['other_flags']+=w['status']!='OK'
                    if c['kind']=='clean':
                        preservation['clean_tokens']+=1;preservation['clean_flags']+=w['status']!='OK';clean_flags+=w['status']!='OK'
            if c['kind']=='clean':
                preservation['clean_sentences']+=1;preservation['clean_sentences_untouched']+=clean_flags==0
        group[mode]={'categories':stats,'preservation':preservation,'examples':examples}
    report[suite]=group
(HERE/'SEPARATE-GOALS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=['# Separate spell-checking goals','',
 'Post-hoc analysis of saved September 5 runs. No new model inference. “Listed” means present in the exact cached full-form lexicon, not independently verified correct Bokmål. Listed target errors include real-word confusions, rare forms and dictionary-coverage quirks; this is not a homophone-only benchmark. Intent labels are provisional.','']
for suite,group in report.items():
    out+=['## '+suite,'','| Approach | Unlisted: flagged / targets | Unlisted: top 3 | Listed: flagged / targets | Listed: top 3 | Clean tokens flagged | Clean sentences untouched |','|---|---:|---:|---:|---:|---:|---:|']
    for mode,r in group.items():
        a,b=r['categories'].values();p=r['preservation']
        out.append(f"| {mode} | {a['flagged']}/{a['targets']} | {a['top3']}/{a['targets']} | {b['flagged']}/{b['targets']} | {b['top3']}/{b['targets']} | {p['clean_flags']}/{p['clean_tokens']} | {p['clean_sentences_untouched']}/{p['clean_sentences']} |")
    out+=['']
out+=['## Not adequately measured','',
 '- True homophones versus merely similar spellings: needs explicit linguistic annotation, including dialect considerations.',
 '- Legitimate Bokmål variants, names and productive compounds: current lexicon membership is not a correctness guarantee.',
 '- Word joining/splitting: deliberately excluded from the token-level score; v3 has a limited joining experiment, v4/v5 do not.',
 '- Whether definitions help a writer recognise their intended word: prototype exists, no user-success measurements yet.',
 '- Grammar agreement and style rewriting: outside the current spelling scope.',
 '', 'Use these categories to diagnose the system, not to claim population-level Norwegian or dyslexia accuracy. Source controls include names and possible editorial inconsistencies. See iteration-2026-09-05/SUMMARY.md for provenance, exclusions and timing.']
(HERE/'SEPARATE-GOALS.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
print('\n'.join(out[:28]))
