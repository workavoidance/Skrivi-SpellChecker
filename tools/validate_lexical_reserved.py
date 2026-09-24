"""One-time validation of frozen proposal-only policy on reserved ASK pairs."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Norbert
from nuspell_backend import NativeNuspell,NuspellChecker
from experimental_lexical_coverage import CoverageNative
from audit_ask_spelling import target_metrics
from audit_recovered_baseline import checkpoint


def main():
 out=ROOT/'results/lexical-reserved-20260924';out.mkdir(exist_ok=False)
 code=ROOT/'tools/experimental_lexical_coverage.py'
 data=ROOT/'data/local/ask-reviewed-20260924/reviewed-cases.json'
 frozen=dict(policy='proposal_only',code_sha256=hashlib.sha256(code.read_bytes()).hexdigest(),
   data_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),frozen_utc=datetime.now(timezone.utc).isoformat(),
   statement='Selected from development results before any reserved inference; no tuning from reserve.')
 checkpoint(out/'frozen-policy.json',frozen)
 cases=[c for c in json.loads(data.read_text(encoding='utf8')) if c['partition']=='reserved']
 if len(cases)!=40:raise ValueError('Expected 20 reserved pairs')
 model=Norbert();native=NativeNuspell();summary={};allrows={}
 for mode in ['baseline','proposal_only']:
  checker=NuspellChecker(model=model)
  checker.native=native if mode=='baseline' else CoverageNative('proposal_only',native=native)
  rows=[];counts=Counter()
  for i,c in enumerate(cases):
   result=checker.check(c['text'],'nuspell_context')
   metrics=target_metrics(c,result);counts.update(metrics)
   rows.append(dict(id=c['id'],metrics=metrics,result=result))
   checkpoint(out/f'{mode}.json',rows)
   if (i+1)%10==0:print(mode,i+1,'/',len(cases),flush=True)
  summary[mode]=dict(counts);allrows[mode]={r['id']:r['metrics'] for r in rows}
 if hashlib.sha256(code.read_bytes()).hexdigest()!=frozen['code_sha256']:raise ValueError('Policy changed during validation')
 transitions=Counter()
 for c in cases:
  a=allrows['baseline'][c['id']];b=allrows['proposal_only'][c['id']]
  if c['kind']=='spelling_error':
   transitions['gained_top3']+=not a['top3'] and b['top3'];transitions['lost_top3']+=a['top3'] and not b['top3']
  else:
   transitions['added_control_flags']+=not a['control_false_flags'] and b['control_false_flags']
   transitions['removed_control_flags']+=a['control_false_flags'] and not b['control_false_flags']
 report=dict(freeze=frozen,completed_checks=80,summary=summary,paired_comparisons=dict(transitions),
   limitation='Only 20 selected learner pairs, not an independent dyslexia test. Reserve is now consumed; do not reuse as untouched data.')
 checkpoint(out/'summary.json',report)
 checkpoint(ROOT/'docs/benchmarks/2026-09-24-lexical-reserved.json',report)
 print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
