@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Cai dat phan mem Quan Ly Can Bo

rem ================= CAU HINH (co the sua) =================
set "HERE=%~dp0"
set "SRC=%HERE%QuanLyCanBo"
set "APP_FILE=quan_ly_can_bo.py"
set "DEST=%LOCALAPPDATA%\QuanLyCanBo"
set "PY_VER=3.12.8"
set "ALLOWLIST=%HERE%allowed_machines.txt"
rem =========================================================

echo ============================================================
echo    CAI DAT PHAN MEM QUAN LY CAN BO  (ban module)
echo ============================================================
echo.

if exist "%SRC%\%APP_FILE%" goto :src_ok
echo [LOI] Khong tim thay thu muc "QuanLyCanBo" (chua chuong trinh) canh file cai dat nay.
echo       Cau truc dung phai la:
echo         CAI_DAT.bat
echo         QuanLyCanBo\quan_ly_can_bo.py
echo         QuanLyCanBo\core\...
echo         QuanLyCanBo\modules\...
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

rem ---------------- Buoc 1: Python ----------------
echo [1/3] Kiem tra Python ...
set "PYEXE="
call :find_python
if defined PYEXE goto :python_ready

echo       Chua co Python (hoac thieu Tkinter). Dang cai dat Python %PY_VER% ...
call :install_python
call :find_python
if defined PYEXE goto :python_ready
goto :no_python

:python_ready
echo       Da co Python: %PYEXE%

rem ---------------- Buoc 2: chep chuong trinh ----------------
echo [2/3] Cai dat chuong trinh vao: %DEST%
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%" goto :fail_dest
xcopy "%SRC%\*" "%DEST%\" /E /I /Y /Q >nul
if errorlevel 1 goto :fail_dest
rem Giu nguyen du lieu cu: chi chep canbo.db neu ben dich chua co (nang cap khong mat du lieu)
if not exist "%HERE%canbo.db" goto :db_done
if exist "%DEST%\canbo.db" goto :db_done
copy "%HERE%canbo.db" "%DEST%\canbo.db" >nul
echo       Da chep du lieu cu (canbo.db) sang thu muc moi.
:db_done
rem Luon chep/cap nhat danh sach may duoc duyet (neu co) de phan mem tu kiem
rem tra lai moi lan mo, phong truong hop thu muc cai dat bi chep sang may khac.
if exist "%ALLOWLIST%" (
  copy /y "%ALLOWLIST%" "%DEST%\allowed_machines.txt" >nul
  echo       Da cap nhat danh sach may duoc duyet trong thu muc cai dat.
)

rem ---------------- Buoc 3: bieu tuong + khoi dong ----------------
echo [3/3] Tao bieu tuong tren Desktop, Start Menu va khoi dong phan mem ...
set "QLCB_PYWFILE=%TEMP%\qlcb_pyw.txt"
set "QLCB_DEST=%DEST%"
set "QLCB_APP=%APP_FILE%"
if exist "%QLCB_PYWFILE%" del "%QLCB_PYWFILE%"
%PYEXE% -c "import sys,os;open(os.environ['QLCB_PYWFILE'],'w',encoding='utf-8').write(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"
if not exist "%QLCB_PYWFILE%" goto :fail_lnk

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $pyw=(Get-Content -Raw -Encoding UTF8 -LiteralPath $env:QLCB_PYWFILE).Trim(); if(-not (Test-Path -LiteralPath $pyw)){ $pyw=$pyw -replace 'pythonw\.exe$','python.exe' }; $q=[char]34; $script=Join-Path $env:QLCB_DEST $env:QLCB_APP; $w=New-Object -ComObject WScript.Shell; $first=$null; foreach($dir in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))){ if(-not $dir){ continue }; $lnk=Join-Path $dir 'Quan Ly Can Bo.lnk'; $s=$w.CreateShortcut($lnk); $s.TargetPath=$pyw; $s.Arguments=$q+$script+$q; $s.WorkingDirectory=$env:QLCB_DEST; $s.IconLocation=($pyw+',0'); $s.Description='Phan mem Quan Ly Can Bo'; $s.Save(); Write-Host ('      Da tao bieu tuong: '+$lnk); if(-not $first){ $first=$lnk } }; if($first){ Start-Process -FilePath $first }"
if errorlevel 1 goto :fail_lnk
if exist "%QLCB_PYWFILE%" del "%QLCB_PYWFILE%"

