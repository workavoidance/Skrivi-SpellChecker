"""Small rule-based Norwegian corruption model, not a trained dyslexia model.

Four fixed demonstration profiles. All word forms and level assignments are
constructed; sources support error families, not their frequency or these labels.
"""
import json
from pathlib import Path
from engine import words

BASE=('I morgen skal jeg besøke biblioteket sammen med søsteren min. '
      'Vi skal finne informasjon om sommerfugler til en oppgave på skolen. '
      'Etterpå vil jeg kjøpe en sjokolade og en flaske vann. '
      'Før vi drar hjem, må jeg huske å legge billetten og nøklene i jakkelomma.')
# word, injected spelling, error family; levels are cumulative except severe overrides.
LITE=[('informasjon','informsjon','omission'),('kjøpe','sjøpe','sound_based'),
      ('billetten','biletten','double_consonant')]
MODERATE=LITE+[
    ('biblioteket','bibloteket','omission'),('søsteren','søstern','ending_reduction'),
    ('sommerfugler','sommerfulger','letter_order'),('sjokolade','sjoklade','omission')]
BAD=MODERATE+[
    ('morgen','mårgen','sound_based'),('vann','van','double_consonant'),
    ('huske','huse','omission'),('nøklene','nølene','omission'),
    ('jakkelomma','jakke lomma','word_boundary')]
VERY_BAD=BAD+[
    ('besøke','besøge','consonant_substitution'),('sammen','samen','double_consonant'),
    ('flaske','faske','cluster_reduction'),('skolen','skoln','ending_reduction'),
    ('legge','lege','double_consonant'),('Etterpå','Etrpå','multiple_omissions')]
OVERRIDES={'biblioteket':'biblteke','informasjon':'infrmasjon',
           'sommerfugler':'somrfugler','sjokolade':'sjokla','søsteren':'søstrn'}

def generate(text, edits):
    """Apply one documented replacement per original occurrence, retaining offsets.

    Caller supplies curated edits. No unrestricted random mutation of a new text.
    """
    tokens=words(text);lookup={a:(b,k) for a,b,k in edits}
    assert len(lookup)==len(edits)
    assert all(sum(t['word']==a for t in tokens)==1 for a in lookup)
    pieces=[];cursor=0;changes=[];output_length=0
    for token in tokens:
        if token['word'] not in lookup:continue
        before=text[cursor:token['start']];pieces.append(before);output_length+=len(before)
        wrong,kind=lookup[token['word']]
        assert wrong!=token['word']
        changes.append(dict(original=token['word'],injected=wrong,family=kind,
                            original_start=token['start'],original_end=token['end'],
                            altered_start=output_length,altered_end=output_length+len(wrong),
                            requires_span_replacement=any(c.isspace() for c in wrong)))
        pieces.append(wrong);output_length+=len(wrong);cursor=token['end']
    pieces.append(text[cursor:]);altered=''.join(pieces)
    restored=altered
    for c in reversed(changes):
        assert restored[c['altered_start']:c['altered_end']]==c['injected']
        restored=restored[:c['altered_start']]+c['original']+restored[c['altered_end']:]
    assert restored==text
    return dict(text=altered,original=text,original_words=len(tokens),
                affected_words=len(changes),affected_percent=round(100*len(changes)/len(tokens),1),
                changes=changes)

def examples():
    rows=[]
    for name,edits in [('Lite',LITE),('Moderate',MODERATE),('Bad',BAD),('Very bad',VERY_BAD)]:
        if name=='Very bad':
            edits=[(a,OVERRIDES.get(a,b),'multiple_changes' if a in OVERRIDES else k) for a,b,k in edits]
        rows.append(dict(level=name,**generate(BASE,edits)))
    return rows

if __name__=='__main__':
    here=Path(__file__).parent
    rows=examples()
    (here/'error-profile-examples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Four Norwegian spelling-corruption profiles','',
           'Synthetic examples created for the Skrivi sandbox. The base paragraph is assistant-authored and checked by the assistant. Neither the examples nor the four level assignments are taken from a diagnosed writer or a validated severity scale. Error family selection is informed by the sources in ERROR-PROFILE-MODEL.md.','',
           '## Intended original','',BASE,'',
           'English: Tomorrow I will visit the library with my sister. We will find information about butterflies for a school assignment. Afterwards I want to buy a chocolate and a bottle of water. Before we go home, I must remember to put the ticket and keys in my jacket pocket.','']
    for row in rows:
        lines += ['## '+row['level'],'',f"{row['affected_words']} of {row['original_words']} original words affected ({row['affected_percent']}%).",'', '```text',row['text'],'```','',
                  '| Written | Intended | Error family |','|---|---|---|']
        lines += [f"| {c['injected']} | {c['original']} | {c['family']} |" for c in row['changes']]
        lines += ['']
    lines += ['Bad and Very bad include a split compound. Current sandbox replacement is single-word only, so it cannot fully repair that split with one suggestion. The JSON uses span offsets and does not pretend this is a single-token gold label. Some mutations form existing words, such as huse or lege: the intended original is recorded, but whether a checker detects these depends on its context coverage. No benchmark results are claimed for these examples.']
    (here/'ERROR-PROFILE-EXAMPLES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for row in rows:print(row['level'],row['affected_words'],row['original_words'],row['affected_percent'],row['text'])
