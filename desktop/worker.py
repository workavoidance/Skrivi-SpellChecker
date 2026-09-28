"""Local JSON worker. Uses the cached engine; never downloads or logs writing."""
import sys,json,contextlib,sqlite3,base64,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'sandbox/norwegian'),str(HERE.parent/'tools')]

def chunks(text):
    """Bound inference at whitespace; prefer sentence boundaries within each window."""
    if len(text)>20000:raise ValueError('Bruk opptil 20 000 tegn om gangen.')
    offset=0
    while offset<len(text):
        tail=text[offset:];matches=list(re.finditer(r"[^\W_]+(?:['’\-][^\W_]+)*",tail))
        end=min(len(tail),3500,matches[80].start() if len(matches)>80 else len(tail))
        if end<len(tail):
            boundaries=list(re.finditer(r'[.!?]\s+|\n',tail[:end]))
            if boundaries and boundaries[-1].end()>end//2:end=boundaries[-1].end()
            else:
                spaces=list(re.finditer(r'\s+',tail[:end]))
                if spaces:end=spaces[-1].end()
                else:raise ValueError('Et ord er for langt til å sjekkes.')
        part=tail[:end]
        if re.search(r'[^\W_]',part):yield offset,part
        offset+=end

def check_document(checker,text):
    tokens=[]
    for offset,part in chunks(text):
        result=checker.check(part,'nuspell_context')
        for token in result['words']:
            token['id']=len(tokens);token['start']+=offset;token['end']+=offset
            tokens.append(token)
    return {'text':text,'words':tokens}

def main():
    if '--speech' in sys.argv:
        from local_speech import synthesize
        import winsound
        request=json.loads(sys.stdin.readline())
        response=synthesize(request['text'])
        winsound.PlaySound(base64.b64decode(response['audio']),winsound.SND_MEMORY)
        return
    from engine import Checker
    from personal_dictionary import PersonalDictionary
    from dictionary_help import DictionaryHelp
    from setup_assets import ROOT,DICT_REV
    from soft_hyphen_policy import SoftHyphenPolicy
    checker=Checker();personal=PersonalDictionary();dictionary=DictionaryHelp()
    db=sqlite3.connect((ROOT/'lexical/ordbank-20220201/ordbank.sqlite3').as_uri()+'?mode=ro',uri=True)
    props={w:{'display':d,'proper':bool(p)} for w,d,p in db.execute('SELECT word,display,proper FROM form')};db.close()
    base=sqlite3.connect((ROOT/'lexical/ordbank-20220201/help-baseforms.sqlite3').as_uri()+'?mode=ro',uri=True)
    for (word,) in base.execute("SELECT DISTINCT form FROM base WHERE tag LIKE 'adj %'"):
        props.setdefault(word,{})['adjective']=True
    base.close()
    dic=ROOT/'models'/('bokmal-lexicon-'+DICT_REV[:12])/'nb_NO.dic'
    forms=set(props)|{line.split('/')[0].strip().casefold() for line in dic.read_text(encoding='utf-8-sig').splitlines()[1:]}
    policy=SoftHyphenPolicy(lambda w:w in forms,lambda w:w in forms,props.get)
    for line in sys.stdin:
        request={}
        try:
            request=json.loads(line)
            if request['action']=='remember':
                personal.add(request['word']);payload={'remembered':True}
            else:
                # Suppress any dependency diagnostics on protocol stdout.
                with contextlib.redirect_stdout(sys.stderr):
                    result=personal.apply(check_document(checker,request['text']))
                entries={}
                for token in result['words']:
                    order=policy.partition(token);token['suggestions']=order['shown'];token['more']=order['more']
                    if token['status']!='OK':
                        for word in token['suggestions']+token['more']:
                            if word not in entries:entries[word]=dictionary.lookup(word)
                payload={'result':result,'help':entries}
            print(json.dumps({'id':request['id'],'ok':True,**payload},ensure_ascii=False),flush=True)
        except Exception as exc:
            # Error detail returned locally, never persisted.
            print(json.dumps({'id':request.get('id'),'ok':False,'error':str(exc)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
