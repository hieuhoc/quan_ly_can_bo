# -*- coding: utf-8 -*-
"""Module: Quản lý thông tin cán bộ.

Đơn vị công tác chọn theo cơ cấu tổ chức (core/co_cau.py):
Công an tỉnh / thành phố -> Phòng hoặc Công an xã, phường -> Đội / Tổ (tự nhập).
"""
import csv
import datetime
import json
import re
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QGridLayout, QHBoxLayout, QLineEdit, QRadioButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from core import attachments, co_cau
from core import tham_so as ts
from ui.widgets import (DataTable, DateField, FilePicker, FormDialog, ListPage, ProvinceWardPicker, SearchDialog,
                        SuggestCombo, ask, button, choice, info, label, open_file_dialog, section,
                        text_edit, valid_date, warn)

MODULE_ID = "employees"
TABLE = "can_bo"
SEC_CONG_TAC = "Quá trình công tác"
SEC_HOC_TAP = "Quá trình học tập"

# Mỗi trường: (khóa_CSDL, nhãn, loại). Loại: text | gender | date | rank | position | salary |
# cccd | phone | province_ward (khóa là cặp cột tỉnh/xã) | ca_tinh | ca_donvi
SECTIONS = [
    ("Thông tin cá nhân", [
        ("ma_cb", "Mã cán bộ *", "text"),
        ("ho_ten", "Họ và tên *", "text"),
        ("ngay_sinh", "Ngày sinh", "date"),
        ("gioi_tinh", "Giới tính", "gender"),
        (("que_quan_tinh", "que_quan_xa"), "Quê quán", "province_ward"),
        ("noi_o_chi_tiet", "Nơi ở hiện tại (số nhà, đường/thôn)", "text"),
        (("noi_o_tinh", "noi_o_xa"), "Nơi ở hiện tại", "province_ward"),
        ("so_cccd", "Số CCCD (đủ 12 số)", "cccd"),
        ("sdt", "Số điện thoại", "phone"),
    ]),
    ("Chức vụ - Đơn vị", [
        ("cap_bac", "Cấp bậc", "rank"),
        ("chuc_vu", "Chức vụ", "position"),
        ("chuc_danh_hien_tai", "Chức danh hiện tại", "title"),
        # Đơn vị theo cơ cấu: Công an tỉnh -> Phòng / CA xã, phường -> Đội / Tổ
        ("cong_an_tinh", "Công an tỉnh / thành phố", "ca_tinh"),
        ("don_vi", "Phòng / Công an xã, phường", "ca_donvi"),
        ("doi_to", "Đội / Tổ", "text"),
        ("he_so_luong", "Hệ số lương", "salary"),
        # Ngoại lệ: hệ số khác bảng hệ số theo cấp bậc thì BẮT BUỘC ghi lý do.
        ("ly_do_he_so", "Lý do (hệ số khác quy định)", "text"),
    ]),
    (SEC_CONG_TAC, [
        ("ngay_vao_nganh", "Ngày vào ngành", "date"),
    ]),
    ("Ngày vào Đảng", [
        ("ngay_vao_dang", "Ngày vào Đảng", "date"),
        ("ngay_chuyen_dang_chinh_thuc", "Ngày chuyển Đảng chính thức", "date"),
    ]),
    ("Trình độ", [
        ("trinh_do_nghiep_vu", "Trình độ nghiệp vụ", "text"),
        ("trinh_do_chinh_tri", "Trình độ chính trị", "text"),
        ("trinh_do_ngoai_ngu", "Trình độ ngoại ngữ", "text"),
    ]),
    (SEC_HOC_TAP, []),
    ("Ghi chú", [
        ("ghi_chu", "Ghi chú", "text"),
    ]),
]


def _flatten(sections):
    out = []
    for title, fields in sections:
        flat = []
        for key, lbl, kind in fields:
            if kind == "province_ward":
                flat.append((key[0], f"{lbl} - Tỉnh/Thành phố", "text"))
                flat.append((key[1], f"{lbl} - Xã/Phường", "text"))
            else:
                flat.append((key, lbl, kind))
        out.append((title, flat))
    return out


SECTIONS_FLAT = _flatten(SECTIONS)
ALL_FIELDS = [f for _s, fs in SECTIONS_FLAT for f in fs]
LABELS = {k: lbl for k, lbl, _t in ALL_FIELDS}
DATE_FIELDS = [k for k, _l, t in ALL_FIELDS if t == "date"]
SHORT_LABELS = {"don_vi": "Phòng / CA xã, phường", "cong_an_tinh": "Công an tỉnh / TP"}


def col_label(key):
    return SHORT_LABELS.get(key) or LABELS[key].replace(" *", "").split(" (")[0]


COLUMNS_SHOW = ["ma_cb", "ho_ten", "ngay_sinh", "gioi_tinh", "cap_bac", "chuc_vu", "don_vi", "doi_to",
                "he_so_luong", "sdt", "so_cccd", "ngay_vao_nganh", "chuc_danh_hien_tai", "trinh_do_nghiep_vu",
                "trinh_do_chinh_tri", "trinh_do_ngoai_ngu", "ghi_chu"]
COLS = [(k, col_label(k), 90) for k in COLUMNS_SHOW]


