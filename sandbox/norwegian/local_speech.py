"""Offline Windows speech; plain text via stdin, audio in memory only."""
import json
from pathlib import Path
import subprocess

def synthesize(text=None):
    if text is not None and (not isinstance(text,str) or not 1 <= len(text) <= 600):
        raise ValueError('Velg et ord eller en kort forklaring å høre.')
    request = {'action':'voices'} if text is None else {'action':'speak','text':text}
    p = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
        '-File',str(Path(__file__).with_suffix('.ps1'))],
        input=json.dumps(request,ensure_ascii=False),encoding='utf-8',text=True,
        capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:
        raise RuntimeError('Norsk opplesning er ikke tilgjengelig. Du kan fortsatt lese forklaringene og velge ord.')
    return json.loads(p.stdout)
