# -*- coding: utf-8 -*-
"""
Khóa theo máy (bản đơn giản - danh sách máy được duyệt).

Mỗi máy Windows có một "MachineGuid" cố định trong registry. Ta băm giá trị
đó để ra một "mã máy" 12 ký tự, dễ đọc, dễ chép tay. Quản trị viên thu thập
mã máy của từng máy muốn cho phép (bằng XEM_MA_MAY.bat) rồi liệt kê vào file
allowed_machines.txt đặt cạnh quan_ly_can_bo.py.

Thiết kế có chủ đích đơn giản: nếu KHÔNG có file allowed_machines.txt, tính
năng coi như đang TẮT và phần mềm chạy bình thường trên mọi máy. Chỉ khi
quản trị viên chủ động tạo file này, việc kiểm tra mới được BẬT.
Đây là cơ chế ở mức "danh sách mềm" - đủ để ngăn cài nhầm hoặc sao chép sang
máy khác một cách vô ý; không phải cơ chế chống sao chép có chữ ký, người
rành kỹ thuật vẫn có thể sửa file danh sách nếu có quyền truy cập máy.
"""
import hashlib
import os
import sys

ALLOWLIST_FILENAME = "allowed_machines.txt"


def _read_machine_guid_windows():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as k:
        return winreg.QueryValueEx(k, "MachineGuid")[0]


def compute_code():
    """Trả về mã máy dạng 'XXXX-XXXX-XXXX', hoặc None nếu không xác định được."""
    try:
        if sys.platform.startswith("win"):
            raw = _read_machine_guid_windows().strip().upper()
        else:
            # Chỉ dùng khi phát triển/thử nghiệm ngoài Windows - KHÔNG dùng để
            # khóa máy thật, vì không dựa trên MachineGuid của Windows.
            import uuid
            raw = f"DEV-{uuid.getnode()}"
    except Exception:
        return None
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    code = h[:12]
    return f"{code[0:4]}-{code[4:8]}-{code[8:12]}"


def _normalize(s):
    return "".join(ch for ch in s.upper() if ch.isalnum())


def _load_allowed(app_dir):
    path = os.path.join(app_dir, ALLOWLIST_FILENAME)
    if not os.path.exists(path):
        return None  # tính năng đang tắt
    codes = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                codes.add(_normalize(line))
    return codes


def check(app_dir):
    """Trả về (is_allowed: bool, code: str|None, reason: str)."""
    allowed = _load_allowed(app_dir)
    code = compute_code()
    if allowed is None:
        return True, code, "Tính năng danh sách máy được duyệt hiện đang tắt."
    if code is None:
        return False, None, "Không xác định được mã máy (không đọc được registry)."
    if _normalize(code) in allowed:
        return True, code, "Máy này có trong danh sách được duyệt."
    if not allowed:
        return False, code, "Danh sách máy được duyệt hiện đang trống."
    return False, code, "Máy này không có trong danh sách được duyệt."
