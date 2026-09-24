import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from run_cloud_reference import validate,reservation

def sample():
 return [dict(id='local-error-label',payload=dict(id='opaque-id',original_id=0,options=[dict(id=0,word='bll'),dict(id=1,word='ball')]))]

def test_blind_id_maps_back_only_locally():
 rows=validate(sample(),dict(results=[dict(id='opaque-id',decision='change',choices=[1])]))
 assert rows==[dict(id='local-error-label',decision='change',choices=['ball'])]

def test_rejects_invented_options_and_inconsistent_keep():
 for decision,ids in [('change',[7]),('change',[1,1]),('keep',[1]),('change',[0]),('change',[]),('invented',[1])]:
  with pytest.raises(ValueError):validate(sample(),dict(results=[dict(id='opaque-id',decision=decision,choices=ids)]))

def test_reservation_covers_output_cap_and_increases_with_input():
 assert reservation(b'a',2048)>=2048*50/1e6
 assert reservation(b'aa',2048)>reservation(b'a',2048)

def test_missing_gold_is_not_a_ranking_failure_when_conditioning():
 from summarize_cloud_reference import score
 case=dict(kind='spelling_error',gold=['ball'],payload=dict(options=[dict(word='bll'),dict(word='bill')]))
 m=score(case,dict(decision='change',choices=['bill']))
 assert m['errors']==1 and m['candidate_available']==0 and m['top3_when_available']==0

def test_keeping_correct_original_counts_as_successful_control():
 from summarize_cloud_reference import score
 case=dict(kind='target_control',gold=['ball'])
 assert score(case,dict(decision='keep',choices=['ball']))==dict(controls=1,unnecessary_reviews=0)
