"""Prepare a whitelisted synthetic-only reference benchmark. No API access."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Checker

def main():
 out=ROOT/'data/local/cloud-reference-20260924'
 if (out/'frozen.json').exists():raise ValueError('Already frozen')
 source=json.loads((ROOT/'data/local/expanded-20260924/cases.json').read_text(encoding='utf8'))
 cached={r['id']:r for r in map(json.loads,(ROOT/'results/expanded-20260924/nuspell_coverage.jsonl').read_text(encoding='utf8').splitlines())}
 rng=random.Random(2409202603);picked=set()
 for category in ['possessive','compound']:
  ids=sorted({c['pair_id'] for c in source if c['group']=='synthetic' and c['category']==category})
  picked.update(rng.sample(ids,30))
 rows=[]
 for c in source:
  if c['group']!='synthetic' or c['pair_id'] not in picked:continue
  assert c['id'].startswith('synthetic-')
  t=c['targets'][0]
  rows.append((dict(id=c['id'],text=c['text'],category=c['category'],**t,cloud_allowed=True,provenance='generated_synthetic'),cached[c['id']]['result']))
 checker=Checker()
 for i,c in enumerate(json.loads((out/'authored.json').read_text(encoding='utf8'))):
  assert c['cloud_allowed'] and c['provenance']=='newly_authored_synthetic'
  rows.append((c,checker.check(c['text'],'nuspell_coverage')))
  if (i+1)%12==0:print('New local context checks',i+1,'/48',flush=True)
 frozen=[]
 for c,result in rows:
  t=next(t for t in result['words'] if t['start']==c['target_start'] and t['end']==c['target_end'])
  assert t['word']==c['target_word']
  pool=list(dict.fromkeys([t['word']]+t['candidates']))
  rng.shuffle(pool)
  payload=dict(id=hashlib.sha256(('blind-reference:'+c['id']).encode()).hexdigest()[:16],sentence=c['text'],target=t['word'],target_start=t['start'],target_end=t['end'],original_id=pool.index(t['word']),options=[dict(id=i,word=w) for i,w in enumerate(pool)])
  frozen.append(dict(id=c['id'],category=c['category'],kind=c['kind'],gold=c['acceptable'],cloud_allowed=True,provenance=c['provenance'],payload=payload,
   local=dict(decision='keep' if t['status']=='OK' else 'change',choices=t['suggestions'] if t['status']!='OK' else [t['word']]),
   unranked=dict(decision='keep' if t['native_known'] else 'change',choices=[t['word']] if t['native_known'] else t['candidates'][:3])))
 rng.shuffle(frozen)
 raw=json.dumps(frozen,ensure_ascii=False,indent=2).encode('utf8');(out/'frozen.json').write_bytes(raw)
 manifest=dict(cases=len(frozen),sha256=hashlib.sha256(raw).hexdigest(),synthetic_only=True,learner_corpus_exported=False,seed=2409202603,notes='120 previously evaluated synthetic cases plus 48 newly authored contextual cases. Candidate order randomized, no gold or local predictions in API payload. No tuning after API outcomes.')
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');print(json.dumps(manifest),flush=True)
if __name__=='__main__':main()
