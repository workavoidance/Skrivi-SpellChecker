"""Counterfactual replay: no model calls, no source text in public output."""
import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from setup_assets import ROOT as CACHE,DICT_REV
from hyphen_policy import HyphenPolicy

ROOT=Path(__file__).resolve().parents[1]
VARIANTS=['guard','guard_native_tiebreak','guard_gap']
def main():
    db=sqlite3.connect((CACHE/'lexical/ordbank-20220201/ordbank.sqlite3').as_uri()+'?mode=ro',uri=True)
    forms={r[0] for r in db.execute('SELECT word FROM form')};db.close()
    dic=CACHE/'models'/('bokmal-lexicon-'+DICT_REV[:12])/'nb_NO.dic'
    explicit={line.split('/')[0].strip().casefold() for line in dic.read_text(encoding='utf-8-sig').splitlines()[1:]}
    policy=HyphenPolicy(lambda w:w in forms or w in explicit,lambda w:w in forms or w in explicit)
    report={};details=[]
    def evaluate(label,rows,targets):
        groups={}
        for variant in VARIANTS:
            count=collections.Counter()
            for row,ts in zip(rows,targets):
                if 'result' not in row:continue
                result=row['result'];mapped={}
                for token in result['words']:
                    shown=policy.apply(token,variant);mapped[token['id']]=shown
                    count['shown_before']+=len(token['suggestions']);count['shown_after']+=len(shown)
                    count['hyphen_before']+=sum('-' in x for x in token['suggestions']);count['hyphen_after']+=sum('-' in x for x in shown)
                    count['fewer_than_three_after']+=token['status']!='OK' and len(shown)<3
                for token,answers in ts(result):
                    if answers is None:
                        count['controls']+=1;count['control_flags']+=token['status']!='OK';continue
                    before=token['suggestions'] if token['status']!='OK' else [];after=mapped[token['id']] if token['status']!='OK' else []
                    count['targets']+=1
                    for n in (1,3):
                        old=bool(set(before[:n])&set(answers));new=bool(set(after[:n])&set(answers))
                        count[f'top{n}_before']+=old;count[f'top{n}_after']+=new
                        count[f'top{n}_gains']+=new and not old;count[f'top{n}_losses']+=old and not new
                        if old and not new:details.append({'suite':label,'variant':variant,'metric':n,'word':token['word'],'answers':answers,'before':before,'after':after})
            groups[variant]=dict(count)
        report[label]=groups
    historical=[];ht=[]
    for p in sorted((ROOT/'results/baseline-20260924').glob('*-nuspell_context.json')):
        for row in json.loads(p.read_text(encoding='utf-8')):
            historical.append(row)
            ds=row.get('details',[])
            def getter(result,ds=ds):
                byid={w['id']:w for w in result['words']}
                return [(byid[d['token_id']],d['answers']) for d in ds]
            ht.append(getter)
    evaluate('historical',historical,ht)
    folder=ROOT/'data/local/expanded-20260924';cases=json.loads((folder/'cases.json').read_text(encoding='utf-8'));excluded=set(json.loads((folder/'label-audit.json').read_text())['excluded_pair_ids'])
    for mode in ['nuspell_context','nuspell_coverage']:
        rows=[json.loads(l) for l in (ROOT/f'results/expanded-20260924/{mode}.jsonl').read_text(encoding='utf-8').splitlines()]
        for group in ['authentic','synthetic','stress']:
            selected=[];targets=[]
            for case,row in zip(cases,rows):
                assert case['id']==row['id']
                if case['group']!=group or group=='authentic' and case['pair_id'] in excluded:continue
                selected.append(row)
                def getter(result,case=case):
                    out=[]
                    for t in case['targets']:
                        match=[w for w in result['words'] if w['start']==t['target_start'] and w['end']==t['target_end'] and w['word']==t['target_word']]
                        if len(match)!=1:raise ValueError('Target mismatch')
                        out.append((match[0],None if t['kind']=='target_control' else t['acceptable']))
                    return out
                targets.append(getter)
            if selected:evaluate(mode+'_'+group,selected,targets)
    out=ROOT/'results/hyphen-policy-20260925';out.mkdir(exist_ok=True)
    (out/'regressions.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
    legitimate=['e-post','TV-utvalg','tv-utvalg','x-akse','EU-motstander','FM-sender',
                '50-årsdag','A4-format','ikke-røyker','romersk-katolsk','svart-hvitt',
                'tur-retur-billett','Nord-Europa','Ny-Zealand','pc-en','Oslo-jente',
                'Office-programmene','trafikk-kork','skole-elev','norsk-engelsk']
    probe={w:policy.evidence(w.replace('-',''),w) for w in legitimate}
    inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*sorted((ROOT/'results/baseline-20260924').glob('*-nuspell_context.json')),
                      ROOT/'data/local/expanded-20260924/cases.json',
                      ROOT/'data/local/expanded-20260924/label-audit.json',
                      ROOT/'results/expanded-20260924/nuspell_context.jsonl',
                      ROOT/'results/expanded-20260924/nuspell_coverage.jsonl']}
    result={'legitimate_form_probe':probe,'input_hashes':inputs,'groups':report,'dictionary_sha256':hashlib.sha256(dic.read_bytes()).hexdigest(),
            'limitations':['Saved-score replay; no scoring normalization or model inference change.',
                          'Reused tests; no new independent accuracy claim.',
                          'Hyphen counts are not human-adjudicated bad-suggestion counts.',
                          'Original detection/status preserved, including flags whose suggestions become empty.']}
    (ROOT/'docs/benchmarks/2026-09-25-hyphen-policy.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
