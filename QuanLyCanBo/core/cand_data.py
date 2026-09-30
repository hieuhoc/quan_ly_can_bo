# -*- coding: utf-8 -*-
"""
Dữ liệu tham chiếu về Công an nhân dân (CAND).

CAP_BAC: hệ thống cấp bậc hàm đầy đủ, từ thấp đến cao, theo Điều 21 Luật
Công an nhân dân 2018 (gộp cả khối chiến sĩ nghĩa vụ và sĩ quan nghiệp vụ
thành một thang bậc liên tục để chọn).

HE_SO_LUONG_THEO_CAP_BAC: hệ số lương cấp bậc quân hàm sĩ quan, hạ sĩ
quan Công an nhân dân, theo Bảng 6 - Nghị định 204/2004/NĐ-CP (vẫn đang
áp dụng, chưa có bảng lương mới thay thế tính đến thời điểm hiện tại).
Binh nhất/Binh nhì hưởng phụ cấp quân hàm riêng, không nằm trong bảng hệ
số lương này nên không có giá trị tương ứng ở đây. Cấp bậc CHUYÊN MÔN KỸ
THUẬT (CMKT) và "Lao động hợp đồng" hưởng theo bảng lương khác (Bảng 7 -
chưa xác minh được số liệu cụ thể) nên CŨNG không có ở đây - hệ số lương
cho các trường hợp này người dùng tự nhập tay (ô hệ số lương vẫn nhận
mọi giá trị tự gõ, không bắt buộc phải nằm trong danh sách gợi ý).

CAP_DON_VI: các cấp/loại hình đơn vị công tác phổ biến trong CAND cấp cơ
sở, để phân loại rõ vị trí công tác (đội/phòng cấp trên, hay tổ/Công an
xã-phường cấp cơ sở sau sắp xếp 01/7/2025, hay vai trò lãnh đạo/chỉ huy).

CHUC_VU_PHO_BIEN: danh sách CHỨC VỤ THƯỜNG GẶP trong CAND để gợi ý khi
gõ - đây KHÔNG phải danh sách đầy đủ mọi chức vụ trong toàn lực lượng
(số lượng chức danh thực tế rất lớn và khác nhau theo từng đơn vị), người
dùng vẫn có thể gõ tự do một chức vụ khác không có trong danh sách.
"""

CAP_BAC = [
    "Binh nhì", "Binh nhất",
    "Hạ sĩ", "Trung sĩ", "Thượng sĩ",
    "Thiếu úy", "Trung úy", "Thượng úy", "Đại úy",
    "Thiếu tá", "Trung tá", "Thượng tá", "Đại tá",
    "Thiếu tướng", "Trung tướng", "Thượng tướng", "Đại tướng",
    # Sĩ quan, hạ sĩ quan CHUYÊN MÔN KỸ THUẬT (CMKT) - cùng tên bậc như
    # trên nhưng KHÔNG có Đại tá và không có cấp tướng (Điều 21 Luật CAND
    # 2018); đánh dấu (CMKT) để phân biệt với nghiệp vụ khi chọn.
    "Hạ sĩ (CMKT)", "Trung sĩ (CMKT)", "Thượng sĩ (CMKT)",
    "Thiếu úy (CMKT)", "Trung úy (CMKT)", "Thượng úy (CMKT)", "Đại úy (CMKT)",
    "Thiếu tá (CMKT)", "Trung tá (CMKT)", "Thượng tá (CMKT)",
    # Không thuộc diện cấp bậc hàm - lao động ký hợp đồng lao động
    "Lao động hợp đồng",
]

HE_SO_LUONG_THEO_CAP_BAC = {
    "Hạ sĩ": "3.20", "Trung sĩ": "3.50", "Thượng sĩ": "3.80",
    "Thiếu úy": "4.20", "Trung úy": "4.60", "Thượng úy": "5.00", "Đại úy": "5.40",
    "Thiếu tá": "6.00", "Trung tá": "6.60", "Thượng tá": "7.30", "Đại tá": "8.00",
    "Thiếu tướng": "8.60", "Trung tướng": "9.20", "Thượng tướng": "9.80", "Đại tướng": "10.40",
}
# Danh sách hệ số hợp lệ để hiển thị trong hộp chọn (không trùng, giữ thứ tự tăng dần)
HE_SO_LUONG_HOP_LE = ["3.20", "3.50", "3.80", "4.20", "4.60", "5.00", "5.40",
                     "6.00", "6.60", "7.30", "8.00", "8.60", "9.20", "9.80", "10.40"]

CAP_DON_VI = [
    "Đội", "Phòng", "Tổ", "Công an xã/phường",
    "Lãnh đạo phòng", "Chỉ huy Công an xã/phường",
]

CHUC_VU_PHO_BIEN = [
    "Chiến sĩ", "Cán bộ", "Nhân viên", "Trinh sát viên", "Điều tra viên",
    "Thư ký", "Văn thư", "Kế toán", "Thủ quỹ", "Lái xe",
    "Tổ trưởng", "Tổ phó",
    "Đội trưởng", "Đội phó",
    "Trưởng Công an xã", "Phó trưởng Công an xã",
    "Trưởng ban", "Phó trưởng ban",
    "Trưởng phòng", "Phó trưởng phòng",
    "Chánh văn phòng", "Phó Chánh văn phòng",
    "Trưởng Công an huyện", "Phó trưởng Công an huyện",
    "Giám đốc Công an tỉnh", "Phó Giám đốc Công an tỉnh",
    "Cục trưởng", "Phó Cục trưởng",
    "Tư lệnh", "Phó Tư lệnh",
    "Thứ trưởng", "Bộ trưởng",
]
