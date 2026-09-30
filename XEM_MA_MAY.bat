@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Xem ma may - Quan Ly Can Bo

echo ============================================================
echo    XEM MA MAY  (dung de xin cap phep cai dat)
echo ============================================================
echo.
echo Dang tinh ma may, vui long doi...
echo.

for /f "usebackq delims=" %%C in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$g=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid -ErrorAction Stop).MachineGuid.ToUpper();$b=[Text.Encoding]::UTF8.GetBytes($g);$h=([Security.Cryptography.SHA256]::Create().ComputeHash($b)|ForEach-Object{$_.ToString('X2')}) -join '';$c=$h.Substring(0,12);Write-Output ($c.Substring(0,4)+'-'+$c.Substring(4,4)+'-'+$c.Substring(8,4))}catch{Write-Output 'LOI'}"`) do set "MACHINE_CODE=%%C"

if "%MACHINE_CODE%"=="LOI" (
  echo [LOI] Khong doc duoc ma may tren thiet bi nay.
  echo       Co the do quyen truy cap registry bi han che.
  goto :end
)

echo Ma may cua thiet bi nay la:
echo.
echo     %MACHINE_CODE%
echo.
echo Vui long gui ma nay cho quan tri vien de duoc bo sung vao
echo danh sach may duoc duyet (allowed_machines.txt), truoc khi
echo chay CAI_DAT.bat tren may nay.
echo.

:end
pause
endlocal
