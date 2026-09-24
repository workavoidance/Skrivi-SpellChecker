"""Freeze a fresh source-restoration validation set before viewing experiment scores.
Derived text CC BY-SA 4.0; attribution: corpus-source/README.md and LICENSE.txt.
"""
import json,random,hashlib
from pathlib import Path
from collections import Counter
from engine import words,replace_word
HERE=Path(__file__).parent
excluded={c['source']['sent_id'] for c in json.loads((HERE/'sourced-cases.json').read_text(encoding='utf-8'))}
records=[]
for block in (HERE/'corpus-source/no_bokmaal-ud-dev.conllu').read_text(encoding='utf-8').split('\n\n'):
    fields=dict(line[2:].split(' = ',1) for line in block.splitlines() if line.startswith('# ') and ' = ' in line)
    text=fields.get('text','')
    if fields.get('sent_id') not in excluded and 7<=len(words(text))<=25 and text.endswith('.') and 'Typo=Yes' not in block:
        records.append(fields)
random.Random(92405).shuffle(records)
swaps={'visste':'viste','viste':'visste','skulle':'skule','vann':'van','sammen':'samen','legge':'lege',
       'huske':'huse','nøklene':'nølene','vært':'hvert','gjerne':'hjerne','får':'for','vil':'vill'}
rows=[];used=set();counts=Counter();revision=(HERE/'corpus-source/revision.txt').read_text(encoding='utf-8-sig').strip()
for rec in records:
    original=rec['text']
    token=next((w for w in words(original) if w['word'] in swaps and counts[w['word']]<3),None)
    if not token:continue
    wrong=swaps[token['word']];text=replace_word(original,token,wrong)
    occurrence=sum(w['word']==wrong for w in words(text)[:token['id']])
    source=dict(sent_id=rec['sent_id'],original_text=original,revision=revision,license='CC BY-SA 4.0')
    rows.append(dict(id='fresh-'+rec['sent_id']+'-original',kind='clean',text=original,errors=[],source=source))
    rows.append(dict(id='fresh-'+rec['sent_id']+'-mutated',kind='context',text=text,
                     errors=[dict(word=wrong,occurrence=occurrence,suggestions=[token['word']])],source=source))
    assert replace_word(text,words(text)[token['id']],token['word'])==original
    used.add(rec['sent_id']);counts[token['word']]+=1
    if sum(counts.values())==20:break
assert sum(counts.values())==20,counts
for rec in records:
    if rec['sent_id'] in used:continue
    rows.append(dict(id='fresh-'+rec['sent_id']+'-control',kind='clean',text=rec['text'],errors=[],
                     source=dict(sent_id=rec['sent_id'],original_text=rec['text'],revision=revision,license='CC BY-SA 4.0')))
    if len(rows)==60:break
assert len(rows)==60
(HERE/'scoring-validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('60 cases: 20 controlled errors and 40 original controls. All source IDs disjoint from previous sourced test.')
print(dict(counts));print(hashlib.sha256((HERE/'scoring-validation.json').read_bytes()).hexdigest())
