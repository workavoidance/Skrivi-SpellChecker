"""Offline target-level evaluation of a locally reviewed ASK spelling sample."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys

from audit_recovered_baseline import checkpoint, MODES, ROOT, ENGINE, SUITES
from summarize_recovered_baseline import visible_top5


def target_metrics(case, result):
    matches = [t for t in result['words']
               if t['start'] == case['target_start'] and t['end'] == case['target_end']]
    if len(matches) != 1 or matches[0]['word'] != case['target_word']:
        raise ValueError('Target span does not match engine tokenization')
    token = matches[0]
    flagged = token['status'] != 'OK'
    if case['kind'] == 'target_control':
        return dict(control_targets=1, control_false_flags=int(flagged))
    answers = set(case['acceptable'])
    shown = token['suggestions']
    pool = bool(answers.intersection(token['candidates']))
    top3 = flagged and bool(answers.intersection(shown[:3]))
    bucket = ('success' if top3 else 'not_flagged' if not flagged else
              'candidate_missing' if not pool else 'ranking_or_threshold')
    return dict(error_targets=1, detected=int(flagged),
                native_candidate_hit=int(bool(answers.intersection(token.get('native_suggestions', [])))),
                candidate_hit=int(pool), top1=int(flagged and bool(shown) and shown[0] in answers),
                top3=int(top3), hypothetical_top5=int(visible_top5(token, answers)),
                **{'partition_'+bucket:1})


def aggregate(rows):
    totals, categories = Counter(), {}
    valid = [r for r in rows if 'metrics' in r]
    for row in valid:
        totals.update(row['metrics'])
        categories.setdefault(row['category'], Counter()).update(row['metrics'])
    return dict(completed=len(valid), failed=len(rows)-len(valid), metrics=dict(totals),
                categories={k:dict(v) for k,v in categories.items()},
                median_seconds=statistics.median(r['elapsed_seconds']-r['load_seconds'] for r in valid) if valid else None,
                load_seconds=sum(r['load_seconds'] for r in valid))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data, output = args.data.resolve(), args.output.resolve()
    if not data.is_relative_to(ROOT/'data/local') or not output.is_relative_to(ROOT/'results'):
        parser.error('Private inputs/outputs must remain under data/local and results')
    all_cases = json.loads(data.read_text(encoding='utf8'))
    cases = [c for c in all_cases if c['partition']=='evaluation']
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Empty sample or duplicate IDs')
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ENGINE))
    from engine import Checker, words
    from setup_assets import REV, DICT_REV
    for case in cases:
        target_metrics(case, {'words':[dict(t,status='OK',suggestions=[],candidates=[])
                                     for t in words(case['text'])]})
    historical = set()
    for name in SUITES.values():
        path = ROOT/'data/local/recovered-original/norwegian'/name
        historical.update(c['text'].strip().casefold() for c in json.loads(path.read_text(encoding='utf8')))
    overlap = sum(c['text'].strip().casefold() in historical for c in cases)
    if overlap:
        raise ValueError('Sample overlaps historical sentence text; resolve before scoring')
    meta = dict(started_utc=datetime.now(timezone.utc).isoformat(),
                data_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [*ENGINE.glob('*.py'), Path(__file__)]},
                model_revision=REV, dictionary_revision=DICT_REV,
                cases=len(cases), reserved_cases_not_run=len(all_cases)-len(cases),
                historical_exact_text_overlap=overlap,
                personal_dictionary='Checker API bypasses UI user overrides',
                limitations=['Single-word pairs reviewed; surrounding sentences not fully adjudicated.',
                             'Controls score only the corrected target, not the entire sentence.',
                             'Nonrandom spelling-focused subset; not representative of dyslexia or all ASK errors.',
                             'Reserve separated by sentence pair; no writer/essay identifiers in release.',
                             'Public training split; upstream model exposure cannot be excluded.',
                             'Top-five hypothetical with current detection/threshold policy; UI unchanged.',
                             'CPU single pass; caches persist within mode; timing is descriptive.'])
    checkpoint(output/'metadata.json', meta)
    summary = {}
    for mode in MODES:
        checker, rows = Checker(), []
        for n, case in enumerate(cases):
            try:
                result = checker.check(case['text'], mode)
                row = dict(id=case['id'], category=case['category'], metrics=target_metrics(case,result),
                           elapsed_seconds=result['elapsed_seconds'], load_seconds=result['load_seconds'], result=result)
            except Exception as exc:
                row = dict(id=case['id'], failure=type(exc).__name__)
            rows.append(row)
            checkpoint(output/f'{mode}.json', rows)
            if (n+1)%20==0 or n+1==len(cases):
                print(mode, n+1, '/', len(cases), 'failed',sum('failure' in r for r in rows),flush=True)
        summary[mode] = aggregate(rows)
        checkpoint(output/'summary.json', summary)
    meta['finished_utc'] = datetime.now(timezone.utc).isoformat()
    checkpoint(output/'metadata.json', meta)
    print(json.dumps(summary, indent=2),flush=True)


if __name__ == '__main__':
    main()
