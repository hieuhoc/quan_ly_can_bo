# -*- coding: utf-8 -*-
"""Module: Quản lý thông tin cán bộ."""
import csv
import datetime
import json
import os
import re
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import cand_data
from core.theme import C, center, make_card
from core.widgets import (DateEntry, DialogShell, FilterCombo, ProvinceWardPicker,
                          ScrollableFrame, RoundedButton, section_label, make_tree, fill_tree)

MODULE_ID = "employees"
TABLE = "can_bo"

SEC_CONG_TAC = "Quá trình công tác"
SEC_HOC_TAP = "Quá trình học tập"

# Mỗi trường: (khóa_CSDL, nhãn, loại)
# loại: text | gender | date | rank | position | salary | unit | province_ward
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
        ("chuc_danh_hien_tai", "Chức danh hiện tại", "text"),
        # Đơn vị ghi rõ theo 2 cấp: Đội/Tổ trước, rồi Phòng hoặc Công an
        # xã/phường (thay cho mục "Cấp đơn vị" chỉ ghi loại đơn vị trước đây).
        ("doi_to", "Đội / Tổ", "unit"),
        ("don_vi", "Phòng / Công an xã, phường", "unit"),
        ("he_so_luong", "Hệ số lương", "salary"),
    ]),
    # Ngày vào ngành thuộc phần Quá trình công tác; bảng các mốc công tác
    # được vẽ ngay dưới trường này (xem TIMELINES).
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


def _flatten_sections(sections):
    out = []
    for sec_title, fields in sections:
        flat = []
        for key, label, kind in fields:
            if kind == "province_ward":
                tinh_col, xa_col = key
                flat.append((tinh_col, f"{label} - Tỉnh/Thành phố", "text"))
                flat.append((xa_col, f"{label} - Xã/Phường", "text"))
            else:
                flat.append((key, label, kind))
        out.append((sec_title, flat))
    return out


SECTIONS_FLAT = _flatten_sections(SECTIONS)
ALL_FIELDS = [f for _sec, fields in SECTIONS_FLAT for f in fields]
LABELS = {k: lbl for k, lbl, _t in ALL_FIELDS}
DATE_FIELDS = [k for k, _l, t in ALL_FIELDS if t == "date"]

# Nhãn ngắn cho tiêu đề cột bảng (nhãn đầy đủ quá dài)
SHORT_LABELS = {"don_vi": "Phòng / Xã, phường"}


def col_label(key):
    return SHORT_LABELS.get(key) or LABELS[key].replace(" *", "").split(" (")[0]


COLUMNS_SHOW = ["ma_cb", "ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "sdt",
                "cap_bac", "chuc_vu", "chuc_danh_hien_tai", "doi_to", "don_vi", "he_so_luong",
                "ngay_vao_nganh", "trinh_do_nghiep_vu", "trinh_do_chinh_tri", "trinh_do_ngoai_ngu", "ghi_chu"]
COL_WIDTH = {"ma_cb": 82, "ho_ten": 150, "ngay_sinh": 88, "gioi_tinh": 62, "so_cccd": 100, "sdt": 100,
             "cap_bac": 110, "chuc_vu": 120, "chuc_danh_hien_tai": 130, "doi_to": 130, "don_vi": 150,
             "he_so_luong": 80, "ngay_vao_nganh": 92, "trinh_do_nghiep_vu": 130, "trinh_do_chinh_tri": 110,
             "trinh_do_ngoai_ngu": 110, "ghi_chu": 160}


def _validate(data):
    """Kiểm tra dữ liệu form - dùng chung cho cả hộp thoại Thêm và Sửa."""
    if not data["ma_cb"] or not data["ho_ten"]:
        messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Mã cán bộ và Họ tên.")
        return False
    for k in DATE_FIELDS:
        if data[k]:
            try:
                datetime.datetime.strptime(data[k], "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Sai định dạng", f"{LABELS[k]} phải theo dạng dd/mm/yyyy.")
                return False
    if data["sdt"] and not re.fullmatch(r"[0-9 .+\-]{8,15}", data["sdt"]):
        messagebox.showwarning("Sai định dạng", "Số điện thoại không hợp lệ.")
        return False
    if data["so_cccd"] and not re.fullmatch(r"\d{12}", data["so_cccd"]):
        messagebox.showwarning("Sai định dạng", "Số CCCD phải gồm đúng 12 chữ số.")
        return False
    return True


def _distinct_values(db, col):
    """Các giá trị đã nhập của một cột (vd các Đội/Tổ) để gợi ý khi gõ."""
    rows = db.conn.execute(f"SELECT DISTINCT {col} AS v FROM can_bo WHERE {col} IS NOT NULL AND {col}<>'' "
                           "ORDER BY v COLLATE NOCASE").fetchall()
    return [r["v"] for r in rows]


