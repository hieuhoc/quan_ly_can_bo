# -*- mode: python ; coding: utf-8 -*-
# Cấu hình đóng gói QuanLyCanBo.exe bằng PyInstaller (dạng thư mục - khởi động nhanh).
# Build (trên Windows):  pip install -r requirements.txt  &&  pyinstaller --noconfirm QuanLyCanBo.spec
# Kết quả:               dist\QuanLyCanBo\QuanLyCanBo.exe  (+ thư mục _internal đi kèm)
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

here = os.path.abspath(SPECPATH)
sys.path.insert(0, here)

a = Analysis(
    [os.path.join(here, "quan_ly_can_bo.py")],
    pathex=[here],
    datas=[
        (os.path.join(here, "assets"), "assets"),
        (os.path.join(here, "core", "data"), os.path.join("core", "data")),
    ],
    # Các module nghiệp vụ được nạp động theo core/registry.py nên phải khai báo rõ.
    hiddenimports=collect_submodules("modules") + collect_submodules("ui") + collect_submodules("core"),
    excludes=["tkinter", "_tkinter", "unittest", "pydoc_data", "PySide6.QtNetwork", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore", "PySide6.QtMultimedia"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QuanLyCanBo",
    console=False,
    icon=os.path.join(here, "assets", "app.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="QuanLyCanBo")
