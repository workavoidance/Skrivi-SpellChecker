"""Sequential offline experiments, 2026-09-05. Never changes production defaults.

Run prepare, then each named stage. JSON checkpoints allow safe resumption.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import time
from datetime import datetime, timezone
import engine
import context_scoring
from engine import Checker, Lexicon, Norbert, words, recase
from evaluate import score, expected

HERE=Path(__file__).parent
OUT=HERE/'iteration-2026-09-05'
ORIGINAL_CONTEXT=engine.context
ORIGINAL_WHOLE=context_scoring.whole_scores
DEADLINE=datetime.fromisoformat('2026-09-05T21:37:05+00:00').timestamp()

def save(path,data):
    path=Path(path);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Windows scanners/readers can briefly hold the destination open.
    for attempt in range(10):
        try:
            temp.replace(path);break
        except PermissionError:
            if attempt==9:raise
            time.sleep(.2)

def log(message):
    OUT.mkdir(exist_ok=True)
    with (OUT/'LOG.md').open('a',encoding='utf-8') as f:
        f.write(f"- {datetime.now(timezone.utc).isoformat(timespec='seconds')}: {message}\n")
    print(message,flush=True)

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def prepare():
    OUT.mkdir(exist_ok=True)
    if (OUT/'development.json').exists():raise RuntimeError('Frozen suite already exists')
    cases=[];seen=set()
    for name in ['cases.json','scoring-development.json','scoring-validation.json']:
        for c in read(HERE/name):
            if c['text'] in seen:continue
            c['suite_origin']=name;cases.append(c);seen.add(c['text'])
    from error_profiles import examples,BASE
    for row in examples():
        c=dict(id='profile-'+row['level'].replace(' ','-'),kind='synthetic_paragraph',text=row['text'],errors=[],unscored=[])
        for change in row['changes']:
            if change['requires_span_replacement']:
                for t in words(c['text']):
                    if change['altered_start']<=t['start']<change['altered_end']:
                        occurrence=sum(w['word']==t['word'] for w in words(c['text'])[:t['id']])
                        c['unscored'].append(dict(word=t['word'],occurrence=occurrence,reason='Compound span outside token metric'))
            else:
                t=next(w for w in words(c['text']) if w['start']==change['altered_start'])
                occurrence=sum(w['word']==t['word'] for w in words(c['text'])[:t['id']])
                c['errors'].append(dict(word=t['word'],occurrence=occurrence,suggestions=[change['original']]))
        cases.append(c)
    cases.append(dict(id='profile-original',kind='clean',text=BASE,errors=[]))
    for c in cases:expected(c)
    save(OUT/'development.json',cases)
    # Fresh source IDs excluded from all previously used sourced tests. Freeze
    # before inspecting any scores, with three spelling mutations per paragraph.
    excluded={c['source']['sent_id'] for name in ['sourced-cases.json','scoring-validation.json'] for c in read(HERE/name)}
    records=[]
    for block in (HERE/'corpus-source/no_bokmaal-ud-dev.conllu').read_text(encoding='utf-8').split('\n\n'):
        fields=dict(line[2:].split(' = ',1) for line in block.splitlines() if line.startswith('# ') and ' = ' in line)
        text=fields.get('text','')
        if fields.get('sent_id') not in excluded and 10<=len(words(text))<=30 and text.endswith('.') and 'Typo=Yes' not in block:
            records.append(fields)
    rng=random.Random(9051937);rng.shuffle(records);fresh=[]
    for record in records[:36]:
        original=record['text'];sid=record['sent_id'];source=dict(sent_id=sid,original_text=original,license='CC BY-SA 4.0')
        fresh.append(dict(id='session-'+sid+'-original',kind='clean',text=original,errors=[],source=source))
        if len(fresh)>=60:break
        if len([c for c in fresh if c['errors']])>=24:continue
        targets=[w for w in words(original) if w['word'].islower() and w['word'].isalpha() and len(w['word'])>=5]
        rng.shuffle(targets);targets=sorted(targets[:3],key=lambda w:w['start'],reverse=True)
        if len(targets)<3:continue
        altered=original;changes=[]
        for i,t in enumerate(targets):
            w=t['word'];p=rng.randrange(1,len(w)-1)
            if i%3==0:wrong=w[:p]+w[p+1:]
            elif i%3==1:
                options=[j for j in range(1,len(w)-1) if w[j]!=w[j+1]]
                if not options:wrong=w[:p]+w[p+1:]
                else:
                    p=rng.choice(options);wrong=w[:p]+w[p+1]+w[p]+w[p+2:]
            else:wrong=w[:p]+w[p]+w[p:]
            altered=altered[:t['start']]+wrong+altered[t['end']:]
            changes.append((t['id'],wrong,w))
        errors=[]
        for tid,wrong,right in changes:
            ts=words(altered);assert ts[tid]['word']==wrong
            errors.append(dict(word=wrong,occurrence=sum(t['word']==wrong for t in ts[:tid]),suggestions=[right]))
        restored=altered
        for tid,wrong,right in sorted(changes,reverse=True):
            t=words(restored)[tid];restored=restored[:t['start']]+right+restored[t['end']:]
        assert restored==original
        fresh.append(dict(id='session-'+sid+'-mutated',kind='synthetic_source',text=altered,errors=errors,source=source))
    for c in fresh:expected(c)
    save(OUT/'fresh.json',fresh)
    save(OUT/'protocol.json',dict(start_utc='2026-09-05T19:37:05Z',deadline_utc='2026-09-05T21:37:05Z',
         sequence=['baseline','cleaner','short','phonetic','agreement','fast'],
         hypotheses='Cleaner internal context; 6-word context; phonetic candidate retrieval; whole/partial agreement; identical masked-input deduplication.',
         labels='Provisional spelling/source-restoration labels. Son paragraph unresolved words and compounds excluded from token metrics. No clinical severity inference.',
         fresh_use='Only evaluate finalists after development decisions. No retuning on fresh results.',
         files={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in ['development.json','fresh.json']},
         engine_sha256=hashlib.sha256((HERE/'engine.py').read_bytes()).hexdigest()))
    log(f'Frozen {len(cases)} development cases and {len(fresh)} fresh cases; source attribution in ../corpus-source/README.md. No production defaults changed.')

def short_context(text,token):
    sentence,a,b=ORIGINAL_CONTEXT(text,token)
    left=words(sentence[:a]);right=words(sentence[b:])
    start=left[-6]['start'] if len(left)>6 else 0
    end=b+right[5]['end'] if len(right)>6 else len(sentence)
    return sentence[start:end],a-start,b-start

def cleaner_context(base,lex,allow_known=False):
    repairs=[]
    for t in base['words']:
        scores=t.get('scores') or []
        if (not allow_known and t['word'].casefold() in lex.vocab) or t['status']=='OK' or not t['suggestions'] or len(scores)<2:continue
        best,s=scores[0];original=dict(scores).get(t['word'],-1000)
        if best!=t['suggestions'][0] or s-original<6 or s-scores[1][1]<2:continue
        repairs.append((t['start'],t['end'],best))
    def cleaned(text,token):
        target=dict(token);changed=text
        # Descending edits preserve original offsets; never repair own target.
        for a,b,replacement in reversed(repairs):
            if a==token['start']:continue
            changed=changed[:a]+replacement+changed[b:]
            if b<=token['start']:
                delta=len(replacement)-(b-a);target['start']+=delta;target['end']+=delta
        assert changed[target['start']:target['end']]==token['word']
        return ORIGINAL_CONTEXT(changed,target)
    return cleaned,repairs

def soundkey(word):
    # Deliberately heuristic retrieval hypotheses, not a Norwegian pronunciation
    # transcriber. Validate overreach on clean controls.
    w=word.casefold()
    w=re.sub(r'skj|sj|kj','S',w)
    w=re.sub(r'gj|hj','j',w)
    w=re.sub(r'^hv','v',w)
    w=re.sub(r'(.)\1+',r'\1',w)
    return w

class SoundLexicon(Lexicon):
    def __init__(self):
        super().__init__(revised=True)
        self.soundindex={}
        for w in self.choices:
            if w.isalpha():self.soundindex.setdefault(soundkey(w),[]).append(w)
        self.soundchoices=sorted(self.soundindex)
        self.soundcache={}
    def candidates(self,word):
        known,original=super().candidates(word)
        if known:return known,original
        key=word.casefold()
        if key not in self.soundcache:
            hits=self.process.extract(soundkey(key),self.soundchoices,scorer=self.distance,score_cutoff=1,limit=12)
            alts=sorted({w for k,_,_ in hits for w in self.soundindex[k] if self.distance(key,w)<=4},key=lambda w:(self.distance(key,w),w))
            self.soundcache[key]=list(dict.fromkeys([w.casefold() for w in original]+alts))[:40]
        return known,[recase(w,word) for w in self.soundcache[key]]

class WideLexicon(Lexicon):
    """Candidate-count control: no sound normalization, same maximum 40."""
    def __init__(self):
        super().__init__(revised=True);self.widecache={}
    def candidates(self,word):
        known,original=super().candidates(word)
        if known:return known,original
        key=word.casefold()
        if key not in self.widecache:
            matches=self.process.extract(key,self.choices,scorer=self.distance,score_cutoff=2 if len(key)<8 else 3,limit=80)
            self.widecache[key]=list(dict.fromkeys([w.casefold() for w in original]+[w for w,_,_ in matches if w!=key and ('-' in key or '-' not in w)]))[:40]
        return known,[recase(w,word) for w in self.widecache[key]]

def fast_whole(model,text,token,candidates,neutral=False):
    torch=model.torch;sentence,start,end=context_scoring.context(text,token)
    if neutral:sentence,start,end=token['word'],0,len(token['word'])
    groups={};lengths={}
    for candidate in candidates:
        enc=model.tokenizer(sentence[:start]+candidate+sentence[end:],return_offsets_mapping=True)
        ids=enc['input_ids'];ps=[i for i,(a,b) in enumerate(enc['offset_mapping']) if b>start and a<start+len(candidate)]
        if not ps or len(ids)>256:raise ValueError('Unscorable candidate')
        masked=list(ids)
        for p in ps:masked[p]=model.tokenizer.mask_token_id
        groups.setdefault(tuple(masked),[]).append((candidate,ps,[ids[p] for p in ps]));lengths[candidate]=len(ps)
    entries=list(groups.items());values={}
    for offset in range(0,len(entries),16):
        batch=entries[offset:offset+16];n=max(len(row) for row,_ in batch)
        ids=torch.tensor([list(r)+[model.tokenizer.pad_token_id]*(n-len(r)) for r,_ in batch])
        mask=torch.tensor([[1]*len(r)+[0]*(n-len(r)) for r,_ in batch])
        with torch.inference_mode():
            logits=model.model(input_ids=ids,attention_mask=mask).logits
            for j,(_,targets) in enumerate(batch):
                probs={p:logits[j,p].log_softmax(-1) for _,ps,_ in targets for p in ps}
                for c,ps,ts in targets:
                    scores=[probs[p][t].item() for p,t in zip(ps,ts)]
                    if not all(math.isfinite(s) for s in scores):raise ValueError('Nonfinite score')
                    values[c]=sum(scores)/len(scores)
    # Preserve candidate order when score ties occur.
    return {c:values[c] for c in candidates},lengths

def fast_rank(model,text,token,candidates):
    """Deduplicate partial-mask inputs too; retain original score definition."""
    torch=model.torch;sentence,start,end=engine.context(text,token)
    groups={};scores=[[] for _ in candidates]
    for c,candidate in enumerate(candidates):
        enc=model.tokenizer(sentence[:start]+candidate+sentence[end:],return_offsets_mapping=True)
        ids=enc['input_ids']
        if len(ids)>256:raise ValueError('Sentence is too long for this experiment.')
        positions=[i for i,(a,b) in enumerate(enc['offset_mapping']) if b>start and a<start+len(candidate)]
        for p in positions:
            masked=list(ids);masked[p]=model.tokenizer.mask_token_id
            groups.setdefault(tuple(masked),[]).append((c,p,ids[p]))
    entries=list(groups.items())
    for offset in range(0,len(entries),16):
        batch=entries[offset:offset+16];n=max(len(r) for r,_ in batch)
        ids=torch.tensor([list(r)+[model.tokenizer.pad_token_id]*(n-len(r)) for r,_ in batch])
        mask=torch.tensor([[1]*len(r)+[0]*(n-len(r)) for r,_ in batch])
        with torch.inference_mode():
            logits=model.model(input_ids=ids,attention_mask=mask).logits
            for j,(_,targets) in enumerate(batch):
                probs={p:logits[j,p].log_softmax(-1) for _,p,_ in targets}
                for c,p,target in targets:
                    value=probs[p][target].item()
                    if not math.isfinite(value):raise ValueError('Nonfinite score')
                    scores[c].append(value)
    values=[sum(s)/len(s) if s else -1000 for s in scores]
    return sorted(zip(candidates,values),key=lambda row:row[1],reverse=True)

class ReuseBase(Checker):
    def check(self,text,mode):
        if mode=='norbert_v2' and getattr(self,'base',None) is not None:return copy.deepcopy(self.base)
        result=super().check(text,mode)
        if mode=='norbert_v2':self.last_base=copy.deepcopy(result)
        return result

def agreement_whole(model,text,token,candidates,neutral=False):
    whole,lengths=ORIGINAL_WHOLE(model,text,token,candidates,neutral)
    partial=dict(model.rank(text,token,candidates));original=token['word']
    alternatives=[w for w in candidates if w!=original]
    if not alternatives:return whole,lengths
    bw=max(alternatives,key=whole.get);bp=max(alternatives,key=partial.get)
    for w in alternatives:
        if bw!=bp or partial[w]-partial[original]<=4:whole[w]=min(whole[w],whole[original])
    return whole,lengths

def summary(rows):
    totals={k:sum(r['metrics'][k] for r in rows if 'metrics' in r) for k in ['errors','detected','top1','top3','candidate_recall','false_alarms']}
    times=[r['seconds'] for r in rows if 'metrics' in r]
    clean=[r for r in rows if r.get('kind')=='clean' and 'metrics' in r]
    totals.update(cases=len(rows),failures=sum('failure' in r for r in rows),median_seconds=statistics.median(times) if times else None,
       total_seconds=sum(times),clean_cases=len(clean),clean_unflagged=sum(r['metrics']['false_alarms']==0 for r in clean))
    return totals

def run(stage,suite='development'):
    cases=read(OUT/(suite+'.json'));path=OUT/(suite+'-'+stage+'.json')
    data=read(path) if path.exists() else dict(stage=stage,suite=suite,rows=[],
       script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),timing='Single fresh process per stage. Model and lexicon startup excluded. Warm candidate caches accumulate per stage; timing comparisons are exploratory.')
    done={r['id'] for r in data['rows']}
    checker=ReuseBase();checker.norbert=Norbert();checker.revised_lexicon=SoundLexicon() if stage in ('phonetic','phonetic_fast') else WideLexicon() if stage=='wide' else Lexicon(revised=True)
    if stage in ('fast_all','phonetic_fast'):checker.norbert.rank=fast_rank.__get__(checker.norbert,Norbert)
    baseline_path=OUT/(suite+'-baseline.json')
    baselines={r['id']:r for r in read(baseline_path)['rows']} if stage not in ('baseline',) else {}
    log(f'Start {suite}/{stage}; {len(cases)-len(done)} cases remain.')
    for case in cases:
        if case['id'] in done:continue
        if time.time()>=DEADLINE:log('Deadline reached; checkpoints retained.');break
        engine.context=ORIGINAL_CONTEXT;context_scoring.context=ORIGINAL_CONTEXT;context_scoring.whole_scores=ORIGINAL_WHOLE
        checker.base=None;extra={};started=time.perf_counter()
        try:
            if stage=='baseline':
                base=checker.check(case['text'],'norbert_v2')
                v2_seconds=time.perf_counter()-started
                checker.base=base
                result=checker.check(case['text'],'norbert_v4')
                extra=dict(base=base,v2_seconds=v2_seconds,v2_metrics=score(case,base))
            else:
                # Cached v2 outputs preserve initial screening identically for
                # the context-only experiments. Add measured v2 time below.
                ref=baselines[case['id']]
                if stage in ('phonetic','wide','fast_all','phonetic_fast'):checker.base=None
                else:checker.base=ref['base']
                if stage in ('cleaner','cleaner_v4'):
                    fn,repairs=cleaner_context(ref['result'] if stage=='cleaner_v4' else ref['base'],checker.revised_lexicon,allow_known=stage=='cleaner_v4')
                    context_scoring.context=fn;extra['internal_repairs']=repairs
                elif stage=='short':
                    engine.context=short_context;context_scoring.context=short_context
                elif stage=='agreement':context_scoring.whole_scores=agreement_whole
                elif stage in ('fast','fast_all','phonetic_fast'):context_scoring.whole_scores=fast_whole
                elif stage not in ('phonetic','wide'):raise ValueError(stage)
                result=checker.check(case['text'],'norbert_v4')
                if stage in ('fast_all','phonetic','phonetic_fast'):extra['base']=checker.last_base
            elapsed=time.perf_counter()-started
            if stage not in ('baseline','phonetic','wide','fast_all','phonetic_fast'):
                elapsed+=baselines[case['id']]['seconds' if stage=='cleaner_v4' else 'v2_seconds']
            assert result['text']==case['text']
            for t in result['words']:
                assert case['text'][t['start']:t['end']]==t['word']
                assert len(t['suggestions'])<=3 and all(engine.single(s) for s in t['suggestions'])
            row=dict(id=case['id'],kind=case['kind'],metrics=score(case,result),seconds=elapsed,result=result,**extra)
        except Exception as e:row=dict(id=case['id'],kind=case['kind'],failure=repr(e))
        finally:
            engine.context=ORIGINAL_CONTEXT;context_scoring.context=ORIGINAL_CONTEXT;context_scoring.whole_scores=ORIGINAL_WHOLE
        data['rows'].append(row);data['summary']=summary(data['rows']);save(path,data)
        print(stage,case['id'],row.get('metrics',row.get('failure')),round(row.get('seconds',0),2),flush=True)
    log(f"Saved {suite}/{stage}: {data['summary']}")

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--suite',default='development');args=parser.parse_args()
    if args.stage=='prepare':prepare()
    else:run(args.stage,args.suite)
