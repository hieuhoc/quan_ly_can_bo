# -*- coding: utf-8 -*-
"""Module: Phân loại, đánh giá, chấm điểm cán bộ theo tháng / quý / năm."""
import datetime

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QStackedWidget, QVBoxLayout, QWidget

import ui.widgets as W
from ui.widgets import (DataTable, EmployeePicker, FormDialog, ListPage, SearchDialog, SuggestCombo, TabBar, ask,
                        button, card, choice, label, rule, warn)

MODULE_ID = "classification"
TABLE = "phan_loai_can_bo"
LOAI_OPTIONS = ["Tháng", "Quý", "Năm"]
XEP_LOAI_OPTIONS = [
    "Hoàn thành xuất sắc nhiệm vụ",
    "Hoàn thành tốt nhiệm vụ",
    "Hoàn thành nhiệm vụ",
    "Không hoàn thành nhiệm vụ",
]
XEP_LOAI_TAT = {
    "Hoàn thành xuất sắc nhiệm vụ": "Xuất sắc",
    "Hoàn thành tốt nhiệm vụ": "Tốt",
    "Hoàn thành nhiệm vụ": "HT",
    "Không hoàn thành nhiệm vụ": "Không HT",
}
QUY_LABELS = ["Quý I", "Quý II", "Quý III", "Quý IV"]
THANG_LABELS = [f"Tháng {i}" for i in range(1, 13)]
COLS = [("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160), ("loai", "Loại kỳ", 80), ("ky", "Kỳ đánh giá", 120),
        ("xep_loai", "Xếp loại", 200), ("diem", "Điểm", 70), ("ghi_chu", "Ghi chú", 160)]


def _current_year():
    return datetime.date.today().year


def _nam_values():
    y = _current_year()
    return [str(n) for n in range(y - 5, y + 2)]


def _ky_info(loai, nam, ky_trong_nam):
    if loai == "Tháng" and ky_trong_nam in THANG_LABELS:
        idx = THANG_LABELS.index(ky_trong_nam) + 1
        return idx, f"Tháng {idx:02d}/{nam}"
    if loai == "Quý" and ky_trong_nam in QUY_LABELS:
        idx = QUY_LABELS.index(ky_trong_nam) + 1
        return idx, f"{ky_trong_nam}/{nam}"
    return None, f"Năm {nam}"


def _short(lbl):
    return lbl.replace("Tháng ", "Th.").replace("Quý ", "Q.")


class Panel(QWidget):
    """Hai tab: Danh sách chi tiết / Bảng tổng hợp theo kỳ."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.tabs = TabBar([("list", "Danh sách chi tiết"), ("grid", "Bảng tổng hợp theo kỳ")])
        v.addWidget(self.tabs)
        self.stack = QStackedWidget()
        self.list_page = ListTab(app, self)
        self.grid_page = GridTab(app)
        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.grid_page)
        v.addWidget(self.stack, 1)
        self.tabs.changed.connect(self._switch)

    def _switch(self, key):
        # Hai tab cùng đọc một bảng dữ liệu; làm mới mỗi lần chuyển để không thấy số liệu cũ.
        if key == "grid":
            self.grid_page.refresh()
            self.stack.setCurrentWidget(self.grid_page)
        else:
            self.list_page.refresh()
            self.stack.setCurrentWidget(self.list_page)


class ListTab(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app, owner):
        self.owner = owner
        super().__init__(app, "Danh sách chi tiết phân loại", COLS,
                         subtitle="Kết quả phân loại, chấm điểm cán bộ theo tháng / quý / năm")
        self.add_action("➕  Thêm kết quả", self.open_add, "primary", perm="add")
        self.add_action("🗑  Xóa", self.on_delete, "danger", perm="delete", needs_selection=True)
        cols = [(k, lbl) for k, lbl, _w in COLS]
        self.add_action("📊  Xuất Excel", lambda: self.export_excel(
            "Danh sách phân loại cán bộ", "phan_loai_can_bo", columns=cols), perm="export", right=True)
        self.add_action("🖨  In PDF", lambda: self.print_pdf(
            "Danh sách phân loại cán bộ", "phan_loai_can_bo", columns=cols), perm="export", right=True)
        self.table.set_display("diem", lambda v, r: "" if v is None else f"{v:g}")
        self.table.delete_pressed.connect(self.on_delete)
        self.refresh()

    def load_rows(self):
        sql = ("SELECT p.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM phan_loai_can_bo p "
               "JOIN can_bo c ON c.id = p.can_bo_id")
        conds, params = [], []
        f = self.adv_filters
        if f:
            if f.get("ho_ten"):
                conds.append("c.ho_ten LIKE ?"); params.append(f"%{f['ho_ten']}%")
            if f.get("loai"):
                conds.append("p.loai = ?"); params.append(f["loai"])
            if f.get("nam"):
                conds.append("p.nam = ?"); params.append(f["nam"])
            if f.get("xep_loai"):
                conds.append("p.xep_loai = ?"); params.append(f["xep_loai"])
        elif self.search_text():
            like = f"%{self.search_text()}%"
            conds.append("(c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR p.ky LIKE ? OR p.xep_loai LIKE ?)")
            params.extend([like] * 4)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY p.nam DESC, p.ky_so DESC, p.id DESC"
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self.load_rows()
        self.table.set_rows(rows)
        self.count_lbl.setText(f"Tổng số: {len(rows)} bản ghi")
        self.owner.tabs.set_count("list", len(rows)) if hasattr(self.owner, "tabs") else None
        self.update_actions()

    def open_advanced(self):
        SearchDialog(self, [("ho_ten", "Họ và tên cán bộ", QLineEdit()),
                            ("loai", "Loại kỳ", choice([""] + LOAI_OPTIONS)),
                            ("nam", "Năm", QLineEdit()),
                            ("xep_loai", "Xếp loại", choice([""] + XEP_LOAI_OPTIONS))]).exec()

    def open_add(self):
        if not self.deny("add") and EntryDialog(self).exec():
            self.refresh()

    def on_delete(self):
        if self.deny("delete"):
            return
        row = self.need_selection("một bản ghi")
        if not row or not ask(self, "Xóa bản ghi phân loại này?\nThao tác không thể hoàn tác.", yes="Xóa",
                              danger=True):
            return
        self.db.delete(TABLE, row["id"])
        self.db.log(self.app.user["username"], "Xóa phân loại cán bộ", f"{row['ho_ten']} - {row['ky']}")
        self.app.set_status("Đã xóa bản ghi.")
        self.refresh()

class GridTab(QWidget):
    """Bảng tổng hợp: mỗi cán bộ một dòng, mỗi tháng/quý một cột, cột cuối là
    điểm trung bình trong khoảng kỳ chọn."""

    def __init__(self, app):
        super().__init__()
        self.app, self.db = app, app.db
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        f, lay = card(18)
        outer.addWidget(f)
        lay.addWidget(label("Bảng tổng hợp xếp loại theo kỳ", "PageTitle"))
        lay.addWidget(rule())
        bar = QHBoxLayout()
        bar.addWidget(label("Xem theo:"))
        self.c_loai = choice(["Tháng", "Quý"])
        self.c_loai.currentTextChanged.connect(self._loai_changed)
        bar.addWidget(self.c_loai)
        bar.addSpacing(12)
        bar.addWidget(label("Năm:"))
        self.c_nam = SuggestCombo(_nam_values(), text=str(_current_year()))
        bar.addWidget(self.c_nam)
        bar.addSpacing(12)
        bar.addWidget(label("Tính điểm TB từ:"))
        self.c_from = choice(THANG_LABELS)
        self.c_to = choice(THANG_LABELS, THANG_LABELS[-1])
        bar.addWidget(self.c_from)
        bar.addWidget(label("đến"))
        bar.addWidget(self.c_to)
        bar.addWidget(button("↻  Xem", self.refresh, "primary"))
        bar.addStretch(1)
        self.btn_export = button("📊  Xuất Excel", self.export_excel)
        self.btn_pdf = button("🖨  In PDF", self.print_pdf)
        bar.addWidget(self.btn_export)
        bar.addWidget(self.btn_pdf)
        lay.addLayout(bar)
        lay.addWidget(label("Xuất sắc / Tốt / HT / Không HT / — (chưa có) — số trong ngoặc là điểm đã chấm", "Muted"))
        self.table_holder = QVBoxLayout()
        lay.addLayout(self.table_holder, 1)
        self.table = None
        self.refresh()

    def _loai_changed(self, loai):
        labels = THANG_LABELS if loai == "Tháng" else QUY_LABELS
        for cb, idx in ((self.c_from, 0), (self.c_to, len(labels) - 1)):
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(labels)
            cb.setCurrentIndex(idx)
            cb.blockSignals(False)
        self.refresh()

    def refresh(self):
        loai = self.c_loai.currentText()
        try:
            nam = int(self.c_nam.text())
        except ValueError:
            warn(self, "Năm không hợp lệ.", "Sai định dạng")
            return
        labels = THANG_LABELS if loai == "Tháng" else QUY_LABELS
        periods = list(range(1, len(labels) + 1))
        a, b = self.c_from.currentIndex() + 1, self.c_to.currentIndex() + 1
        a, b = min(a, b), max(a, b)
        cols = ([("stt", "STT", 50), ("ho_ten", "Họ và tên", 160), ("cap_bac", "Cấp bậc", 90),
                 ("don_vi", "Đơn vị", 150)] +
                [(f"k{p}", _short(labels[p - 1]), 70) for p in periods] +
                [("diem_tb", f"Điểm TB ({_short(labels[a - 1])}–{_short(labels[b - 1])})", 120)])
        if self.table is not None:
            self.table_holder.removeWidget(self.table)
            self.table.deleteLater()
        self.table = DataTable(cols)
        self.table_holder.addWidget(self.table)
        emps = self.db.conn.execute("SELECT id, ho_ten, cap_bac, don_vi FROM can_bo "
                                    "ORDER BY ho_ten COLLATE NOCASE").fetchall()
        data = self.db.conn.execute("SELECT can_bo_id, ky_so, xep_loai, diem FROM phan_loai_can_bo "
                                    "WHERE loai=? AND nam=? ORDER BY id", (loai, nam)).fetchall()
        by_emp = {}
        for r in data:
            by_emp.setdefault(r["can_bo_id"], {})[r["ky_so"]] = (r["xep_loai"], r["diem"])
        rows = []
        for i, e in enumerate(emps, start=1):
            d = by_emp.get(e["id"], {})
            row = dict(id=e["id"], stt=i, ho_ten=e["ho_ten"], cap_bac=e["cap_bac"] or "—", don_vi=e["don_vi"] or "—")
            for p in periods:
                xep, diem = d.get(p, (None, None))
                row[f"k{p}"] = "—" if xep is None else (
                    f"{XEP_LOAI_TAT.get(xep, xep)} ({diem:g})" if diem is not None else XEP_LOAI_TAT.get(xep, xep))
            scores = [d[p][1] for p in periods if a <= p <= b and p in d and d[p][1] is not None]
            row["diem_tb"] = f"{sum(scores) / len(scores):.1f}" if scores else "—"
            rows.append(row)
        self.table.set_rows(rows)
        self.btn_export.setEnabled(self.app.can(MODULE_ID, "export"))
        self.btn_pdf.setEnabled(self.app.can(MODULE_ID, "export"))

    def _title(self):
        return f"Bảng tổng hợp xếp loại cán bộ theo {self.c_loai.currentText().lower()} năm {self.c_nam.text()}"

    def _meta(self):
        return ["Xuất sắc / Tốt / HT / Không HT / — (chưa có); số trong ngoặc là điểm đã chấm"]

    def _name(self):
        return f"tong_hop_phan_loai_{self.c_loai.currentText().lower()}_{self.c_nam.text()}"

    def export_excel(self):
        W.export_excel(self, self.app, self.table, self._title(), self._name(), meta_lines=self._meta())

    def print_pdf(self):
        W.print_pdf(self, self.app, self.table, self._title(), self._name(), meta_lines=self._meta())


class EntryDialog(FormDialog):
    """Nhập một kết quả phân loại / chấm điểm cán bộ."""

    def __init__(self, panel):
        super().__init__(panel, "Thêm kết quả phân loại", 540, 520)
        self.panel, self.db = panel, panel.db
        f = self.form()
        self.picker = EmployeePicker(self.db)
        self.c_loai = choice(LOAI_OPTIONS)
        self.c_nam = SuggestCombo(_nam_values(), text=str(_current_year()))
        self.c_ky = choice(THANG_LABELS, THANG_LABELS[datetime.date.today().month - 1])
        self.c_xep = choice(XEP_LOAI_OPTIONS, XEP_LOAI_OPTIONS[1])
        self.e_diem = QLineEdit()
        self.e_diem.setPlaceholderText("0 - 100 (không bắt buộc)")
        self.e_note = QLineEdit()
        f.addRow("Cán bộ *", self.picker)
        f.addRow("Loại kỳ *", self.c_loai)
        f.addRow("Năm *", self.c_nam)
        self.ky_label = label("Tháng *")
        f.addRow(self.ky_label, self.c_ky)
        f.addRow("Xếp loại *", self.c_xep)
        f.addRow("Điểm", self.e_diem)
        f.addRow("Ghi chú", self.e_note)
        self.body.addStretch(1)
        self.c_loai.currentTextChanged.connect(self._loai_changed)
        self.add_buttons("➕  Thêm", self.save)

    def _loai_changed(self, loai):
        if loai == "Năm":
            self.ky_label.hide()
            self.c_ky.hide()
            return
        labels = THANG_LABELS if loai == "Tháng" else QUY_LABELS
        self.ky_label.setText(f"{loai} *")
        self.c_ky.clear()
        self.c_ky.addItems(labels)
        self.ky_label.show()
        self.c_ky.show()

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            warn(self, "Vui lòng chọn một cán bộ.", "Thiếu thông tin")
            return
        try:
            nam = int(self.c_nam.text())
            if not 1900 <= nam <= 2200:
                raise ValueError
        except ValueError:
            warn(self, "Năm không hợp lệ.", "Sai định dạng")
            return
        diem = None
        if self.e_diem.text().strip():
            try:
                diem = float(self.e_diem.text().strip().replace(",", "."))
                if not 0 <= diem <= 100:
                    raise ValueError
            except ValueError:
                warn(self, "Điểm phải là số từ 0 đến 100.", "Sai định dạng")
                return
        loai = self.c_loai.currentText()
        ky_so, ky = _ky_info(loai, nam, self.c_ky.currentText())
        user = self.panel.app.user["username"]
        data = dict(can_bo_id=emp_id, loai=loai, nam=nam, ky_so=ky_so, ky=ky, xep_loai=self.c_xep.currentText(),
                    diem=diem, ghi_chu=self.e_note.text().strip(), created_by=user)
        self.db.insert(TABLE, data)
        self.db.log(user, "Thêm phân loại cán bộ", f"{self.db.employee_label(emp_id)} - {ky}: {data['xep_loai']}")
        self.panel.app.set_status("Đã lưu kết quả phân loại.")
        self.accept()
