"""Paired warm end-to-end v4 timing; includes original v2 screening each run."""
import statistics
import time
from iteration_session import OUT,read,save,log,fast_whole,fast_rank,ORIGINAL_WHOLE,DEADLINE
import context_scoring
from engine import Checker,Norbert,Lexicon,words

cases=read(OUT/'development.json')
chosen=[next(c for c in cases if c['id']==cid) for cid in ['natural-paragraph01','profile-Very-bad','context01']]
chosen.append(max((c for c in cases if c.get('source')),key=lambda c:len(words(c['text']))))
checker=Checker();checker.norbert=Norbert();checker.revised_lexicon=Lexicon(revised=True)
checker.check('Jeg liker å lese bøker.','norbert_v4')
original_rank=checker.norbert.rank
data=dict(note='Three paired rounds per text, alternating order; same resident model and shared lexical cache. Full v4 including v2 screening. Startup excluded. No inference output cache.',rows=[])
def signature(result):return [(w['id'],w['word'],w['status'],w['suggestions']) for w in result['words']]
for case in chosen:
    reference=None
    for repeat in range(3):
        for mode in (['reference','fast'] if repeat%2==0 else ['fast','reference']):
            if time.time()>=DEADLINE:raise RuntimeError('Session deadline reached')
            context_scoring.whole_scores=fast_whole if mode=='fast' else ORIGINAL_WHOLE
            checker.norbert.rank=fast_rank.__get__(checker.norbert,Norbert) if mode=='fast' else original_rank
            start=time.perf_counter()
            try:result=checker.check(case['text'],'norbert_v4')
            finally:context_scoring.whole_scores=ORIGINAL_WHOLE
            elapsed=time.perf_counter()-start
            sig=signature(result)
            if reference is None:reference=sig
            assert sig==reference,(case['id'],mode,'Decisions changed')
            data['rows'].append(dict(id=case['id'],repeat=repeat,mode=mode,seconds=elapsed,identical=True))
            save(OUT/'paired-timing.json',data)
            print(case['id'],repeat,mode,round(elapsed,3),flush=True)
data['summary']={}
for case in chosen:
    vals={m:statistics.median(r['seconds'] for r in data['rows'] if r['id']==case['id'] and r['mode']==m) for m in ['reference','fast']}
    vals['speedup']=vals['reference']/vals['fast'];data['summary'][case['id']]=vals
save(OUT/'paired-timing.json',data);log('Paired end-to-end timing complete: '+str(data['summary']))
