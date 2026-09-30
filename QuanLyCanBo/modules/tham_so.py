# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): chỉnh các tham số nghiệp vụ - cấp bậc, hệ số
lương, niên hạn thăng cấp, tuổi nghỉ hưu, thời gian báo trước, danh mục xếp
loại / đơn thư... (xem core/tham_so.py)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from core import tham_so as ts
from ui.theme import C
from ui.widgets import ask, button, card, info, label, rule, warn

MODULE_ID = "tham_so"


class _Editor(QWidget):
    """Ô chỉnh một tham số theo kiểu của nó."""

    def __init__(self, key):
        super().__init__()
        self.key = key
        _k, group, title, kind, _d, helptext, columns = ts.spec(key)
        self.kind, self.columns = kind, columns
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(label(title, "CardTitle"))
        if helptext:
            v.addWidget(label(helptext, "Muted", wrap=True))
        self.status = label("", "Note")
        v.addWidget(self.status)
        v.addWidget(rule())
        if kind == "list":
            v.addWidget(label("Mỗi dòng một mục:", "Muted"))
            self.w = QPlainTextEdit()
            v.addWidget(self.w, 1)
        elif kind == "table":
            self.w = QTableWidget(0, len(columns))
            self.w.setHorizontalHeaderLabels([c.upper() for c in columns])
            self.w.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.w.verticalHeader().hide()
            self.w.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.w.setAlternatingRowColors(True)
            v.addWidget(self.w, 1)
            h = QHBoxLayout()
            h.addWidget(button("➕  Thêm dòng", self._add_row))
            h.addWidget(button("🗑  Xóa dòng đang chọn", self._del_row))
            h.addStretch(1)
            v.addLayout(h)
        else:
            self.w = QSpinBox()
            self.w.setRange(0, 1000)
            self.w.setFixedWidth(160)
            v.addWidget(self.w)
            v.addStretch(1)
        self.load(ts.get(key))

    def load(self, value):
        if self.kind == "list":
            self.w.setPlainText("\n".join(value))
        elif self.kind == "table":
            self.w.setRowCount(0)
            for row in value:
                self._add_row(row)
        else:
            self.w.setValue(int(value or 0))

    def _add_row(self, values=None):
        r = self.w.rowCount()
        self.w.insertRow(r)
        for c in range(len(self.columns)):
            val = values[c] if values and c < len(values) else ""
            self.w.setItem(r, c, QTableWidgetItem(str(val)))
        if not values:
            self.w.scrollToBottom()
            self.w.editItem(self.w.item(r, 0))

    def _del_row(self):
        rows = sorted({i.row() for i in self.w.selectedIndexes()}, reverse=True)
        for r in rows:
            self.w.removeRow(r)

    def value(self):
        if self.kind == "list":
            return [ln.strip() for ln in self.w.toPlainText().splitlines() if ln.strip()]
        if self.kind == "table":
            out = []
            for r in range(self.w.rowCount()):
                row = [(self.w.item(r, c).text().strip() if self.w.item(r, c) else "")
                       for c in range(len(self.columns))]
                if row[0]:
                    out.append(row)
            return out
        return int(self.w.value())

    def problem(self):
        """Kiểm tra dữ liệu trước khi lưu: cột số phải là số."""
        if self.kind != "table":
            return None
        for i, row in enumerate(self.value(), start=1):
            for c, name in enumerate(self.columns):
                if name in ("Hệ số", "Số năm", "Nam", "Nữ") and row[c]:
                    try:
                        float(row[c].replace(",", "."))
                    except ValueError:
                        return f"Dòng {i}, cột '{name}': '{row[c]}' không phải là số."
        return None


class Panel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.db = app, app.db
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        f, lay = card(18)
        outer.addWidget(f)
        lay.addWidget(label("Tham số nghiệp vụ", "PageTitle"))
        lay.addWidget(label("Mọi danh mục và con số theo quy định đều chỉnh được tại đây. Giá trị mặc định lấy theo "
                            "Luật CAND và các văn bản liên quan ở mức tham khảo - đơn vị đối chiếu văn bản hiện hành "
                            "và chỉnh lại nếu khác. Trường hợp riêng lẻ khác quy định vẫn nhập được trong từng hồ sơ "
                            "nhưng phải ghi lý do.", "Muted", wrap=True))
        lay.addWidget(rule())
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(330)
        self.list.setStyleSheet(f"QListWidget {{ border: 1px solid {C['border']}; border-radius: 8px; padding: 4px; }}"
                                f"QListWidget::item {{ padding: 7px 8px; border-radius: 6px; }}"
                                f"QListWidget::item:selected {{ background: {C['sel']}; color: {C['text']}; }}")
        self.stack = QStackedWidget()
        self.editors = []
        group = None
        for key, grp, title, *_x in ts.PARAMS:
            if grp != group:
                group = grp
                it = QListWidgetItem(grp.upper())
                it.setFlags(Qt.NoItemFlags)
                it.setForeground(Qt.gray)
                self.list.addItem(it)
            it = QListWidgetItem(title)
            it.setData(Qt.UserRole, len(self.editors))
            self.list.addItem(it)
            ed = _Editor(key)
            self.editors.append(ed)
            self.stack.addWidget(ed)
        self.list.currentItemChanged.connect(self._select)
        body.addWidget(self.list)
        right = QVBoxLayout()
        right.addWidget(self.stack, 1)
        btns = QHBoxLayout()
        btns.addWidget(button("💾  Lưu tham số này", self.save, "primary"))
        btns.addWidget(button("Khôi phục mặc định", self.reset))
        btns.addStretch(1)
        right.addLayout(btns)
        body.addLayout(right, 1)
        lay.addLayout(body, 1)
        self.list.setCurrentRow(1)
        self._refresh_status()

    def _select(self, item, _prev=None):
        if item is not None and item.data(Qt.UserRole) is not None:
            self.stack.setCurrentIndex(item.data(Qt.UserRole))

    def _current(self):
        return self.stack.currentWidget()

    def _refresh_status(self):
        for ed in self.editors:
            ed.status.setText("Đang dùng giá trị đã chỉnh (khác mặc định)." if ts.is_custom(self.db, ed.key)
                              else "Đang dùng giá trị mặc định.")

    def save(self):
        ed = self._current()
        problem = ed.problem()
        if problem:
            warn(self, problem, "Sai dữ liệu")
            return
        value = ed.value()
        if ed.kind in ("list", "table") and not value:
            warn(self, "Danh sách đang trống.", "Thiếu dữ liệu")
            return
        ts.set_value(self.db, ed.key, value)
        self.db.log(self.app.user["username"], "Chỉnh tham số nghiệp vụ", ts.spec(ed.key)[2])
        self._refresh_status()
        info(self, "Đã lưu. Các màn hình mở sau sẽ dùng giá trị mới.", "Đã lưu")

    def reset(self):
        ed = self._current()
        if not ask(self, f"Khôi phục '{ts.spec(ed.key)[2]}' về giá trị mặc định?"):
            return
        ts.reset(self.db, ed.key)
        ed.load(ts.get(ed.key))
        self.db.log(self.app.user["username"], "Khôi phục tham số mặc định", ts.spec(ed.key)[2])
        self._refresh_status()
