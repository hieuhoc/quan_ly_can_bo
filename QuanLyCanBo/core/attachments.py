# -*- coding: utf-8 -*-
"""
Đính kèm file (vd quyết định nâng lương, đơn thư gốc đã scan...).

File được SAO CHÉP vào thư mục "attachments/<bang>/" bên trong nơi cài
đặt phần mềm, đặt tên lại với một mã ngẫu nhiên ở đầu để không bao giờ
trùng nhau dù người dùng tải lên hai file cùng tên - CSDL chỉ lưu đường
dẫn tương đối (vd "attachments/qua_trinh_luong/a1b2c3_quyetdinh.pdf").
"""
import os
import shutil
import subprocess
import sys
import uuid

ATTACH_DIR = "attachments"


def save_attachment(app_dir, table, src_path):
    """Sao chép src_path vào attachments/<table>/, trả về đường dẫn tương đối."""
    if not src_path or not os.path.isfile(src_path):
        return None
    folder = os.path.join(app_dir, ATTACH_DIR, table)
    os.makedirs(folder, exist_ok=True)
    original_name = os.path.basename(src_path)
    safe_name = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in original_name)
    rel_path = os.path.join(ATTACH_DIR, table, f"{uuid.uuid4().hex[:10]}_{safe_name}")
    shutil.copy2(src_path, os.path.join(app_dir, rel_path))
    return rel_path.replace(os.sep, "/")


def full_path(app_dir, rel_path):
    if not rel_path:
        return None
    return os.path.join(app_dir, rel_path.replace("/", os.sep))


def display_name(rel_path):
    if not rel_path:
        return ""
    name = os.path.basename(rel_path)
    # bỏ tiền tố mã ngẫu nhiên 10 ký tự + dấu gạch dưới, cho tên gọn để hiển thị
    if len(name) > 11 and name[10] == "_":
        return name[11:]
    return name


def open_file(app_dir, rel_path):
    path = full_path(app_dir, rel_path)
    if not path or not os.path.isfile(path):
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def delete_attachment(app_dir, rel_path):
    path = full_path(app_dir, rel_path)
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
