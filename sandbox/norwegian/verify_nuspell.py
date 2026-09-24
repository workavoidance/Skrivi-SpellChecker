"""Real selectable backend checks and full-request timings; no external text transfer."""
import json
from pathlib import Path
import statistics
from engine import Checker, replace_word, single, words
from evaluate import score
from nuspell_backend import MODES

HERE=Path(__file__).parent
OUT=HERE/'nuspell-experiments'

def signature(result):
    return [(w['id'],w['word'],w['start'],w['end'],w['status'],w['suggestions']) for w in result['words']]

def main():
    cases=json.loads((HERE/'iteration-2026-09-05/development.json').read_text(encoding='utf-8'))
    target=next(c for c in cases if c['id']=='natural-paragraph01')
    report=dict(note='Full Checker dispatch with no native precomputation. First request includes native dictionary startup and model load. Three subsequent warm requests. Sequential timings, not cross-system speed benchmark.',modes={})
    for mode in MODES:
        checker=Checker()
        reference=json.loads((OUT/f'development-{mode}.json').read_text(encoding='utf-8'))
        expected=next(r['result'] for r in reference['runs'] if r['case']==target['id'])
        runs=[]
        for i in range(4):
            result=checker.check(target['text'],mode)
            assert signature(result)==signature(expected)
            assert result['text']==target['text']
            assert len(result['words'])==len(words(target['text']))
            for w in result['words']:
                assert target['text'][w['start']:w['end']]==w['word']
                assert w['start_utf16']==len(target['text'][:w['start']].encode('utf-16-le'))//2
                assert w['end_utf16']==len(target['text'][:w['end']].encode('utf-16-le'))//2
                assert len(w['suggestions'])<=3 and all(single(s) for s in w['suggestions'])
                for s in w['suggestions']:
                    changed=replace_word(target['text'],w,s)
                    assert changed==target['text'][:w['start']]+s+target['text'][w['end']:]
            runs.append(result['elapsed_seconds'])
        report['modes'][mode]=dict(first_request_seconds=runs[0], warm_seconds=runs[1:],
            median_warm_seconds=statistics.median(runs[1:]), metrics=score(target,result), exact_saved_output_match=True)
        (OUT/'integration-timing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(mode,report['modes'][mode],flush=True)
    checker=Checker()
    for mode in MODES:
        for bad in ['', 'word '*101, 'a'*4001]:
            try: checker.check(bad,mode)
            except ValueError: pass
            else: raise AssertionError('Invalid input accepted')
    report['invalid_input_checks']=12
    (OUT/'integration-timing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__': main()
