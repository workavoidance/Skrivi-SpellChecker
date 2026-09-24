import math
from engine import context

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