def validate(data):
    """Trả về thông báo lỗi (chuỗi) hoặc None nếu dữ liệu hợp lệ."""
    if not data.get("ma_cb") or not data.get("ho_ten"):
        return "Vui lòng nhập Mã cán bộ và Họ tên."
    for k in DATE_FIELDS:
        if data.get(k) and not valid_date(data[k]):
            return f"{LABELS[k]} phải theo dạng dd/mm/yyyy."
    if data.get("sdt") and not re.fullmatch(r"[0-9 .+\-]{8,15}", data["sdt"]):
        return "Số điện thoại không hợp lệ."
    if data.get("so_cccd") and not re.fullmatch(r"\d{12}", data["so_cccd"]):
        return "Số CCCD phải gồm đúng 12 chữ số."
    why = he_so_ngoai_quy_dinh(data.get("cap_bac"), data.get("he_so_luong"))
    if why and not (data.get("ly_do_he_so") or "").strip():
        return f"{why}.\nVui lòng ghi rõ Lý do (hệ số khác quy định)."
    return None


def he_so_ngoai_quy_dinh(cap_bac, he_so):
    """Mô tả điểm khác bảng hệ số lương theo cấp bậc, hoặc None nếu khớp / không áp dụng."""
    chuan = ts.he_so_chuan(cap_bac or "")
    if not chuan or not he_so:
        return None
    try:
        if abs(float(str(he_so).replace(",", ".")) - float(chuan)) < 1e-9:
            return None
    except ValueError:
        return None
    return f"Hệ số lương {he_so} khác hệ số theo cấp bậc {cap_bac} ({chuan})"


PHOTO_DIR = "anh_the"


def photo_path(app_dir, rel):
    return attachments.full_path(app_dir, rel) if rel else None


def save_photo(app_dir, src):
    """Thu nhỏ ảnh (tối đa 450x600, giữ tỉ lệ), lưu JPG vào attachments/anh_the/."""
    import os
    import uuid
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QImage
    img = QImage(src)
    if img.isNull():
        return None
    img = img.scaled(450, 600, _Qt.KeepAspectRatio, _Qt.SmoothTransformation)
    folder = os.path.join(app_dir, attachments.ATTACH_DIR, PHOTO_DIR)
    os.makedirs(folder, exist_ok=True)
    rel = f"{attachments.ATTACH_DIR}/{PHOTO_DIR}/{uuid.uuid4().hex[:12]}.jpg"
    img.save(attachments.full_path(app_dir, rel), "JPG", 90)
    return rel


# ------------------------------------------------------------------ quá trình công tác / học tập
_QD = [("so_quyet_dinh", "Số quyết định", "text", False), ("ngay_ban_hanh", "Ngày ban hành", "date", False),
       ("nguoi_ky", "Người ký", "text", False)]
TIMELINES = {
    "cong_tac": dict(
        table="qua_trinh_cong_tac", noun="mốc công tác",
        fields=[("tu_ngay", "Từ ngày", "date", False),
                ("den_ngay", "Đến ngày (để trống nếu vẫn đang công tác)", "date", False),
                ("don_vi_cong_tac", "Đơn vị công tác", "text", True)] + _QD,
        cols=[("tu_ngay", "Từ ngày", 90), ("den_ngay", "Đến ngày", 90), ("don_vi_cong_tac", "Đơn vị công tác", 200),
              ("so_quyet_dinh", "Số QĐ", 100), ("ngay_ban_hanh", "Ngày ban hành", 100), ("nguoi_ky", "Người ký", 120)]),
    "hoc_tap": dict(
        table="qua_trinh_hoc_tap", noun="mốc học tập",
        fields=[("tu_ngay", "Từ ngày", "date", False),
                ("den_ngay", "Đến ngày (để trống nếu vẫn đang học)", "date", False),
                ("co_so_dao_tao", "Cơ sở đào tạo", "text", True),
                ("chuyen_nganh", "Chuyên ngành / nội dung học", "text", False),
                ("van_bang", "Văn bằng / chứng chỉ", "text", False)] + _QD,
        cols=[("tu_ngay", "Từ ngày", 90), ("den_ngay", "Đến ngày", 90), ("co_so_dao_tao", "Cơ sở đào tạo", 170),
              ("chuyen_nganh", "Chuyên ngành", 130), ("van_bang", "Văn bằng", 110), ("so_quyet_dinh", "Số QĐ", 100),
              ("ngay_ban_hanh", "Ngày ban hành", 100), ("nguoi_ky", "Người ký", 120)]),
}
SECTION_TIMELINE = {SEC_CONG_TAC: "cong_tac", SEC_HOC_TAP: "hoc_tap"}


def timeline_rows(db, kind, can_bo_id):
    cfg = TIMELINES[kind]
    keys = ",".join(["id"] + [f[0] for f in cfg["fields"]])
    rows = db.conn.execute(
        f"SELECT {keys} FROM {cfg['table']} WHERE can_bo_id=? ORDER BY (tu_ngay=='' OR tu_ngay IS NULL), "
        "substr(tu_ngay,7,4)||substr(tu_ngay,4,2)||substr(tu_ngay,1,2), id", (can_bo_id,)).fetchall()
    return [dict(r) for r in rows]


def _display(key, val):
    if key == "den_ngay":
        return val or "(hiện tại)"
    return val or "—"


