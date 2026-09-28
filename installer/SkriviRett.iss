#ifndef PackageDir
#error PackageDir required
#endif
#ifndef OutputDir
#error OutputDir required
#endif
[Setup]
AppId={{29FF9B59-7610-4E49-B80F-84AB995E60E9}
AppName=Skrivi Rett
AppVersion=0.1.0
AppPublisher=Skrivi
AppPublisherURL=https://skrivi.no
AppSupportURL=https://github.com/workavoidance/Skrivi-SpellChecker/issues
DefaultDirName={localappdata}\SkriviRett\app
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Skrivi-Rett-0.1.0-local-setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\SkriviRett.exe
CloseApplications=yes
RestartApplications=no
InfoBeforeFile=local-test.txt
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "norwegian"; MessagesFile: "compiler:Languages\Norwegian.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Skrivi Rett"; Filename: "{app}\SkriviRett.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Skrivi Rett"; Filename: "{app}\SkriviRett.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\SkriviRett.exe"; Description: "Start Skrivi Rett"; Flags: nowait postinstall skipifsilent
[Code]
function InitializeSetup(): Boolean;
var Cache: String;
begin
  Cache := GetEnv('SKRIVI_CACHE_DIR');
  if Cache = '' then Cache := ExpandConstant('{localappdata}\Skrivi');
  Result := FileExists(Cache + '\runtime\norwegian-py312-v1\Scripts\python.exe');
  if not Result then MsgBox('This local test build requires the existing Skrivi Norwegian sandbox cache. No models will be downloaded. Set up the sandbox on this PC first.', mbError, MB_OK);
end;
