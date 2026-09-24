"""Aggregate frozen, synthetic-only ranking comparison; never publish sentences."""
import json,statistics
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def score(case,prediction):
 keep=prediction['decision']=='keep';choices=prediction['choices'];gold=set(case['gold'])
 if case['kind']=='target_control':return dict(controls=1,unnecessary_reviews=int(not keep))
 available=bool(gold.intersection(o['word'] for o in case['payload']['options']))
 top1=int(not keep and bool(choices) and choices[0] in gold)
 top3=int(not keep and bool(gold.intersection(choices[:3])))
 return dict(errors=1,candidate_available=int(available),top1=top1,top3=top3,top1_when_available=top1 if available else 0,top3_when_available=top3 if available else 0,keep_on_error=int(keep))

def main():
 data=ROOT/'data/local/cloud-reference-20260924';out=ROOT/'results/cloud-reference-20260924'
 cases=json.loads((data/'frozen.json').read_text(encoding='utf8'));cloud={r['id']:r for r in map(json.loads,(out/'predictions.jsonl').read_text(encoding='utf8').splitlines())}
 ledger=json.loads((out/'ledger.json').read_text());groups={};changes={};invalid=0
 for c in cases:
  if c['id'] not in cloud:continue
  group='synthetic_context' if c['category']=='authored_context' else 'synthetic_morphology'
  metrics={name:score(c,pred) for name,pred in [('unranked',c['unranked']),('norbert',c['local']),('reference',cloud[c['id']])]}
  for name,m in metrics.items():groups.setdefault(group,{}).setdefault(name,Counter()).update(m)
  change=changes.setdefault(group,Counter());a,b=metrics['norbert'],metrics['reference']
  if 'errors' in a:
   for metric in ['top1','top3']:
    change[metric+'_gains']+=int(b[metric]>a[metric]);change[metric+'_losses']+=int(b[metric]<a[metric])
  else:
   change['warnings_added']+=int(b['unnecessary_reviews']>a['unnecessary_reviews']);change['warnings_removed']+=int(b['unnecessary_reviews']<a['unnecessary_reviews'])
 requests=ledger['requests'];usage=Counter()
 audit_path=out/'isolation-predictions.jsonl';audit=[]
 if audit_path.exists():audit=list(map(json.loads,audit_path.read_text(encoding='utf8').splitlines()))
 case_map={c['id']:c for c in cases}
 audit_summary=dict(cases=len(audit),same_scored_outcome=sum(score(case_map[r['id']],r)==score(case_map[r['id']],cloud[r['id']]) for r in audit),same_decision=sum(r['decision']==cloud[r['id']]['decision'] for r in audit))
 primary=[r for r in requests if not r.get('isolation_audit')]
 for r in requests:
  if r.get('usage'):
   usage['input_tokens']+=r['usage']['input_tokens'];usage['output_tokens']+=r['usage']['output_tokens'];usage['reasoning_tokens']+=r['usage'].get('output_tokens_details',{}).get('reasoning_tokens',0)
 report=dict(isolation_audit=audit_summary,primary_requests=len(primary),audit_requests=len(requests)-len(primary),model=ledger['model'],returned_models=sorted({r.get('model_returned','unknown') for r in requests}),reasoning='medium',completed=len(cloud),planned=len(cases),groups=groups,changes=changes,usage=dict(usage),requests=len(requests),request_statuses=dict(Counter(r['status'] for r in requests)),estimated_standard_usd=sum(r.get('estimated_standard_usd',r['reserved_usd']) for r in requests),conservative_accounted_usd=ledger['accounted_usd'],median_batch_seconds=statistics.median(r['elapsed_seconds'] for r in primary if 'elapsed_seconds' in r),data_sha256=ledger['data_sha256'],prompt_sha256=ledger['prompt_sha256'],synthetic_only=True,app_changed=False)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
