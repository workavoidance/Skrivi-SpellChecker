"""Build the small desktop shell; spelling runtime and all lexical assets stay cached."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENGINE=('engine.py','nuspell_backend.py','experimental_inference.py','context_scoring.py',
 'setup_assets.py','setup_nuspell.py','personal_dictionary.py','dictionary_help.py','local_speech.py','local_speech.ps1')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--compiler',type=Path,required=True);args=parser.parse_args()
    os.chdir(ROOT)
    git=os.environ.get('SKRIVI_GIT','git')
    git_args=[git,'-c','safe.directory='+ROOT.as_posix()]
    if subprocess.check_output(git_args+['status','--porcelain'],text=True).strip():
        raise RuntimeError('Commit source changes before building a recorded installer.')
    stage=ROOT/'build/rett-payload';stage.mkdir(parents=True,exist_ok=True)
    for folder,names in [('desktop',('worker.py',)),('tools',('soft_hyphen_policy.py','hyphen_policy.py')),('sandbox/norwegian',ENGINE)]:
        dest=stage/folder;dest.mkdir(parents=True,exist_ok=True)
        for name in names:shutil.copy2(ROOT/folder/name,dest/name)
    env=dict(os.environ);env.pop('PYTHONPATH',None);env['PATH']=os.environ['WINDIR']+'/System32;'+os.environ['WINDIR']+';'+str(Path(sys.executable).parent)
    sys.path.insert(0,str(ROOT/'desktop'))
    from PySide6.QtWidgets import QApplication
    from main import icon
    app=QApplication.instance() or QApplication([])
    icon_path=ROOT/'build/rett.ico'
    if not icon().pixmap(256,256).save(str(icon_path)):raise RuntimeError('Icon export failed')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','SkriviRett','--icon',str(icon_path),'--paths','desktop']
    for folder in ('desktop','tools','sandbox'):command+=['--add-data',str(stage/folder)+';'+folder]
    command+=['--add-data',str(ROOT/'LICENSE')+';.',str(ROOT/'desktop/main.py')]
    subprocess.run(command,env=env,check=True)
    output=ROOT/'dist/SkriviRett'
    # Include readable sources for the local test build and Qt replacement/rebuild.
    shutil.copytree(ROOT/'desktop',output/'source/desktop',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(ROOT/'LICENSE',output/'LICENSE.txt')
    shutil.copytree(ROOT/'desktop/licenses',output/'licenses',dirs_exist_ok=True)
    shutil.copy2(ROOT/'desktop/THIRD_PARTY_NOTICES.md',output/'THIRD_PARTY_NOTICES.md')
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',output/'licenses/Python-LICENSE.txt')
    git=os.environ.get('SKRIVI_GIT','git')
    revision=subprocess.check_output([git,'-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],text=True).strip()
    manifest={'version':'0.1.0','source_commit':revision,'cached_engine_required':True,'files':{}}
    for path in output.rglob('*'):
        if path.is_file():manifest['files'][str(path.relative_to(output))]=hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'package.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    subprocess.run([str(output/'SkriviRett.exe'),'--check-startup'],check=True,timeout=30)
    release=ROOT/'dist/installer';release.mkdir(exist_ok=True)
    subprocess.run([str(args.compiler.resolve()),'/DPackageDir='+str(output),'/DOutputDir='+str(release),str(ROOT/'installer/SkriviRett.iss')],check=True)
    setup=release/'Skrivi-Rett-0.1.0-local-setup.exe'
    (release/'SHA256SUMS.txt').write_text(hashlib.sha256(setup.read_bytes()).hexdigest()+'  '+setup.name+'\n',encoding='ascii')
if __name__=='__main__':main()
