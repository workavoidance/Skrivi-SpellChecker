import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1]/'tools/audit_recovered_baseline.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_audit_separates_overlapping_failure_stages_and_ignored_targets():
    case = {'errors': [{'word':'a','suggestions':['A']}, {'word':'b','suggestions':['B']},
                       {'word':'c','suggestions':['C']}, {'word':'d','suggestions':['D']}],
            'unscored':[{'word':'e'}]}
    rows = []
    for i, (word, status, pool, suggestions) in enumerate([
        ('a','OK',[],[]), ('b','UNCERTAIN',[],['other']),
        ('c','UNCERTAIN',['C'],['other']), ('d','UNCERTAIN',['D'],['D']),
        ('e','UNCERTAIN',[],[]), ('f','UNCERTAIN',[],[])]):
        rows.append(dict(id=i,word=word,status=status,candidates=pool,suggestions=suggestions))
    metrics, details = audit.diagnose(case, {'words':rows})
    assert metrics['errors']==4 and metrics['detected']==3
    assert metrics['detection_misses']==1 and metrics['candidate_misses']==2
    assert metrics['pool_present_not_shown']==1 and metrics['top3']==1
    assert metrics['non_target_flags']==1 and metrics['ignored']==1
    assert [r['bucket'] for r in details]==['not_flagged','candidate_missing','ranking_or_threshold','success']


def test_suggestions_on_an_unflagged_word_are_not_visible_success():
    case={'errors':[{'word':'bad','suggestions':['good']}]}
    result={'words':[dict(id=0,word='bad',status='OK',candidates=['good'],suggestions=['good'])]}
    metrics,_=audit.diagnose(case,result)
    assert metrics['candidate_hit']==1 and metrics['top3']==0
    assert metrics['ranked_top5_potential']==1


def test_ui_curated_forms_include_both_loaded_tables():
    forms=audit.curated_forms()
    assert {'lekser','masse','gjerne','hjerne'} <= forms


def test_five_options_preserve_detection_and_known_word_threshold():
    spec = importlib.util.spec_from_file_location('summary', Path(__file__).parents[1]/'tools/summarize_recovered_baseline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    token=dict(word='original',status='UNCERTAIN',native_known=True,
               scores=[['wrong',10],['answer',3],['original',0]],candidates=['wrong','answer'])
    assert not module.visible_top5(token,['answer'])
    token['scores'][1][1]=5
    assert module.visible_top5(token,['answer'])
    token['status']='OK'
    assert not module.visible_top5(token,['answer'])
