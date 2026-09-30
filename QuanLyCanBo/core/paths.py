# -*- coding: utf-8 -*-
"""Đường dẫn dùng chung, chạy đúng cả khi chạy mã nguồn (python) lẫn khi
đã đóng gói thành QuanLyCanBo.exe bằng PyInstaller.

APP_DIR : thư mục GHI được - nơi đặt canbo.db, backup/, attachments/,
          allowed_machines.txt (cạnh quan_ly_can_bo.py hoặc cạnh file .exe).
RES_DIR : thư mục tài nguyên CHỈ ĐỌC đóng kèm phần mềm (biểu tượng, dữ liệu
          địa giới...). Với bản .exe đây là thư mục _internal do PyInstaller
          giải nén; với mã nguồn thì trùng APP_DIR.
"""
import os
import sys

FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = (os.path.dirname(os.path.abspath(sys.executable)) if FROZEN
           else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES_DIR = getattr(sys, "_MEIPASS", APP_DIR)


def resource(*parts):
    return os.path.join(RES_DIR, *parts)
