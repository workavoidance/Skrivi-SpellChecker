"""Optional portable runtime setup. No system install and no model downloads."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
from setup_assets import ROOT

HERE = Path(__file__).parent
RUNTIME = ROOT / 'runtime' / 'nuspell-5.1.8-msys2-v1'
PACKAGES = [
    ('nuspell-5.1.8-1', '3d29cb7b1fa84cb7a09175377ace6bfd9deee3df183c55137f4a035c41750a72'),
    ('icu-78.3-4', 'db9282bbd0a2e74c31d66af6bd89eb68d647a09f721eef4c661768588dca4324'),
    ('gcc-libs-16.2.0-3', '5763fabf86fa13a4449ee765006d3446384ed66af7bf827459710eb777e0b11c'),
    ('libwinpthread-14.0.0.r353.g6df76fa52-2', 'ec1a46e63d424a90992a14c0996c0b5bb17370af6044380b590d05f725eeb43f'),
]

def main():
    receipts = []
    for name, expected in PACKAGES:
        filename = 'mingw-w64-ucrt-x86_64-' + name + '-any.pkg.tar.zst'
        url = 'https://repo.msys2.org/mingw/ucrt64/' + filename
        archive = RUNTIME / 'packages' / filename
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            print('Downloading runtime component:', name, flush=True)
            data = urllib.request.urlopen(url, timeout=120).read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError('Package checksum mismatch: ' + name)
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Cached package checksum mismatch: ' + name)
        entries = subprocess.check_output(['tar', '-tf', str(archive)], text=True).splitlines()
        files = {}
        for entry in entries:
            p = PurePosixPath(entry)
            if p.is_absolute() or '..' in p.parts or ':' in entry:
                raise RuntimeError('Unsafe archive path')
            wanted = (entry.startswith('ucrt64/bin/') and
                      (entry.endswith('.dll') or p.name == 'nuspell.exe')) or entry.startswith('ucrt64/share/licenses/')
            if not wanted or entry.endswith('/'):
                continue
            # Read selected members as bytes; never extract archive links or paths.
            data = subprocess.check_output(['tar', '-xOf', str(archive), entry])
            target = RUNTIME.joinpath(*p.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.read_bytes() != data:
                target.write_bytes(data)
            files[entry] = hashlib.sha256(data).hexdigest()
        receipts.append(dict(url=url, sha256=expected, bytes=archive.stat().st_size, files=files))
    (RUNTIME / 'receipt.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    exe = RUNTIME / 'ucrt64/bin/nuspell.exe'
    subprocess.run([str(exe), '--version'], check=True)
    print('Portable Nuspell ready:', exe)

if __name__ == '__main__':
    main()
