"""Experimental inference reuse. Same masked inputs and scoring rules; fewer repeated rows."""
import math
from engine import context

def fast_whole(model,text,token,candidates,neutral=False):
    torch=model.torch;sentence,start,end=context(text,token)
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
    torch=model.torch;sentence,start,end=context(text,token)
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

class FastNorbert:
    """Borrow resident weights; do not load a second model."""
    def __init__(self, original):
        self.torch = original.torch
        self.tokenizer = original.tokenizer
        self.model = original.model
    rank = fast_rank
