"""Fresh-process target diagnostic and Windows memory/time measurements."""
import argparse,ctypes,json,sys,time,statistics,hashlib
from ctypes import wintypes
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Checker
from nuspell_backend import NuspellChecker
from experimental_lexical_coverage import CoverageNative
from audit_ask_spelling import target_metrics
from audit_recovered_baseline import checkpoint

class Memory(ctypes.Structure):
 _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]

def memory():
 kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
 psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
 m=Memory();m.cb=ctypes.sizeof(m)
 if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(m),m.cb):raise ctypes.WinError()
 return dict(peak_working_set_mib=m.PeakWorkingSetSize/2**20,working_set_mib=m.WorkingSetSize/2**20,private_mib=m.PrivateUsage/2**20)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['baseline','proposal_only']);a=p.parse_args()
 source=ROOT/'data/local/coverage-targeted-20260924/cases.json';cases=json.loads(source.read_text(encoding='utf8'))
 out=ROOT/'results/coverage-targeted-20260924';out.mkdir(exist_ok=True)
 if (out/f'{a.mode}.json').exists():raise ValueError('Refusing to overwrite measurement')
 started=time.perf_counter();checker=Checker()
 if a.mode=='proposal_only':
  checker.nuspell_checker=NuspellChecker();checker.nuspell_checker.native=CoverageNative('proposal_only')
 setup=time.perf_counter()-started
 rows=[];counts=Counter();latencies=[]
 for i,c in enumerate(cases):
  start=time.perf_counter();result=checker.check(c['text'],'nuspell_context');elapsed=time.perf_counter()-start
  metrics=target_metrics(c,result);counts.update(metrics);latencies.append(elapsed)
  rows.append(dict(id=c['id'],metrics=metrics,result=result,wall_seconds=elapsed))
  checkpoint(out/f'{a.mode}.json',rows)
  if (i+1)%10==0:print(a.mode,i+1,'/',len(cases),flush=True)
 report=dict(mode=a.mode,cases=len(cases),metrics=dict(counts),setup_seconds=setup,
   first_check_seconds=latencies[0],subsequent_median_seconds=statistics.median(latencies[1:]),
   subsequent_p95_seconds=sorted(latencies[1:])[int(.95*(len(latencies)-2))],total_seconds=time.perf_counter()-started,
   memory=memory(),data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
   limitation='One fresh process per mode, identical synthetic sentence order. Paired and repeated words share caches within process. Windows memory is process-specific; not a machine requirement.')
 checkpoint(out/f'{a.mode}-summary.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
