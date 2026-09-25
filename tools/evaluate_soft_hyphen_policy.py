"""Replay softer policy, plus a frozen synthetic gate diagnostic."""
import json
from pathlib import Path
import sqlite3
from contextlib import redirect_stdout
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from setup_assets import ROOT as CACHE,DICT_REV
from soft_hyphen_policy import SoftHyphenPolicy
from evaluate_hyphen_policy import main as replay, ROOT

# Frozen before evaluating: prior examples separately labelled from new diagnostics.
PRIOR=['e-post','TV-utvalg','tv-utvalg','x-akse','EU-motstander','FM-sender','50-årsdag','A4-format','ikke-røyker','romersk-katolsk','svart-hvitt','tur-retur-billett','Nord-Europa','Ny-Zealand','pc-en','Oslo-jente','Office-programmene','trafikk-kork','skole-elev','norsk-engelsk']
NEW=['Bergen-jente','Trondheim-gutt','Oslo-dialekten','svensk-norsk','dansk-tysk','fransk-engelsk','norsk-svensk','pc-utstyr','sms-varsling','DNA-analyse','EU-land','FN-møte','IT-avdeling','x-retning','y-akse','50-åring','20-årsdag','e-bok','T-skjorter','ikke-medlem']
NEGATIVE=['nøkk-lene','notat-bokk','finn-nes','fles-ste','kalender-ren','land-enes','Hann-ah','Sig-ny','Svin-dal','Knaus-gård','studentforening-er','operasjonsteam-et']

def main():
    db=sqlite3.connect((CACHE/'lexical/ordbank-20220201/ordbank.sqlite3').as_uri()+'?mode=ro',uri=True)
    props={w:{'display':display,'proper':bool(proper),'tag':tag} for w,display,proper,tag in db.execute('SELECT word,display,proper,tag FROM form')};db.close()
    # Compact form table keeps only one analysis; consult all cached base analyses.
    base=sqlite3.connect((CACHE/'lexical/ordbank-20220201/help-baseforms.sqlite3').as_uri()+'?mode=ro',uri=True)
    for (form,) in base.execute("SELECT DISTINCT form FROM base WHERE tag LIKE 'adj %'"):
        props.setdefault(form,{})['adjective']=True
    base.close()
    dic=CACHE/'models'/('bokmal-lexicon-'+DICT_REV[:12])/'nb_NO.dic'
    listed=set(props)|{l.split('/')[0].strip().casefold() for l in dic.read_text(encoding='utf-8-sig').splitlines()[1:]}
    policy=SoftHyphenPolicy(lambda w:w in listed,lambda w:w in listed,props.get)
    folder=ROOT/'results/soft-hyphen-policy-20260925';folder.mkdir(exist_ok=True)
    with (folder/'replay-console.json').open('w',encoding='utf-8') as stream:
        with redirect_stdout(stream):replay(policy,['soft_narrow','soft_extended'],'soft-hyphen-policy')
    probes={}
    for group,words in [('prior_legitimate',PRIOR),('new_constructed_legitimate',NEW),('suspect_splits',NEGATIVE)]:
        rows=[]
        for word in words:
            token={'word':word.replace('-',''),'status':'UNCERTAIN','native_known':False,
                   'suggestions':[word,'alternativeone','alternativetwo'],
                   'scores':[(word,-1),('alternativeone',-2),('alternativetwo',-3),('alternativethree',-4)]}
            result=policy.partition(token)
            rows.append({'candidate':word,'support':policy.extended_evidence(token['word'],word),
                         'preserved':word in result['shown']+result['more'],'in_first_three':word in result['shown']})
        probes[group]={'count':len(rows),'supported':sum(bool(r['support']) for r in rows),'preserved':sum(r['preserved'] for r in rows),'rows':rows}
    path=ROOT/'docs/benchmarks/2026-09-25-soft-hyphen-policy.json';report=json.loads(path.read_text(encoding='utf-8'))
    report['legacy_narrow_form_probe']=report.pop('legitimate_form_probe')
    report['synthetic_gate_diagnostic']=probes
    report['limitations'] += ['Synthetic gate probes use constructed scores, not fresh model inference. They test retention/demotion only.', 'More suggestions exists only in the experimental return payload; app UI is unchanged.', 'Name/adjective evidence is a heuristic; lexical properties can be ambiguous and are not proof of correct usage.']
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'groups':report['groups'],'probes':{k:{a:b for a,b in v.items() if a!='rows'} for k,v in probes.items()}},indent=2))
if __name__=='__main__':main()
