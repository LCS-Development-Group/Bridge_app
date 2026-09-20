[Setup]
AppId=LCS_Bridge_E06E523D
AppName=LCS Bridge
AppVersion=1.1.0
AppPublisher=Karol Pach (UMIR, PWr)
DefaultDirName={autopf}\LCS_Bridge
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\LCS_Bridge_Win11.exe
OutputBaseFilename=LCS_Bridge_Win11_setup_110
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\LCS_Bridge_Win11\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\LCS Bridge"; Filename: "{app}\LCS_Bridge_Win11.exe"
Name: "{autodesktop}\LCS Bridge"; Filename: "{app}\LCS_Bridge_Win11.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LCS_Bridge_Win11.exe"; Description: "{cm:LaunchProgram,LCS Bridge}"; Flags: nowait postinstall skipifsilent