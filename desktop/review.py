"""Review state independent of Qt. Offsets always refer to the exact displayed text."""
from copy import deepcopy
import html

class Review:
    def __init__(self,text,result):
        self.text=text;self.tokens=deepcopy(result['words']);self.history=[]
    def pending(self):
        return [t for t in self.tokens if t['status']!='OK' and not t.get('reviewed')]
    def decide(self,identifier,replacement=None):
        token=next(t for t in self.tokens if t['id']==identifier)
        if self.text[token['start']:token['end']]!=token['word']:
            raise ValueError('Teksten er endret. Sjekk teksten på nytt.')
        if replacement is not None and replacement not in token.get('suggestions',[])+token.get('more',[]):
            raise ValueError('Velg et tilgjengelig forslag.')
        self.history.append((self.text,deepcopy(self.tokens)))
        if replacement is not None:
            start,end=token['start'],token['end'];delta=len(replacement)-(end-start)
            self.text=self.text[:start]+replacement+self.text[end:]
            token.update(word=replacement,end=start+len(replacement))
            for other in self.tokens:
                if other is token:continue
                if other['start']>=end:other['start']+=delta;other['end']+=delta
                elif other['end']>start:other['reviewed']=True
        token['reviewed']=True
    def undo(self):
        if self.history:self.text,self.tokens=self.history.pop()
    def markup(self,selected=None):
        chunks=[];last=0
        for t in sorted(self.tokens,key=lambda t:t['start']):
            if t['start']<last:continue
            chunks.append(html.escape(self.text[last:t['start']]))
            word=html.escape(self.text[t['start']:t['end']])
            if t['status']=='OK' or t.get('reviewed'):
                chunks.append('<span style="text-decoration:underline; text-decoration-color:#157A52">'+word+'</span>')
            else:
                color='#A9362A' if t['status']=='LIKELY_ERROR' else '#865900'
                weight='font-weight:bold;' if t['id']==selected else ''
                chunks.append(f'<a href="word:{t["id"]}" style="color:{color};{weight}">{word}</a>')
            last=t['end']
        chunks.append(html.escape(self.text[last:]))
        return '<div style="white-space:pre-wrap;line-height:1.65">'+''.join(chunks).replace('\n','<br>')+'</div>'
