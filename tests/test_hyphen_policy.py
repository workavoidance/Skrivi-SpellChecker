from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hyphen_policy import HyphenPolicy

def policy():
 return HyphenPolicy(lambda w:w in {'e-post','tv-utvalg'},lambda w:w in {'utvalg','akse','hund'})

def token():
 return {'word':'wrod','status':'UNCERTAIN','native_known':False,
         'suggestions':['wr-od','word','ward'],'native_suggestions':['word','ward','wr-od','third'],
         'scores':[['wr-od',-1],['word',-2],['ward',-2.5],['third',-6],['wrod',-8]]}

def test_remove_unsupported_inserted_hyphen_and_refill():
 t=token();assert policy().apply(t)==['word','ward','third']
 assert t['suggestions']==['wr-od','word','ward']

def test_preserve_listed_and_rule_supported_forms():
 p=policy()
 for c in ['e-post','tv-utvalg','TV-utvalg','EU-utvalg','x-akse','3-hund']:
  assert p.evidence('original',c)
 assert p.evidence('word','wr-od') is None
 assert p.evidence('already-hyphenated','wr-od')

def test_preserve_detection_known_word_threshold_and_special_paths():
 t=token();t['status']='OK';assert policy().apply(t)==t['suggestions']
 t=token();t['native_known']=True;t['scores'][-1]=['wrod',-6]
 assert policy().apply(t)==[] # difference exactly 4 must not bypass threshold
 t=token();del t['native_known'];assert policy().apply(t)==t['suggestions']

def test_gap_cutoff_is_separate_experiment():
 assert policy().apply(token(),'guard_gap')==['word','ward']