def _build_form_fields(body, vars_, compound_widgets, on_rank_change, db=None, after_section=None):
    """Dựng các trường theo SECTIONS vào `body` (thân hộp thoại hoặc form).
    vars_: dict khóa CSDL đơn -> StringVar. compound_widgets: dict điền vào,
    (cột_tỉnh, cột_xã) -> ProvinceWardPicker. after_section: dict tên mục ->
    hàm(body) vẽ thêm nội dung ngay sau các trường của mục đó (vd bảng quá
    trình công tác). Trả về dict khóa -> (widget, kind)."""
    widgets = {}
    after_section = after_section or {}
    for title, fields in SECTIONS:
        section_label(body, title).pack(fill="x", pady=(10, 0))
        grid = ttk.Frame(body, style="Card.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        if title in after_section:
            extra = ttk.Frame(body, style="Card.TFrame")
            extra.pack(fill="x", pady=(4, 0))
            after_section[title](extra)
        for i, (key, label, kind) in enumerate(fields):
            if kind == "province_ward":
                ttk.Label(grid, text=label, style="Card.TLabel").grid(
                    row=i, column=0, sticky="w", pady=4, padx=(0, 10))
                w = ProvinceWardPicker(grid, width_tinh=12, width_xa=15)
                w.grid(row=i, column=1, pady=4, sticky="ew")
                compound_widgets[key] = w
                continue
            ttk.Label(grid, text=label, style="Card.TLabel").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if kind == "gender":
                w = ttk.Combobox(grid, textvariable=vars_[key], values=["Nam", "Nữ"], state="readonly", width=25)
            elif kind == "date":
                w = DateEntry(grid, textvariable=vars_[key], width=20)
            elif kind == "rank":
                w = ttk.Combobox(grid, textvariable=vars_[key], values=cand_data.CAP_BAC, state="readonly", width=25)
                w.bind("<<ComboboxSelected>>", on_rank_change)
            elif kind == "position":
                w = FilterCombo(grid, values=cand_data.CHUC_VU_PHO_BIEN, width=25, textvariable=vars_[key])
            elif kind == "salary":
                w = FilterCombo(grid, values=cand_data.HE_SO_LUONG_HOP_LE, width=25, textvariable=vars_[key])
            elif kind == "unit":
                w = FilterCombo(grid, values=_distinct_values(db, key) if db else [], width=25,
                                textvariable=vars_[key])
            else:
                w = ttk.Entry(grid, textvariable=vars_[key], width=28)
            w.grid(row=i, column=1, pady=4, sticky="ew")
            widgets[key] = (w, kind)
    return widgets


# Các bảng "quá trình" gắn với một cán bộ. Mỗi trường: (khóa, nhãn, loại,
# bắt buộc). Số quyết định / ngày ban hành / người ký đều KHÔNG bắt buộc.
_QD_FIELDS = [("so_quyet_dinh", "Số quyết định", "text", False),
              ("ngay_ban_hanh", "Ngày ban hành", "date", False),
              ("nguoi_ky", "Người ký", "text", False)]
TIMELINES = {
    "cong_tac": dict(
        table="qua_trinh_cong_tac", title=SEC_CONG_TAC, noun="mốc công tác", main="don_vi_cong_tac",
        fields=[("tu_ngay", "Từ ngày", "date", False),
                ("den_ngay", "Đến ngày\n(để trống nếu vẫn đang công tác)", "date", False),
                ("don_vi_cong_tac", "Đơn vị công tác", "text", True)] + _QD_FIELDS,
        cols=[("tu_ngay", "Từ ngày", 90), ("den_ngay", "Đến ngày", 90), ("don_vi_cong_tac", "Đơn vị công tác", 200),
              ("so_quyet_dinh", "Số QĐ", 100), ("ngay_ban_hanh", "Ngày ban hành", 100), ("nguoi_ky", "Người ký", 120)]),
    "hoc_tap": dict(
        table="qua_trinh_hoc_tap", title=SEC_HOC_TAP, noun="mốc học tập", main="co_so_dao_tao",
        fields=[("tu_ngay", "Từ ngày", "date", False),
                ("den_ngay", "Đến ngày\n(để trống nếu vẫn đang học)", "date", False),
                ("co_so_dao_tao", "Cơ sở đào tạo", "text", True),
                ("chuyen_nganh", "Chuyên ngành / nội dung học", "text", False),
                ("van_bang", "Văn bằng / chứng chỉ", "text", False)] + _QD_FIELDS,
        cols=[("tu_ngay", "Từ ngày", 90), ("den_ngay", "Đến ngày", 90), ("co_so_dao_tao", "Cơ sở đào tạo", 170),
              ("chuyen_nganh", "Chuyên ngành", 130), ("van_bang", "Văn bằng", 110),
              ("so_quyet_dinh", "Số QĐ", 100), ("ngay_ban_hanh", "Ngày ban hành", 100), ("nguoi_ky", "Người ký", 120)]),
}


def timeline_rows(db, kind, can_bo_id):
    """Các mốc của một cán bộ, sắp theo Từ ngày (đúng thứ tự thời gian)."""
    cfg = TIMELINES[kind]
    keys = ",".join(["id"] + [f[0] for f in cfg["fields"]])
    rows = db.conn.execute(
        f"SELECT {keys} FROM {cfg['table']} WHERE can_bo_id=? "
        "ORDER BY (tu_ngay=='' OR tu_ngay IS NULL), "
        "substr(tu_ngay,7,4)||substr(tu_ngay,4,2)||substr(tu_ngay,1,2), id", (can_bo_id,)).fetchall()
    return [dict(r) for r in rows]


def _display(key, val):
    if key == "den_ngay":
        return val or "(hiện tại)"
    return val or "—"


class TimelineEntryDialog(tk.Toplevel):
    """Popup thêm / sửa một mốc quá trình công tác hoặc học tập."""

    def __init__(self, parent_widget, kind, on_save, initial=None):
        super().__init__(parent_widget.winfo_toplevel())
        self.cfg = TIMELINES[kind]
        self.on_save = on_save
        n = len(self.cfg["fields"])
        height = 170 + 50 * n
        verb = "Sửa" if initial else "Thêm"
        shell = DialogShell(self, f"{verb} {self.cfg['noun']}", width=480, height=height, min_height=300)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.vars = {}
        for r, (key, label, typ, required) in enumerate(self.cfg["fields"]):
            v = tk.StringVar(value=(initial or {}).get(key) or "")
            self.vars[key] = v
            ttk.Label(form, text=label + (" *" if required else ""), style="Card.TLabel").grid(
                row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            w = DateEntry(form, textvariable=v, width=18) if typ == "date" else \
                ttk.Entry(form, textvariable=v, width=24)
            w.grid(row=r, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Các trường không có dấu * có thể để trống.", style="CardMuted.TLabel").grid(
            row=n, column=0, columnspan=2, sticky="w", pady=(6, 0))

        RoundedButton(shell.footer, text="💾  Lưu" if initial else "➕  Thêm", command=self.save,
                      variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)
        center(self, 480, height)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        for key, label, typ, required in self.cfg["fields"]:
            name = label.split("\n")[0]
            if required and not data[key]:
                messagebox.showwarning("Thiếu thông tin", f"Vui lòng nhập {name}.", parent=self)
                return
            if typ == "date" and data[key]:
                try:
                    datetime.datetime.strptime(data[key], "%d/%m/%Y")
                except ValueError:
                    messagebox.showwarning("Sai định dạng", f"{name} phải theo dạng dd/mm/yyyy.", parent=self)
                    return
        self.on_save(data)
        self.destroy()


class TimelineSection(ttk.Frame):
    """Bảng quá trình (công tác / học tập) kèm nút Thêm / Sửa / Xóa mốc.
    Nếu can_bo_id=None (đang tạo cán bộ mới, chưa có id), các mốc được giữ
    tạm trong bộ nhớ - gọi flush_to_db(id_mới) ngay sau khi cán bộ được tạo
    xong. Nếu đã có can_bo_id, mọi thao tác ghi thẳng xuống CSDL.
    readonly=True: chỉ xem (tài khoản không có quyền Sửa cán bộ)."""

    def __init__(self, parent, db, kind, can_bo_id=None, height=4, readonly=False):
        super().__init__(parent, style="Card.TFrame")
        self.db, self.kind, self.cfg = db, kind, TIMELINES[kind]
        self.can_bo_id = can_bo_id
        self.pending = []
        self.tree, wrap = make_tree(self, self.cfg["cols"], sortable=False)
        self.tree.configure(height=height)
        wrap.pack(fill="x")
        if not readonly:
            btn_row = ttk.Frame(self, style="Card.TFrame")
            btn_row.pack(fill="x", pady=(6, 0))
            RoundedButton(btn_row, text=f"➕  Thêm {self.cfg['noun']}", command=self._add,
                          variant="secondary").pack(side="left")
            RoundedButton(btn_row, text="✏  Sửa", command=self._edit, variant="secondary").pack(
                side="left", padx=(6, 0))
            RoundedButton(btn_row, text="🗑  Xóa", command=self._delete, variant="secondary").pack(
                side="left", padx=(6, 0))
            self.tree.bind("<Double-1>", lambda e: self._edit())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self._load_rows()):
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=[_display(k, r.get(k)) for k, _l, _w in self.cfg["cols"]],
                             tags=("odd" if i % 2 else "even",))

    def _load_rows(self):
        if self.can_bo_id is not None:
            return timeline_rows(self.db, self.kind, self.can_bo_id)
        return [dict(d, id=i) for i, d in enumerate(self.pending)]

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Chưa chọn", f"Hãy chọn một {self.cfg['noun']}.", parent=self.winfo_toplevel())
            return None
        return int(sel[0])

    def _add(self):
        def on_save(data):
            if self.can_bo_id is not None:
                self.db.insert(self.cfg["table"], dict(data, can_bo_id=self.can_bo_id))
            else:
                self.pending.append(data)
            self.refresh()
        TimelineEntryDialog(self, self.kind, on_save)

    def _edit(self):
        idx = self._selected()
        if idx is None:
            return
        if self.can_bo_id is not None:
            row = self.db.fetch_one(self.cfg["table"], idx)
            initial = dict(row) if row else None
        else:
            initial = self.pending[idx] if 0 <= idx < len(self.pending) else None
        if not initial:
            return

        def on_save(data):
            if self.can_bo_id is not None:
                self.db.update(self.cfg["table"], idx, data, touch_updated=False)
            else:
                self.pending[idx] = data
            self.refresh()
        TimelineEntryDialog(self, self.kind, on_save, initial=initial)

    def _delete(self):
        idx = self._selected()
        if idx is None:
            return
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa {self.cfg['noun']} này?", parent=self.winfo_toplevel()):
            return
        if self.can_bo_id is not None:
            self.db.delete(self.cfg["table"], idx)
        elif 0 <= idx < len(self.pending):
            self.pending.pop(idx)
        self.refresh()

    def flush_to_db(self, can_bo_id):
        """Ghi các mốc đang chờ (khi tạo cán bộ mới) xuống CSDL sau khi đã có id."""
        for data in self.pending:
            self.db.insert(self.cfg["table"], dict(data, can_bo_id=can_bo_id))
        self.pending = []
        self.can_bo_id = can_bo_id


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.selected_id = None
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.adv_filters = {}
        self.adv_note = tk.StringVar()
        self._build()
        self.apply_permissions()
        self.refresh()

    def _build(self):
        lo, card = make_card(self, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Danh sách cán bộ", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.count_var, style="CardMuted.TLabel").pack(side="right")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="🔍", style="Card.TLabel").pack(side="left")
        self.e_search = ttk.Entry(bar, textvariable=self.search_var)
        self.e_search.pack(side="left", fill="x", expand=True, padx=8)
        RoundedButton(bar, text="Xóa lọc", command=lambda: self.search_var.set(""), variant="secondary").pack(side="left")
        RoundedButton(bar, text="🔎  Tìm nâng cao", command=self.open_advanced_search, variant="secondary").pack(side="left", padx=(6, 0))
        self.search_var.trace_add("write", self._on_simple_search_typed)

        note_row = ttk.Frame(card, style="Card.TFrame")
        note_row.pack(fill="x", pady=(0, 8))
        ttk.Label(note_row, textvariable=self.adv_note, style="Error.TLabel").pack(side="left")

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.btn_add = RoundedButton(toolbar, text="➕  Thêm mới", command=self.open_add, variant="primary")
        self.btn_edit = RoundedButton(toolbar, text="✏  Sửa", command=self.open_edit, variant="secondary")
        self.btn_del = RoundedButton(toolbar, text="🗑  Xóa", command=self.on_delete, variant="danger")
        self.btn_profile = RoundedButton(toolbar, text="📄  Hồ sơ chi tiết", command=self.show_profile, variant="secondary")
        self.btn_import = RoundedButton(toolbar, text="📥  Nhập từ CSV", command=self.import_csv, variant="secondary")
        self.btn_export = RoundedButton(toolbar, text="📤  Xuất CSV", command=self.export_csv, variant="secondary")
        self.btn_print_list = RoundedButton(toolbar, text="🖨  In danh sách", command=self.print_list, variant="secondary")
        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_profile,
                 self.btn_import, self.btn_export, self.btn_print_list):
            b.pack(side="left", padx=(0, 6))
        RoundedButton(toolbar, text="🗂  Đã xóa / điều chuyển", command=self.show_deleted,
                      variant="secondary").pack(side="right")

        cols = [(k, col_label(k), COL_WIDTH[k]) for k in COLUMNS_SHOW]
        self.tree, wrap = make_tree(card, cols)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.on_delete())
        self.tree.bind("<Double-1>", lambda e: self.open_edit())

    # ---- quyền + trạng thái nút (theo quyền VÀ theo đã chọn dòng hay chưa)
    def apply_permissions(self):
        self._refresh_button_states()

    def _refresh_button_states(self):
        has_sel = self.selected_id is not None

        def st(btn, ok):
            btn.state(["!disabled"] if ok else ["disabled"])

        st(self.btn_add, self.app.can(MODULE_ID, "add"))
        st(self.btn_edit, self.app.can(MODULE_ID, "edit") and has_sel)
        st(self.btn_del, self.app.can(MODULE_ID, "delete") and has_sel)
        st(self.btn_profile, has_sel)
        st(self.btn_import, self.app.can(MODULE_ID, "add"))
        st(self.btn_export, self.app.can(MODULE_ID, "export"))
        st(self.btn_print_list, self.app.can(MODULE_ID, "export"))

    def deny(self, action):
        if self.app.can(MODULE_ID, action):
            return False
        from core.registry import ACTION_LABEL
        messagebox.showwarning("Không đủ quyền", f"Tài khoản của bạn không có quyền «{ACTION_LABEL[action]}».")
        return True

    # ---- tìm kiếm
    def _on_simple_search_typed(self, *_a):
        if self.adv_filters:
            self.adv_filters = {}
            self.adv_note.set("")
        self.refresh()

    def open_advanced_search(self):
        AdvancedSearchDialog(self)

    def apply_advanced(self, filters):
        # Xóa ô tìm kiếm thường TRƯỚC: lệnh này kích hoạt _on_simple_search_typed,
        # vốn xóa bộ lọc nâng cao - nếu gọi sau thì bộ lọc vừa áp bị mất ngay.
        self.search_var.set("")
        self.adv_filters = filters
        n = len(filters)
        self.adv_note.set(f"Đang áp dụng tìm kiếm nâng cao ({n} tiêu chí) — gõ vào ô tìm kiếm thường để bỏ lọc này.")
        self.refresh()

    def _advanced_rows(self):
        conds, params = [], []
        f = self.adv_filters
        if f.get("ma_cb"):
            conds.append("ma_cb LIKE ?"); params.append(f"%{f['ma_cb']}%")
        if f.get("ho_ten"):
            conds.append("ho_ten LIKE ?"); params.append(f"%{f['ho_ten']}%")
        if f.get("don_vi"):
            conds.append("don_vi LIKE ?"); params.append(f"%{f['don_vi']}%")
        if f.get("cap_bac"):
            conds.append("cap_bac = ?"); params.append(f["cap_bac"])
        if f.get("doi_to"):
            conds.append("doi_to LIKE ?"); params.append(f"%{f['doi_to']}%")
        if f.get("chuc_vu"):
            conds.append("chuc_vu LIKE ?"); params.append(f"%{f['chuc_vu']}%")
        if f.get("gioi_tinh"):
            conds.append("gioi_tinh = ?"); params.append(f["gioi_tinh"])
        if f.get("que_quan_tinh"):
            conds.append("que_quan_tinh = ?"); params.append(f["que_quan_tinh"])
        sql = "SELECT * FROM can_bo"
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY ho_ten COLLATE NOCASE"
        return self.db.conn.execute(sql, params).fetchall()

    # ---- dữ liệu
    def refresh(self):
        if self.adv_filters:
            rows = self._advanced_rows()
        else:
            keys = [k for k, _l, _t in ALL_FIELDS]
            rows = self.db.fetch_all(TABLE, "ho_ten COLLATE NOCASE", self.search_var.get().strip(), keys)
        fill_tree(self.tree, rows, COLUMNS_SHOW)
        self.count_var.set(f"Tổng số: {len(rows)} cán bộ")

    def on_select(self, _=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        self._refresh_button_states()

    def open_add(self):
        if self.deny("add"):
            return
        EmployeeFormDialog(self, row=None)

    def open_edit(self):
        if self.deny("edit"):
            return
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một cán bộ trong danh sách để sửa.")
            return
        row = self.db.fetch_one(TABLE, self.selected_id)
        if row:
            EmployeeFormDialog(self, row=row)

    def on_delete(self):
        if self.deny("delete"):
            return
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một cán bộ trong danh sách để xóa.")
            return
        row = self.db.fetch_one(TABLE, self.selected_id)
        if row:
            DeleteEmployeeDialog(self, row)

    def after_delete(self):
        self.selected_id = None
        self.refresh()
        self._refresh_button_states()

    def show_deleted(self):
        DeletedHistoryDialog(self.app)

    def export_csv(self):
        if self.deny("export"):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=datetime.datetime.now().strftime("danh_sach_can_bo_%Y%m%d.csv"))
        if not path:
            return
        keys = [k for k, _l, _t in ALL_FIELDS]
        rows = self._advanced_rows() if self.adv_filters else \
            self.db.fetch_all(TABLE, "ho_ten COLLATE NOCASE", self.search_var.get().strip(), keys)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([LABELS[k].replace(" *", "") for k in keys])
            for r in rows:
                w.writerow([r[k] or "" for k in keys])
        self.db.log(self.app.user["username"], "Xuất CSV", f"{len(rows)} bản ghi (cán bộ)")
        messagebox.showinfo("Xuất CSV", f"Đã xuất file:\n{path}")

    def import_csv(self):
        if self.deny("add"):
            return
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Tất cả file", "*.*")])
        if not path:
            return
        keys = [k for k, _l, _t in ALL_FIELDS]
        label_to_key = {LABELS[k].replace(" *", ""): k for k in keys}
        label_to_key.setdefault("Đơn vị", "don_vi")  # tiêu đề cột của file CSV xuất từ bản cũ
        added = updated = skipped = 0
        errors = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for line_no, row in enumerate(reader, start=2):
                    data = {}
                    for col_name, val in row.items():
                        key = label_to_key.get((col_name or "").strip())
                        if key:
                            data[key] = (val or "").strip()
                    for k in keys:
                        data.setdefault(k, "")
                    if not data.get("ma_cb") or not data.get("ho_ten"):
                        skipped += 1
                        errors.append(f"Dòng {line_no}: thiếu Mã cán bộ hoặc Họ tên.")
                        continue
                    existing = self.db.conn.execute(
                        "SELECT id FROM can_bo WHERE ma_cb=?", (data["ma_cb"],)).fetchone()
                    if existing:
                        self.db.update(TABLE, existing["id"], data)
                        updated += 1
                    else:
                        self.db.insert(TABLE, data)
                        added += 1
        except Exception as e:  # noqa
            messagebox.showerror("Lỗi đọc file", f"Không thể đọc file CSV:\n{e}")
            return
        self.db.log(self.app.user["username"], "Nhập CSV",
                    f"Thêm mới {added}, cập nhật {updated}, bỏ qua {skipped}")
        self.refresh()
        msg = f"Đã thêm mới: {added}\nĐã cập nhật: {updated}\nBỏ qua (thiếu dữ liệu): {skipped}"
        if errors:
            msg += "\n\nChi tiết dòng bị bỏ qua:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += f"\n... và {len(errors) - 10} dòng khác."
        messagebox.showinfo("Kết quả nhập file", msg)

    def show_profile(self):
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một cán bộ trong danh sách để xem hồ sơ.")
            return
        row = self.db.fetch_one(TABLE, self.selected_id)
        if row:
            ProfileDialog(self.app, row)

    def print_list(self):
        if self.deny("export"):
            return
        import core.report as report
        keys = [k for k, _l, _t in ALL_FIELDS]
        rows = self._advanced_rows() if self.adv_filters else \
            self.db.fetch_all(TABLE, "ho_ten COLLATE NOCASE", self.search_var.get().strip(), keys)
        columns = [(k, col_label(k)) for k in COLUMNS_SHOW]
        meta = [f"Người xuất: {self.app.user['ho_ten'] or self.app.user['username']}",
               f"Số lượng: {len(rows)} cán bộ"]
        html_str = report.build_list_html("Danh sách cán bộ", meta, columns, rows)
        report.open_html(html_str, "danh_sach_can_bo.html")
        self.db.log(self.app.user["username"], "In danh sách", f"{len(rows)} cán bộ")


