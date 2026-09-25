"""Publishable aggregates only; source text and per-case identifiers stay private."""
import json,statistics
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def summarize(cases,baseline,coverage,excluded):
 assert len(cases)==len(baseline)==len(coverage)
 groups={}
 for c,a,b in zip(cases,baseline,coverage):
  assert c['id']==a['id']==b['id']
  if 'failure' in a or 'failure' in b:
   assert 'failure' in a and 'failure' in b
   continue
  names=[c['group']]
  if c['group']=='authentic' and c['pair_id'] not in excluded:names.append('authentic_conservative')
  for name in names:
   g=groups.setdefault(name,dict(cases=0,baseline=Counter(),coverage=Counter(),changes=Counter(),categories={}))
   g['cases']+=1;g['baseline'].update(a['metrics']);g['coverage'].update(b['metrics'])
   category=g['categories'].setdefault(c['category'],dict(baseline=Counter(),coverage=Counter()))
   category['baseline'].update(a['metrics']);category['coverage'].update(b['metrics'])
   for old,new in zip(a['target_metrics'],b['target_metrics']):
    if 'top3' in old:
     for metric in ['top3','top1']:
      g['changes'][metric+'_gains']+=int(new[metric]>old[metric]);g['changes'][metric+'_losses']+=int(new[metric]<old[metric])
    else:
     g['changes']['warnings_removed']+=int(new['control_false_flags']<old['control_false_flags'])
     g['changes']['warnings_added']+=int(new['control_false_flags']>old['control_false_flags'])
 return groups

def main():
 data=ROOT/'data/local/expanded-20260924';out=ROOT/'results/expanded-20260924'
 cases=json.loads((data/'cases.json').read_text(encoding='utf8'))
 read=lambda p:[json.loads(s) for s in p.read_text(encoding='utf8').splitlines()]
 a=read(out/'nuspell_context.jsonl');b=read(out/'nuspell_coverage.jsonl')
 audit=json.loads((data/'label-audit.json').read_text());manifest=json.loads((data/'manifest.json').read_text())
 verified=0
 for c,old,new in zip(cases,a,b):
  for row in [old,new]:
   if 'result' not in row:continue
   result=row['result'];assert result['text']==c['text']
   for t in result['words']:
    assert c['text'][t['start']:t['end']]==t['word']
    assert len(t['suggestions'])<=3
    assert all(x and not any(ch.isspace() for ch in x) for x in t['suggestions'])
   verified+=1
 excluded=set(audit['excluded_pair_ids'])
 groups=summarize(cases,a,b,excluded)
 missing=Counter()
 for c,row in zip(cases,b):
  if c['group']=='authentic' and c['pair_id'] not in excluded and row.get('metrics',{}).get('partition_candidate_missing'):
   missing['missing_from_scored_pool']+=1
   missing['present_in_full_native_list']+=row['metrics']['native_candidate_hit']
 report=dict(data=manifest,remaining_candidate_diagnostic=dict(missing),output_contract_checks=verified,invalid_benchmark_cases=sum('failure' in r for r in a),label_audit=dict(excluded_pairs=len(audit['excluded_pair_ids']),reason=audit['reason'],frozen_data_unchanged=True),groups=groups,baseline_run=json.loads((out/'nuspell_context-summary.json').read_text()),coverage_run=json.loads((out/'nuspell_coverage-summary.json').read_text()))
 (out/'aggregate.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 for name,g in groups.items():print(json.dumps(dict(group=name,baseline=g['baseline'],coverage=g['coverage'],changes=g['changes'])))
if __name__=='__main__':main()
