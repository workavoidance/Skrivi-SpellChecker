"""Offline threshold sensitivity only: no model reruns and no app changes."""
import copy,json
from pathlib import Path
from collections import Counter
from audit_recovered_baseline import ROOT,SUITES,diagnose
from audit_ask_spelling import target_metrics


def at_threshold(result,threshold):
 r=copy.deepcopy(result)
 for token in r['words']:
  if not token.get('native_known') or not token.get('scores'):continue
  values=dict(token['scores']); original=values[token['word']]
  suggestions=[w for w,s in token['scores'] if w!=token['word'] and s-original>threshold][:3]
  token['suggestions']=suggestions;token['status']='UNCERTAIN' if suggestions else 'OK'
 return r


def main():
 suites={'ask':[c for c in json.loads((ROOT/'data/local/ask-reviewed-20260924/reviewed-cases.json').read_text(encoding='utf8')) if c['partition']=='evaluation']}
 results={'ask':json.loads((ROOT/'results/ask-reviewed-20260924/nuspell_context.json').read_text(encoding='utf8'))}
 for name,file in SUITES.items():
  suites[name]=json.loads((ROOT/'data/local/recovered-original/norwegian'/file).read_text(encoding='utf8'))
  results[name]=json.loads((ROOT/f'results/baseline-20260924/{name}-nuspell_context.json').read_text(encoding='utf8'))
 report={}
 for threshold in [4.0,3.0,2.0]:
  for name,cases in suites.items():
   rows={r.get('id',r.get('case')):r['result'] for r in results[name]}; counts=Counter()
   for case in cases:
    result=at_threshold(rows[case['id']],threshold)
    if name=='ask':counts.update(target_metrics(case,result))
    else:
     metrics,_=diagnose(case,result);counts.update(metrics)
     if case['kind']=='clean':
      counts['clean_cases']+=1;counts['clean_cases_flagged']+=metrics.get('non_target_flags',0)>0
   report[str(threshold)+' / '+name]=dict(counts)
 out=ROOT/'results/lexical-coverage-20260924/threshold-sensitivity.json'
 out.write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({k:{x:v.get(x,0) for x in ['top3','detected','control_false_flags','non_target_flags','clean_cases_flagged']} for k,v in report.items()},indent=2))

if __name__=='__main__':main()
