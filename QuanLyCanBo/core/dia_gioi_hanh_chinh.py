# -*- coding: utf-8 -*-
"""
Dữ liệu địa giới hành chính Việt Nam hiện hành (34 tỉnh/thành, 3.321 xã/
phường sau sắp xếp 01/7/2025), nguồn Tổng cục Thống kê qua thư viện mã
nguồn mở vietnam-provinces (danhmuchanhchinh.nso.gov.vn), phiên bản dữ
liệu 2026-09-20. Chỉ nạp một lần, dùng chung cho toàn phần mềm.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "data", "dia_gioi_hanh_chinh.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def danh_sach_tinh():
    """Danh sách tên tỉnh/thành, đã sắp xếp theo alphabet."""
    return [t["ten"] for t in _load()["tinh"]]


def danh_sach_xa(ten_tinh):
    """Danh sách tên xã/phường thuộc một tỉnh/thành, đã sắp xếp theo alphabet."""
    for t in _load()["tinh"]:
        if t["ten"] == ten_tinh:
            return [x["ten"] for x in t["xa"]]
    return []


def phien_ban_du_lieu():
    return _load().get("phien_ban_du_lieu", "")
