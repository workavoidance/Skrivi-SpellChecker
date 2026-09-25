import gzip
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from dictionary_help import Renderer, DictionaryHelp, build_index

def explanation(text):return {'type_':'explanation','content':text,'items':[]}
def definition(text, examples=(), children=()):
    return {'type_':'definition','id':text,'elements':[explanation(text),*[{'type_':'example','quote':{'content':x,'items':[]}} for x in examples],*children]}

def test_expands_items_without_recursive_reference_cycles():
    r=Renderer({'1':{'lemmas':[{'lemma':'target'}]}},{'concepts':{'x':{'expansion':'expanded'}}})
    assert r.text({'content':'$ and $','items':[{'type_':'entity','id':'x'},{'type_':'article_ref','article_id':1}]})=='expanded and target'
    assert r.text({'content':'$','items':[{'type_':'usage','text':'form','content':[]}]})=='form'
    assert r.safe({'content':'$','items':[{'type_':'entity','id':'absent'}]}) is None
    assert r.safe({'content':'$','items':[]}) is None

def test_senses_do_not_mix_examples_or_expression_definitions():
    r=Renderer({}, {})
    nodes=[definition('parent',children=[definition('one',['first']),definition('two',['second'])]),
           {'type_':'sub_article','article':{'body':{'definitions':[definition('idiom',['unrelated'])]}}}]
    senses=r.senses(nodes)
    assert [(s['definition'],[e['text'] for e in s['examples']]) for s in senses]==[
        ('parent',[]),('parent; one',['first']),('parent; two',['second'])]

def test_unknown_placeholder_suppresses_affected_sense():
    node=definition('valid',['example'])
    node['elements'].append({'type_':'explanation','content':'$','items':[{'id':'absent'}]})
    assert Renderer({},{}).senses([node])==[]

def test_index_forms_ambiguity_metadata_and_missing_words(tmp_path):
    article={'article_id':1,'status':8,'lemmas':[{'lemma':'test','paradigm_info':[
        {'to':None,'standardisation':'STANDARD','tags':['NOUN'],'inflection':[{'word_form':'tests','tags':['Plur']}]},
        {'to':'1900','standardisation':'STANDARD','inflection':[{'word_form':'obsolete'}]}]}],
        'body':{'definitions':[definition('first',['example'])]}}
    other={'article_id':2,'lemmas':[{'lemma':'tests'}],'body':{'definitions':[definition('second')]}}
    source=tmp_path/'input.gz';source.write_bytes(gzip.compress(json.dumps({'1':article,'2':other}).encode()))
    concepts=tmp_path/'concepts.json';concepts.write_text('{}');target=tmp_path/'index.sqlite3'
    stats=build_index(source,concepts,target);help=DictionaryHelp(target)
    assert stats['counts']['indexed_articles']==2
    assert len(help.lookup('TESTS')['senses'])==2
    assert help.lookup('obsolete') is None
    assert help.lookup('missing') is None
    assert help.lookup_many(['test','test',None]).keys()=={'test'}
    with pytest.raises(ValueError):help.lookup_many(['x']*501)
    # A failed replacement must leave a working previous index intact.
    source.write_bytes(b'invalid')
    with pytest.raises(Exception):build_index(source,concepts,target)
    assert help.lookup('test')

def test_embedded_entries_keep_expression_identity(tmp_path):
    child={'article_id':2,'latest_status':8,'lemmas':[{'lemma':'red book'}],
           'body':{'definitions':[definition('expression meaning',['expression example'])]}}
    parent={'article_id':1,'lemmas':[{'lemma':'red'}], 'body':{'definitions':[
        {'type_':'definition','elements':[{'type_':'sub_article','article':child}]}]}}
    source=tmp_path/'input.gz';source.write_bytes(gzip.compress(json.dumps({'1':parent}).encode()))
    concepts=tmp_path/'concepts.json';concepts.write_text('{}');target=tmp_path/'index.sqlite3'
    stats=build_index(source,concepts,target,include_embedded=True);help=DictionaryHelp(target)
    assert stats['counts']['embedded_articles_added']==1
    assert help.lookup('red') is None
    assert help.lookup('red book')['senses'][0]['definition']=='expression meaning'
    related=help.lookup_expressions('red')
    assert len(related)==1 and related[0]['expression']=='red book'
    assert related[0]['kind']=='related_expression'
    assert help.lookup_expressions('book')==[]  # no invented reverse word matching
    # A top-level entry is authoritative; duplicate embedded copies cannot overwrite it.
    child2=dict(child,body={'definitions':[definition('top-level meaning')]})
    source.write_bytes(gzip.compress(json.dumps({'1':parent,'2':child2}).encode()))
    stats=build_index(source,concepts,target,include_embedded=True)
    assert stats['counts']['embedded_articles_added']==0
    assert help.lookup('red book')['senses'][0]['definition']=='top-level meaning'
