# -*- coding: utf-8 -*-
"""
Tham số nghiệp vụ - MỌI con số / danh mục có thể thay đổi theo quy định đều
nằm ở đây và quản trị viên chỉnh được trong phần mềm (mục "Tham số nghiệp
vụ"), không cần sửa mã nguồn. Giá trị đã chỉnh lưu trong CSDL (bảng cai_dat,
khóa "ts:<tên>"); chưa chỉnh thì dùng giá trị MẶC ĐỊNH bên dưới.

Giá trị mặc định lấy theo Luật Công an nhân dân 2018 (sửa đổi 2023) và
Nghị định 204/2004/NĐ-CP ở mức hiểu biết chung - đơn vị cần đối chiếu văn bản
hiện hành và chỉnh lại nếu khác. Trường hợp riêng lẻ không theo quy định vẫn
nhập được nhưng phần mềm bắt buộc ghi lý do.

Kiểu tham số:
  list  - danh sách chuỗi (mỗi dòng một mục)
  table - bảng nhiều cột, mỗi dòng là một danh sách chuỗi; cột đầu là khóa
  int   - số nguyên
"""
import json

from core import cand_data

_DB = None


def bind(db):
    """Gắn CSDL đang dùng (gọi một lần khi mở phần mềm)."""
    global _DB
    _DB = db


_HA_SI = ["Hạ sĩ", "Trung sĩ", "Thượng sĩ"]
_CAP_UY = ["Thiếu úy", "Trung úy", "Thượng úy", "Đại úy"]


def _cmkt(names):
    return [f"{n} (CMKT)" for n in names]


def _nien_han_mac_dinh():
    # Luật CAND 2018, Điều 22: thời hạn xét thăng cấp bậc hàm
    chain = [("Hạ sĩ", "Trung sĩ", 1), ("Trung sĩ", "Thượng sĩ", 1), ("Thượng sĩ", "Thiếu úy", 2),
             ("Thiếu úy", "Trung úy", 2), ("Trung úy", "Thượng úy", 3), ("Thượng úy", "Đại úy", 3),
             ("Đại úy", "Thiếu tá", 4), ("Thiếu tá", "Trung tá", 4), ("Trung tá", "Thượng tá", 4),
             ("Thượng tá", "Đại tá", 4), ("Đại tá", "Thiếu tướng", 4)]
    rows = [[a, b, str(n)] for a, b, n in chain]
    rows += [[f"{a} (CMKT)", f"{b} (CMKT)", str(n)] for a, b, n in chain[:9]]
    return rows


def _tuoi_nghi_huu_mac_dinh():
    # Luật CAND (sửa đổi 2023), Điều 30: hạn tuổi phục vụ cao nhất (nam, nữ)
    rows = []
    for names, nam, nu in ((_HA_SI, 47, 47), (_CAP_UY, 55, 55), (["Thiếu tá"], 56, 56), (["Trung tá"], 58, 56),
                           (["Thượng tá"], 60, 58), (["Đại tá"], 62, 60),
                           (["Thiếu tướng", "Trung tướng", "Thượng tướng", "Đại tướng"], 62, 60)):
        for n in names:
            rows.append([n, str(nam), str(nu)])
            if n not in ("Đại tá",) and "tướng" not in n:
                rows.append([f"{n} (CMKT)", str(nam), str(nu)])
    return rows