echo.
echo ============================================================
echo    CAI DAT HOAN TAT!
echo ============================================================
echo  - Mo phan mem bang bieu tuong "Quan Ly Can Bo" o Desktop.
echo  - Tai khoan mac dinh: admin / admin@123
echo    (phan mem se yeu cau doi mat khau o lan dang nhap dau tien)
echo  - Du lieu luu tai: %DEST%\canbo.db
echo  - Thu muc sao luu tu dong: %DEST%\backup
echo.
pause
endlocal
exit /b 0

rem ================= Cac thong bao loi =================
:no_python
echo.
echo [LOI] Khong cai duoc Python tu dong (co the may khong co Internet).
echo       Cach cai tren may OFFLINE:
echo         1. Tren may co mang, tai bo cai Python 3.12 (Windows installer 64-bit) tai
echo            https://www.python.org/downloads/windows/
echo         2. Chep file python-3.xx.x-amd64.exe vao CUNG THU MUC voi CAI_DAT.bat
echo         3. Chay lai CAI_DAT.bat - chuong trinh se tu dung bo cai do.
goto :fail

:fail_dest
echo.
echo [LOI] Khong the tao hoac ghi vao thu muc cai dat: %DEST%
goto :fail

:fail_lnk
echo.
echo [LOI] Khong tao duoc bieu tuong. Chuong trinh da duoc chep vao:
echo       %DEST%
echo       Ban van co the chay bang lenh: python "%DEST%\%APP_FILE%"
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

rem ================= Ham: tim Python co Tkinter =================
:find_python
set "PYEXE="
where py >nul 2>nul
if errorlevel 1 goto :fp_where
py -3 -c "import tkinter, sqlite3" >nul 2>nul
if errorlevel 1 goto :fp_where
set "PYEXE=py -3"
exit /b 0
:fp_where
for /f "usebackq delims=" %%P in (`where python 2^>nul`) do call :try_python "%%~P"
if defined PYEXE exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*") do call :try_python "%%~D\python.exe"
exit /b 0

:try_python
if defined PYEXE exit /b 0
set "CAND=%~1"
if not exist "%CAND%" exit /b 0
echo "%CAND%" | find /i "WindowsApps" >nul
if not errorlevel 1 exit /b 0
"%CAND%" -c "import tkinter, sqlite3" >nul 2>nul
if errorlevel 1 exit /b 0
set PYEXE="%CAND%"
exit /b 0

rem ================= Ham: cai dat Python =================
:install_python
set "PYINST="
for %%F in ("%HERE%python-3*.exe") do set "PYINST=%%~fF"
if not defined PYINST goto :ip_winget
echo       Dung bo cai Python co san canh file cai dat: "%PYINST%"
goto :ip_run

:ip_winget
where winget >nul 2>nul
if errorlevel 1 goto :ip_download
echo       Dang cai Python bang winget ...
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
if not errorlevel 1 exit /b 0
echo       Winget khong thanh cong, thu tai truc tiep tu python.org ...

:ip_download
set "ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "ARCH=%PROCESSOR_ARCHITEW6432%"
set "PYFILE=python-%PY_VER%-amd64.exe"
if /i "%ARCH%"=="x86" set "PYFILE=python-%PY_VER%.exe"
if /i "%ARCH%"=="ARM64" set "PYFILE=python-%PY_VER%-arm64.exe"
set "QLCB_URL=https://www.python.org/ftp/python/%PY_VER%/%PYFILE%"
set "PYINST=%TEMP%\%PYFILE%"
echo       Dang tai %QLCB_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri $env:QLCB_URL -OutFile $env:PYINST; exit 0 } catch { exit 1 }"
if errorlevel 1 exit /b 1

:ip_run
echo       Dang cai dat Python (vui long doi 1-3 phut, khong tat cua so nay) ...
start /wait "" "%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1 Include_test=0 Shortcuts=0
exit /b 0
