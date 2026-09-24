"""Package an explicit application allowlist; never include user writing or experiment logs."""
from pathlib import Path
import zipfile

HERE = Path(__file__).parent
OUT = HERE.parent / 'releases'
OUT.mkdir(exist_ok=True)
files = ['server.py', 'engine.py', 'nuspell_backend.py', 'experimental_inference.py',
         'context_scoring.py', 'setup_assets.py', 'setup_nuspell.py', 'local_speech.py',
         'personal_dictionary.py',
         'local_speech.ps1', 'poc.js', 'responsive.js', 'responsive.html',
         'Launch-Responsive.ps1', 'Launch-Responsive.cmd', 'Setup-Responsive.ps1',
         'wordnet_help.py', 'setup_wordnet.py', 'wordnet.js', 'responsive-wordnet.html',
         'Setup-Wordnet.ps1', 'Setup-Wordnet.cmd', 'Launch-Wordnet-Experiment.ps1',
         'Launch-Wordnet-Experiment.cmd', 'WORDNET-EXPERIMENT.md', 'WORDNET-NOTICE.md']
archive = OUT / 'Skrivi-Responsive-POC.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for name in files:
        bundle.write(HERE / name, 'Skrivi-Responsive-POC/norwegian/' + name)
    for name in ['Core.ps1', 'config.json']:
        bundle.write(HERE.parent / name, 'Skrivi-Responsive-POC/' + name)
    bundle.write(HERE / 'RESPONSIVE-README.md', 'Skrivi-Responsive-POC/README.md')
    bundle.writestr('Skrivi-Responsive-POC/Start-Skrivi.cmd',
        '@echo off\r\ncall "%~dp0norwegian\\Launch-Responsive.cmd"\r\n')
    bundle.writestr('Skrivi-Responsive-POC/Setup-Once.cmd',
        '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0norwegian\\Setup-Responsive.ps1"\r\npause\r\n')
    bundle.writestr('Skrivi-Responsive-POC/Setup-Wordnet-Experiment.cmd',
        '@echo off\r\ncall "%~dp0norwegian\\Setup-Wordnet.cmd"\r\n')
    bundle.writestr('Skrivi-Responsive-POC/Start-Wordnet-Experiment.cmd',
        '@echo off\r\ncall "%~dp0norwegian\\Launch-Wordnet-Experiment.cmd"\r\n')
print(f'{archive}: {archive.stat().st_size:,} bytes; {len(files)+7} application/documentation files')
