"""Reproducible source-restoration benchmark. Derived text: CC BY-SA 4.0.

Original text/annotations: UD Norwegian Bokmaal / Norwegian Dependency Treebank.
No checker outputs or checker lexicon are used to select source sentences/errors.
"""
import hashlib
import json
from pathlib import Path
import random
from engine import words, replace_word

HERE=Path(__file__).parent
SOURCE=HERE/'corpus-source'
SEED=20260906
rng=random.Random(SEED)
raw=(SOURCE/'no_bokmaal-ud-dev.conllu').read_bytes()
revision=(SOURCE/'revision.txt').read_text(encoding='utf-8-sig').strip()
records=[]
for block in raw.decode('utf-8').strip().split('\n\n'):
    meta={}; annotations=[]
    for line in block.splitlines():
        if line.startswith('# ') and ' = ' in line:
            key,value=line[2:].split(' = ',1);meta[key]=value
        elif line and not line.startswith('#'):
            c=line.split('\t')
            if c[0].isdigit(): annotations.append(c)
    text=meta.get('text','')
    tokens=words(text)
    if 7<=len(tokens)<=25 and text.endswith(('.', '!', '?')) and 'Typo=Yes' not in block:
        records.append((meta,annotations,tokens))
rng.shuffle(records)
# Entire corpus vocabulary is used only to avoid injecting an already attested
# spelling in the mechanical-error arm; it is not an authoritative dictionary.
corpus_vocab={line.split('\t')[1].casefold() for line in raw.decode('utf-8').splitlines()
              if line and line[0].isdigit() and '\t' in line}
used=set(); pairs=[]

def add(record,token,changed,kind):
    meta,annotations,tokens=record
    original=meta['text']; altered=replace_word(original,token,changed)
    assert original!=altered and len(words(original))==len(words(altered))
    offset_token=words(altered)[token['id']]
    assert replace_word(altered,offset_token,token['word'])==original
    occurrence=sum(w['word']==changed for w in words(altered)[:token['id']])
    pair=f"source-{len(pairs)+1:03}"
    provenance={'corpus':'UD Norwegian-Bokmaal / Norwegian Dependency Treebank',
        'revision':revision,'file':'no_bokmaal-ud-dev.conllu','sent_id':meta['sent_id'],
        'source_url':f'https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal/blob/{revision}/no_bokmaal-ud-dev.conllu',
        'license':'CC BY-SA 4.0','original_text':original,
        'original_sha256':hashlib.sha256(original.encode()).hexdigest()}
    clean=dict(id=pair+'-original',pair_id=pair,kind='clean',text=original,errors=[],source=provenance)
    corrupt=dict(id=pair+'-mutated',pair_id=pair,kind=kind,text=altered,
        errors=[dict(word=changed,occurrence=occurrence,suggestions=[token['word']])],source=provenance,
        mutation=dict(token_id=token['id'],start=token['start'],end=token['end'],
                      original=token['word'],injected=changed,operation=kind))
    pairs.append((clean,corrupt));used.add(meta['sent_id'])

for kind in ['delete_letter','duplicate_letter','transpose_letters','substitute_letter']:
    count=0
    for record in records:
        meta,annotations,tokens=record
        if meta['sent_id'] in used:continue
        eligible_forms={c[1] for c in annotations if c[3] in ('NOUN','VERB','ADJ','ADV')}
        eligible=[w for w in tokens if w['word'] in eligible_forms and w['word'].islower()
                  and w['word'].isalpha() and 5<=len(w['word'])<=16]
        rng.shuffle(eligible)
        for token in eligible:
            word=token['word'];p=rng.randrange(1,len(word)-1)
            if kind=='delete_letter': changed=word[:p]+word[p+1:]
            elif kind=='duplicate_letter':changed=word[:p]+word[p]+word[p:]
            elif kind=='transpose_letters':changed=word[:p]+word[p+1]+word[p]+word[p+2:]
            else:changed=word[:p]+rng.choice('abcdefghijklmnopqrstuvwxyzæøå')+word[p+1:]
            if changed==word or changed.casefold() in corpus_vocab:continue
            add(record,token,changed,kind);count+=1;break
        if count==20:break
    assert count==20,(kind,count)

# POS annotation selects an infinitive marker and avoids blindly changing every å.
# Other pairs are small predeclared context probes, not an exhaustive error list.
for original,injected,pos,quota in [('å','og','PART',8),('vært','hvert',None,4),
                                  ('gjerne','hjerne',None,4),('får','for','VERB',4)]:
    count=0
    for record in records:
        meta,annotations,tokens=record
        if meta['sent_id'] in used:continue
        if not any(c[1]==original and (pos is None or c[3]==pos) for c in annotations):continue
        token=next((w for w in tokens if w['word']==original),None)
        if token:
            add(record,token,injected,'context');count+=1
        if count==quota:break
    assert count==quota,(original,count)

rows=[row for pair in pairs for row in pair]
(HERE/'sourced-cases.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=dict(seed=SEED,revision=revision,corpus_sha256=hashlib.sha256(raw).hexdigest(),
    pairs=len(pairs),cases=len(rows),selection='7–25 words; sentence-final punctuation; no Typo=Yes; seeded shuffle; unique sentence per pair; 20 per mechanical operation plus 20 predeclared context probes',
    license='CC BY-SA 4.0',note='Exact source restoration, not exhaustive linguistic correctness. Originals are corpus text, not certified spelling-clean. Mutations are synthetic, not observed dyslexic errors.')
(HERE/'sourced-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
for clean,corrupt in pairs:
    if corrupt['kind']=='context':print(clean['source']['sent_id'],clean['text'],corrupt['mutation'])
