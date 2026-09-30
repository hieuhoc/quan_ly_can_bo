# -*- coding: utf-8 -*-
"""
Danh mục module của phần mềm.
Muốn THÊM một module nghiệp vụ mới: viết file modules/<ten>.py có sẵn lớp
Panel(parent, app) rồi thêm một dòng vào BUSINESS_MODULES bên dưới.
Muốn BỎ một module: xóa (hoặc comment) dòng tương ứng - không cần sửa gì
ở nơi khác, và không ảnh hưởng tới các module còn lại.
Quản trị viên cũng có thể bật/tắt các module nghiệp vụ ngay trong phần mềm
(mục "Cấu hình module") mà không cần sửa mã nguồn.
"""

ACTIONS = [("view", "Xem"), ("add", "Thêm"), ("edit", "Sửa"),
           ("delete", "Xóa"), ("export", "Xuất file / In")]
ACTION_LABEL = dict(ACTIONS)

# Trang chủ - luôn hiển thị cho MỌI tài khoản đã đăng nhập, không cần cấp
# quyền riêng và không thể tắt qua "Cấu hình module" (nội dung bên trong tự
# ẩn theo quyền xem từng module của người dùng).
HOME_MODULES = [
    ("dashboard", "Tổng quan", "🏠", "modules.dashboard", "Panel"),
    ("reminders", "Cảnh báo đến hạn", "⏰", "modules.reminders", "Panel"),
]

# (id, tiêu đề, biểu tượng, tên module python, tên lớp)
BUSINESS_MODULES = [
    ("employees", "Thông tin cán bộ", "👤", "modules.employees", "Panel"),
    ("classification", "Phân loại cán bộ", "🏆", "modules.classification", "Panel"),
    ("salary", "Nâng lương - Thăng cấp", "📈", "modules.salary", "Panel"),
    ("complaints", "Đơn thư - Khiếu nại", "📮", "modules.complaints", "Panel"),
]

# Các module chỉ quản trị viên thấy được, không thể bị tắt qua "Cấu hình module"
ADMIN_MODULES = [
    ("accounts", "Quản trị tài khoản", "⚙", "modules.accounts", "Panel"),
    ("settings_mod", "Cấu hình", "🧩", "modules.settings_mod", "Panel"),
    ("tham_so", "Tham số nghiệp vụ", "🎛", "modules.tham_so", "Panel"),
    ("backup", "Sao lưu - Khôi phục", "💾", "modules.backup", "Panel"),
    ("logs", "Nhật ký hoạt động", "📜", "modules.logs", "Panel"),
]


def module_by_id(mod_id):
    for m in HOME_MODULES + BUSINESS_MODULES + ADMIN_MODULES:
        if m[0] == mod_id:
            return m
    return None
