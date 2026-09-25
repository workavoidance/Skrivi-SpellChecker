"""Verify opt-in UI mode, cross-request reuse, Unicode, and missing assets locally."""
import json,re,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sandbox/norwegian'))
from engine import Checker,replace_word,single
from unittest.mock import patch


def main():
 checker=Checker()
 with patch('lexical_coverage.available',return_value=False):
  try:checker.check('Dette er en test.','nuspell_coverage')
  except RuntimeError as exc:assert 'orddata' in str(exc)
  else:raise AssertionError('Missing assets accepted')
 assert checker.coverage_checker is None and checker.norbert is None
 proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'sandbox/norwegian/server.py'),'--responsive','--no-browser'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 try:
  line=proc.stdout.readline().strip();assert line.startswith('Skrivi Norwegian POC: http://127.0.0.1:')
  url=line.split('POC: ',1)[1];html=urllib.request.urlopen(url,timeout=15).read().decode('utf8')
  assert 'value="nuspell_context" selected' in html
  assert '<option value="nuspell_coverage">Flere ordforslag (utprøving)</option>' in html
  assert '__COVERAGE_OPTION__' not in html
  key=re.search(r"const KEY='([^']+)'",html).group(1)
  def request(path,data):
   req=urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Skrivi-Key':key,'Origin':url})
   return json.load(urllib.request.urlopen(req,timeout=120))
  text='😀 Dette er lærerns bok.'
  a=request('/check',dict(text=text,mode='nuspell_context'))
  for _ in range(2):
   result=request('/check',dict(text=text,mode='nuspell_coverage'))
   assert result['mode']=='nuspell_coverage' and result['text']==text
   target=next(w for w in result['words'] if w['word']=='lærerns')
   assert 'lærerens' in target['suggestions']
   assert replace_word(text,target,'lærerens')=='😀 Dette er lærerens bok.'
   for t in result['words']:
    assert text[t['start']:t['end']]==t['word']
    assert t['start_utf16']==len(text[:t['start']].encode('utf-16-le'))//2
    assert len(t['suggestions'])<=3 and all(single(x) for x in t['suggestions'])
  b=request('/check',dict(text=text,mode='nuspell_context'))
  fields=lambda r:[(w['word'],w['status'],w['suggestions'],w['candidates']) for w in r['words']]
  assert fields(a)==fields(b)
  request('/shutdown',{});proc.wait(timeout=15)
  report=dict(opt_in_option=True,default_selected_unchanged=True,repeated_http_requests=2,
              unicode_offsets=True,single_word_replacement=True,default_before_after_identical=True,
              missing_assets_fail_without_model_load=True,own_server_stopped=True)
  out=ROOT/'results/coverage-targeted-20260924/http.json';out.write_text(json.dumps(report,indent=2))
  print(json.dumps(report,indent=2))
 finally:
  if proc.poll() is None:proc.terminate();proc.wait(timeout=15)

if __name__=='__main__':main()
