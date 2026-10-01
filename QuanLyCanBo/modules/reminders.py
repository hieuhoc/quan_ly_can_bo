# -*- coding: utf-8 -*-
"""Module Cảnh báo đến hạn: xét thăng cấp bậc hàm, nâng lương, nghỉ hưu,
chuyển Đảng chính thức (cách tính: core/canh_bao.py; con số: Tham số nghiệp vụ).
Hiển thị cho tài khoản có quyền Xem cán bộ; đặt ngoại lệ cần quyền Sửa cán bộ."""
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QRadioButton, QVBoxLayout, QWidget

from core import canh_bao
from ui.theme import C
from ui.widgets import (DateField, FormDialog, ListPage, TabBar, ask, choice, label, section, text_edit,
                        valid_date, warn)

MODULE_ID = "reminders"
COLS = [("trang_thai", "Tình trạng", 110), ("han", "Hạn", 100), ("con_lai", "Còn lại", 100),
        ("loai_text", "Nội dung", 200), ("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160),
        ("cap_bac", "Cấp bậc", 90), ("don_vi", "Đơn vị", 200), ("chi_tiet", "Căn cứ tính", 300),
        ("ngoai_le", "Ngoại lệ - lý do", 220)]
TABS = [("alerts", "Cần xử lý"), ("missing", "Thiếu dữ liệu"), ("excepted", "Ngoại lệ")]


class Panel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        if not app.can("employees", "view"):
            v.addWidget(label("Tài khoản của bạn chưa được cấp quyền xem thông tin cán bộ.", "Muted"))
            v.addStretch(1)
            return
        self.page = Page(app)
        v.addWidget(self.page)


class Page(ListPage):
    MODULE_ID = "employees"     # quyền theo module Thông tin cán bộ

    def __init__(self, app):
        super().__init__(app, "Cảnh báo đến hạn", COLS, advanced=False,
                         subtitle="Xét thăng cấp bậc hàm, nâng lương, nghỉ hưu, chuyển Đảng chính thức, hết hạn chức danh - "
                                  "niên hạn và thời gian báo trước chỉnh tại Tham số nghiệp vụ")
        self.tab = "alerts"
        self.tabs = TabBar(TABS)
        self.tabs.changed.connect(self._switch)
        self.card_layout.insertWidget(2, self.tabs)
        self.c_loai = choice(["Tất cả nội dung"] + list(canh_bao.LOAI.values()))
        self.c_loai.currentTextChanged.connect(lambda *_: self.refresh())
        self.toolbar.addWidget(self.c_loai)
        self.add_action("🛈  Đặt ngoại lệ", self.set_exception, perm="edit", needs_selection=True)
        self.add_action("↩  Bỏ ngoại lệ", self.clear_exception, perm="edit", needs_selection=True,
                        check=lambda r: r and r.get("ngoai_le"))
        self.add_action("📄  Hồ sơ cán bộ", self.open_profile, needs_selection=True)
        self.add_action("📊  Xuất Excel", lambda: self.export_excel("Danh sách cán bộ đến hạn", "canh_bao_den_han"),
                        perm="export", right=True)
        self.add_action("🖨  In PDF", lambda: self.print_pdf(
            "Danh sách cán bộ đến hạn", "canh_bao_den_han",
            columns=[(k, lbl) for k, lbl, _w in COLS if k not in ("con_lai",)]), perm="export", right=True)
        self.table.set_row_color(lambda r: C["red"] if r["trang_thai"] == canh_bao.QUA_HAN
                                 else (C["amber"] if r["trang_thai"] == canh_bao.SAP_DEN else None))
        self.table.activated_row.connect(self.open_profile)
        self.refresh()

    def _switch(self, key):
        self.tab = key
        self.refresh()

    def refresh(self):
        alerts, missing, excepted = canh_bao.compute(self.db)
        data = {"alerts": alerts, "missing": missing, "excepted": excepted}
        for key, rows in data.items():
            self.tabs.set_count(key, len(rows))
        rows = data[self.tab]
        loai = self.c_loai.currentText() if hasattr(self, "c_loai") else ""
        if loai in canh_bao.LOAI.values():
            rows = [r for r in rows if r["loai_text"] == loai]
        kw = self.search_text().lower()
        if kw:
            rows = [r for r in rows if kw in " ".join(str(v or "") for v in r.values()).lower()]
        self.table.set_rows(rows)
        n_qh = sum(1 for r in alerts if r["trang_thai"] == canh_bao.QUA_HAN)
        self.count_lbl.setText(f"Quá hạn: {n_qh}  •  Sắp đến hạn: {len(alerts) - n_qh}")
        self.update_actions()

    def open_profile(self):
        row = self.need_selection("một dòng")
        if not row:
            return
        import modules.employees as me
        cb = self.db.fetch_one("can_bo", row["can_bo_id"])
        if cb:
            me.ProfileDialog(self, cb).exec()
            self.refresh()

    def set_exception(self):
        if self.deny("edit"):
            return
        row = self.need_selection("một dòng")
        if row and ExceptionDialog(self, row).exec():
            self.refresh()

    def clear_exception(self):
        if self.deny("edit"):
            return
        row = self.need_selection("một dòng")
        if row and ask(self, f"Bỏ ngoại lệ '{row['loai_text']}' của {row['ho_ten']}?"):
            canh_bao.clear_exception(self.db, row["can_bo_id"], row["loai"])
            self.db.log(self.app.user["username"], "Bỏ ngoại lệ cảnh báo", f"{row['ma_cb']} - {row['loai_text']}")
            self.refresh()


class ExceptionDialog(FormDialog):
    """Ngoại lệ cho một cảnh báo: dời hạn sang ngày khác hoặc không nhắc nữa - bắt buộc ghi lý do."""

    def __init__(self, page, row):
        super().__init__(page, "Đặt ngoại lệ cảnh báo", 560, 480)
        self.page, self.row = page, row
        self.body.addWidget(label(f"{row['ho_ten']} ({row['ma_cb']}) - {row['loai_text']}", "CardTitle"))
        self.body.addWidget(label(row.get("chi_tiet") or "", "Muted", wrap=True))
        self.body.addWidget(section("Cách xử lý"))
        self.r_doi = QRadioButton("Dời hạn đến ngày")
        self.r_bo = QRadioButton("Không nhắc nội dung này cho cán bộ này nữa")
        self.r_doi.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.r_doi)
        grp.addButton(self.r_bo)
        h = QHBoxLayout()
        h.addWidget(self.r_doi)
        self.d_han = DateField()
        h.addWidget(self.d_han, 1)
        self.body.addLayout(h)
        self.body.addWidget(self.r_bo)
        self.r_doi.toggled.connect(self.d_han.setEnabled)
        self.body.addWidget(section("Lý do *"))
        self.t_lydo = text_edit(row.get("ngoai_le") or "", 90)
        self.body.addWidget(self.t_lydo)
        self.body.addStretch(1)
        self.add_buttons("💾  Lưu ngoại lệ", self.save)

    def save(self):
        lydo = self.t_lydo.toPlainText().strip()
        if not lydo:
            warn(self, "Vui lòng ghi rõ lý do ngoại lệ.", "Thiếu thông tin")
            return
        han = ""
        if self.r_doi.isChecked():
            han = self.d_han.text()
            if not valid_date(han):
                warn(self, "Ngày hạn mới phải theo dạng dd/mm/yyyy.", "Sai định dạng")
                return
        db, user = self.page.db, self.page.app.user["username"]
        canh_bao.set_exception(db, self.row["can_bo_id"], self.row["loai"], han, lydo, user)
        db.log(user, "Đặt ngoại lệ cảnh báo",
               f"{self.row['ma_cb']} - {self.row['loai_text']}: {'dời đến ' + han if han else 'không nhắc'} ({lydo})")
        self.accept()
