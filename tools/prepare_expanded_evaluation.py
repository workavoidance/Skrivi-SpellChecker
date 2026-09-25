"""Freeze a larger private diagnostic before inference; never print corpus text."""
import hashlib,json,random,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import words
from ordbank_resources import OrdbankResources
from traditional_resources import TraditionalResources
from prepare_ask_spelling import finalize
from audit_recovered_baseline import SUITES

def main():
 out=ROOT/'data/local/expanded-20260924'
 if (out/'cases.json').exists():raise ValueError('Frozen sample already exists')
 source=ROOT/'data/local/ask-reviewed-20260924'
 candidates=json.loads((source/'candidates.json').read_text(encoding='utf8'))
 reviews=json.loads((out/'reviews.json').read_text(encoding='utf8'))
 cases=finalize(candidates,reviews,reserve=0)
 old=[]
 for name in SUITES.values():old+=json.loads((ROOT/'data/local/recovered-original/norwegian'/name).read_text(encoding='utf8'))
 old+=json.loads((source/'reviewed-cases.json').read_text(encoding='utf8'))
 old+=json.loads((ROOT/'data/local/coverage-targeted-20260924/cases.json').read_text(encoding='utf8'))
 texts={c['text'].strip().casefold() for c in old}
 blocked={c['pair_id'] for c in cases if c['text'].strip().casefold() in texts}
 cases=[dict(c,group='authentic',targets=[{k:c[k] for k in ('target_start','target_end','target_word','acceptable','kind')}]) for c in cases if c['pair_id'] not in blocked]
 bank=OrdbankResources();frequency=TraditionalResources()
 rng=random.Random(2409202602)
 pool=[w for w,n in frequency.connection.execute('select word,count from unigram where count>=100 order by word') if w.isalpha() and w.islower() and 5<=len(w)<=20]
 rng.shuffle(pool)
 nouns=[];compounds=[]
 previous={t['word'].casefold() for c in old for t in words(c['text'])}
 for w in pool:
  row=bank.lookup(w)
  if not row or row['proper'] or not row['tag'].startswith('subst ') or 'normert' not in row['tag'].split():continue
  if len(nouns)<60 and 'ent' in row['tag'].split() and 'be' in row['tag'].split() and not w.endswith(('s','x','z')) and w+'s' not in previous:nouns.append(w+'s')
  if len(compounds)<60 and len(w)>=9 and bank.decompositions(w) and w not in previous:compounds.append(w)
  if len(nouns)==len(compounds)==60:break
 assert len(nouns)==len(compounds)==60
 synthetic=[]
 for category,ws in [('possessive',nouns),('compound',compounds)]:
  for i,gold in enumerate(ws):
   prefix='Jeg la merke til ' if category=='possessive' else 'Vi snakket om '
   suffix=' betydning i teksten.' if category=='possessive' else ' etter m\u00f8tet.'
   clean=prefix+gold+suffix
   # Four mechanical edit types; no model output influences sampling.
   bad=None
   for j in range(1,len(gold)-2):
    method=i%4
    proposal=(gold[:j]+gold[j+1:] if method==0 else gold[:j]+gold[j+1]+gold[j]+gold[j+2:] if method==1 else gold[:j]+'x'+gold[j+1:] if method==2 else gold[:j]+gold[j]+gold[j:])
    if proposal!=gold and not bank.lookup(proposal):bad=proposal;break
   assert bad
   for control in (False,True):
    word=gold if control else bad
    target=dict(target_start=len(prefix),target_end=len(prefix)+len(word),target_word=word,acceptable=[gold],kind='target_control' if control else 'spelling_error')
    c=dict(id=f'synthetic-{category}-{i}-'+('control' if control else 'error'),pair_id=f'synthetic-{category}-{i}',group='synthetic',category=category,text=prefix+word+suffix,targets=[target],kind=target['kind'],redistributable=False)
    synthetic.append(c)
 cases+=synthetic
 # Stress tests reuse synthetic targets deliberately; not extra independent evidence.
 errors=[c for c in synthetic if c['kind']=='spelling_error']
 for n in range(24):
  parts=[];targets=[];offset=0
  for k in range(8):
   c=errors[(n*5+k*13)%len(errors)]
   part=c['text'].rstrip('.')
   targets += [dict(t,target_start=t['target_start']+offset,target_end=t['target_end']+offset) for t in c['targets']]
   parts.append(part);offset+=len(part)+2
  text=', '.join(parts)+'.'
  assert len(words(text))<=100
  cases.append(dict(id=f'stress-{n}',group='stress',category='reused_synthetic_targets',text=text,targets=targets,redistributable=False))
 for c in cases:
  for t in c['targets']:assert c['text'][t['target_start']:t['target_end']]==t['target_word']
 raw=json.dumps(cases,ensure_ascii=False,indent=2).encode('utf8');(out/'cases.json').write_bytes(raw)
 meta=dict(data_sha256=hashlib.sha256(raw).hexdigest(),reviewed_pairs=len(reviews),accepted_before_overlap=sum(r['decision']=='accept' for r in reviews),excluded_overlap_pairs=len(blocked),groups=dict(Counter(c['group'] for c in cases)),targets=dict(Counter(c['group']+' / '+t['kind'] for c in cases for t in c['targets'])),seed=2409202602,limitations=['ASK isolated-pair assistant review, not full-sentence or Norwegian-human adjudication','Corrected-target controls are not fully verified clean sentences','Synthetic words come from cached lexical resources also used by the experiment; structural diagnostics only','Stress paragraphs are artificial concatenations with reused targets, not authentic dyslexic paragraphs','Previously unused pairs/sentences, not writer-independent or model-training-independent data'])
 meta.update(source='ltg/ask-gec train',source_revision=(source/'revision.txt').read_text().strip(),source_sha256=hashlib.sha256((source/'train.jsonl').read_bytes()).hexdigest(),review_sha256=hashlib.sha256((out/'reviews.json').read_bytes()).hexdigest())
 invalid=[];ambiguous=[]
 for c in cases:
  for t in c['targets']:
   if not any(w['start']==t['target_start'] and w['end']==t['target_end'] and w['word']==t['target_word'] for w in words(c['text'])):invalid.append(dict(id=c['id'],cause='Target is not a whole engine token'))
  if c['group']=='authentic' and c['kind']=='spelling_error':
   row=bank.lookup(c['target_word'])
   if row and 'normert' in row['tag'].split():ambiguous.append(c['pair_id'])
 (out/'span-audit.json').write_text(json.dumps(invalid,indent=2),encoding='utf8')
 (out/'label-audit.json').write_text(json.dumps(dict(excluded_pair_ids=ambiguous,reason='Normative original needs context adjudication; excluded from conservative spelling-only analysis regardless of predictions.',frozen_data_unchanged=True),indent=2),encoding='utf8')
 (out/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf8');print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
