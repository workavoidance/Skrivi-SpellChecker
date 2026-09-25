"""Aggregate the candidate pilot without publishing sentences or word lists."""
import json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/cloud-candidates-20260924'
def main():
 rows=list(map(json.loads,(OUT/'local.jsonl').read_text(encoding='utf8').splitlines()))
 assert len(rows)==168 and len({r['id'] for r in rows})==168
 def score(rs):
  errors=[r for r in rs if r['kind']=='spelling_error'];controls=[r for r in rs if r['kind']!='spelling_error']
  result=dict(cases=len(rs),errors=len(errors),controls=len(controls))
  for mode in ['base','combined','flagged_only']:
   def choices(r):return r['combined'] if mode=='combined' or mode=='flagged_only' and r['base_flag'] else r['base']
   result[mode]=dict(top1=sum(bool(set(r['gold'])&set(choices(r)[:1])) for r in errors),top3=sum(bool(set(r['gold'])&set(choices(r)[:3])) for r in errors),control_flags=sum(bool(choices(r)) for r in controls))
  result.update(base_available=sum(r['base_available'] for r in errors),combined_available=sum(r['combined_available'] for r in errors),ai_answer_present=sum(bool(set(r['gold'])&set(r['ai'])) for r in errors),added_cases=sum(bool(r['added']) for r in rs),top3_gains=sum(not set(r['gold'])&set(r['base']) and bool(set(r['gold'])&set(r['combined'])) for r in errors),top3_losses=sum(bool(set(r['gold'])&set(r['base'])) and not set(r['gold'])&set(r['combined']) for r in errors))
  return result
 ledger=json.loads((OUT/'ledger.json').read_text());report=dict(total=score(rows),categories={c:score([r for r in rows if r['category']==c]) for c in sorted({r['category'] for r in rows})},requests=len(ledger['requests']),estimated_usd=sum(r.get('estimated_standard_usd',0) for r in ledger['requests']),accounted_usd=ledger['accounted_usd'],median_batch_seconds=statistics.median(r['elapsed_seconds'] for r in ledger['requests']),prompt_sha256=ledger['prompt_sha256'])
 (OUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
