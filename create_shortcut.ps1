$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\数据分析软件.lnk")
$Shortcut.TargetPath = "e:\AntiAPP\run.bat"
$Shortcut.WorkingDirectory = "e:\AntiAPP"
$Shortcut.WindowStyle = 1
$Shortcut.Save()