"""Offline checkpointed comparisons on frozen development and previous fresh suites."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from datetime import datetime, timezone
from engine import words
from evaluate import score
from nuspell_backend import NuspellChecker, MODES

HERE = Path(__file__).parent
OUT = HERE / 'nuspell-experiments'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, data):
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(10):
        try:
            temp.replace(p)
            return
        except PermissionError:
            if attempt == 9: raise
            time.sleep(.2)

def run(mode, suite):
    OUT.mkdir(exist_ok=True)
    path = HERE/'iteration-2026-09-05'/f'{suite}.json'
    cases = read(path)
    result_path = OUT/f'{suite}-{mode}.json'
    report = read(result_path) if result_path.exists() else dict(mode=mode, suite=suite,
        cases_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        backend_sha256=hashlib.sha256((HERE/'nuspell_backend.py').read_bytes()).hexdigest(),
        note='Previously inspected frozen cases; not a new untouched test. No training or tuning on this run. Son text remains local. Token-only provisional labels.', runs=[])
    if report['backend_sha256'] != hashlib.sha256((HERE/'nuspell_backend.py').read_bytes()).hexdigest():
        raise RuntimeError('Backend changed: use a new output directory rather than mix results.')
    done = {r['case'] for r in report['runs']}
    checker = NuspellChecker()
    warm = time.perf_counter()
    checker.native.lookup(list(dict.fromkeys(w['word'] for c in cases for w in words(c['text']))))
    report['native_precompute_seconds'] = time.perf_counter()-warm
    for c in cases:
        if c['id'] in done: continue
        result = checker.check(c['text'], mode)
        report['runs'].append(dict(case=c['id'], kind=c['kind'], result=result, metrics=score(c,result)))
        save(result_path, report)
        if len(report['runs']) % 10 == 0:
            print(mode, suite, len(report['runs']), '/',len(cases), flush=True)
    rows = report['runs']
    report['summary'] = {key:sum(r['metrics'][key] for r in rows) for key in rows[0]['metrics']}
    report['summary'].update(cases=len(rows), clean_cases=sum(r['kind']=='clean' for r in rows),
        clean_unflagged=sum(r['kind']=='clean' and r['metrics']['false_alarms']==0 for r in rows),
        median_warm_seconds=statistics.median(r['result']['elapsed_seconds']-r['result']['load_seconds'] for r in rows))
    save(result_path, report)
    with (OUT/'LOG.md').open('a',encoding='utf-8') as f:
        f.write(f"- {datetime.now(timezone.utc).isoformat()}: {suite} {mode}: {report['summary']}\n")
    print(suite, mode, report['summary'],flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--mode', choices=MODES, required=True)
    p.add_argument('--suite', choices=['development','fresh'], required=True)
    args=p.parse_args()
    run(args.mode,args.suite)
