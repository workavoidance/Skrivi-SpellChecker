"""Five offline scoring experiments. No app defaults are changed.

Scores are collected without passing answer keys to any model method.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from engine import Checker, context
from evaluate import score

HERE=Path(__file__).parent

def whole_scores(model,text,token,candidates,neutral=False):
    torch=model.torch
    sentence,start,end=context(text,token)
    if neutral:sentence,start,end=token['word'],0,len(token['word'])
    rows=[];positions=[];targets=[]
    for candidate in candidates:
        changed=sentence[:start]+candidate+sentence[end:]
        enc=model.tokenizer(changed,return_offsets_mapping=True)
        ids=enc['input_ids'];ps=[i for i,(a,b) in enumerate(enc['offset_mapping']) if b>start and a<start+len(candidate)]
        if not ps or len(ids)>256:raise ValueError('Unscorable candidate')
        masked=list(ids)
        for p in ps:masked[p]=model.tokenizer.mask_token_id
        rows.append(masked);positions.append(ps);targets.append([ids[p] for p in ps])
    values=[]
    for offset in range(0,len(rows),16):
        batch=rows[offset:offset+16];n=max(map(len,batch))
        ids=torch.tensor([r+[model.tokenizer.pad_token_id]*(n-len(r)) for r in batch])
        mask=torch.tensor([[1]*len(r)+[0]*(n-len(r)) for r in batch])
        with torch.inference_mode():
            logits=model.model(input_ids=ids,attention_mask=mask).logits
            for j in range(len(batch)):
                logs=[logits[j,p].log_softmax(-1)[t].item() for p,t in zip(positions[offset+j],targets[offset+j])]
                if not all(math.isfinite(s) for s in logs):raise ValueError('Nonfinite scores')
                values.append(sum(logs)/len(logs))
    return dict(zip(candidates,values)),dict(zip(candidates,map(len,positions)))

def collect(cases_path,output):
    cases=json.loads(Path(cases_path).read_text(encoding='utf-8'))
    checker=Checker();data={'cases_file':str(cases_path),'cases_sha256':hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
        'experiment_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'note':'Exploratory, synthetic/source-restoration labels. Baseline v2, no compounds; known lowercase words >=3 only.', 'rows':[]}
    prior_cache={}
    for case in cases:
        start=time.perf_counter();base=checker.check(case['text'],'norbert_v2');lex=checker.revised_lexicon
        extra=[]
        for token in base['words']:
            word=token['word']
            if not(word.islower() and word.isalpha() and len(word)>=3 and word in lex.vocab):continue
            matches=lex.process.extract(word,lex.choices,scorer=lex.distance,score_cutoff=1,limit=64)
            doubles=[word[:p]+word[p]+word[p:] for p in range(len(word))]
            alts=list(dict.fromkeys(token['candidates']+[w for w in doubles if w in lex.vocab]
                                   +[w for w,_,_ in matches if w!=word and w.isalpha()]))[:24]
            if not alts:continue
            pool=[word]+alts
            partial=dict(checker.norbert.rank(case['text'],token,pool))
            whole,lengths=whole_scores(checker.norbert,case['text'],token,pool)
            key=tuple(pool)
            if key not in prior_cache:prior_cache[key]=whole_scores(checker.norbert,case['text'],token,pool,neutral=True)[0]
            extra.append(dict(id=token['id'],original=word,partial=partial,whole=whole,
                              neutral=prior_cache[key],lengths=lengths))
        data['rows'].append(dict(case=case,baseline=base,comparisons=extra,collection_seconds=time.perf_counter()-start))
        Path(output).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(case['id'],'scored',len(extra),'words',round(time.perf_counter()-start,2),flush=True)

VARIANTS=['baseline','broad_v3','whole_mask','agreement','context_gain','single_token','strict_margin']
def proposal(c,mode):
    original=c['original'];p=c['partial'];w=c['whole'];n=c['neutral'];lengths=c['lengths']
    if mode=='broad_v3':scores=p;threshold=4
    elif mode=='strict_margin':scores=p;threshold=8
    elif mode in ('whole_mask','agreement','single_token'):scores=w;threshold=4
    elif mode=='context_gain':scores={k:w[k]-n[k] for k in w};threshold=4
    else:return []
    ranked=sorted(((k,v) for k,v in scores.items() if k!=original),key=lambda x:x[1],reverse=True)
    good=[k for k,v in ranked if v-scores[original]>threshold]
    if mode=='agreement':
        # Same best word in two scoring views, with a strong partial-score gap.
        best_p=max((k for k in p if k!=original),key=p.get)
        if not good or good[0]!=best_p or p[best_p]-p[original]<=4:return []
        good=[k for k in good if p[k]-p[original]>4]
    if mode=='context_gain':good=[k for k in good if p[k]-p[original]>4]
    if mode=='single_token':
        if lengths[original]!=1:return []
        good=[k for k in good if lengths[k]==1]
    return good[:3]

def summarize(paths,output):
    report={}
    for path in paths:
        data=json.loads(Path(path).read_text(encoding='utf-8'));group={}
        for mode in VARIANTS:
            totals={k:0 for k in ['errors','detected','top1','top3','false_alarms']};clean=0;untouched=0;changes=[]
            for row in data['rows']:
                result=json.loads(json.dumps(row['baseline']))
                if mode!='baseline':
                    for c in row['comparisons']:
                        proposed=proposal(c,mode)
                        if proposed:
                            t=next(w for w in result['words'] if w['id']==c['id'])
                            t.update(status='UNCERTAIN',suggestions=proposed)
                metrics=score(row['case'],result)
                for k in totals:totals[k]+=metrics[k]
                if not row['case']['errors']:
                    clean+=1;untouched+=metrics['false_alarms']==0
                changes.append(dict(id=row['case']['id'],metrics=metrics,flags=[{'word':w['word'],'suggestions':w['suggestions']} for w in result['words'] if w['status']!='OK']))
            group[mode]={**totals,'cases':len(data['rows']),'clean':clean,'clean_unflagged':untouched,'details':changes}
        report[Path(path).stem]=group
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,group in report.items():
        print(name)
        for mode,row in group.items():print(mode,{k:v for k,v in row.items() if k!='details'})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cases');parser.add_argument('--output',required=True);parser.add_argument('--summarize',nargs='+')
    args=parser.parse_args()
    if args.summarize:summarize(args.summarize,args.output)
    else:collect(args.cases,args.output)