class TimelineEntryDialog(FormDialog):
    def __init__(self, parent, kind, initial=None):
        cfg = TIMELINES[kind]
        super().__init__(parent, ("Sửa " if initial else "Thêm ") + cfg["noun"], 540, 140 + 52 * len(cfg["fields"]))
        self.cfg = cfg
        self.data = None
        f = self.form()
        self.widgets = {}
        for key, text, typ, required in cfg["fields"]:
            val = (initial or {}).get(key) or ""
            w = DateField(val) if typ == "date" else QLineEdit(val)
            f.addRow(text + (" *" if required else ""), w)
            self.widgets[key] = w
        self.body.addWidget(label("Các trường không có dấu * có thể để trống.", "Muted"))
        self.body.addStretch(1)
        self.add_buttons("💾  Lưu" if initial else "➕  Thêm", self.save)

    def save(self):
        data = {k: w.text().strip() for k, w in self.widgets.items()}
        for key, text, typ, required in self.cfg["fields"]:
            name = text.split(" (")[0]
            if required and not data[key]:
                warn(self, f"Vui lòng nhập {name}.", "Thiếu thông tin")
                return
            if typ == "date" and data[key] and not valid_date(data[key]):
                warn(self, f"{name} phải theo dạng dd/mm/yyyy.", "Sai định dạng")
                return
        self.data = data
        self.accept()


class TimelineWidget(QWidget):
    """Bảng quá trình kèm nút Thêm / Sửa / Xóa. Chưa có can_bo_id (đang tạo
    cán bộ mới) thì các mốc được giữ tạm, ghi xuống CSDL khi gọi flush_to_db()."""

    def __init__(self, db, kind, can_bo_id=None, readonly=False, rows_visible=4):
        super().__init__()
        self.db, self.kind, self.cfg = db, kind, TIMELINES[kind]
        self.can_bo_id = can_bo_id
        self.pending = []
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.table = DataTable(self.cfg["cols"], sortable=False)
        for key, *_x in self.cfg["cols"]:
            self.table.set_display(key, lambda val, r, k=key: _display(k, val))
        self.table.setMinimumHeight(46 + 36 * rows_visible)
        self.table.setMaximumHeight(46 + 36 * (rows_visible + 2))
        v.addWidget(self.table)
        if not readonly:
            h = QHBoxLayout()
            h.addWidget(button(f"➕  Thêm {self.cfg['noun']}", self._add))
            self.b_edit = button("✏  Sửa", self._edit)
            self.b_del = button("🗑  Xóa", self._delete)
            h.addWidget(self.b_edit)
            h.addWidget(self.b_del)
            h.addStretch(1)
            v.addLayout(h)
            self.table.activated_row.connect(self._edit)
        self.refresh()

    def refresh(self):
        if self.can_bo_id is not None:
            rows = timeline_rows(self.db, self.kind, self.can_bo_id)
        else:
            rows = [dict(d, id=i) for i, d in enumerate(self.pending)]
        self.table.set_rows(rows)

    def _add(self):
        d = TimelineEntryDialog(self, self.kind)
        if d.exec():
            if self.can_bo_id is not None:
                self.db.insert(self.cfg["table"], dict(d.data, can_bo_id=self.can_bo_id))
            else:
                self.pending.append(d.data)
            self.refresh()

    def _selected(self):
        row = self.table.selected_row()
        if row is None:
            info(self, f"Hãy chọn một {self.cfg['noun']}.", "Chưa chọn")
        return row

    def _edit(self):
        row = self._selected()
        if not row:
            return
        d = TimelineEntryDialog(self, self.kind, initial=row)
        if d.exec():
            if self.can_bo_id is not None:
                self.db.update(self.cfg["table"], row["id"], d.data, touch_updated=False)
            else:
                self.pending[row["id"]] = d.data
            self.refresh()

    def _delete(self):
        row = self._selected()
        if not row or not ask(self, f"Xóa {self.cfg['noun']} này?", yes="Xóa", danger=True):
            return
        if self.can_bo_id is not None:
            self.db.delete(self.cfg["table"], row["id"])
        else:
            self.pending.pop(row["id"])
        self.refresh()

    def flush_to_db(self, can_bo_id):
        for data in self.pending:
            self.db.insert(self.cfg["table"], dict(data, can_bo_id=can_bo_id))
        self.pending = []
        self.can_bo_id = can_bo_id


# ------------------------------------------------------------------ đơn vị theo cơ cấu
class UnitFields:
    """Ba ô chọn đơn vị liên kết với nhau: Công an tỉnh -> Phòng / CA xã, phường -> Đội / Tổ."""

    def __init__(self, db):
        self.db = db
        self.tinh = SuggestCombo(co_cau.danh_sach_cong_an_tinh(), editable=True)
        self.don_vi = SuggestCombo([], editable=True)
        self.don_vi.lineEdit().setPlaceholderText("Chọn phòng hoặc Công an xã, phường (gõ để tìm)")
        self.doi_to = QLineEdit()
        self.doi_to.setPlaceholderText("Tự nhập, vd: Đội Cảnh sát giao thông trật tự")
        self.tinh.currentTextChanged.connect(self._reload)
        self.tinh.setText(co_cau.tinh_mac_dinh(db))
        self._reload()

    def _reload(self, *_):
        self.don_vi.set_items(co_cau.danh_sach_don_vi(self.db, self.tinh.text()))


