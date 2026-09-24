"""Compare opt-in coverage, reusing provably unchanged baseline sentences."""
import hashlib,json,sys,time,statistics
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Checker
from lexical_coverage import CandidateCoverage
from nuspell_backend import NativeNuspell
from audit_ask_spelling import target_metrics
from audit_recovered_baseline import checkpoint

def main():
 out=ROOT/'results/expanded-20260924';folder=ROOT/'data/local/expanded-20260924'
 raw=(folder/'cases.json').read_bytes();cases=json.loads(raw)
 meta=json.loads((out/'nuspell_context-manifest.json').read_text())
 assert meta['data_sha256']==hashlib.sha256(raw).hexdigest()
 for file,digest in meta['code_sha256'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest
 base=[json.loads(s) for s in (out/'nuspell_context.jsonl').read_text(encoding='utf8').splitlines()]
 assert len(base)==len(cases)
 invalid={r['id'] for r in json.loads((folder/'span-audit.json').read_text())}
 assert all('result' in r or r['id'] in invalid for r in base)
 target=out/'nuspell_coverage.jsonl'
 if target.exists():raise ValueError('Existing comparison must not be overwritten')
 native=NativeNuspell();coverage=CandidateCoverage(native=native);checker=Checker()
 totals={};transitions={};recomputed=Counter();checked=Counter();timings={}
 with target.open('w',encoding='utf8') as log:
  for i,(c,old) in enumerate(zip(cases,base)):
   assert c['id']==old['id']
   if c['id'] in invalid:
    log.write(json.dumps(dict(id=c['id'],group=c['group'],failure='InvalidBenchmarkSpan'))+'\n');log.flush();continue
   ws=[t['word'] for t in old['result']['words']]
   a=native.lookup(ws);b=coverage.lookup(ws)
   touched=any((a[w]['known'],a[w]['segmented'],a[w]['suggestions'][:24])!=(b[w]['known'],b[w]['segmented'],b[w]['suggestions'][:24]) for w in ws)
   # First five unchanged cases in each group validate the equivalence rule.
   spot=not touched and checked[c['group']]<5
   tick=time.perf_counter()
   result=checker.check(c['text'],'nuspell_coverage') if touched or spot else old['result']
   elapsed=time.perf_counter()-tick
   if spot:
    fields=lambda r:[(t['word'],t['status'],t['suggestions'],t['candidates']) for t in r['words']]
    assert fields(result)==fields(old['result']);checked[c['group']]+=1
   if touched or spot:
    recomputed[c['group']]+=1;timings.setdefault(c['group'],[]).append(elapsed)
   metrics=Counter();per=[];changes=transitions.setdefault(c['group'],Counter())
   for t,mold in zip(c['targets'],old['target_metrics']):
    m=target_metrics(t,result);metrics.update(m);per.append(m)
    if t['kind']=='spelling_error':
     changes['top3_gains']+=int(m['top3']>mold['top3']);changes['top3_losses']+=int(m['top3']<mold['top3'])
     changes['top1_gains']+=int(m['top1']>mold['top1']);changes['top1_losses']+=int(m['top1']<mold['top1'])
    else:
     changes['warnings_removed']+=int(m['control_false_flags']<mold['control_false_flags'])
     changes['warnings_added']+=int(m['control_false_flags']>mold['control_false_flags'])
   totals.setdefault(c['group'],Counter()).update(metrics)
   row=dict(id=c['id'],group=c['group'],category=c['category'],metrics=dict(metrics),target_metrics=per,result=result,recomputed=touched or spot,spot_check=spot,wall_seconds=elapsed if touched or spot else None)
   log.write(json.dumps(row,ensure_ascii=False)+'\n');log.flush()
   if (i+1)%40==0 or i+1==len(cases):print('coverage',i+1,'/',len(cases),'recomputed',sum(recomputed.values()),flush=True)
 report=dict(cases=len(cases),invalid_benchmark_cases=len(invalid),groups={k:dict(v) for k,v in totals.items()},transitions={k:dict(v) for k,v in transitions.items()},recomputed=dict(recomputed),unchanged_spot_checks=dict(checked),timing_limitation='Unchanged sentences reuse exact baseline predictions after candidate/acceptance equivalence checks. No full-mode timing comparison.',affected_and_spot_timing={k:statistics.median(v) for k,v in timings.items()},data_sha256=meta['data_sha256'])
 checkpoint(out/'nuspell_coverage-summary.json',report);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
