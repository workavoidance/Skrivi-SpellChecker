"""Ensure aggregate totals do not hide regressions or mix ambiguous labels."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from summarize_expanded_evaluation import summarize

def test_equal_net_score_still_reports_gain_and_regression():
 cases=[dict(id=str(i),pair_id=str(i),group='authentic',category='test') for i in range(2)]
 def row(i,hit):
  m=dict(error_targets=1,top3=hit,top1=hit)
  return dict(id=str(i),metrics=m,target_metrics=[m])
 a=[row(0,0),row(1,1)];b=[row(0,1),row(1,0)]
 result=summarize(cases,a,b,{'1'})
 g=result['authentic']
 assert g['baseline']['top3']==g['coverage']['top3']==1
 assert g['changes']['top3_gains']==g['changes']['top3_losses']==1
 assert result['authentic_conservative']['changes']['top3_losses']==0
 assert result['authentic_conservative']['cases']==1

def test_invalid_span_does_not_become_spelling_miss():
 c=dict(id='invalid',group='authentic',pair_id='p',category='test')
 assert summarize([c],[dict(id='invalid',failure='ValueError')],[dict(id='invalid',failure='InvalidBenchmarkSpan')],set())=={}
