"""Local HTTP smoke test. Starts and stops only its own hidden sandbox process."""
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from engine import single, words
from nuspell_backend import MODES

HERE=Path(__file__).parent

def main():
    proc=subprocess.Popen([sys.executable,'-u',str(HERE/'server.py'),'--no-browser'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        line=proc.stdout.readline().strip()
        if not line.startswith('Skrivi Norwegian POC: http://127.0.0.1:'):
            raise RuntimeError('Local test server failed to start')
        url=line.split('POC: ',1)[1]
        html=urllib.request.urlopen(url,timeout=15).read().decode('utf-8')
        key=re.search(r"const KEY='([^']+)'",html).group(1)
        assert 'value="norbert_v2" selected' in html
        assert all('value="'+mode+'"' in html for mode in MODES)
        text='😀 Hei! Jeg arbeider med budsjet og lekser.'
        records=[]
        for mode in MODES:
            request=urllib.request.Request(url+'/check',data=json.dumps(dict(text=text,mode=mode)).encode(),
                headers={'Content-Type':'application/json','X-Skrivi-Key':key,'Origin':url})
            result=json.load(urllib.request.urlopen(request,timeout=120))
            assert result['text']==text and result['mode']==mode
            assert len(result['words'])==len(words(text))
            for w in result['words']:
                assert text[w['start']:w['end']]==w['word']
                assert w['start_utf16']==len(text[:w['start']].encode('utf-16-le'))//2
                assert len(w['suggestions'])<=3 and all(single(s) for s in w['suggestions'])
            target=next(w for w in result['words'] if w['word']=='budsjet')
            assert 'budsjett' in target['suggestions']
            records.append(dict(mode=mode,http=200,unchanged_text=True,offsets_verified=True,suggestion_contract=True))
        shutdown=urllib.request.Request(url+'/shutdown',data=b'{}',headers={'X-Skrivi-Key':key,'Origin':url})
        urllib.request.urlopen(shutdown,timeout=10).close()
        proc.wait(timeout=10)
        report=dict(default_unchanged=True, modes=records, own_server_stopped=True,
                    note='HTTP integration plus existing simulated-DOM UI tests; no full visual/accessibility browser audit.')
        (HERE/'nuspell-experiments/http-integration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('Four local HTTP modes passed; default, Unicode offsets and single-word suggestions verified; test server stopped.')
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)

if __name__=='__main__':main()
