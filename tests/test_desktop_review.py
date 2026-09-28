from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from review import Review
from worker import chunks,check_document

def test_exact_occurrence_unicode_and_undo():
    text='😀 feil og feil.'
    tokens=[{'id':0,'word':'feil','start':2,'end':6,'status':'UNCERTAIN','suggestions':['riktig'],'more':['rett']}, {'id':1,'word':'feil','start':10,'end':14,'status':'UNCERTAIN','suggestions':['rett'],'more':[]}]
    r=Review(text,{'words':tokens});r.decide(0,'riktig')
    assert r.text=='😀 riktig og feil.' and r.tokens[1]['start']==12
    r.decide(1,'rett');assert r.text=='😀 riktig og rett.'
    r.undo();r.undo();assert r.text==text and r.tokens==tokens

def test_more_suggestion_allowed_but_arbitrary_rewrite_rejected():
    import pytest
    r=Review('feil',{'words':[{'id':0,'word':'feil','start':0,'end':4,'status':'UNCERTAIN','suggestions':['rett'],'more':['riktig']}]})
    with pytest.raises(ValueError):r.decide(0,'something unrelated')
    r.decide(0,'riktig');assert r.text=='riktig'

def test_render_treats_writing_as_text():
    r=Review('<img src=x> & tekst',{'words':[]})
    assert '&lt;img' in r.markup() and '<img' not in r.markup()

def test_chunks_cover_words_and_keep_offsets():
    import re
    text=('Dette er en setning.\n'*70)+'Et siste ord.'
    pieces=list(chunks(text));assert len(pieces)>1
    for offset,part in pieces:assert text[offset:offset+len(part)]==part and len(part.split())<=80
    assert ''.join(part for _,part in pieces)==text

def test_document_merges_offsets_without_changing_text():
    import re
    class Checker:
        def check(self,text,mode):
            return {'words':[{'id':i,'word':m.group(),'start':m.start(),'end':m.end()} for i,m in enumerate(re.finditer(r'\w+',text))]}
    text='Ord. '*160
    result=check_document(Checker(),text)
    assert result['text']==text and len(result['words'])==160
    for i,t in enumerate(result['words']):assert t['id']==i and text[t['start']:t['end']]==t['word']
