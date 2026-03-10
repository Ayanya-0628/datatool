' SlyLab desktop entry
Option Explicit
Dim WshShell, fso, projectDir, pyCmd
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
If Not fso.FolderExists(projectDir) Then
    MsgBox "Project directory not found: " & projectDir, vbCritical, "SlyLab"
    WScript.Quit
End If
If fso.FileExists(projectDir & "\\.venv\\Scripts\\python.exe") Then
    pyCmd = Chr(34) & projectDir & "\\.venv\\Scripts\\python.exe" & Chr(34)
Else
    pyCmd = "python"
End If
WshShell.CurrentDirectory = projectDir
WshShell.Run "cmd /c " & pyCmd & " stable_launcher.py", 0, False
Set fso = Nothing
Set WshShell = Nothing
