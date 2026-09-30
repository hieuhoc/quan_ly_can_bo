# -*- coding: utf-8 -*-
"""Thành phần giao diện tái sử dụng giữa các module (PySide6)."""
import datetime
import os

from PySide6.QtCore import (QAbstractTableModel, QDate, QModelIndex, QSortFilterProxyModel, Qt, QTimer,
                            Signal)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QCalendarWidget, QComboBox, QCompleter, QDialog, QFileDialog,
                               QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPushButton, QScrollArea, QSizePolicy, QTableView, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction, QApplication)

from ui.theme import C

DATE_FMT = "%d/%m/%Y"


# ------------------------------------------------------------------ tiện ích
def button(text, slot=None, variant="secondary", parent=None, tooltip=None):
    b = QPushButton(text, parent)
    b.setProperty("variant", variant)
    b.setCursor(Qt.PointingHandCursor)
    if slot:
        b.clicked.connect(lambda *_: slot())
    if tooltip:
        b.setToolTip(tooltip)
    return b


def label(text="", name=None, wrap=False):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def rule():
    f = QFrame()
    f.setObjectName("Rule")
    f.setFrameShape(QFrame.NoFrame)
    return f


def card(padding=16, spacing=10):
    """Khung thẻ trắng bo góc. Trả về (khung, layout dọc bên trong)."""
    f = QFrame()
    f.setObjectName("Card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(padding, padding, padding, padding)
    lay.setSpacing(spacing)
    return f, lay


def section(text):
    """Tiêu đề nhóm trường: vạch đỏ + chữ in hoa + đường kẻ mảnh."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 10, 0, 2)
    h.setSpacing(8)
    bar = QFrame()
    bar.setObjectName("SectionBar")
    bar.setFixedSize(3, 16)
    h.addWidget(bar)
    h.addWidget(label(text.upper(), "SectionTitle"))
    line = rule()
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    h.addWidget(line, 1)
    return w


def valid_date(text):
    try:
        datetime.datetime.strptime(text, DATE_FMT)
        return True
    except ValueError:
        return False


def date_key(text):
    """'05/03/2026' -> '20260305' để so sánh / sắp xếp đúng thời gian."""
    try:
        return datetime.datetime.strptime(text.strip(), DATE_FMT).strftime("%Y%m%d")
    except (ValueError, AttributeError):
        return None


def sql_date_key(col):
    """Biểu thức SQL đổi 'dd/mm/yyyy' thành 'yyyymmdd'."""
    return f"(substr({col},7,4)||substr({col},4,2)||substr({col},1,2))"


# ------------------------------------------------------------------ hộp thông báo
def _box(parent, icon, title, text, buttons):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    result = {}
    for btext, role, key, variant in buttons:
        b = box.addButton(btext, role)
        b.setProperty("variant", variant)
        result[b] = key
    box.exec()
    return result.get(box.clickedButton())


def warn(parent, text, title="Thông báo"):
    _box(parent, QMessageBox.Warning, title, text, [("Đóng", QMessageBox.AcceptRole, True, "primary")])


def info(parent, text, title="Thông báo"):
    _box(parent, QMessageBox.Information, title, text, [("Đóng", QMessageBox.AcceptRole, True, "primary")])


def error(parent, text, title="Lỗi"):
    _box(parent, QMessageBox.Critical, title, text, [("Đóng", QMessageBox.AcceptRole, True, "primary")])


def ask(parent, text, title="Xác nhận", yes="Đồng ý", danger=False):
    return bool(_box(parent, QMessageBox.Question, title, text,
                     [(yes, QMessageBox.YesRole, True, "danger" if danger else "primary"),
                      ("Hủy", QMessageBox.NoRole, False, "secondary")]))


def save_file_dialog(parent, default_name, filter_="CSV (*.csv)"):
    path, _ = QFileDialog.getSaveFileName(parent, "Lưu file", default_name, filter_)
    return path


def open_file_dialog(parent, title="Chọn file",
                     filter_="Tài liệu (*.pdf *.doc *.docx *.jpg *.jpeg *.png);;Tất cả file (*.*)"):
    path, _ = QFileDialog.getOpenFileName(parent, title, "", filter_)
    return path


# ------------------------------------------------------------------ bảng dữ liệu
def _sort_key(val):
    if val is None or val == "" or val == "—":
        return "~"
    s = str(val).strip()
    k = date_key(s)
    if k:
        return "D" + k
    try:
        return "N%020.4f" % (float(s.replace(",", "")) + 1e12)
    except ValueError:
        return "T" + s.casefold()


class RowModel(QAbstractTableModel):
    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.rows = []
        self.row_color = None       # hàm(row) -> mã màu chữ hoặc None
        self.display = {}           # khóa cột -> hàm(giá trị, row) -> chuỗi hiển thị

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = [dict(r) for r in rows]
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def _text(self, row, key):
        v = row.get(key)
        if key in self.display:
            return self.display[key](v, row)
        return "" if v is None else str(v)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        key = self.columns[index.column()][0]
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            return self._text(row, key)
        if role == Qt.UserRole:
            return _sort_key(self._text(row, key))
        if role == Qt.ForegroundRole and self.row_color:
            c = self.row_color(row)
            return QColor(c) if c else None
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignVCenter | Qt.AlignLeft)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section][1].upper()
        return None


class DataTable(QTableView):
    """Bảng dữ liệu: bấm tiêu đề cột để sắp xếp (nhận biết số và ngày
    dd/mm/yyyy), chọn cả dòng, bấm đúp để mở, phím Delete để xóa, cột tự
    giãn theo nội dung (tối thiểu bằng độ rộng khai báo)."""
    selection_changed = Signal()
    activated_row = Signal()
    delete_pressed = Signal()
    MAX_AUTO_W = 380

    def __init__(self, columns, sortable=True, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.model_ = RowModel(columns)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model_)
        self.proxy.setSortRole(Qt.UserRole)
        self.setModel(self.proxy)
        self.setSortingEnabled(sortable)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)
        self.setMouseTracking(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(36)
        hh = self.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setSortIndicatorShown(sortable)
        if sortable:
            hh.setSortIndicator(-1, Qt.AscendingOrder)
        self.empty_text = "Không có dữ liệu"
        self.selectionModel().selectionChanged.connect(lambda *_: self.selection_changed.emit())
        self.doubleClicked.connect(lambda *_: self.activated_row.emit())
        for i, (_k, _l, w) in enumerate(columns):
            self.setColumnWidth(i, w)

    # ---- dữ liệu
    def set_rows(self, rows, keep_selection=True):
        sel = self.selected_id() if keep_selection else None
        self.model_.set_rows(rows)
        self._autofit()
        if sel is not None:
            self.select_id(sel)
        self.selection_changed.emit()

    def set_row_color(self, fn):
        self.model_.row_color = fn

    def set_display(self, key, fn):
        self.model_.display[key] = fn

    def _autofit(self):
        fm = self.fontMetrics()
        hfm = self.horizontalHeader().fontMetrics()
        rows = self.model_.rows[:400]
        for i, (key, lbl, w) in enumerate(self.columns):
            best = hfm.horizontalAdvance(lbl.upper()) + 44
            for r in rows:
                best = max(best, fm.horizontalAdvance(self.model_._text(r, key)) + 28)
                if best >= self.MAX_AUTO_W:
                    break
            self.setColumnWidth(i, max(w, min(best, self.MAX_AUTO_W)))

    def rows(self):
        return [self.model_.rows[self.proxy.mapToSource(self.proxy.index(i, 0)).row()]
                for i in range(self.proxy.rowCount())]

    def row_count(self):
        return self.proxy.rowCount()

    def selected_row(self):
        idx = self.selectionModel().selectedRows()
        if not idx:
            return None
        return self.model_.rows[self.proxy.mapToSource(idx[0]).row()]

    def selected_id(self):
        r = self.selected_row()
        return r.get("id") if r else None

    def select_id(self, rid):
        for i in range(self.proxy.rowCount()):
            src = self.proxy.mapToSource(self.proxy.index(i, 0))
            if self.model_.rows[src.row()].get("id") == rid:
                self.selectRow(i)
                return

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.delete_pressed.emit()
            return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.activated_row.emit()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.proxy.rowCount() == 0 and self.empty_text:
            p = QPainter(self.viewport())
            p.setPen(QColor(C["muted"]))
            p.drawText(self.viewport().rect().adjusted(0, 24, 0, 0), Qt.AlignHCenter | Qt.AlignTop, self.empty_text)


# ------------------------------------------------------------------ ô nhập
class DateField(QWidget):
    """Ô nhập ngày dd/mm/yyyy (gõ tay được) + nút lịch để chọn."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        self.edit = QLineEdit(text or "")
        self.edit.setPlaceholderText("dd/mm/yyyy")
        self.edit.setMaxLength(10)
        h.addWidget(self.edit, 1)
        self.btn = QToolButton()
        self.btn.setText("📅")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setToolTip("Chọn ngày")
        self.btn.clicked.connect(self._popup)
        h.addWidget(self.btn)

    def _popup(self):
        menu = QMenu(self)
        cal = QCalendarWidget()
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal.setFirstDayOfWeek(Qt.Monday)
        if valid_date(self.text()):
            d = datetime.datetime.strptime(self.text(), DATE_FMT)
            cal.setSelectedDate(QDate(d.year, d.month, d.day))
        act = QWidgetAction(menu)
        act.setDefaultWidget(cal)
        menu.addAction(act)

        def picked(qd):
            self.setText(f"{qd.day():02d}/{qd.month():02d}/{qd.year():04d}")
            menu.close()
        cal.clicked.connect(picked)
        menu.exec(self.btn.mapToGlobal(self.btn.rect().bottomLeft()))

    def text(self):
        return self.edit.text().strip()

    def setText(self, t):
        self.edit.setText(t or "")

    def setEnabled(self, on):
        self.edit.setEnabled(on)
        self.btn.setEnabled(on)


class Combo(QComboBox):
    """QComboBox KHÔNG đổi giá trị khi con lăn chuột lướt qua (lúc đang cuộn
    biểu mẫu dài) - chỉ nhận con lăn khi người dùng đã bấm chọn vào ô."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class SuggestCombo(Combo):
    """Ô chọn có gõ để lọc (khớp mọi vị trí, không phân biệt hoa thường).
    editable=True cho phép nhập giá trị không có trong danh sách."""

    def __init__(self, items=(), editable=True, text="", parent=None):
        super().__init__(parent)
        self.setEditable(editable)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(15)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)
        self.set_items(items)
        if editable:
            comp = QCompleter(self.model(), self)
            comp.setFilterMode(Qt.MatchContains)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setCompletionMode(QCompleter.PopupCompletion)
            self.setCompleter(comp)
        self.setText(text)

    def set_items(self, items, keep=True):
        cur = self.text() if keep else ""
        self.blockSignals(True)
        self.clear()
        self.addItems(list(items))
        self.setText(cur)
        self.blockSignals(False)

    def text(self):
        return self.currentText().strip()

    def setText(self, t):
        t = t or ""
        i = self.findText(t)
        if i >= 0:
            self.setCurrentIndex(i)
        elif self.isEditable():
            self.setCurrentIndex(-1)
            self.setEditText(t)
        else:
            self.setCurrentIndex(-1)


def choice(items, current=None):
    """Ô chọn cố định (không gõ được)."""
    cb = Combo()
    cb.addItems(list(items))
    if current is not None:
        i = cb.findText(current)
        if i >= 0:
            cb.setCurrentIndex(i)
        else:
            cb.addItem(current)
            cb.setCurrentText(current)
    return cb


class EmployeePicker(SuggestCombo):
    """Chọn một cán bộ theo 'Mã - Họ tên' (gõ để lọc)."""

    def __init__(self, db, parent=None):
        self.db = db
        self._map = {}
        super().__init__([], editable=True, parent=parent)
        self.reload()

    def reload(self):
        rows = self.db.employees_for_picker()
        self._map = {f"{r['ma_cb']} - {r['ho_ten']}": r["id"] for r in rows}
        self.set_items(self._map.keys())
        self.setCurrentIndex(-1)
        self.setEditText("")
        self.lineEdit().setPlaceholderText("Gõ mã hoặc tên cán bộ để tìm...")

    def get(self):
        return self._map.get(self.text())

    def set_by_id(self, emp_id):
        if emp_id is None:
            self.setText("")
            return
        lbl = self.db.employee_label(emp_id)
        if lbl not in self._map:
            self._map[lbl] = emp_id
            self.addItem(lbl)
        self.setText(lbl)


class ProvinceWardPicker(QWidget):
    """Cặp ô Tỉnh/Thành phố -> Xã/Phường (theo địa giới hành chính hiện hành)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        import core.dia_gioi_hanh_chinh as dgh
        self._dgh = dgh
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.tinh = SuggestCombo(dgh.danh_sach_tinh())
        self.tinh.lineEdit().setPlaceholderText("Tỉnh / thành phố")
        self.xa = SuggestCombo([])
        self.xa.lineEdit().setPlaceholderText("Xã / phường")
        h.addWidget(self.tinh, 1)
        h.addWidget(self.xa, 1)
        self.tinh.currentTextChanged.connect(self._reload)

    def _reload(self, *_):
        self.xa.set_items(self._dgh.danh_sach_xa(self.tinh.text()))

    def get(self):
        return self.tinh.text(), self.xa.text()

    def set(self, tinh, xa):
        self.tinh.setText(tinh or "")
        self._reload()
        self.xa.setText(xa or "")


class FilePicker(QWidget):
    """Chọn file đính kèm: hiện tên file + nút chọn."""

    def __init__(self, existing_name="", parent=None):
        super().__init__(parent)
        self.pending = None
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.lbl = label(existing_name or "(chưa có file)", "Muted")
        h.addWidget(self.lbl, 1)
        h.addWidget(button("📎  Chọn file...", self._pick))

    def _pick(self):
        path = open_file_dialog(self)
        if path:
            self.pending = path
            self.lbl.setText(os.path.basename(path) + "  (chưa lưu)")


def text_edit(text="", height=70):
    from PySide6.QtWidgets import QPlainTextEdit
    t = QPlainTextEdit()
    t.setPlainText(text or "")
    t.setFixedHeight(height)
    return t


# ------------------------------------------------------------------ hộp thoại chuẩn
class FormDialog(QDialog):
    """Khung chuẩn cho hộp thoại Thêm/Sửa: tiêu đề lớn, phần thân CUỘN
    ĐƯỢC (con lăn chuột hoạt động ở mọi vị trí), thanh nút cố định phía
    dưới; tự thu nhỏ vừa màn hình."""

    def __init__(self, parent, title, width=560, height=620):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        head = QFrame()
        head.setObjectName("DialogHead")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 14, 22, 12)
        hl.addWidget(label(title, "DialogTitle"))
        root.addWidget(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("DialogBody")
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(22, 12, 22, 16)
        self.body.setSpacing(6)
        self.scroll.setWidget(body)
        self.scroll.setStyleSheet("QScrollArea { background: white; }")
        root.addWidget(self.scroll, 1)

        foot = QFrame()
        foot.setObjectName("DialogFoot")
        self.footer = QHBoxLayout(foot)
        self.footer.setContentsMargins(16, 10, 16, 10)
        self.footer.setSpacing(8)
        root.addWidget(foot)

        scr = (parent.screen() if parent is not None else QApplication.primaryScreen()).availableGeometry()
        self.resize(min(width, scr.width() - 40), min(height, scr.height() - 60))

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_aligned", False):
            self._aligned = True
            self.align_forms()

    def align_forms(self):
        """Mọi khối trường trong hộp thoại dùng CHUNG một độ rộng cột nhãn,
        để các ô nhập thẳng hàng từ trên xuống dưới (không thò ra thụt vào
        giữa các nhóm)."""
        forms = self.findChildren(QFormLayout)
        labels = []
        for f in forms:
            for i in range(f.rowCount()):
                item = f.itemAt(i, QFormLayout.LabelRole)
                if item and item.widget():
                    labels.append(item.widget())
        if labels:
            w = max(lb.sizeHint().width() for lb in labels)
            for lb in labels:
                lb.setMinimumWidth(w)

    def form(self):
        """Thêm một khối nhãn - ô nhập (QFormLayout) vào thân hộp thoại."""
        w = QWidget()
        f = QFormLayout(w)
        f.setContentsMargins(0, 4, 0, 4)
        f.setHorizontalSpacing(14)
        f.setVerticalSpacing(8)
        f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.body.addWidget(w)
        return f

    def add_section(self, title):
        self.body.addWidget(section(title))
        return self.form()

    def add_buttons(self, ok_text, on_ok, variant="primary", cancel_text="Hủy"):
        ok = button(ok_text, on_ok, variant)
        ok.setDefault(True)
        cancel = button(cancel_text, self.reject)
        self.footer.addWidget(ok, 1)
        self.footer.addWidget(cancel, 1)
        return ok


# ------------------------------------------------------------------ thanh tab gạch chân
class TabBar(QWidget):
    """Tab kiểu hiện đại: chữ phẳng, tab đang chọn gạch chân màu thương
    hiệu, kèm ô đếm số bản ghi (tùy chọn)."""
    changed = Signal(str)

    def __init__(self, tabs, selected=None, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        row = QHBoxLayout()
        row.setSpacing(24)
        row.setContentsMargins(0, 0, 0, 0)
        self.buttons, self.badges = {}, {}
        self.selected = selected or tabs[0][0]
        for key, text in tabs:
            h = QHBoxLayout()
            h.setSpacing(6)
            b = QPushButton(text)
            b.setObjectName("TabButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.select(k, notify=True))
            bold = b.font()
            bold.setBold(True)
            bold.setPointSizeF(10.5)
            from PySide6.QtGui import QFontMetrics
            b.setMinimumWidth(QFontMetrics(bold).horizontalAdvance(text) + 12)
            badge = label("", "Badge")
            badge.setFixedHeight(18)
            badge.setAlignment(Qt.AlignCenter)
            badge.hide()
            h.addWidget(b)
            h.addWidget(badge, 0, Qt.AlignVCenter)
            row.addLayout(h)
            self.buttons[key], self.badges[key] = b, badge
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(rule())
        self.select(self.selected)

    def select(self, key, notify=False):
        changed = key != self.selected
        self.selected = key
        for k, b in self.buttons.items():
            b.setChecked(k == key)
            self.badges[k].setProperty("active", "true" if k == key else "false")
            self.badges[k].style().unpolish(self.badges[k])
            self.badges[k].style().polish(self.badges[k])
        if notify and changed:
            self.changed.emit(key)

    def set_count(self, key, n):
        b = self.badges[key]
        b.setVisible(n is not None)
        b.setText("" if n is None else str(n))


# ------------------------------------------------------------------ trang danh sách chuẩn
class ListPage(QWidget):
    """Trang danh sách dùng chung cho các module: tiêu đề + số lượng, ô tìm
    kiếm (+ tìm nâng cao), thanh nút theo quyền, bảng dữ liệu.
    Lớp con cài đặt load_rows() và gọi refresh()."""
    MODULE_ID = None

    def __init__(self, app, title, columns, subtitle=None, searchable=True, advanced=True, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self.app, self.db = app, app.db
        self.adv_filters = {}
        self._actions = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame, lay = card(18, 10)
        outer.addWidget(frame)
        self.card_layout = lay

        top = QHBoxLayout()
        tl = QVBoxLayout()
        tl.setSpacing(2)
        tl.addWidget(label(title, "PageTitle"))
        if subtitle:
            tl.addWidget(label(subtitle, "Muted"))
        top.addLayout(tl, 1)
        self.count_lbl = label("", "Muted")
        top.addWidget(self.count_lbl, 0, Qt.AlignBottom)
        lay.addLayout(top)
        lay.addWidget(rule())

        self.search = None
        if searchable:
            bar = QHBoxLayout()
            self.search = QLineEdit()
            self.search.setPlaceholderText("🔍  Tìm kiếm nhanh...")
            self.search.setClearButtonEnabled(True)
            bar.addWidget(self.search, 1)
            if advanced:
                bar.addWidget(button("🔎  Tìm nâng cao", self.open_advanced))
            lay.addLayout(bar)
            self._debounce = QTimer(self)
            self._debounce.setSingleShot(True)
            self._debounce.setInterval(180)
            self._debounce.timeout.connect(self._on_search)
            self.search.textChanged.connect(lambda *_: self._debounce.start())
        self.note = label("", "Note")
        self.note.hide()
        lay.addWidget(self.note)

        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(6)
        self.toolbar_right = QHBoxLayout()
        self.toolbar_right.setSpacing(6)
        tb = QHBoxLayout()
        tb.addLayout(self.toolbar)
        tb.addStretch(1)
        tb.addLayout(self.toolbar_right)
        lay.addLayout(tb)

        self.table = DataTable(columns)
        lay.addWidget(self.table, 1)
        self.table.selection_changed.connect(self.update_actions)

    # ---- nút theo quyền / theo dòng đang chọn
    def add_action(self, text, slot, variant="secondary", perm=None, needs_selection=False, check=None,
                   right=False):
        b = button(text, slot, variant)
        (self.toolbar_right if right else self.toolbar).addWidget(b)
        self._actions.append((b, perm, needs_selection, check))
        return b

    def update_actions(self):
        row = self.table.selected_row()
        for b, perm, needs_sel, check in self._actions:
            ok = True
            if perm and not self.app.can(self.MODULE_ID, perm):
                ok = False
            if needs_sel and row is None:
                ok = False
            if ok and check is not None:
                ok = bool(check(row))
            b.setEnabled(ok)

    def deny(self, action):
        if self.app.can(self.MODULE_ID, action):
            return False
        from core.registry import ACTION_LABEL
        warn(self, f"Tài khoản của bạn không có quyền «{ACTION_LABEL[action]}».", "Không đủ quyền")
        return True

    def need_selection(self, what="một bản ghi"):
        row = self.table.selected_row()
        if row is None:
            info(self, f"Hãy chọn {what} trong danh sách.", "Chưa chọn")
        return row

    # ---- tìm kiếm
    def search_text(self):
        return self.search.text().strip() if self.search else ""

    def _on_search(self):
        if self.adv_filters and self.search_text():
            self.clear_advanced(refresh=False)
        self.refresh()

    def open_advanced(self):
        pass

    def apply_advanced(self, filters):
        self.adv_filters = filters
        if self.search:
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        self.note.setText(f"Đang áp dụng tìm kiếm nâng cao ({len(filters)} tiêu chí) — "
                          "gõ vào ô tìm kiếm nhanh để bỏ lọc này.")
        self.note.setVisible(bool(filters))
        self.refresh()

    def clear_advanced(self, refresh=True):
        self.adv_filters = {}
        self.note.hide()
        if refresh:
            self.refresh()

    def refresh(self):
        raise NotImplementedError


class SearchDialog(FormDialog):
    """Hộp thoại Tìm kiếm nâng cao dùng chung: fields = [(khóa, nhãn, widget)]."""

    def __init__(self, page, fields, validate=None):
        super().__init__(page, "Tìm kiếm nâng cao", 480, 120 + 50 * len(fields))
        self.page, self.fields, self.validate = page, fields, validate
        f = self.form()
        for key, text, w in fields:
            cur = page.adv_filters.get(key, "")
            if isinstance(w, QComboBox):
                if w.isEditable():
                    w.setCurrentIndex(-1)
                    w.setEditText(cur)
                else:
                    w.setCurrentIndex(max(0, w.findText(cur)))
            else:
                w.setText(cur)
            f.addRow(text, w)
        ok = button("Áp dụng", self._apply, "primary")
        ok.setDefault(True)
        self.footer.addWidget(ok, 1)
        self.footer.addWidget(button("Xóa bộ lọc", self._clear), 1)
        self.footer.addWidget(button("Đóng", self.reject), 1)

    def values(self):
        out = {}
        for key, _t, w in self.fields:
            v = (w.currentText() if isinstance(w, QComboBox) else w.text()).strip()
            if v:
                out[key] = v
        return out

    def _apply(self):
        vals = self.values()
        if self.validate:
            problem = self.validate(vals)
            if problem:
                warn(self, problem, "Sai định dạng")
                return
        self.page.apply_advanced(vals)
        self.accept()

    def _clear(self):
        self.page.clear_advanced()
        self.accept()


# ------------------------------------------------------------------ thẻ số liệu, biểu đồ
class StatCard(QFrame):
    def __init__(self, value, text, color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 14, 0)
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(f"background: {color or C['primary']}; border-top-left-radius: 10px;"
                          "border-bottom-left-radius: 10px;")
        h.addWidget(bar)
        v = QVBoxLayout()
        v.setContentsMargins(12, 12, 0, 12)
        v.setSpacing(2)
        v.addWidget(label(text, "Muted", wrap=True))
        v.addWidget(label(str(value), "StatValue"))
        h.addLayout(v, 1)


class BarChart(QWidget):
    """Biểu đồ cột ngang vẽ bằng QPainter (không cần thư viện ngoài)."""
    ROW_H = 30

    def __init__(self, items, color=None, parent=None):
        super().__init__(parent)
        self.items = items
        self.color = QColor(color or C["primary"])
        self.setMinimumHeight(max(1, len(items)) * self.ROW_H)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        if not self.items:
            p.setPen(QColor(C["muted"]))
            p.drawText(self.rect(), Qt.AlignCenter, "Chưa có dữ liệu")
            return
        label_w = min(220, int(w * 0.42))
        max_v = max(v for _l, v in self.items) or 1
        area = max(40, w - label_w - 50)
        fm = p.fontMetrics()
        for i, (text, val) in enumerate(self.items):
            y = i * self.ROW_H
            p.setPen(QColor(C["muted"]))
            p.drawText(0, y, label_w - 10, self.ROW_H, Qt.AlignRight | Qt.AlignVCenter,
                       fm.elidedText(str(text), Qt.ElideRight, label_w - 12))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["table_head"]))
            p.drawRoundedRect(label_w, y + 9, area, 12, 6, 6)
            p.setBrush(self.color)
            p.drawRoundedRect(label_w, y + 9, max(6, area * val / max_v), 12, 6, 6)
            p.setPen(QColor(C["text"]))
            p.drawText(label_w + area + 8, y, 40, self.ROW_H, Qt.AlignLeft | Qt.AlignVCenter, str(val))
