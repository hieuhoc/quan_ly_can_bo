# -*- coding: utf-8 -*-
"""Thông tin thể thức dùng khi in / xuất file: tên cơ quan chủ quản, đơn vị
lập biểu, địa danh, chức danh người ký. Quản trị viên sửa ở mục Cấu hình."""
import os

from core import co_cau
from core.paths import APP_DIR

EXPORT_DIR = os.path.join(APP_DIR, "xuat_file")

KEYS = {
    "in_co_quan": "Cơ quan chủ quản (dòng trên)",
    "in_don_vi": "Đơn vị lập biểu (dòng dưới, in đậm)",
    "in_dia_danh": "Địa danh ghi ngày tháng",
    "in_ky_trai": "Chức danh ký bên trái",
    "in_ky_phai": "Chức danh ký bên phải",
}


def settings(db):
    tinh = co_cau.tinh_mac_dinh(db)
    defaults = {
        "in_co_quan": "BỘ CÔNG AN",
        "in_don_vi": tinh.upper(),
        "in_dia_danh": tinh.replace("Công an tỉnh ", "").replace("Công an thành phố ", ""),
        "in_ky_trai": "NGƯỜI LẬP BIỂU",
        "in_ky_phai": "THỦ TRƯỞNG ĐƠN VỊ",
    }
    return {k: (db.get_setting(k, "") or v) for k, v in defaults.items()}


def org_lines(db):
    s = settings(db)
    return [s["in_co_quan"].upper(), s["in_don_vi"].upper()]


def export_path(name):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    return os.path.join(EXPORT_DIR, name)
