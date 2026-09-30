# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): cấu hình hệ thống.

- Bật / tắt các module nghiệp vụ (tắt module nào thì mục đó biến mất với
  mọi tài khoản; dữ liệu vẫn giữ nguyên và hiện lại khi bật lại).
- Cơ cấu tổ chức: Công an tỉnh mặc định và danh mục phòng thuộc Công an
  tỉnh dùng để chọn đơn vị công tác của cán bộ.
- Xem mã máy / trạng thái khóa theo máy.
"""
from PySide6.QtWidgets import (QCheckBox, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
                               QScrollArea, QVBoxLayout, QWidget)

from core import co_cau, registry, report
from ui.widgets import SuggestCombo, ask, button, card, info, label, rule, warn

MODULE_ID = "settings_mod"


class Panel(QScrollArea):
    def __init__(self, app):
        super().__init__()
        self.app, self.db = app, app.db
        self.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("Page")
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(14)
        self.setWidget(body)

        # ---- module
        f, lay = card(18)
        lay.addWidget(label("Cấu hình module", "PageTitle"))
        lay.addWidget(label("Bỏ chọn một module để ẩn khỏi thanh bên của mọi tài khoản. Dữ liệu vẫn được giữ "
                            "và hiện lại khi bật lại. Các mục quản trị hệ thống luôn hiển thị với quản trị viên.",
                            "Muted", wrap=True))
        lay.addWidget(rule())
        grid = QGridLayout()
        disabled = self.db.disabled_modules()
        self.checks = {}
        for i, (mid, title, icon, *_x) in enumerate(registry.BUSINESS_MODULES):
            cb = QCheckBox(f"{icon}   {title}")
            cb.setChecked(mid not in disabled)
            grid.addWidget(cb, i // 2, i % 2)
            self.checks[mid] = cb
        lay.addLayout(grid)
        row = QHBoxLayout()
        row.addWidget(button("💾  Lưu cấu hình module", self.save_modules, "primary"))
        row.addStretch(1)
        lay.addLayout(row)
        v.addWidget(f)

        # ---- cơ cấu tổ chức
        f, lay = card(18)
        lay.addWidget(label("Cơ cấu tổ chức", "CardTitle"))
        lay.addWidget(label("Dùng khi chọn đơn vị của cán bộ: Công an tỉnh / thành phố → Phòng hoặc Công an xã, "
                            "phường → Đội / Tổ. Danh sách Công an xã, phường tự lấy theo địa giới hành chính "
                            "hiện hành của tỉnh đã chọn. Danh mục phòng bên dưới là danh mục tham khảo - hãy "
                            "sửa lại cho đúng cơ cấu thực tế của đơn vị (mỗi dòng một phòng).", "Muted", wrap=True))
        lay.addWidget(rule())
        r1 = QHBoxLayout()
        r1.addWidget(label("Công an tỉnh / thành phố mặc định:"))
        self.c_tinh = SuggestCombo(co_cau.danh_sach_cong_an_tinh(), editable=False,
                                   text=co_cau.tinh_mac_dinh(self.db))
        r1.addWidget(self.c_tinh, 1)
        lay.addLayout(r1)
        lay.addWidget(label("Danh mục phòng thuộc Công an tỉnh:"))
        self.t_phong = QPlainTextEdit("\n".join(co_cau.danh_muc_phong(self.db)))
        self.t_phong.setMinimumHeight(260)
        lay.addWidget(self.t_phong)
        r2 = QHBoxLayout()
        r2.addWidget(button("💾  Lưu cơ cấu tổ chức", self.save_org, "primary"))
        r2.addWidget(button("Khôi phục danh mục mặc định", self.reset_org))
        r2.addStretch(1)
        lay.addLayout(r2)
        v.addWidget(f)

        # ---- thể thức in / xuất file
        f, lay = card(18)
        lay.addWidget(label("Thể thức in ấn / xuất file", "CardTitle"))
        lay.addWidget(label("Dùng cho phần đầu (tên cơ quan) và phần chữ ký của các bản in PDF, file Excel.",
                            "Muted", wrap=True))
        lay.addWidget(rule())
        form = QFormLayout()
        cur = report.settings(self.db)
        self.print_edits = {}
        for key, text in report.KEYS.items():
            e = QLineEdit(cur[key])
            form.addRow(text, e)
            self.print_edits[key] = e
        lay.addLayout(form)
        r3 = QHBoxLayout()
        r3.addWidget(button("💾  Lưu thể thức in", self.save_print, "primary"))
        r3.addStretch(1)
        lay.addLayout(r3)
        v.addWidget(f)

        # ---- khóa máy
        from core.machine_lock import check as check_machine
        _ok, code, reason = check_machine(self.app.app_dir)
        f, lay = card(18)
        lay.addWidget(label("Khóa theo máy (danh sách máy được duyệt)", "CardTitle"))
        lay.addWidget(label(f"Mã máy này: {code or '(không xác định được)'}\nTrạng thái: {reason}\n"
                            "Để bật / sửa danh sách, chỉnh file allowed_machines.txt cạnh file chạy phần mềm "
                            "rồi khởi động lại.", "Muted", wrap=True))
        v.addWidget(f)
        v.addStretch(1)

    def save_modules(self):
        disabled = {mid for mid, cb in self.checks.items() if not cb.isChecked()}
        if len(disabled) == len(self.checks) and not ask(
                self, "Bạn sắp tắt TẤT CẢ module nghiệp vụ. Người dùng thường sẽ không thấy mục nào để làm "
                      "việc. Vẫn tiếp tục?"):
            return
        self.db.set_disabled_modules(disabled)
        self.db.log(self.app.user["username"], "Cấu hình module", f"Tắt: {', '.join(sorted(disabled)) or '(không)'}")
        info(self, "Đã lưu cấu hình module.", "Đã lưu")
        self.app.reload_shell(open_module=MODULE_ID)

    def save_org(self):
        lines = [ln.strip() for ln in self.t_phong.toPlainText().splitlines() if ln.strip()]
        if not lines:
            warn(self, "Danh mục phòng đang trống.", "Thiếu thông tin")
            return
        self.db.set_setting(co_cau.SETTING_TINH, self.c_tinh.text())
        self.db.set_setting(co_cau.SETTING_PHONG, "\n".join(lines))
        self.db.log(self.app.user["username"], "Cấu hình cơ cấu tổ chức",
                    f"{self.c_tinh.text()}; {len(lines)} phòng")
        info(self, "Đã lưu cơ cấu tổ chức.", "Đã lưu")

    def save_print(self):
        for key, e in self.print_edits.items():
            self.db.set_setting(key, e.text().strip())
        self.db.log(self.app.user["username"], "Cấu hình thể thức in", self.print_edits["in_don_vi"].text())
        info(self, "Đã lưu thể thức in.", "Đã lưu")

    def reset_org(self):
        if ask(self, "Khôi phục danh mục phòng mặc định (danh mục tham khảo)?"):
            self.t_phong.setPlainText("\n".join(co_cau.PHONG_MAC_DINH))
