"""Run one production mode against a frozen private expanded diagnostic."""
import argparse,hashlib,json,statistics,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Checker
from audit_ask_spelling import target_metrics
from audit_recovered_baseline import checkpoint
from measure_lexical_coverage import memory

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['nuspell_context','nuspell_coverage']);args=p.parse_args()
 folder=ROOT/'data/local/expanded-20260924';raw=(folder/'cases.json').read_bytes();manifest=json.loads((folder/'manifest.json').read_text())
 assert hashlib.sha256(raw).hexdigest()==manifest['data_sha256']
 cases=json.loads(raw);out=ROOT/'results/expanded-20260924';out.mkdir(exist_ok=True)
 target=out/(args.mode+'.jsonl')
 if target.exists():raise ValueError('Refusing to overwrite existing run')
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'sandbox/norwegian').glob('*.py')}
 checkpoint(out/(args.mode+'-manifest.json'),dict(data_sha256=manifest['data_sha256'],code_sha256=hashes,mode=args.mode))
 checker=Checker();groups={};timings={};failures=0;started=time.perf_counter()
 with target.open('w',encoding='utf8') as log:
  for i,c in enumerate(cases):
   tick=time.perf_counter()
   try:
    result=checker.check(c['text'],args.mode)
    metrics=Counter()
    per_target=[]
    for t in c['targets']:
     m=target_metrics(t,result);metrics.update(m);per_target.append(m)
    row=dict(id=c['id'],group=c['group'],category=c['category'],metrics=dict(metrics),target_metrics=per_target,result=result,wall_seconds=time.perf_counter()-tick)
    groups.setdefault(c['group'],Counter()).update(metrics)
    timings.setdefault(c['group'],[]).append(row['wall_seconds'])
   except Exception as exc:
    failures+=1;row=dict(id=c['id'],group=c['group'],failure=type(exc).__name__)
   log.write(json.dumps(row,ensure_ascii=False)+'\n');log.flush()
   if (i+1)%20==0 or i+1==len(cases):
    checkpoint(out/(args.mode+'-progress.json'),dict(completed=i+1,total=len(cases),failures=failures,groups={k:dict(v) for k,v in groups.items()}))
    print(args.mode,i+1,'/',len(cases),'failures',failures,flush=True)
 report=dict(mode=args.mode,cases=len(cases),failures=failures,groups={k:dict(v) for k,v in groups.items()},timings={k:dict(median_seconds=statistics.median(v),p95_seconds=sorted(v)[int(.95*(len(v)-1))],total_seconds=sum(v)) for k,v in timings.items()},memory=memory(),total_seconds=time.perf_counter()-started,data_sha256=manifest['data_sha256'])
 checkpoint(out/(args.mode+'-summary.json'),report);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