DEL_DIEU_CHUYEN = "Điều chuyển công tác đi"
DEL_KHAC = "Lý do khác"
DELETED_TABLE = "can_bo_da_xoa"


class DeleteEmployeeDialog(tk.Toplevel):
    """Xóa cán bộ khỏi danh sách - BẮT BUỘC chọn lý do:
    - Điều chuyển công tác đi: nhập nơi chuyển đến và quyết định điều động
      (số QĐ, ngày ban hành, người ký, file QĐ nếu có);
    - Lý do khác: bắt buộc ghi rõ lý do.
    Hồ sơ (kèm quá trình công tác, học tập) được lưu lại vào bảng
    can_bo_da_xoa trước khi xóa, xem lại ở nút "Đã xóa / điều chuyển"."""

    def __init__(self, panel, row):
        super().__init__(panel.app)
        self.panel, self.db, self.row = panel, panel.db, row
        self.pending_file = None
        shell = DialogShell(self, f"Xóa cán bộ: {row['ho_ten']}", width=560, height=640, min_height=460)
        form = shell.body
        form.columnconfigure(1, weight=1)

        ttk.Label(form, style="CardMuted.TLabel", wraplength=480, justify="left",
                  text=f"Mã cán bộ: {row['ma_cb']}. Các dữ liệu phân loại, nâng lương - thăng cấp của cán bộ "
                       "cũng bị xóa theo. Thông tin hồ sơ được lưu lại cùng lý do xóa.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(form, text="Lý do xóa *", style="Section.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")
        self.v_kind = tk.StringVar(value=DEL_DIEU_CHUYEN)
        for r, val in enumerate((DEL_DIEU_CHUYEN, DEL_KHAC), start=2):
            ttk.Radiobutton(form, text=val, value=val, variable=self.v_kind, style="Card.TRadiobutton",
                            command=self._switch).grid(row=r, column=0, columnspan=2, sticky="w", pady=2)

        self.box_move = ttk.Frame(form, style="Card.TFrame")
        self.box_move.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.box_move.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar() for k in ("noi_den", "ngay_dieu_chuyen", "so_quyet_dinh",
                                               "ngay_ban_hanh", "nguoi_ky")}
        fields = [("noi_den", "Nơi chuyển đến *", "text"), ("ngay_dieu_chuyen", "Ngày điều chuyển", "date"),
                  ("so_quyet_dinh", "Số quyết định *", "text"), ("ngay_ban_hanh", "Ngày ban hành", "date"),
                  ("nguoi_ky", "Người ký", "text")]
        for r, (key, label, typ) in enumerate(fields):
            ttk.Label(self.box_move, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w",
                                                                          pady=5, padx=(0, 10))
            w = DateEntry(self.box_move, textvariable=self.v[key], width=18) if typ == "date" else \
                ttk.Entry(self.box_move, textvariable=self.v[key], width=26)
            w.grid(row=r, column=1, sticky="ew", pady=5)
        ttk.Label(self.box_move, text="File quyết định", style="Card.TLabel").grid(
            row=len(fields), column=0, sticky="w", pady=5, padx=(0, 10))
        file_row = ttk.Frame(self.box_move, style="Card.TFrame")
        file_row.grid(row=len(fields), column=1, sticky="ew", pady=5)
        self.v_filename = tk.StringVar(value="(chưa có file)")
        ttk.Label(file_row, textvariable=self.v_filename, style="CardMuted.TLabel", wraplength=200).pack(side="left")
        RoundedButton(file_row, text="📎  Chọn file...", command=self._pick_file, variant="secondary").pack(
            side="left", padx=(8, 0))

        self.box_other = ttk.Frame(form, style="Card.TFrame")
        self.box_other.columnconfigure(0, weight=1)
        ttk.Label(self.box_other, text="Ghi rõ lý do *", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        self.txt_reason = tk.Text(self.box_other, height=5, width=40, font=("Segoe UI", 10), wrap="word",
                                  highlightthickness=1, highlightbackground=C["border"], relief="flat")
        self.txt_reason.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        RoundedButton(shell.footer, text="🗑  Xóa khỏi danh sách", command=self.confirm, variant="danger").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)
        center(self, 560, 640)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _switch(self):
        if self.v_kind.get() == DEL_DIEU_CHUYEN:
            self.box_other.grid_forget()
            self.box_move.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        else:
            self.box_move.grid_forget()
            self.box_other.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            self.txt_reason.focus_set()

    def _pick_file(self):
        path = filedialog.askopenfilename(
            parent=self, title="Chọn file quyết định",
            filetypes=[("Tài liệu", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"), ("Tất cả file", "*.*")])
        if path:
            self.pending_file = path
            self.v_filename.set(os.path.basename(path))

    def confirm(self):
        kind = self.v_kind.get()
        rec = dict(hinh_thuc=kind, ma_cb=self.row["ma_cb"], ho_ten=self.row["ho_ten"])
        if kind == DEL_DIEU_CHUYEN:
            data = {k: v.get().strip() for k, v in self.v.items()}
            if not data["noi_den"] or not data["so_quyet_dinh"]:
                messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Nơi chuyển đến và Số quyết định.",
                                       parent=self)
                return
            for key, name in (("ngay_dieu_chuyen", "Ngày điều chuyển"), ("ngay_ban_hanh", "Ngày ban hành")):
                if data[key]:
                    try:
                        datetime.datetime.strptime(data[key], "%d/%m/%Y")
                    except ValueError:
                        messagebox.showwarning("Sai định dạng", f"{name} phải theo dạng dd/mm/yyyy.", parent=self)
                        return
            rec.update(data)
            detail = f"điều chuyển đến {data['noi_den']} theo QĐ {data['so_quyet_dinh']}"
        else:
            reason = self.txt_reason.get("1.0", "end").strip()
            if not reason:
                messagebox.showwarning("Thiếu thông tin", "Vui lòng ghi rõ lý do xóa.", parent=self)
                return
            rec["ly_do"] = reason
            detail = f"lý do: {reason}"
        if not messagebox.askyesno("Xác nhận xóa",
                                   f"Xóa cán bộ '{self.row['ho_ten']}' khỏi danh sách ({detail})?", parent=self):
            return

        app = self.panel.app
        snapshot = {k: self.row[k] for k in self.row.keys()}
        snapshot["qua_trinh_cong_tac"] = timeline_rows(self.db, "cong_tac", self.row["id"])
        snapshot["qua_trinh_hoc_tap"] = timeline_rows(self.db, "hoc_tap", self.row["id"])
        if kind == DEL_DIEU_CHUYEN and self.pending_file:
            from core import attachments
            rec["file_dinh_kem"] = attachments.save_attachment(app.app_dir, DELETED_TABLE, self.pending_file)
        rec.update(thoi_gian=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   nguoi_thuc_hien=app.user["username"],
                   du_lieu=json.dumps(snapshot, ensure_ascii=False))
        self.db.insert(DELETED_TABLE, rec)
        self.db.delete(TABLE, self.row["id"])
        self.db.log(app.user["username"], "Xóa cán bộ", f"{self.row['ma_cb']} - {self.row['ho_ten']} ({detail})")
        app.status.set("Đã xóa cán bộ khỏi danh sách.")
        self.panel.after_delete()
        self.destroy()


class DeletedHistoryDialog(tk.Toplevel):
    """Danh sách cán bộ đã xóa khỏi danh sách (điều chuyển đi / lý do khác)."""

    COLS = [("thoi_gian", "Thời gian xóa", 140), ("ma_cb", "Mã CB", 80), ("ho_ten", "Họ và tên", 160),
            ("hinh_thuc", "Lý do", 160), ("chi_tiet", "Nơi đến / Lý do cụ thể", 220),
            ("so_quyet_dinh", "Số QĐ", 100), ("ngay_ban_hanh", "Ngày ban hành", 100),
            ("nguoi_ky", "Người ký", 120), ("file", "File QĐ", 70), ("nguoi_thuc_hien", "Người xóa", 100)]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        shell = DialogShell(self, "Cán bộ đã xóa / điều chuyển đi", width=980, height=520, min_height=360)
        self.tree, wrap = make_tree(shell.body, self.COLS)
        wrap.pack(fill="both", expand=True)
        self.rows = {}
        for i, r in enumerate(app.db.conn.execute(f"SELECT * FROM {DELETED_TABLE} ORDER BY id DESC")):
            self.rows[str(r["id"])] = r
            chi_tiet = r["noi_den"] if r["hinh_thuc"] == DEL_DIEU_CHUYEN else r["ly_do"]
            self.tree.insert("", "end", iid=str(r["id"]), tags=("odd" if i % 2 else "even",), values=(
                r["thoi_gian"], r["ma_cb"], r["ho_ten"], r["hinh_thuc"], chi_tiet or "",
                r["so_quyet_dinh"] or "", r["ngay_ban_hanh"] or "", r["nguoi_ky"] or "",
                "📎 Có" if r["file_dinh_kem"] else "—", r["nguoi_thuc_hien"] or ""))
        self.tree.bind("<Double-1>", lambda e: self.open_file())
        RoundedButton(shell.footer, text="📎  Mở file quyết định", command=self.open_file,
                      variant="secondary").pack(side="left")
        RoundedButton(shell.footer, text="Đóng", command=self.destroy, variant="primary").pack(side="right")
        center(self, 980, 520)

    def open_file(self):
        sel = self.tree.selection()
        r = self.rows.get(sel[0]) if sel else None
        if r and r["file_dinh_kem"]:
            from core import attachments
            if not attachments.open_file(self.app.app_dir, r["file_dinh_kem"]):
                messagebox.showwarning("Không mở được file", "Không tìm thấy file quyết định.", parent=self)


class AdvancedSearchDialog(tk.Toplevel):
    """Tìm kiếm nâng cao - từng tiêu chí riêng, kết hợp bằng VÀ (AND)."""

    def __init__(self, panel):
        super().__init__(panel.app)
        self.panel = panel
        shell = DialogShell(self, "Tìm kiếm nâng cao", width=460, height=440, min_height=380)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar(value=panel.adv_filters.get(k, "")) for k in
                 ("ma_cb", "ho_ten", "doi_to", "don_vi", "cap_bac", "chuc_vu", "gioi_tinh", "que_quan_tinh")}

        def row(r, label, widget):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Mã cán bộ", ttk.Entry(form, textvariable=self.v["ma_cb"], width=26))
        row(1, "Họ và tên", ttk.Entry(form, textvariable=self.v["ho_ten"], width=26))
        row(2, "Đội / Tổ", ttk.Entry(form, textvariable=self.v["doi_to"], width=26))
        row(3, "Phòng / Xã, phường", ttk.Entry(form, textvariable=self.v["don_vi"], width=26))
        row(4, "Cấp bậc", ttk.Combobox(form, textvariable=self.v["cap_bac"],
                                       values=[""] + cand_data.CAP_BAC, state="readonly", width=24))
        row(5, "Chức vụ", ttk.Entry(form, textvariable=self.v["chuc_vu"], width=26))
        row(6, "Giới tính", ttk.Combobox(form, textvariable=self.v["gioi_tinh"],
                                         values=["", "Nam", "Nữ"], state="readonly", width=24))
        import core.dia_gioi_hanh_chinh as dgh
        row(7, "Quê quán - Tỉnh/Thành", ttk.Combobox(form, textvariable=self.v["que_quan_tinh"],
                                                     values=[""] + dgh.danh_sach_tinh(), width=24))

        RoundedButton(shell.footer, text="Áp dụng", command=self.apply, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Xóa bộ lọc", command=self.clear, variant="secondary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Đóng", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self, 460, 440)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def apply(self):
        filters = {k: v.get().strip() for k, v in self.v.items() if v.get().strip()}
        self.panel.apply_advanced(filters)
        self.destroy()

    def clear(self):
        self.panel.adv_filters = {}
        self.panel.adv_note.set("")
        self.panel.refresh()
        self.destroy()


class EmployeeFormDialog(tk.Toplevel):
    """Hộp thoại popup Thêm mới / Sửa cán bộ - kéo thả đổi kích thước được."""

    def __init__(self, panel, row=None):
        super().__init__(panel.app)
        self.panel, self.db, self.row = panel, panel.db, row
        is_edit = row is not None
        title = f"Sửa thông tin: {row['ho_ten']}" if is_edit else "Thêm cán bộ mới"
        shell = DialogShell(self, title, width=720, height=720)
        self.vars = {k: tk.StringVar() for k, _l, _t in ALL_FIELDS}
        self.compound_widgets = {}
        self.timelines = {}
        cb_id = row["id"] if is_edit else None

        def timeline(kind):
            def build(parent):
                sec = TimelineSection(parent, self.db, kind, can_bo_id=cb_id)
                sec.pack(fill="x")
                self.timelines[kind] = sec
            return build

        self.widgets = _build_form_fields(
            shell.body, self.vars, self.compound_widgets, self._on_rank_change, db=self.db,
            after_section={SEC_CONG_TAC: timeline("cong_tac"), SEC_HOC_TAP: timeline("hoc_tap")})

        if is_edit:
            for k in self.vars:
                self.vars[k].set(row[k] or "")
            for (tc, xc), w in self.compound_widgets.items():
                w.set(row[tc] or "", row[xc] or "")

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Thêm mới"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self, 720, 720)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _on_rank_change(self, _e=None):
        coef = cand_data.HE_SO_LUONG_THEO_CAP_BAC.get(self.vars["cap_bac"].get())
        if coef:
            self.vars["he_so_luong"].set(coef)

    def save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        for (tc, xc), w in self.compound_widgets.items():
            t, x = w.get()
            data[tc] = t
            data[xc] = x
        if not _validate(data):
            return
        try:
            if self.row is None:
                new_id = self.db.insert(TABLE, data)
                for sec in self.timelines.values():
                    sec.flush_to_db(new_id)
                self.db.log(self.panel.app.user["username"], "Thêm cán bộ", f"{data['ma_cb']} - {data['ho_ten']}")
                self.panel.app.status.set("Đã thêm cán bộ mới.")
            else:
                self.db.update(TABLE, self.row["id"], data)
                self.db.log(self.panel.app.user["username"], "Sửa cán bộ", f"{data['ma_cb']} - {data['ho_ten']}")
                self.panel.app.status.set("Đã cập nhật thông tin.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Trùng mã", f"Mã cán bộ '{data['ma_cb']}' đã tồn tại.", parent=self)
            return
        self.panel.refresh()
        self.destroy()


class ProfileDialog(tk.Toplevel):
    """Xem hồ sơ đầy đủ của một cán bộ, có thể xuất ra HTML để in."""

    def __init__(self, app, row):
        super().__init__(app)
        self.app, self.row = app, row
        self.title(f"Hồ sơ cán bộ - {row['ho_ten']}")
        self.configure(bg=C["bg"])
        self.minsize(520, 480)
        self.geometry("640x680")
        center(self, 640, 680)

        head = tk.Frame(self, bg=C["primary"])
        head.pack(fill="x")
        tk.Label(head, text=row["ho_ten"], bg=C["primary"], fg="white",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 0))
        tk.Label(head, text=f"Mã cán bộ: {row['ma_cb']}", bg=C["primary"], fg="white",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 12))

        scroll = ScrollableFrame(self, width=600)
        scroll.pack(fill="both", expand=True, padx=14, pady=10)
        body = scroll.body
        # Chỉ tài khoản có quyền Sửa cán bộ mới được thêm/sửa/xóa các mốc
        # quá trình ngay trong màn hình hồ sơ.
        readonly = not app.can(MODULE_ID, "edit")
        section_kind = {SEC_CONG_TAC: "cong_tac", SEC_HOC_TAP: "hoc_tap"}
        for sec_title, fields in SECTIONS_FLAT:
            sec = ttk.Frame(body, style="Card.TFrame", padding=(4, 8))
            sec.pack(fill="x")
            ttk.Label(sec, text=sec_title, style="Section.TLabel").pack(anchor="w")
            grid = ttk.Frame(sec, style="Card.TFrame")
            grid.pack(fill="x", pady=(2, 4))
            for i, (key, label, _t) in enumerate(fields):
                val = row[key] or "—"
                ttk.Label(grid, text=label.replace(" *", ""), style="CardMuted.TLabel",
                         width=30, anchor="w").grid(row=i, column=0, sticky="w", pady=3)
                ttk.Label(grid, text=val, style="Card.TLabel", font=("Segoe UI", 10, "bold"),
                         wraplength=340, justify="left").grid(row=i, column=1, sticky="w", pady=3)
            if sec_title in section_kind:
                TimelineSection(sec, self.app.db, section_kind[sec_title], can_bo_id=row["id"],
                                height=4, readonly=readonly).pack(fill="x", pady=(4, 4))

        btns = ttk.Frame(self, padding=(14, 8))
        btns.pack(fill="x")
        btn_print = RoundedButton(btns, text="🖨  Xuất hồ sơ (HTML để in)", command=self.export_html, variant="primary")
        btn_print.pack(side="left")
        if not app.can(MODULE_ID, "export"):
            btn_print.state(["disabled"])
        RoundedButton(btns, text="Đóng", command=self.destroy, variant="secondary").pack(side="right")

    def export_html(self):
        import core.report as report
        section_kind = {SEC_CONG_TAC: "cong_tac", SEC_HOC_TAP: "hoc_tap"}
        sections = []
        for sec, fields in SECTIONS_FLAT:
            item = [sec, [(lbl.replace(" *", ""), self.row[key] or "") for key, lbl, _t in fields]]
            if sec in section_kind:
                cfg = TIMELINES[section_kind[sec]]
                rows = [{k: _display(k, r.get(k)) for k, _l, _w in cfg["cols"]}
                        for r in timeline_rows(self.app.db, section_kind[sec], self.row["id"])]
                item.append(([(k, lbl) for k, lbl, _w in cfg["cols"]], rows))
            sections.append(tuple(item))
        don_vi = ", ".join(x for x in (self.row["doi_to"], self.row["don_vi"]) if x) or "—"
        meta = [f"Đơn vị: {don_vi}",
               f"Người xuất: {self.app.user['ho_ten'] or self.app.user['username']}"]
        html_str = report.build_profile_html(f"Hồ sơ cán bộ: {self.row['ho_ten']}", sections, meta)
        path = report.open_html(html_str, f"ho_so_{self.row['ma_cb']}.html")
        self.app.db.log(self.app.user["username"], "In hồ sơ cán bộ",
                        f"{self.row['ma_cb']} - {self.row['ho_ten']}")
        messagebox.showinfo("Đã xuất", f"Đã mở hồ sơ trong trình duyệt.\nFile: {path}", parent=self)
