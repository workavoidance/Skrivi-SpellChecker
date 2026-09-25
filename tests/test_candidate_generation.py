import importlib.util
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_cloud_candidates import validate

def test_rejects_multiword_and_punctuation_candidates():
 batch=[{'id':'local','payload':{'id':'blind','target':'wrod'}}]
 for value in ['two words','word.','', 'a'*61]:
  with pytest.raises(ValueError):validate(batch,{'results':[{'id':'blind','suggestions':[value]}]})

def test_rejects_wrong_identity_and_excess_candidates():
 batch=[{'id':'local','payload':{'id':'blind','target':'wrod'}}]
 with pytest.raises(ValueError):validate(batch,{'results':[{'id':'other','suggestions':[]}]})
 with pytest.raises(ValueError):validate(batch,{'results':[{'id':'blind','suggestions':['a']*6}]})

def test_deduplicates_and_removes_original():
 batch=[{'id':'local','payload':{'id':'blind','target':'wrod'}}]
 assert validate(batch,{'results':[{'id':'blind','suggestions':['word','word','wrod']}]})==[{'id':'local','suggestions':['word']}]
