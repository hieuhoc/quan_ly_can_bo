# -*- coding: utf-8 -*-
"""
Cơ cấu tổ chức dùng để chọn đơn vị công tác của cán bộ, theo thứ tự:

    1. Công an tỉnh / thành phố trực thuộc trung ương (34 đơn vị hành chính
       cấp tỉnh hiện hành, mặc định: Công an tỉnh Hưng Yên);
    2. Phòng thuộc Công an tỉnh, HOẶC Công an xã / phường của chính tỉnh đó
       (danh sách xã, phường lấy từ dữ liệu địa giới hành chính sau sắp xếp
       01/7/2025 - xem core/dia_gioi_hanh_chinh.py);
    3. Đội / Tổ: người dùng tự nhập.

DANH MỤC PHÒNG bên dưới là danh mục THAM KHẢO theo mô hình chung của Công
an cấp tỉnh; cơ cấu thực tế mỗi tỉnh có thể khác (sáp nhập, đổi tên...).
Quản trị viên sửa lại cho đúng tại mục "Cấu hình" trong phần mềm - danh
mục đã sửa được lưu trong CSDL (bảng cai_dat) và dùng thay cho danh mục này.
Ô chọn vẫn cho phép gõ tay một đơn vị không có trong danh sách.
"""
import core.dia_gioi_hanh_chinh as dgh

SETTING_TINH = "co_cau_cong_an_tinh_mac_dinh"
SETTING_PHONG = "co_cau_danh_muc_phong"
TINH_MAC_DINH = "Công an tỉnh Hưng Yên"

PHONG_MAC_DINH = [
    "Văn phòng Công an tỉnh",
    "Phòng Tham mưu",
    "Phòng Tổ chức cán bộ",
    "Phòng Công tác đảng và công tác chính trị",
    "Phòng Hậu cần",
    "Thanh tra Công an tỉnh",
    "Phòng Hồ sơ nghiệp vụ",
    "Phòng Kỹ thuật nghiệp vụ",
    "Phòng An ninh chính trị nội bộ",
    "Phòng An ninh kinh tế",
    "Phòng An ninh đối ngoại",
    "Phòng An ninh điều tra",
    "Phòng An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao",
    "Phòng Quản lý xuất nhập cảnh",
    "Phòng Cảnh sát hình sự",
    "Phòng Cảnh sát kinh tế",
    "Phòng Cảnh sát điều tra tội phạm về ma túy",
    "Phòng Cảnh sát điều tra tội phạm về trật tự xã hội",
    "Phòng Cảnh sát điều tra tội phạm về tham nhũng, kinh tế, buôn lậu, môi trường",
    "Phòng Cảnh sát quản lý hành chính về trật tự xã hội",
    "Phòng Cảnh sát giao thông",
    "Phòng Cảnh sát phòng cháy, chữa cháy và cứu nạn, cứu hộ",
    "Phòng Cảnh sát cơ động",
    "Phòng Cảnh sát thi hành án hình sự và hỗ trợ tư pháp",
    "Phòng Kỹ thuật hình sự",
    "Trại tạm giam",
]


def _lower_first(s):
    return s[:1].lower() + s[1:] if s else s


def ten_cong_an_tinh(ten_tinh):
    """'Tỉnh Hưng Yên' -> 'Công an tỉnh Hưng Yên'; 'Thành phố Hà Nội' -> 'Công an thành phố Hà Nội'."""
    return f"Công an {_lower_first(ten_tinh)}"


def danh_sach_cong_an_tinh():
    return [ten_cong_an_tinh(t) for t in dgh.danh_sach_tinh()]


def _ten_tinh(cong_an_tinh):
    for t in dgh.danh_sach_tinh():
        if ten_cong_an_tinh(t) == cong_an_tinh:
            return t
    return None


def danh_sach_cong_an_xa(cong_an_tinh):
    """Công an các xã, phường, đặc khu thuộc một Công an tỉnh / thành phố."""
    tinh = _ten_tinh(cong_an_tinh)
    return [f"Công an {_lower_first(x)}" for x in dgh.danh_sach_xa(tinh)] if tinh else []


def tinh_mac_dinh(db):
    return db.get_setting(SETTING_TINH, "") or TINH_MAC_DINH


def danh_muc_phong(db):
    raw = db.get_setting(SETTING_PHONG, "")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    return lines or list(PHONG_MAC_DINH)


def danh_sach_don_vi(db, cong_an_tinh):
    """Các lựa chọn cho ô 'Phòng / Công an xã, phường': các phòng trước, rồi
    đến Công an xã, phường của tỉnh đã chọn."""
    return danh_muc_phong(db) + danh_sach_cong_an_xa(cong_an_tinh)
