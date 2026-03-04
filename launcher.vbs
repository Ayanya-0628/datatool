' =============================================
'  数据分析工具 - 快捷启动器
'  功能: 静默启动Flask服务 + 自动打开浏览器
'  双击桌面快捷方式即可使用
' =============================================
Option Explicit

Dim WshShell, fso
Dim strProjectDir, strPort, strUrl

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 自动使用 launcher.vbs 所在目录为项目目录，便于分享到任意路径
strProjectDir = fso.GetParentFolderName(WScript.ScriptFullName)
strPort = "7860"
strUrl = "http://localhost:" & strPort

' --- 检查项目目录 ---
If Not fso.FolderExists(strProjectDir) Then
    MsgBox "项目目录不存在: " & strProjectDir, vbCritical, "启动失败"
    WScript.Quit
End If

' --- Step 1: 清理占用端口的旧进程 ---
WshShell.Run "powershell -WindowStyle Hidden -Command " & Chr(34) & _
    "Get-NetTCPConnection -LocalPort " & strPort & " -ErrorAction SilentlyContinue | " & _
    "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" & _
    Chr(34), 0, True

WScript.Sleep 1000

' --- Step 2: 启动 Flask 服务 (隐藏窗口) ---
WshShell.CurrentDirectory = strProjectDir
WshShell.Run "cmd /c python app.py", 0, False

' --- Step 3: 等待服务就绪 ---
WScript.Sleep 3000

' --- Step 4: 打开浏览器 ---
WshShell.Run strUrl, 1, False

Set fso = Nothing
Set WshShell = Nothing