# ------------------------------------------------------------------ trang danh sách
class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Danh sách cán bộ", COLS, subtitle="Hồ sơ, đơn vị công tác và quá trình của cán bộ")
        self.add_action("➕  Thêm mới", self.open_add, "primary", perm="add")
        self.add_action("✏  Sửa", self.open_edit, perm="edit", needs_selection=True)
        self.add_action("🗑  Xóa", self.on_delete, "danger", perm="delete", needs_selection=True)
        self.add_action("📄  Hồ sơ chi tiết", self.show_profile, needs_selection=True)
        self.add_action("📥  Nhập Excel / CSV", self.import_file, perm="add", right=True)
        self.add_action("📊  Xuất Excel", self.export_xlsx, perm="export", right=True)
        self.add_action("🖨  In danh sách (PDF)", self.print_list, perm="export", right=True)
        self.add_action("🗂  Đã xóa / điều chuyển", self.show_deleted, right=True)
        self.table.activated_row.connect(self.show_profile)
        self.table.delete_pressed.connect(self.on_delete)
        self.refresh()

    def load_rows(self):
        f = self.adv_filters
        conds, params = [], []
        if f:
            for key in ("ma_cb", "ho_ten", "don_vi", "doi_to", "chuc_vu"):
                if f.get(key):
                    conds.append(f"{key} LIKE ?"); params.append(f"%{f[key]}%")
            for key in ("cong_an_tinh", "cap_bac", "gioi_tinh", "que_quan_tinh"):
                if f.get(key):
                    conds.append(f"{key} = ?"); params.append(f[key])
        elif self.search_text():
            keys = [k for k, _l, _t in ALL_FIELDS]
            conds.append("(" + " OR ".join(f"{k} LIKE ?" for k in keys) + ")")
            params.extend([f"%{self.search_text()}%"] * len(keys))
        sql = "SELECT * FROM can_bo" + (" WHERE " + " AND ".join(conds) if conds else "")
        return self.db.conn.execute(sql + " ORDER BY ho_ten COLLATE NOCASE", params).fetchall()

    def refresh(self):
        rows = self.load_rows()
        self.table.set_rows(rows)
        self.count_lbl.setText(f"Tổng số: {len(rows)} cán bộ")
        self.update_actions()

    def open_advanced(self):
        import core.dia_gioi_hanh_chinh as dgh
        SearchDialog(self, [
            ("ma_cb", "Mã cán bộ", QLineEdit()), ("ho_ten", "Họ và tên", QLineEdit()),
            ("cong_an_tinh", "Công an tỉnh / thành phố", choice([""] + co_cau.danh_sach_cong_an_tinh())),
            ("don_vi", "Phòng / Công an xã, phường", QLineEdit()), ("doi_to", "Đội / Tổ", QLineEdit()),
            ("cap_bac", "Cấp bậc", choice([""] + ts.cap_bac())), ("chuc_vu", "Chức vụ", QLineEdit()),
            ("gioi_tinh", "Giới tính", choice(["", "Nam", "Nữ"])),
            ("que_quan_tinh", "Quê quán - Tỉnh/Thành", choice([""] + dgh.danh_sach_tinh()))]).exec()

    def open_add(self):
        if not self.deny("add") and EmployeeDialog(self, None).exec():
            self.refresh()

    def open_edit(self):
        if self.deny("edit"):
            return
        row = self.need_selection("một cán bộ")
        if row and EmployeeDialog(self, self.db.fetch_one(TABLE, row["id"])).exec():
            self.refresh()

    def show_profile(self):
        row = self.need_selection("một cán bộ")
        if row:
            ProfileDialog(self, self.db.fetch_one(TABLE, row["id"])).exec()
            self.refresh()

    def on_delete(self):
        if self.deny("delete"):
            return
        row = self.need_selection("một cán bộ")
        if row and DeleteEmployeeDialog(self, self.db.fetch_one(TABLE, row["id"])).exec():
            self.refresh()

    def show_deleted(self):
        DeletedHistoryDialog(self).exec()

    # ---- Excel / CSV / PDF
    def export_xlsx(self):
        """Xuất Excel ĐẦY ĐỦ các trường - dùng được để sửa rồi nhập lại."""
        cols = [(k, LABELS[k].replace(" *", "")) for k, _l, _t in ALL_FIELDS]
        self.export_excel("Danh sách cán bộ", "danh_sach_can_bo", columns=cols, rows=self.table.rows())

    def print_list(self):
        """In danh sách trích ngang (PDF, khổ A4 ngang)."""
        cols = [("ho_ten", "Họ và tên"), ("ngay_sinh", "Ngày sinh"), ("cap_bac", "Cấp bậc"), ("chuc_vu", "Chức vụ"),
                ("don_vi_day_du", "Đơn vị"), ("he_so_luong", "Hệ số lương"), ("ngay_vao_nganh", "Vào ngành"),
                ("ngay_vao_dang", "Vào Đảng"), ("trinh_do_nghiep_vu", "Trình độ nghiệp vụ"),
                ("trinh_do_chinh_tri", "Lý luận chính trị")]
        rows = []
        for r in self.table.rows():
            d = dict(r)
            d["don_vi_day_du"] = ", ".join(x for x in (r.get("doi_to"), r.get("don_vi")) if x)
            rows.append(d)
        self.print_pdf("Danh sách trích ngang cán bộ", "danh_sach_trich_ngang", columns=cols, rows=rows)

    def _read_rows(self, path):
        if path.lower().endswith((".xlsx", ".xlsm")):
            from core import xlsx
            return xlsx.read_table(path)
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return [(n, row) for n, row in enumerate(csv.DictReader(f), start=2)]

    def import_file(self):
        """Nhập từ Excel hoặc CSV (tiêu đề cột như file xuất ra): chỉ ghi những
        cột CÓ trong file (không xóa trắng các trường khác của cán bộ đã có);
        cập nhật cán bộ đã có cần quyền Sửa; dòng sai bị bỏ qua và liệt kê lại."""
        if self.deny("add"):
            return
        path = open_file_dialog(self, "Chọn file Excel hoặc CSV",
                                "Excel / CSV (*.xlsx *.csv);;Tất cả file (*.*)")
        if not path:
            return
        keys = [k for k, _l, _t in ALL_FIELDS]
        label_to_key = {LABELS[k].replace(" *", ""): k for k in keys}
        label_to_key.setdefault("Đơn vị", "don_vi")
        can_edit = self.app.can(MODULE_ID, "edit")
        added = updated = skipped = 0
        errors = []
        try:
            for line_no, row in self._read_rows(path):
                data = {}
                for col, val in row.items():
                    key = label_to_key.get((col or "").strip().rstrip("*").strip())
                    if key:
                        data[key] = (val or "").strip()
                if not data:
                    continue
                existing = self.db.conn.execute("SELECT * FROM can_bo WHERE ma_cb=?",
                                                (data.get("ma_cb", ""),)).fetchone()
                merged = dict(existing) if existing else {}
                merged.update(data)
                problem = validate(merged)
                if problem:
                    skipped += 1
                    errors.append(f"Dòng {line_no}: {problem.splitlines()[0]}")
                    continue
                if existing:
                    if not can_edit:
                        skipped += 1
                        errors.append(f"Dòng {line_no}: mã {data['ma_cb']} đã có - cần quyền Sửa để cập nhật.")
                        continue
                    self.db.update(TABLE, existing["id"], data)
                    updated += 1
                else:
                    self.db.insert(TABLE, data)
                    added += 1
        except Exception as e:  # noqa
            warn(self, f"Không thể đọc file:\n{e}", "Lỗi đọc file")
            return
        self.db.log(self.app.user["username"], "Nhập file", f"Thêm mới {added}, cập nhật {updated}, bỏ qua {skipped}")
        self.refresh()
        msg = f"Đã thêm mới: {added}\nĐã cập nhật: {updated}\nBỏ qua: {skipped}"
        if errors:
            msg += "\n\nChi tiết dòng bị bỏ qua:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n... và {len(errors) - 10} dòng khác."
        info(self, msg, "Kết quả nhập file")


