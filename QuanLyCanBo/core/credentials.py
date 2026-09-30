# -*- coding: utf-8 -*-
"""
Lưu tài khoản đăng nhập cục bộ để tự động điền (KHÔNG phải tự động đăng
nhập - vẫn phải bấm nút "Đăng nhập" mỗi lần mở phần mềm).

Trên Windows, mật khẩu được mã hóa bằng DPAPI (CryptProtectData) - cơ chế
mã hóa sẵn có của Windows, gắn với chính tài khoản Windows đang dùng máy,
không cần khóa rời (cùng cơ chế trình duyệt Chrome/Edge dùng để lưu mật
khẩu đã lưu). Người dùng Windows khác trên cùng máy KHÔNG giải mã được.

Trên hệ điều hành khác (không phải Windows), tính năng này tắt hẳn - hàm
save()/load() không làm gì, giống cách "Chạy cùng Windows" chỉ hoạt động
trên Windows.
"""
import base64
import ctypes
import os
import sys

FILENAME = ".saved_login"


def available():
    return sys.platform.startswith("win")


def _protect(data: bytes) -> bytes:
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), "QuanLyCanBo", None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("CryptProtectData that bai")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _unprotect(data: bytes) -> bytes:
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("CryptUnprotectData that bai")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def save(app_dir, username, password):
    if not available():
        return
    path = os.path.join(app_dir, FILENAME)
    try:
        payload = f"{username}\n{password}".encode("utf-8")
        enc = _protect(payload)
        with open(path, "wb") as f:
            f.write(base64.b64encode(enc))
    except Exception:
        pass


def load(app_dir):
    """Trả về (username, password) hoặc None."""
    if not available():
        return None
    path = os.path.join(app_dir, FILENAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            enc = base64.b64decode(f.read())
        dec = _unprotect(enc).decode("utf-8")
        username, password = dec.split("\n", 1)
        return username, password
    except Exception:
        return None


def clear(app_dir):
    path = os.path.join(app_dir, FILENAME)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
