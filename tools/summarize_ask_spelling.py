"""Export aggregate ASK results only; no corpus words, sentences or record IDs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from audit_ask_spelling import aggregate
from audit_recovered_baseline import MODES, ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    meta=json.loads((args.results/'metadata.json').read_text(encoding='utf8'))
    if not meta.get('finished_utc'):
        raise ValueError('Run has not finished')
    cases=json.loads(args.data.read_text(encoding='utf8'))
    if hashlib.sha256(args.data.read_bytes()).hexdigest()!=meta['data_sha256']:
        raise ValueError('Sample changed since evaluation')
    rows={m:json.loads((args.results/f'{m}.json').read_text(encoding='utf8')) for m in MODES}
    wanted={c['id'] for c in cases if c['partition']=='evaluation'}
    for mode, entries in rows.items():
        if len(entries)!=len(wanted) or {r['id'] for r in entries}!=wanted or any('failure' in r for r in entries):
            raise ValueError('Incomplete run or unexpected/reserved case scored')
    report={k:meta[k] for k in ['started_utc','finished_utc','data_sha256','model_revision','dictionary_revision',
                              'code_sha256','cases','reserved_cases_not_run','historical_exact_text_overlap','limitations']}
    report['modes']={m:aggregate(entries) for m,entries in rows.items()}
    report['comparisons']={}
    for before,after in zip(MODES,MODES[1:]):
        a={r['id']:r['metrics'] for r in rows[before]}; b={r['id']:r['metrics'] for r in rows[after]}
        errors=[i for i in a if a[i].get('error_targets')]
        controls=[i for i in a if a[i].get('control_targets')]
        report['comparisons'][before+' -> '+after]=dict(
            gained_top3=sum(not a[i]['top3'] and b[i]['top3'] for i in errors),
            lost_top3=sum(a[i]['top3'] and not b[i]['top3'] for i in errors),
            added_control_flags=sum(not a[i]['control_false_flags'] and b[i]['control_false_flags'] for i in controls),
            removed_control_flags=sum(a[i]['control_false_flags'] and not b[i]['control_false_flags'] for i in controls))
    args.output.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'modes':{m:r['metrics'] for m,r in report['modes'].items()},'comparisons':report['comparisons']},indent=2))


if __name__=='__main__':
    main()
