"""Setup-only network access. All downloaded assets live outside the application."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(os.environ.get('SKRIVI_CACHE_DIR') or Path(os.environ['LOCALAPPDATA']) / 'Skrivi')
REV = 'f84759ddd3e628afcabb561253d80bbb845e3c8b'
DICT_REV = '32b006a2c22a4ac7e8ed3f03346f7b3d85a970a4'
WEIGHT_HASH = '4cd603c95384f63cda9e925c769904269f3ebfbf4bd77aa791b4db21acb62f7d'

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def fetch(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = path.with_name(path.name + '.sha256')
    if path.exists():
        known = expected or (receipt.read_text().strip() if receipt.exists() else None)
        if not known or digest(path) != known:
            raise RuntimeError(f'Cache integrity check failed: {path}. Remove this specific file to redownload.')
        print(f'Reusing {path.name}', flush=True)
        return
    partial = path.with_name(path.name + '.partial')
    print(f'Downloading {path.name}', flush=True)
    with urllib.request.urlopen(url, timeout=60) as src, partial.open('wb') as dst:
        while chunk := src.read(1024 * 1024):
            dst.write(chunk)
    actual = digest(partial)
    if expected and actual != expected:
        raise RuntimeError(f'Checksum mismatch: {path.name}')
    partial.replace(path)
    receipt.write_text(actual)

if __name__ == '__main__':
    model = ROOT / 'models' / f'norbert3-small-{REV[:12]}'
    for name in ['config.json', 'configuration_norbert.py', 'modeling_norbert.py',
                 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json',
                 'pytorch_model.bin', 'README.md']:
        fetch(f'https://huggingface.co/ltg/norbert3-small/resolve/{REV}/{name}',
              model / name, WEIGHT_HASH if name == 'pytorch_model.bin' else None)
    dictionaries = ROOT / 'models' / f'bokmal-lexicon-{DICT_REV[:12]}'
    for name in ['nb_NO.dic', 'nb_NO.aff', 'README', 'COPYING']:
        fetch(f'https://raw.githubusercontent.com/LibreOffice/dictionaries/{DICT_REV}/no/{name}', dictionaries / name)
    manifest = {'norbert_revision': REV, 'dictionary_revision': DICT_REV,
                'model': str(model), 'dictionary': str(dictionaries),
                'files': {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                          for folder in (model, dictionaries) for p in folder.iterdir()
                          if p.is_file() and not p.name.endswith(('.sha256', '.partial'))}}
    (ROOT / 'models' / 'norwegian-poc-assets.json').write_text(json.dumps(manifest, indent=2))
    print('Norwegian assets ready. Normal launch is offline.', flush=True)
