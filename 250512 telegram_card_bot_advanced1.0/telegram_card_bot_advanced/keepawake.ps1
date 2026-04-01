
@echo off
powershell -ExecutionPolicy Bypass -File "D:\Desktop\FunCoding\keep-awake.ps1"
pause

# 每隔 30 秒轻挪鼠标 1 像素再挪回
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

while ($true) {
    $p = [System.Windows.Forms.Cursor]::Position
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($p.X + 1, $p.Y + 1)
    Start-Sleep -Milliseconds 200
    [System.Windows.Forms.Cursor]::Position = $p
    Start-Sleep -Seconds 30
}
