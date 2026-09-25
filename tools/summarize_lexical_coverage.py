"""Export aggregate-only lexical experiment results and paired regression counts."""
import json,hashlib
from pathlib import Path
from collections import Counter
from audit_recovered_baseline import ROOT,SUITES,diagnose
from audit_ask_spelling import target_metrics


def main():
 out=ROOT/'results/lexical-coverage-20260924'
 manifest=json.loads((out/'manifest.json').read_text())
 if not manifest.get('complete') or manifest['reserve_run']:
  raise ValueError('Experiment incomplete or reserve used')
 cases={'ask':[c for c in json.loads((ROOT/'data/local/ask-reviewed-20260924/reviewed-cases.json').read_text(encoding='utf8')) if c['partition']=='evaluation']}
 base={'ask':json.loads((ROOT/'results/ask-reviewed-20260924/nuspell_context.json').read_text(encoding='utf8'))}
 for name,file in SUITES.items():
  cases[name]=json.loads((ROOT/'data/local/recovered-original/norwegian'/file).read_text(encoding='utf8'))
  base[name]=json.loads((ROOT/f'results/baseline-20260924/{name}-nuspell_context.json').read_text(encoding='utf8'))
 summary=json.loads((out/'summary.json').read_text()); comparisons={}
 extra=ROOT/'results/lexical-proposal-only-20260924'
 extra_manifest=json.loads((extra/'manifest.json').read_text())
 if not extra_manifest.get('complete') or extra_manifest['reserve_run']:raise ValueError('Fourth policy unfinished')
 summary.update(json.loads((extra/'summary.json').read_text()))
 # The wrapper augments backend suggestions; do not label those as native-only.
 for item in summary.values():item['metrics'].pop('native_candidate_hit',None)
 for policy in ['genitive','attested','productive','proposal_only']:
  for name,cc in cases.items():
   before={r.get('id',r.get('case')):r['result'] for r in base[name]}
   folder=extra if policy=='proposal_only' else out
   rows=json.loads((folder/f'{policy}-{name}.json').read_text(encoding='utf8'))
   after={r['id']:r['result'] for r in rows}
   if set(after)!={c['id'] for c in cc} or len(after)!=len(rows):raise ValueError('Wrong cases')
   delta=Counter()
   for c in cc:
    a,b=before[c['id']],after[c['id']]
    if name=='ask':
     am,bm=target_metrics(c,a),target_metrics(c,b)
     if c['kind']=='spelling_error':
      delta['gained_top3']+=not am['top3'] and bm['top3'];delta['lost_top3']+=am['top3'] and not bm['top3']
     else:
      delta['added_control_flags']+=not am['control_false_flags'] and bm['control_false_flags']
      delta['removed_control_flags']+=am['control_false_flags'] and not bm['control_false_flags']
    else:
     am,ad=diagnose(c,a);bm,bd=diagnose(c,b)
     aa={x['token_id']:x['bucket']=='success' for x in ad};bb={x['token_id']:x['bucket']=='success' for x in bd}
     if aa.keys()!=bb.keys():raise ValueError('Target alignment changed')
     delta['gained_top3']+=sum(not aa[i] and bb[i] for i in aa)
     delta['lost_top3']+=sum(aa[i] and not bb[i] for i in aa)
     if c['id']=='natural-paragraph01':
      delta['private_paragraph_baseline_top3']=am.get('top3',0)
      delta['private_paragraph_experimental_top3']=bm.get('top3',0)
   comparisons[policy+' / '+name]=dict(delta)
 report=dict(manifest=manifest,proposal_only_manifest=extra_manifest,summary=summary,paired_comparisons=comparisons,
             threshold_sensitivity=json.loads((out/'threshold-sensitivity.json').read_text()),
             code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [ROOT/'tools'/n for n in ['experimental_lexical_coverage.py','run_lexical_coverage.py','ask_threshold_sensitivity.py']]})
 (ROOT/'docs/benchmarks/2026-09-24-lexical-summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({'paired_comparisons':comparisons,'summary':{k:{'top3':v['metrics'].get('top3'),
   'control_flags':v['metrics'].get('control_false_flags'),'non_target_flags':v['metrics'].get('non_target_flags'),
   'clean_flagged':v['metrics'].get('clean_cases_flagged'),'recomputed':v['recomputed']} for k,v in summary.items()}},indent=2))

if __name__=='__main__':main()
