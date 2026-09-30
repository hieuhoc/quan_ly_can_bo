@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Cai dat phan mem Quan Ly Can Bo

rem ================= CAU HINH (co the sua) =================
set "HERE=%~dp0"
set "SRC=%HERE%QuanLyCanBo"
set "EXE_NAME=QuanLyCanBo.exe"
set "DEST=%LOCALAPPDATA%\QuanLyCanBo"
set "ALLOWLIST=%HERE%allowed_machines.txt"
rem =========================================================

echo ============================================================
echo    CAI DAT PHAN MEM QUAN LY CAN BO  (ban 4.0 - file .exe)
echo ============================================================
echo.

if exist "%SRC%\%EXE_NAME%" goto :src_ok
echo [LOI] Khong tim thay "QuanLyCanBo\%EXE_NAME%" canh file cai dat nay.
echo       Cau truc dung cua bo cai phai la:
echo         CAI_DAT.bat
echo         QuanLyCanBo\QuanLyCanBo.exe
echo         QuanLyCanBo\_internal\...
echo       Neu ban dang mo ma nguon (co file quan_ly_can_bo.py), hay tai bo cai
echo       dat da dong goi (QuanLyCanBo_v4.x.zip) o muc Releases cua kho ma nguon.
goto :fail
:src_ok

rem ---------------- Buoc 0: kiem tra may co duoc duyet khong (neu co cau hinh) ----------------
if not exist "%ALLOWLIST%" goto :machine_ok
echo [0/3] Kiem tra may nay co trong danh sach duoc duyet ...
call :get_machine_code
if "%MACHINE_CODE%"=="LOI" (
  echo.
  echo [LOI] Khong doc duoc ma may tren thiet bi nay - tu choi cai dat de an toan.
  goto :fail
)
set "MACHINE_FOUND="
for /f "usebackq delims=" %%L in ("%ALLOWLIST%") do call :qlcb_check_line "%%L"
if defined MACHINE_FOUND (
  echo       Ma may %MACHINE_CODE% - duoc phep cai dat. Tiep tuc...
  goto :machine_ok
)
echo.
echo ============================================================
echo    MAY NAY CHUA DUOC CAP PHEP CAI DAT PHAN MEM
echo ============================================================
echo  Ma may cua thiet bi nay la:
echo.
echo      %MACHINE_CODE%
echo.
echo  Vui long gui ma nay cho quan tri vien de duoc bo sung vao
echo  danh sach may duoc duyet (allowed_machines.txt), sau do chay lai
echo  CAI_DAT.bat. Chua co gi duoc cai dat len may nay.
echo.
goto :fail

:machine_ok

rem ---------------- Buoc 1: dong phan mem neu dang mo ----------------
echo [1/3] Chuan bi cai dat ...
tasklist /fi "imagename eq %EXE_NAME%" 2>nul | find /i "%EXE_NAME%" >nul
if errorlevel 1 goto :not_running
echo       Phan mem dang mo - se duoc dong lai de cap nhat.
echo       (Hay luu cong viec dang lam, roi bam phim bat ky de tiep tuc.)
pause >nul
taskkill /im "%EXE_NAME%" /f >nul 2>nul
timeout /t 2 /nobreak >nul
:not_running

rem ---------------- Buoc 2: chep chuong trinh ----------------
echo [2/3] Cai dat chuong trinh vao: %DEST%
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%" goto :fail_dest
rem Chi chep chuong trinh (QuanLyCanBo.exe + _internal). Du lieu dang dung
rem (canbo.db, backup, attachments, xuat_file) KHONG nam trong bo cai nen giu
rem nguyen - ke ca du lieu cua ban cu (ban chay bang Python) cung thu muc nay.
if exist "%DEST%\_internal" rmdir /s /q "%DEST%\_internal"
xcopy "%SRC%\*" "%DEST%\" /E /I /Y /Q >nul
if errorlevel 1 goto :fail_dest
rem Chep du lieu cu (canbo.db) dat canh bo cai, neu ben dich chua co
if not exist "%HERE%canbo.db" goto :db_done
if exist "%DEST%\canbo.db" goto :db_done
copy "%HERE%canbo.db" "%DEST%\canbo.db" >nul
echo       Da chep du lieu cu (canbo.db) sang thu muc cai dat.
:db_done
if exist "%ALLOWLIST%" (
  copy /y "%ALLOWLIST%" "%DEST%\allowed_machines.txt" >nul
  echo       Da cap nhat danh sach may duoc duyet trong thu muc cai dat.
)

rem ---------------- Buoc 3: bieu tuong + khoi dong ----------------
echo [3/3] Tao bieu tuong tren Desktop, Start Menu va khoi dong phan mem ...
set "QLCB_DEST=%DEST%"
set "QLCB_EXE=%EXE_NAME%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $exe=Join-Path $env:QLCB_DEST $env:QLCB_EXE; $w=New-Object -ComObject WScript.Shell; $first=$null; foreach($dir in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))){ if(-not $dir){ continue }; $lnk=Join-Path $dir 'Quan Ly Can Bo.lnk'; $s=$w.CreateShortcut($lnk); $s.TargetPath=$exe; $s.Arguments=''; $s.WorkingDirectory=$env:QLCB_DEST; $s.IconLocation=($exe+',0'); $s.Description='Phan mem Quan Ly Can Bo'; $s.Save(); Write-Host ('      Da tao bieu tuong: '+$lnk); if(-not $first){ $first=$lnk } }; if($first){ Start-Process -FilePath $first }"
if errorlevel 1 goto :fail_lnk

echo.
echo ============================================================
echo    CAI DAT HOAN TAT!
echo ============================================================
echo  - Mo phan mem bang bieu tuong "Quan Ly Can Bo" o Desktop.
echo  - Tai khoan mac dinh (lan dau): admin / admin@123
echo    (phan mem se yeu cau doi mat khau o lan dang nhap dau tien)
echo  - Du lieu luu tai: %DEST%\canbo.db
echo  - Thu muc sao luu tu dong: %DEST%\backup
echo.
pause
endlocal
exit /b 0

rem ================= Cac thong bao loi =================
:fail_dest
echo.
echo [LOI] Khong the tao hoac ghi vao thu muc cai dat: %DEST%
goto :fail

:fail_lnk
echo.
echo [LOI] Khong tao duoc bieu tuong. Chuong trinh da duoc chep vao:
echo       %DEST%
echo       Ban van co the chay truc tiep file: "%DEST%\%EXE_NAME%"
goto :fail

:fail
echo.
pause
endlocal
exit /b 1


rem ================= Ham: tinh ma may (giong XEM_MA_MAY.bat) =================
:get_machine_code
for /f "usebackq delims=" %%C in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$g=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid -ErrorAction Stop).MachineGuid.ToUpper();$b=[Text.Encoding]::UTF8.GetBytes($g);$h=([Security.Cryptography.SHA256]::Create().ComputeHash($b)|ForEach-Object{$_.ToString('X2')}) -join '';$c=$h.Substring(0,12);Write-Output ($c.Substring(0,4)+'-'+$c.Substring(4,4)+'-'+$c.Substring(8,4))}catch{Write-Output 'LOI'}"`) do set "MACHINE_CODE=%%C"
exit /b 0

:qlcb_check_line
set "LINE=%~1"
for /f "tokens=1 delims=#" %%A in ("%LINE%") do set "LINE=%%A"
for /f "tokens=* delims= " %%A in ("%LINE%") do set "LINE=%%A"
if "%LINE%"=="" exit /b 0
if /i "%LINE%"=="%MACHINE_CODE%" set "MACHINE_FOUND=1"
exit /b 0
