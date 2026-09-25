import json
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from compound_help import CompoundHelp

class Dictionary:
    def lookup(self,w):
        if w in ('book','note','good','whole'):
            return {'word':w,'senses':[{'definition':'Meaning of '+w,'examples':[]}]}

def helper(tmp_path):
    base=tmp_path/'base.db';compound=tmp_path/'compound.db'
    db=sqlite3.connect(base);db.execute('CREATE TABLE base(form,lemma,tag)')
    db.executemany('INSERT INTO base VALUES(?,?,?)',[
        ('books','book','subst normert'),('notebooks','notebook','subst normert'),
        ('book','book','subst normert'),('note','note','subst normert'),
        ('good','good','adj normert'),('whole','other','subst normert')])
    db.commit();db.close()
    db=sqlite3.connect(compound);db.execute('CREATE TABLE compound(form,first,fugue,second)')
    db.executemany('INSERT INTO compound VALUES(?,?,?,?)',[
        ('notebook','note','','book'),('notesbook','note','s','book'),
        ('notegood','note','','good'),('broken','note','','book'),
        ('missingbook','missing','','book')])
    db.commit();db.close()
    return CompoundHelp(Dictionary(),base,compound)

def test_exact_precedence_and_recorded_base(tmp_path):
    h=helper(tmp_path)
    assert h.lookup('whole')['kind']=='exact'
    assert h.lookup('books')['matches'][0]['base']=='book'
    assert h.lookup('bookssss') is None

def test_recorded_compound_and_linking_letter(tmp_path):
    h=helper(tmp_path)
    assert h.lookup('notebooks')['kind']=='components'
    assert h.lookup('notesbook')['analyses'][0]['linking']=='s'
    assert h.lookup('note-book') is None
    assert h.lookup('bookbook') is None
    assert h.lookup('broken') is None
    assert h.lookup('missingbook') is None

def test_components_are_not_whole_definitions_and_noun_guard(tmp_path):
    h=helper(tmp_path);x=h.lookup('notebook')
    assert 'senses' not in x and len(x['analyses'][0]['parts'])==2
    assert h.lookup('notegood') is None
    assert h.lookup('notegood',noun_only=False)['kind']=='components'
