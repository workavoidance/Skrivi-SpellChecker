"""Compare isolated lexical policies using cached baselines and local text only."""
import sys,json,copy,hashlib,time,argparse
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Norbert
from nuspell_backend import NativeNuspell,NuspellChecker
from experimental_lexical_coverage import CoverageNative
from audit_ask_spelling import target_metrics
from audit_recovered_baseline import diagnose,checkpoint,SUITES


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--policies',nargs='+',default=['genitive','attested','productive'])
 parser.add_argument('--output',default='lexical-coverage-20260924')
 args=parser.parse_args()
 if Path(args.output).name!=args.output:parser.error('Output must be a directory name')
 out=ROOT/'results'/args.output;out.mkdir(exist_ok=False)
 ask=json.loads((ROOT/'data/local/ask-reviewed-20260924/reviewed-cases.json').read_text(encoding='utf8'))
 suites={'ask': [c for c in ask if c['partition']=='evaluation']}
 baseline={'ask':json.loads((ROOT/'results/ask-reviewed-20260924/nuspell_context.json').read_text(encoding='utf8'))}
 for name,file in SUITES.items():
  suites[name]=json.loads((ROOT/'data/local/recovered-original/norwegian'/file).read_text(encoding='utf8'))
  baseline[name]=json.loads((ROOT/f'results/baseline-20260924/{name}-nuspell_context.json').read_text(encoding='utf8'))
 native=NativeNuspell();model=Norbert();summary={}
 all_words=sorted({t['word'] for rows in baseline.values() for r in rows for t in r['result']['words']})
 native.lookup(all_words)
 print('Dictionary prewarmed for',len(all_words),'unique words',flush=True)
 for policy in args.policies:
  wrapper=CoverageNative(policy,native=native)
  checker=NuspellChecker(model=model);checker.native=wrapper
  for name,cases in suites.items():
   base={r.get('id',r.get('case')):r for r in baseline[name]}
   rows=[]; totals=Counter(); changed=0;transitions=Counter()
   for i,c in enumerate(cases):
    previous=base[c['id']]['result']; ws=[t['word'] for t in previous['words']]
    original=native.lookup(ws); amended=wrapper.lookup(ws)
    touched=any((original[w]['known'],original[w]['suggestions'][:24]) != (amended[w]['known'],amended[w]['suggestions'][:24]) for w in ws)
    result=checker.check(c['text'],'nuspell_context') if touched else previous
    if name=='ask':
     metrics=target_metrics(c,result);old=target_metrics(c,previous)
     if c['kind']=='spelling_error':
      transitions['gained_top3']+=not old['top3'] and metrics['top3']
      transitions['lost_top3']+=old['top3'] and not metrics['top3']
    else:
     metrics,_=diagnose(c,result)
     old,_=diagnose(c,previous)
     transitions['net_top3']+=metrics.get('top3',0)-old.get('top3',0)
     if c['kind']=='clean':
      metrics['clean_cases']=1
      metrics['clean_cases_flagged']=int(metrics.get('non_target_flags',0)>0)
    totals.update(metrics);changed+=touched
    rows.append(dict(id=c['id'],metrics=metrics,recomputed=touched,result=result))
    checkpoint(out/f'{policy}-{name}.json',rows)
    if (i+1)%40==0 or i+1==len(cases):print(policy,name,i+1,'/',len(cases),'recomputed',changed,flush=True)
   summary[policy+' / '+name]=dict(cases=len(cases),recomputed=changed,metrics=dict(totals),transitions=dict(transitions))
   checkpoint(out/'summary.json',summary)
 checkpoint(out/'manifest.json',dict(complete=True,reserve_run=False,
   experiment_sha256=hashlib.sha256((ROOT/'tools/experimental_lexical_coverage.py').read_bytes()).hexdigest(),
   note='Unchanged sentences reuse exact default baseline results; affected sentences rerun. Timings not comparable.'))
 print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