# ------------------------------------------------------------------ ảnh thẻ
class PhotoBox(QWidget):
    """Khung ảnh thẻ 3x4 + nút Chọn ảnh / Xóa ảnh (readonly: chỉ hiển thị)."""
    W, H = 113, 151

    def __init__(self, app_dir, rel=None, readonly=False):
        super().__init__()
        self.app_dir, self.rel = app_dir, rel
        self.pending = None      # đường dẫn ảnh mới chọn (chưa lưu)
        self.removed = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.img = label()
        self.img.setFixedSize(self.W, self.H)
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setStyleSheet("border: 1px dashed #C9CED6; border-radius: 6px; background: #F9FAFB; color: #9CA3AF;")
        v.addWidget(self.img, 0, Qt.AlignHCenter)
        if not readonly:
            h = QHBoxLayout()
            h.setSpacing(4)
            h.addWidget(button("Chọn ảnh", self._pick))
            h.addWidget(button("Xóa", self._remove))
            v.addLayout(h)
        self._show(photo_path(app_dir, rel))

    def _show(self, path):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(path) if path else QPixmap()
        if pm.isNull():
            self.img.setPixmap(QPixmap())
            self.img.setText("Ảnh thẻ\n3 x 4")
        else:
            self.img.setPixmap(pm.scaled(self.W, self.H, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _pick(self):
        path = open_file_dialog(self, "Chọn ảnh thẻ", "Ảnh (*.jpg *.jpeg *.png *.bmp)")
        if path:
            self.pending, self.removed = path, False
            self._show(path)

    def _remove(self):
        self.pending, self.removed = None, True
        self._show(None)

    def commit(self):
        """Lưu ảnh mới (nếu có) và trả về đường dẫn tương đối cần ghi vào CSDL."""
        if self.pending:
            new_rel = save_photo(self.app_dir, self.pending)
            if new_rel:
                if self.rel:
                    attachments.delete_attachment(self.app_dir, self.rel)
                self.rel, self.pending = new_rel, None
        elif self.removed and self.rel:
            attachments.delete_attachment(self.app_dir, self.rel)
            self.rel = None
        return self.rel


# ------------------------------------------------------------------ thêm / sửa cán bộ
class EmployeeDialog(FormDialog):
    def __init__(self, panel, row):
        super().__init__(panel, f"Sửa thông tin: {row['ho_ten']}" if row else "Thêm cán bộ mới", 820, 860)
        self.panel, self.db, self.row = panel, panel.db, row
        r = dict(row) if row else {}
        self.fields = {}      # khóa -> (widget, loại)
        self.pickers = {}     # (cột tỉnh, cột xã) -> ProvinceWardPicker
        self.timelines = {}
        self.unit = UnitFields(self.db)
        self.photo = PhotoBox(panel.app.app_dir, r.get("anh_the"))
        top = QHBoxLayout()
        top.addWidget(self.photo, 0, Qt.AlignTop)
        top.addSpacing(12)
        top.addWidget(label("Ảnh thẻ (không bắt buộc): chọn file ảnh chân dung, phần mềm tự thu nhỏ và lưu kèm "
                            "hồ sơ. Ảnh được in trên hồ sơ cán bộ.", "Muted", wrap=True), 1, Qt.AlignVCenter)
        self.body.addLayout(top)
        for title, fields in SECTIONS:
            f = self.add_section(title)
            for key, text, kind in fields:
                if kind == "province_ward":
                    w = ProvinceWardPicker()
                    w.set(r.get(key[0]), r.get(key[1]))
                    self.pickers[key] = w
                    f.addRow(text, w)
                    continue
                w = self._widget(key, kind, r.get(key))
                self.fields[key] = (w, kind)
                f.addRow(text, w)
            if title in SECTION_TIMELINE:
                kind = SECTION_TIMELINE[title]
                tl = TimelineWidget(self.db, kind, can_bo_id=r.get("id"))
                self.timelines[kind] = tl
                self.body.addWidget(tl)
        if not r:
            self.unit.tinh.setText(co_cau.tinh_mac_dinh(self.db))
        self.note_he_so = label("", "Note", wrap=True)
        self.body.insertWidget(self.body.indexOf(self.fields["ly_do_he_so"][0].parentWidget()) + 1, self.note_he_so)
        self.fields["ly_do_he_so"][0].setPlaceholderText("Bắt buộc khi hệ số lương khác bảng hệ số theo cấp bậc")
        self.fields["he_so_luong"][0].currentTextChanged.connect(self._check_he_so)
        self.fields["cap_bac"][0].currentTextChanged.connect(self._check_he_so)
        self._check_he_so()
        self.body.addStretch(1)
        self.add_buttons("💾  Lưu thay đổi" if row else "➕  Thêm mới", self.save)

    def _widget(self, key, kind, val):
        val = val or ""
        if kind == "date":
            return DateField(val)
        if kind == "gender":
            return choice(["", "Nam", "Nữ"], val)
        if kind == "rank":
            w = choice([""] + ts.cap_bac(), val)
            w.currentTextChanged.connect(self._on_rank)
            return w
        if kind == "position":
            return SuggestCombo(ts.get("chuc_vu_goi_y"), text=val)
        if kind == "salary":
            return SuggestCombo(ts.he_so_goi_y(), text=val)
        if kind == "title":
            return SuggestCombo(ts.get("chuc_danh_goi_y"), text=val)
        if kind == "ca_tinh":
            if val:
                self.unit.tinh.setText(val)
            return self.unit.tinh
        if kind == "ca_donvi":
            self.unit.don_vi.setText(val)
            return self.unit.don_vi
        if key == "doi_to":
            self.unit.doi_to.setText(val)
            return self.unit.doi_to
        e = QLineEdit(val)
        if kind == "cccd":
            e.setMaxLength(12)
        return e

    def _on_rank(self, text):
        coef = ts.he_so_chuan(text)
        if coef and "he_so_luong" in self.fields:
            self.fields["he_so_luong"][0].setText(coef)

    def _check_he_so(self, *_):
        why = he_so_ngoai_quy_dinh(self.fields["cap_bac"][0].currentText(), self.fields["he_so_luong"][0].text())
        self.note_he_so.setText(f"⚠ {why} - vui lòng ghi lý do." if why else "")
        self.note_he_so.setVisible(bool(why))

    def values(self):
        data = {}
        for key, (w, _kind) in self.fields.items():
            data[key] = (w.currentText() if hasattr(w, "currentText") and not hasattr(w, "text") else w.text()).strip()
        for (tc, xc), w in self.pickers.items():
            data[tc], data[xc] = w.get()
        return data

    def save(self):
        data = self.values()
        problem = validate(data)
        if problem:
            warn(self, problem, "Kiểm tra lại thông tin")
            return
        user = self.panel.app.user["username"]
        data["anh_the"] = self.photo.commit()
        try:
            if self.row is None:
                new_id = self.db.insert(TABLE, data)
                for tl in self.timelines.values():
                    tl.flush_to_db(new_id)
                self.db.log(user, "Thêm cán bộ", f"{data['ma_cb']} - {data['ho_ten']}")
                self.panel.app.set_status("Đã thêm cán bộ mới.")
            else:
                self.db.update(TABLE, self.row["id"], data)
                self.db.log(user, "Sửa cán bộ", f"{data['ma_cb']} - {data['ho_ten']}")
                self.panel.app.set_status("Đã cập nhật thông tin cán bộ.")
        except sqlite3.IntegrityError:
            warn(self, f"Mã cán bộ '{data['ma_cb']}' đã tồn tại.", "Trùng mã")
            return
        self.accept()


# ------------------------------------------------------------------ hồ sơ chi tiết
class ProfileDialog(FormDialog):
    def __init__(self, panel, row):
        super().__init__(panel, f"Hồ sơ cán bộ: {row['ho_ten']}", 860, 860)
        self.panel, self.app, self.row = panel, panel.app, row
        readonly = not self.app.can(MODULE_ID, "edit")
        head = QHBoxLayout()
        head.addWidget(PhotoBox(self.app.app_dir, row["anh_the"], readonly=True))
        head.addSpacing(14)
        who = QVBoxLayout()
        who.addWidget(label(row["ho_ten"], "PageTitle"))
        who.addWidget(label(f"Mã cán bộ: {row['ma_cb']}   •   {row['cap_bac'] or ''}   {row['chuc_vu'] or ''}", "Muted"))
        unit = ", ".join(x for x in (row["doi_to"], row["don_vi"], row["cong_an_tinh"]) if x)
        who.addWidget(label(unit or "(chưa có đơn vị)", "Muted", wrap=True))
        who.addStretch(1)
        head.addLayout(who, 1)
        self.body.addLayout(head)
        for title, fields in SECTIONS_FLAT:
            self.body.addWidget(section(title))
            if fields:
                gw = QWidget()
                g = QGridLayout(gw)
                g.setContentsMargins(0, 2, 0, 2)
                g.setHorizontalSpacing(18)
                g.setVerticalSpacing(6)
                for i, (key, text, _t) in enumerate(fields):
                    g.addWidget(label(text.replace(" *", ""), "Muted"), i // 2, (i % 2) * 2)
                    v = label(row[key] or "—", wrap=True)
                    v.setStyleSheet("font-weight: 600;")
                    v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    g.addWidget(v, i // 2, (i % 2) * 2 + 1)
                g.setColumnStretch(1, 1)
                g.setColumnStretch(3, 1)
                self.body.addWidget(gw)
            if title in SECTION_TIMELINE:
                self.body.addWidget(TimelineWidget(self.app.db, SECTION_TIMELINE[title], can_bo_id=row["id"],
                                                   readonly=readonly, rows_visible=3))
        self.body.addStretch(1)
        b = button("🖨  In hồ sơ (PDF)", self.export_pdf, "primary")
        b.setEnabled(self.app.can(MODULE_ID, "export"))
        self.footer.addWidget(b, 1)
        self.footer.addWidget(button("Đóng", self.accept), 1)

    def export_pdf(self):
        from core import report
        from ui import printing
        from ui.widgets import save_file_dialog
        sections = []
        for title, fields in SECTIONS_FLAT:
            item = [title, [(t.replace(" *", ""), self.row[k] or "") for k, t, _x in fields
                            if not (k == "ly_do_he_so" and not self.row[k])]]
            if title in SECTION_TIMELINE:
                kind = SECTION_TIMELINE[title]
                cfg = TIMELINES[kind]
                rows = [{k: _display(k, r.get(k)) for k, _l, _w in cfg["cols"]}
                        for r in timeline_rows(self.app.db, kind, self.row["id"])]
                item.append(([(k, lbl) for k, lbl, _w in cfg["cols"]], rows))
            sections.append(tuple(item))
        path = save_file_dialog(self, report.export_path(f"ho_so_{self.row['ma_cb']}.pdf"), "PDF (*.pdf)")
        if not path:
            return
        printing.profile_pdf(path, self.app.db, "Hồ sơ cán bộ", sections,
                             photo_path(self.app.app_dir, self.row["anh_the"]),
                             meta_lines=[f"{self.row['ho_ten']} - Mã cán bộ: {self.row['ma_cb']}"])
        self.app.db.log(self.app.user["username"], "In hồ sơ cán bộ", f"{self.row['ma_cb']} - {self.row['ho_ten']}")
        if ask(self, f"Đã lưu file:\n{path}\n\nMở file ngay?", "Đã xuất", yes="Mở file"):
            printing.open_pdf(path)


# ------------------------------------------------------------------ xóa kèm lý do
DEL_DIEU_CHUYEN = "Điều chuyển công tác đi"
DEL_KHAC = "Lý do khác"
DELETED_TABLE = "can_bo_da_xoa"


class DeleteEmployeeDialog(FormDialog):
    """Xóa cán bộ khỏi danh sách - BẮT BUỘC chọn lý do: điều chuyển công tác đi
    (nơi đến + quyết định) hoặc lý do khác (ghi rõ). Hồ sơ được lưu lại."""

    def __init__(self, panel, row):
        super().__init__(panel, f"Xóa cán bộ: {row['ho_ten']}", 600, 660)
        self.panel, self.db, self.row = panel, panel.db, row
        self.body.addWidget(label(f"Mã cán bộ: {row['ma_cb']}. Dữ liệu phân loại, nâng lương - thăng cấp của cán bộ "
                                  "cũng bị xóa theo. Thông tin hồ sơ được lưu lại cùng lý do xóa.", "Muted", wrap=True))
        self.body.addWidget(section("Lý do xóa *"))
        self.r_move = QRadioButton(DEL_DIEU_CHUYEN)
        self.r_other = QRadioButton(DEL_KHAC)
        self.r_move.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.r_move)
        grp.addButton(self.r_other)
        rr = QHBoxLayout()
        rr.addWidget(self.r_move)
        rr.addSpacing(20)
        rr.addWidget(self.r_other)
        rr.addStretch(1)
        self.body.addLayout(rr)

        self.stack = QStackedWidget()
        move = QWidget()
        from PySide6.QtWidgets import QFormLayout
        fm = QFormLayout(move)
        fm.setContentsMargins(0, 8, 0, 0)
        self.e_noi_den = QLineEdit()
        self.d_ngay = DateField()
        self.e_so = QLineEdit()
        self.d_bh = DateField()
        self.e_ky = QLineEdit()
        self.file = FilePicker()
        for text, w in (("Nơi chuyển đến *", self.e_noi_den), ("Ngày điều chuyển", self.d_ngay),
                        ("Số quyết định *", self.e_so), ("Ngày ban hành", self.d_bh), ("Người ký", self.e_ky),
                        ("File quyết định", self.file)):
            fm.addRow(text, w)
        other = QWidget()
        vo = QVBoxLayout(other)
        vo.setContentsMargins(0, 8, 0, 0)
        vo.addWidget(label("Ghi rõ lý do *"))
        self.t_reason = text_edit("", 110)
        vo.addWidget(self.t_reason)
        vo.addStretch(1)
        self.stack.addWidget(move)
        self.stack.addWidget(other)
        self.body.addWidget(self.stack)
        self.body.addStretch(1)
        self.r_move.toggled.connect(lambda on: self.stack.setCurrentIndex(0 if on else 1))
        self.add_buttons("🗑  Xóa khỏi danh sách", self.confirm, "danger")

    def confirm(self):
        rec = dict(ma_cb=self.row["ma_cb"], ho_ten=self.row["ho_ten"])
        if self.r_move.isChecked():
            rec["hinh_thuc"] = DEL_DIEU_CHUYEN
            if not self.e_noi_den.text().strip() or not self.e_so.text().strip():
                warn(self, "Vui lòng nhập Nơi chuyển đến và Số quyết định.", "Thiếu thông tin")
                return
            for name, w in (("Ngày điều chuyển", self.d_ngay), ("Ngày ban hành", self.d_bh)):
                if w.text() and not valid_date(w.text()):
                    warn(self, f"{name} phải theo dạng dd/mm/yyyy.", "Sai định dạng")
                    return
            rec.update(noi_den=self.e_noi_den.text().strip(), ngay_dieu_chuyen=self.d_ngay.text(),
                       so_quyet_dinh=self.e_so.text().strip(), ngay_ban_hanh=self.d_bh.text(),
                       nguoi_ky=self.e_ky.text().strip())
            detail = f"điều chuyển đến {rec['noi_den']} theo QĐ {rec['so_quyet_dinh']}"
        else:
            rec["hinh_thuc"] = DEL_KHAC
            reason = self.t_reason.toPlainText().strip()
            if not reason:
                warn(self, "Vui lòng ghi rõ lý do xóa.", "Thiếu thông tin")
                return
            rec["ly_do"] = reason
            detail = f"lý do: {reason}"
        if not ask(self, f"Xóa cán bộ '{self.row['ho_ten']}' khỏi danh sách ({detail})?", yes="Xóa", danger=True):
            return
        app = self.panel.app
        snapshot = dict(self.row)
        snapshot["qua_trinh_cong_tac"] = timeline_rows(self.db, "cong_tac", self.row["id"])
        snapshot["qua_trinh_hoc_tap"] = timeline_rows(self.db, "hoc_tap", self.row["id"])
        if rec["hinh_thuc"] == DEL_DIEU_CHUYEN and self.file.pending:
            rec["file_dinh_kem"] = attachments.save_attachment(app.app_dir, DELETED_TABLE, self.file.pending)
        rec.update(thoi_gian=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   nguoi_thuc_hien=app.user["username"], du_lieu=json.dumps(snapshot, ensure_ascii=False))
        self.db.insert(DELETED_TABLE, rec)
        # File đính kèm của các quyết định nâng lương - thăng cấp bị xóa theo cán bộ
        # (xóa dây chuyền trong CSDL) - dọn luôn file để không bỏ lại file rác.
        # Ảnh thẻ được giữ lại cùng bản lưu hồ sơ đã xóa.
        for tbl in ("qua_trinh_luong", "qua_trinh_chuc_danh"):
            for f in self.db.conn.execute(f"SELECT file_dinh_kem FROM {tbl} WHERE can_bo_id=? "
                                          "AND file_dinh_kem IS NOT NULL AND file_dinh_kem<>''", (self.row["id"],)):
                attachments.delete_attachment(app.app_dir, f["file_dinh_kem"])
        self.db.delete(TABLE, self.row["id"])
        self.db.log(app.user["username"], "Xóa cán bộ", f"{self.row['ma_cb']} - {self.row['ho_ten']} ({detail})")
        app.set_status("Đã xóa cán bộ khỏi danh sách.")
        self.accept()


class DeletedHistoryDialog(FormDialog):
    COLS = [("thoi_gian", "Thời gian xóa", 140), ("ma_cb", "Mã CB", 80), ("ho_ten", "Họ và tên", 160),
            ("hinh_thuc", "Lý do", 160), ("chi_tiet", "Nơi đến / Lý do cụ thể", 220), ("so_quyet_dinh", "Số QĐ", 100),
            ("ngay_ban_hanh", "Ngày ban hành", 100), ("nguoi_ky", "Người ký", 120), ("file", "File QĐ", 70),
            ("nguoi_thuc_hien", "Người xóa", 100)]

    def __init__(self, panel):
        super().__init__(panel, "Cán bộ đã xóa / điều chuyển đi", 1100, 600)
        self.app = panel.app
        self.table = DataTable(self.COLS)
        rows = []
        for r in self.app.db.conn.execute(f"SELECT * FROM {DELETED_TABLE} ORDER BY id DESC"):
            d = dict(r)
            d["chi_tiet"] = d["noi_den"] if d["hinh_thuc"] == DEL_DIEU_CHUYEN else d["ly_do"]
            d["file"] = "📎 Có" if d["file_dinh_kem"] else "—"
            rows.append(d)
        self.table.set_rows(rows)
        self.body.addWidget(self.table, 1)
        self.table.activated_row.connect(self.open_file)
        self.footer.addWidget(button("📎  Mở file quyết định", self.open_file))
        self.footer.addStretch(1)
        self.footer.addWidget(button("Đóng", self.accept, "primary"))

    def open_file(self):
        r = self.table.selected_row()
        if r and r["file_dinh_kem"] and not attachments.open_file(self.app.app_dir, r["file_dinh_kem"]):
            warn(self, "Không tìm thấy file quyết định.", "Không mở được file")
