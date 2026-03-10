; Inno Setup 脚本 - SlyLab
; 使用前请先执行: pyinstaller SlyLab.spec --clean --noconfirm
; 将生成 dist\SlyLab 目录，本脚本会将该目录打包为安装程序

#define MyAppName "SlyLab"
#define MyAppExe "SlyLab.exe"
#define MyAppOutput "SlyLab"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVerName={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 安装程序输出：当前目录下的 Output 文件夹，安装包名为 SlyLab_Setup.exe
OutputDir=Output
OutputBaseFilename=SlyLab_Setup
; SetupIconFile=static\favicon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "default"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
; 将 PyInstaller 生成的整个目录内容安装到 {app}
Source: "dist\{#MyAppOutput}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Comment: "启动 SlyLab"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon; Comment: "启动 SlyLab"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}"



