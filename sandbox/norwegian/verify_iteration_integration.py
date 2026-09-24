"""Verify the selectable v5 path against saved original v4 decisions."""
import time
from unittest.mock import patch
from engine import Checker,Norbert
from iteration_session import OUT,read,save,log,DEADLINE

checker=Checker();report=dict(rows=[])
def signature(result):
    return [(w['id'],w['word'],w['status'],w['suggestions'],w['start'],w['end'],w['start_utf16'],w['end_utf16']) for w in result['words']]
for suite in ['development','fresh']:
    cases={c['id']:c for c in read(OUT/(suite+'.json'))}
    for row in read(OUT/(suite+'-baseline.json'))['rows']:
        if time.time()>=DEADLINE:raise RuntimeError('Deadline reached; checkpoints retained')
        start=time.perf_counter();result=checker.check(cases[row['id']]['text'],'norbert_v5')
        assert signature(result)==signature(row['result']),(suite,row['id'],'Changed decisions or offsets')
        assert result['mode']=='norbert_v5'
        assert isinstance(checker.norbert,Norbert),'Original model not restored'
        assert checker.norbert.rank.__func__ is Norbert.rank
        report['rows'].append(dict(suite=suite,id=row['id'],identical=True,seconds=time.perf_counter()-start))
        save(OUT/'app-integration.json',report)
        if len(report['rows'])%20==0:print(len(report['rows']),'app checks passed',flush=True)
original=checker.norbert
with patch.object(checker,'check_context',side_effect=RuntimeError('injected test failure')):
    try:checker.check('Hei','norbert_v5')
    except RuntimeError:pass
    else:raise AssertionError('Expected injected failure')
assert checker.norbert is original
base=read(OUT/'development-baseline.json')['rows'][0]
result=checker.check(cases.get(base['id'],{}).get('text',read(OUT/'development.json')[0]['text']),'norbert_v2')
assert signature(result)==signature(base['base'])
for text in ['', 'ord '*101]:
    try:checker.check(text,'norbert_v5')
    except ValueError:pass
    else:raise AssertionError('Invalid length accepted')
report.update(total=len(report['rows']),state_restoration=True,default_mode_unchanged=True,invalid_length_rejected=True)
save(OUT/'app-integration.json',report);log('Selectable v5 integration: '+str(report['total'])+' cases identical to saved v4, exact offsets; original scorer restored on success and injected failure; default v2 preserved.')
