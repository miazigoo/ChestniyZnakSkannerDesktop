#define MyAppName "Chestniy Znak Desktop"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "DevAndProd"
#define MyAppExeName "ChestniyZnakDesktop.exe"
#define MyBuildDir "..\dist\ChestniyZnakDesktop"
#define MyInstallerDir "..\installer"

[Setup]
AppId={{8C36C870-ECF8-46C0-83BA-F8BB3B3D4D8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ChestniyZnakDesktop
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyInstallerDir}
OutputBaseFilename=ChestniyZnakDesktopSetup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardImageFile=installer_assets\installer_wizard.bmp
WizardSmallImageFile=installer_assets\installer_small.bmp
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\src\chestniy_znak_desktop\resources\icons\chestniy_znak_app.ico
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"; Flags: unchecked

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
