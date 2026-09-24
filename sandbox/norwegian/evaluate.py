import argparse
import csv
import json
from pathlib import Path
import statistics
import time
import hashlib
import platform
from engine import Checker, words

HERE = Path(__file__).parent

def expected(case):
    tokens = words(case['text'])
    result = {}
    for e in case['errors']:
        matches = [w for w in tokens if w['word'] == e['word']]
        result[matches[e.get('occurrence', 0)]['id']] = e['suggestions']
    return result

def score(case, result):
    gold = expected(case)
    # Unresolved intent and operations outside this token-only metric are
    # recorded in the fixture, but must not count as false alarms.
    ignored = set(expected({'text': case['text'], 'errors': [
        {**entry, 'suggestions': []} for entry in case.get('unscored', [])]}))
    metrics = dict(errors=len(gold), detected=0, top1=0, top3=0, candidate_recall=0, false_alarms=0)
    for w in result['words']:
        if w['id'] in ignored:
            continue
        if w['id'] in gold:
            answers = gold[w['id']]
            metrics['detected'] += w['status'] != 'OK'
            metrics['top1'] += bool(w['suggestions']) and w['suggestions'][0] in answers
            metrics['top3'] += bool(set(w['suggestions']) & set(answers))
            metrics['candidate_recall'] += bool(set(w['candidates']) & set(answers))
        elif w['status'] != 'OK':
            metrics['false_alarms'] += 1
    return metrics

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--modes', nargs='+', default=['dictionary','norbert','qwen'])
    parser.add_argument('--limit', type=int)
    parser.add_argument('--cases', default=str(HERE/'cases.json'))
    parser.add_argument('--output', default=str(HERE/'results.json'))
    args = parser.parse_args()
    case_bytes = Path(args.cases).read_bytes()
    cases = json.loads(case_bytes.decode('utf-8'))
    if args.limit:
        cases = cases[:args.limit]
    report = {'note':'Constructed exploratory cases, not independent benchmark or Lingdys comparison. Group coverage was chosen by hand. Scores are not calibrated.', 'runs':[], 'summary':{}}
    report.update(cases_file=Path(args.cases).name, cases_sha256=hashlib.sha256(case_bytes).hexdigest(),
                  engine_sha256=hashlib.sha256((HERE/'engine.py').read_bytes()).hexdigest(),
                  python=platform.python_version(), platform=platform.platform(),
                  timing_note='Fresh Checker and candidate cache per mode; single run; model load separately recorded.')
    for mode in args.modes:
        checker = Checker()
        for case in cases:
            try:
                result = checker.check(case['text'],mode)
                row = {'case':case['id'],'kind':case['kind'],'mode':mode,'result':result,'metrics':score(case,result)}
                print(mode,case['id'],row['metrics'],round(result['elapsed_seconds'],2),flush=True)
            except Exception as e:
                row = {'case':case['id'],'mode':mode,'failure':str(e)}
                print(mode,case['id'],'FAILED',str(e),flush=True)
            report['runs'].append(row)
            Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        valid=[r for r in report['runs'] if r['mode']==mode and 'metrics' in r]
        totals={k:sum(r['metrics'][k] for r in valid) for k in ['errors','detected','top1','top3','candidate_recall','false_alarms']}
        totals.update(completed=len(valid),failed=len(cases)-len(valid),
            clean_cases=sum(r['kind']=='clean' for r in valid),
            clean_cases_unflagged=sum(r['kind']=='clean' and r['metrics']['false_alarms']==0 for r in valid),
            median_check_seconds=statistics.median([r['result']['elapsed_seconds']-r['result']['load_seconds'] for r in valid]) if valid else None,
            load_seconds=sum(r['result']['load_seconds'] for r in valid))
        report['summary'][mode]=totals
        if checker.qwen:
            checker.qwen.close()
        Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],indent=2),flush=True)
