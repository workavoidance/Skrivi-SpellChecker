import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
from prepare_ask_spelling import isolated_edit, edit_category, finalize
from audit_ask_spelling import target_metrics


def test_isolation_rejects_extra_edits_and_keeps_exact_span():
    row={'source':'Vi har en bll i dag.', 'correction':'Vi har en ball i dag.'}
    item=isolated_edit(row)
    assert item and row['source'][item['start']:item['end']]=='bll'
    assert isolated_edit(dict(row, correction='Vi hadde en ball i dag.')) is None
    assert isolated_edit(dict(row, correction='Vi har en ball  i dag.')) is None


def test_control_scores_only_target_not_other_flags():
    case=dict(kind='target_control',target_start=4,target_end=8,target_word='ball',acceptable=['ball'])
    result={'words':[dict(start=0,end=2,word='Vi',status='UNCERTAIN'),
                     dict(start=4,end=8,word='ball',status='OK')]}
    assert target_metrics(case,result)=={'control_targets':1,'control_false_flags':0}


def test_span_prevents_scoring_wrong_repeated_word():
    case=dict(kind='spelling_error',target_start=7,target_end=10,target_word='bll',acceptable=['ball'])
    result={'words':[dict(start=0,end=3,word='bll',status='LIKELY_ERROR',suggestions=['ball'],candidates=['ball']),
                     dict(start=7,end=10,word='bll',status='OK',suggestions=[],candidates=['ball'])]}
    metrics=target_metrics(case,result)
    assert metrics['top3']==0 and metrics['candidate_hit']==1 and metrics['partition_not_flagged']==1


def test_reserve_keeps_pair_together_and_requires_review():
    candidates=[dict(original='bll',corrected='ball',source='En bll er her.',correction='En ball er her.',
                     start=3,end=6,source_row=i,category='omitted_letters') for i in range(3)]
    reviews=[dict(candidate_index=i,decision='accept',reason='Synthetic test decision') for i in range(3)]
    cases=finalize(candidates,reviews,reserve=1)
    assert sum(c['partition']=='reserved' for c in cases)==2
    for i in range(0,len(cases),2):
        assert cases[i]['partition']==cases[i+1]['partition']
        assert cases[i]['pair_id']==cases[i+1]['pair_id']


def test_taxonomy_is_mechanical():
    assert edit_category('bal','ball')=='omitted_letters'
    assert edit_category('balll','ball')=='extra_letters'
    assert edit_category('blal','ball')=='adjacent_transposition'
    assert edit_category('bell','ball')=='substitution'
