from copy import deepcopy
from test_hyphen_policy import token
from soft_hyphen_policy import SoftHyphenPolicy

def policy():
    props={'oslo':{'proper':True},'norsk':{'adjective':True},'engelsk':{'adjective':True},'pc':{'display':'PC'}}
    return SoftHyphenPolicy(lambda w:w=='e-post',lambda w:w in {'jente','utstyr'},props.get)

def test_stable_partition_retains_all_eligible_without_mutation():
    t=token();before=deepcopy(t);r=policy().partition(t)
    assert r['shown']==['word','ward','third']
    assert r['more']==['wr-od'] and r['uncertain']==['wr-od']
    assert t==before

def test_extended_evidence_and_unsupported_retention():
    p=policy()
    for word in ['Oslo-jente','norsk-engelsk','pc-utstyr','e-post']:
        assert p.extended_evidence('original',word)
    assert p.extended_evidence('original','Office-programmene') is None
    t=token();t['scores']=[['wr-od',-1],['wrod',-8]]
    assert p.partition(t)['shown']==['wr-od']

def test_original_hyphen_and_special_paths_unchanged():
    for update in [{'word':'wr-od'},{'status':'OK'},{'scores':[]}]:
        t=token();t.update(update);assert policy().apply(t)==t['suggestions']
    t=token();del t['native_known'];assert policy().apply(t)==t['suggestions']

def test_known_word_threshold_is_preserved():
    t=token();t['native_known']=True;t['scores'][-1]=['wrod',-6]
    r=policy().partition(t)
    assert r['shown']==['wr-od'] and r['more']==[]