# (khóa, nhóm, tiêu đề, kiểu, mặc định, giải thích, tên cột - chỉ dùng cho table)
PARAMS = [
    ("cap_bac", "Cấp bậc - Lương", "Danh sách cấp bậc hàm", "list", list(cand_data.CAP_BAC),
     "Thứ tự từ thấp đến cao. Dùng cho mọi ô chọn cấp bậc.", None),
    ("he_so_theo_cap_bac", "Cấp bậc - Lương", "Hệ số lương theo cấp bậc", "table",
     [[k, v] for k, v in cand_data.HE_SO_LUONG_THEO_CAP_BAC.items()],
     "Tự điền hệ số khi chọn cấp bậc. Nhập hệ số khác bảng này thì bắt buộc ghi lý do.",
     ["Cấp bậc", "Hệ số"]),
    ("he_so_goi_y", "Cấp bậc - Lương", "Danh sách hệ số lương gợi ý", "list", list(cand_data.HE_SO_LUONG_HOP_LE),
     "Các giá trị gợi ý trong ô hệ số lương (vẫn gõ được giá trị khác).", None),
    ("chuc_vu_goi_y", "Cấp bậc - Lương", "Chức vụ gợi ý", "list", list(cand_data.CHUC_VU_PHO_BIEN),
     "Gợi ý khi gõ chức vụ (vẫn gõ được chức vụ khác).", None),
    ("hinh_thuc_qd", "Cấp bậc - Lương", "Hình thức quyết định nâng lương - thăng cấp", "list",
     ["Định kỳ", "Trước hạn", "Khác"], "", None),
    ("hinh_thuc_can_ly_do", "Cấp bậc - Lương", "Hình thức bắt buộc ghi lý do", "list", ["Khác"],
     "Chọn các hình thức này thì quyết định phải ghi lý do (ngoài quy định).", None),

    ("nien_han_thang_cap", "Niên hạn - Cảnh báo", "Niên hạn xét thăng cấp bậc hàm", "table",
     _nien_han_mac_dinh(), "Mặc định theo Điều 22 Luật CAND 2018. Tính từ ngày quyết định lên cấp bậc hiện tại.",
     ["Cấp bậc hiện tại", "Cấp bậc tiếp theo", "Số năm"]),
    ("chu_ky_nang_luong", "Niên hạn - Cảnh báo", "Chu kỳ nhắc xét nâng lương (năm)", "int", 0,
     "Tính từ quyết định nâng lương / thăng cấp gần nhất. Để 0 nếu không nhắc (chỉ nhắc thăng cấp).", None),
    ("tuoi_nghi_huu", "Niên hạn - Cảnh báo", "Hạn tuổi phục vụ (nghỉ hưu)", "table", _tuoi_nghi_huu_mac_dinh(),
     "Mặc định theo Luật CAND sửa đổi 2023 - đề nghị đối chiếu lại văn bản hiện hành.",
     ["Cấp bậc", "Nam", "Nữ"]),
    ("thoi_gian_du_bi_dang", "Niên hạn - Cảnh báo", "Thời gian dự bị đảng viên (tháng)", "int", 12, "", None),
    ("bao_truoc_thang_cap", "Niên hạn - Cảnh báo", "Báo trước hạn thăng cấp / nâng lương (tháng)", "int", 3, "", None),
    ("bao_truoc_nghi_huu", "Niên hạn - Cảnh báo", "Báo trước hạn nghỉ hưu (tháng)", "int", 12, "", None),
    ("bao_truoc_dang", "Niên hạn - Cảnh báo", "Báo trước hạn chuyển Đảng chính thức (tháng)", "int", 1, "", None),

    ("xep_loai", "Danh mục", "Mức xếp loại cán bộ", "table",
     [["Hoàn thành xuất sắc nhiệm vụ", "Xuất sắc"], ["Hoàn thành tốt nhiệm vụ", "Tốt"],
      ["Hoàn thành nhiệm vụ", "HT"], ["Không hoàn thành nhiệm vụ", "Không HT"]],
     "Cột 'Viết tắt' dùng trong bảng tổng hợp theo kỳ.", ["Mức xếp loại", "Viết tắt"]),
    ("loai_don_thu", "Danh mục", "Loại đơn thư", "list", ["Đơn thư", "Khiếu nại", "Tố cáo", "Phản ánh"], "", None),
    ("trang_thai_don_thu", "Danh mục", "Trạng thái xử lý đơn thư", "list",
     ["Mới tiếp nhận", "Đang xác minh", "Đang xử lý", "Đã giải quyết", "Tồn đọng"], "", None),
    ("trang_thai_da_xong", "Danh mục", "Trạng thái coi là đã giải quyết", "list", ["Đã giải quyết"],
     "Đơn thư ở các trạng thái này không còn tính là đang xử lý.", None),
    ("trang_thai_ton_dong", "Danh mục", "Trạng thái coi là tồn đọng", "list", ["Tồn đọng"], "", None),
]
_BY_KEY = {p[0]: p for p in PARAMS}


def spec(key):
    return _BY_KEY[key]


def default(key):
    return json.loads(json.dumps(_BY_KEY[key][4]))


def get(key, db=None):
    db = db or _DB
    if db is not None:
        raw = db.get_setting("ts:" + key, "")
        if raw:
            try:
                return json.loads(raw)
            except ValueError:
                pass
    return default(key)


def set_value(db, key, value):
    db.set_setting("ts:" + key, json.dumps(value, ensure_ascii=False))


def reset(db, key):
    db.set_setting("ts:" + key, "")


def is_custom(db, key):
    return bool(db.get_setting("ts:" + key, ""))


# ------------------------------------------------------------------ tiện ích tra cứu
def cap_bac():
    return get("cap_bac")


def he_so_chuan(cap):
    for row in get("he_so_theo_cap_bac"):
        if row and row[0] == cap:
            return row[1] if len(row) > 1 else None
    return None


def he_so_goi_y():
    return get("he_so_goi_y")


def xep_loai():
    return [r[0] for r in get("xep_loai") if r and r[0]]


def xep_loai_tat(name):
    for r in get("xep_loai"):
        if r and r[0] == name:
            return r[1] if len(r) > 1 and r[1] else name
    return name


def nien_han(cap):
    """(cấp bậc tiếp theo, số năm) hoặc None."""
    for r in get("nien_han_thang_cap"):
        if r and r[0] == cap:
            try:
                return (r[1] if len(r) > 1 else "", float(r[2]))
            except (IndexError, ValueError):
                return None
    return None


def tuoi_nghi_huu(cap, gioi_tinh):
    for r in get("tuoi_nghi_huu"):
        if r and r[0] == cap:
            try:
                return float(r[2] if gioi_tinh == "Nữ" else r[1])
            except (IndexError, ValueError):
                return None
    return None


def as_int(key):
    try:
        return int(get(key))
    except (TypeError, ValueError):
        return int(default(key))
