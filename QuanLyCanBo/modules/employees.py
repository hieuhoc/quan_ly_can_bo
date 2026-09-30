# -*- coding: utf-8 -*-
"""Module: Quản lý thông tin cán bộ."""
import csv
import datetime
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

# Mỗi trường: (khóa_CSDL, nhãn, loại)
# loại: text | gender | date | rank | position | salary | province_ward
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
        ("cap_don_vi", "Cấp đơn vị", "unit_level"),
        ("don_vi", "Đơn vị", "text"),
        ("he_so_luong", "Hệ số lương", "salary"),
    ]),
    ("Quá trình công tác - Đảng", [
        ("ngay_vao_nganh", "Ngày vào ngành", "date"),
        ("ngay_vao_dang", "Ngày vào Đảng", "date"),
        ("ngay_chuyen_dang_chinh_thuc", "Ngày chuyển Đảng chính thức", "date"),
    ]),
    ("Trình độ", [
        ("trinh_do_nghiep_vu", "Trình độ nghiệp vụ", "text"),
        ("trinh_do_chinh_tri", "Trình độ chính trị", "text"),
        ("trinh_do_ngoai_ngu", "Trình độ ngoại ngữ", "text"),
    ]),
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

COLUMNS_SHOW = ["ma_cb", "ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "sdt",
                "cap_bac", "chuc_vu", "chuc_danh_hien_tai", "cap_don_vi", "don_vi", "he_so_luong",
                "ngay_vao_nganh", "trinh_do_nghiep_vu", "trinh_do_chinh_tri", "trinh_do_ngoai_ngu", "ghi_chu"]
COL_WIDTH = {"ma_cb": 82, "ho_ten": 150, "ngay_sinh": 88, "gioi_tinh": 62, "so_cccd": 100, "sdt": 100,
             "cap_bac": 110, "chuc_vu": 120, "chuc_danh_hien_tai": 130, "cap_don_vi": 130, "don_vi": 140,
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


def _build_form_fields(body, vars_, compound_widgets, on_rank_change):
    """Dựng các trường theo SECTIONS vào `body` (thân hộp thoại hoặc form).
    vars_: dict khóa CSDL đơn -> StringVar. compound_widgets: dict điền vào,
    (cột_tỉnh, cột_xã) -> ProvinceWardPicker. Trả về dict khóa -> (widget, kind)."""
    widgets = {}
    for title, fields in SECTIONS:
        section_label(body, title).pack(fill="x", pady=(10, 0))
        grid = ttk.Frame(body, style="Card.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
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
            elif kind == "unit_level":
                w = ttk.Combobox(grid, textvariable=vars_[key], values=cand_data.CAP_DON_VI,
                                 state="readonly", width=25)
            else:
                w = ttk.Entry(grid, textvariable=vars_[key], width=28)
            w.grid(row=i, column=1, pady=4, sticky="ew")
            widgets[key] = (w, kind)
    return widgets


class CongTacEntryDialog(tk.Toplevel):
    """Popup nhỏ: thêm một mốc quá trình công tác (từ ngày - đến ngày - đơn vị)."""

    def __init__(self, parent_widget, on_save):
        super().__init__(parent_widget.winfo_toplevel())
        self.on_save = on_save
        shell = DialogShell(self, "Thêm mốc quá trình công tác", width=420, height=300, min_height=280)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v_tu = tk.StringVar()
        self.v_den = tk.StringVar()
        self.v_donvi = tk.StringVar()

        ttk.Label(form, text="Từ ngày", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        DateEntry(form, textvariable=self.v_tu, width=18).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Đến ngày\n(để trống nếu vẫn đang công tác)", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        DateEntry(form, textvariable=self.v_den, width=18).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Đơn vị công tác *", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(form, textvariable=self.v_donvi, width=22).grid(row=2, column=1, sticky="ew", pady=6)

        RoundedButton(shell.footer, text="➕  Thêm", command=self.save, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)
        center(self, 420, 300)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def save(self):
        donvi = self.v_donvi.get().strip()
        if not donvi:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Đơn vị công tác.", parent=self)
            return
        for label, val in (("Từ ngày", self.v_tu.get().strip()), ("Đến ngày", self.v_den.get().strip())):
            if val:
                try:
                    datetime.datetime.strptime(val, "%d/%m/%Y")
                except ValueError:
                    messagebox.showwarning("Sai định dạng", f"{label} phải theo dạng dd/mm/yyyy.", parent=self)
                    return
        self.on_save(self.v_tu.get().strip(), self.v_den.get().strip(), donvi)
        self.destroy()


class CongTacSection(ttk.Frame):
    """Danh sách quá trình công tác (từ ngày - đến ngày - đơn vị) kèm nút
    thêm mốc mới. Nếu can_bo_id=None (đang tạo cán bộ mới, chưa có id),
    các mốc được giữ tạm trong bộ nhớ - gọi flush_to_db(id_mới) ngay sau
    khi cán bộ được tạo xong để ghi các mốc đó xuống CSDL. Nếu đã có
    can_bo_id (đang sửa cán bộ có sẵn, hoặc đang xem hồ sơ), mọi thao tác
    ghi thẳng xuống CSDL ngay lập tức."""

    def __init__(self, parent, db, can_bo_id=None, height=4):
        super().__init__(parent, style="Card.TFrame")
        self.db = db
        self.can_bo_id = can_bo_id
        self.pending = []
        cols = [("tu_ngay", "Từ ngày", 90), ("den_ngay", "Đến ngày", 100), ("don_vi_cong_tac", "Đơn vị công tác", 240)]
        self.tree, wrap = make_tree(self, cols, sortable=False)
        self.tree.configure(height=height)
        wrap.pack(fill="x")
        btn_row = ttk.Frame(self, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(6, 0))
        RoundedButton(btn_row, text="➕  Thêm mốc công tác", command=self._add, variant="secondary").pack(side="left")
        RoundedButton(btn_row, text="🗑  Xóa mốc đã chọn", command=self._delete, variant="secondary").pack(
            side="left", padx=(6, 0))
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self._load_rows()):
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r["tu_ngay"] or "—", r["den_ngay"] or "(hiện tại)", r["don_vi_cong_tac"]),
                             tags=("odd" if i % 2 else "even",))

    def _load_rows(self):
        if self.can_bo_id is not None:
            rows = self.db.conn.execute(
                "SELECT id, tu_ngay, den_ngay, don_vi_cong_tac FROM qua_trinh_cong_tac "
                "WHERE can_bo_id=? ORDER BY (tu_ngay=='' OR tu_ngay IS NULL), tu_ngay", (self.can_bo_id,)).fetchall()
            return [dict(r) for r in rows]
        return [{"id": i, "tu_ngay": t, "den_ngay": d, "don_vi_cong_tac": u}
               for i, (t, d, u) in enumerate(self.pending)]

    def _add(self):
        def on_save(tu, den, donvi):
            if self.can_bo_id is not None:
                self.db.insert("qua_trinh_cong_tac",
                               dict(can_bo_id=self.can_bo_id, tu_ngay=tu, den_ngay=den, don_vi_cong_tac=donvi))
            else:
                self.pending.append((tu, den, donvi))
            self.refresh()
        CongTacEntryDialog(self, on_save)

    def _delete(self):
        sel = self.tree.selection()
        top = self.winfo_toplevel()
        if not sel:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một mốc để xóa.", parent=top)
            return
        if not messagebox.askyesno("Xác nhận xóa", "Xóa mốc công tác này?", parent=top):
            return
        idx = int(sel[0])
        if self.can_bo_id is not None:
            self.db.delete("qua_trinh_cong_tac", idx)
        elif 0 <= idx < len(self.pending):
            self.pending.pop(idx)
        self.refresh()

    def flush_to_db(self, can_bo_id):
        """Ghi các mốc đang chờ (khi tạo cán bộ mới) xuống CSDL sau khi đã có id."""
        for tu, den, donvi in self.pending:
            self.db.insert("qua_trinh_cong_tac",
                           dict(can_bo_id=can_bo_id, tu_ngay=tu, den_ngay=den, don_vi_cong_tac=donvi))
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
        tk.Frame(card, height=2, width=44, bg=C["gold"]).pack(anchor="w", pady=(4, 10))

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

        cols = [(k, LABELS[k].replace(" *", "").split(" (")[0], COL_WIDTH[k]) for k in COLUMNS_SHOW]
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
        self.adv_filters = filters
        n = len(filters)
        self.adv_note.set(f"Đang áp dụng tìm kiếm nâng cao ({n} tiêu chí) — gõ vào ô tìm kiếm thường để bỏ lọc này.")
        self.search_var.set("")
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
        if f.get("cap_don_vi"):
            conds.append("cap_don_vi = ?"); params.append(f["cap_don_vi"])
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
        if messagebox.askyesno("Xác nhận xóa",
                               f"Xóa cán bộ '{row['ho_ten']}'?\nCác dữ liệu phân loại, nâng lương, đơn thư liên "
                               "quan cũng sẽ bị xóa theo.\nThao tác không thể hoàn tác."):
            self.db.delete(TABLE, self.selected_id)
            self.db.log(self.app.user["username"], "Xóa cán bộ", f"{row['ma_cb']} - {row['ho_ten']}")
            self.selected_id = None
            self.refresh()
            self._refresh_button_states()
            self.app.status.set("Đã xóa cán bộ.")

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
        columns = [(k, LABELS[k].replace(" *", "").split(" (")[0]) for k in COLUMNS_SHOW]
        meta = [f"Người xuất: {self.app.user['ho_ten'] or self.app.user['username']}",
               f"Số lượng: {len(rows)} cán bộ"]
        html_str = report.build_list_html("Danh sách cán bộ", meta, columns, rows)
        report.open_html(html_str, "danh_sach_can_bo.html")
        self.db.log(self.app.user["username"], "In danh sách", f"{len(rows)} cán bộ")


class AdvancedSearchDialog(tk.Toplevel):
    """Tìm kiếm nâng cao - từng tiêu chí riêng, kết hợp bằng VÀ (AND)."""

    def __init__(self, panel):
        super().__init__(panel.app)
        self.panel = panel
        shell = DialogShell(self, "Tìm kiếm nâng cao", width=460, height=440, min_height=380)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar(value=panel.adv_filters.get(k, "")) for k in
                 ("ma_cb", "ho_ten", "don_vi", "cap_bac", "cap_don_vi", "chuc_vu", "gioi_tinh", "que_quan_tinh")}

        def row(r, label, widget):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Mã cán bộ", ttk.Entry(form, textvariable=self.v["ma_cb"], width=26))
        row(1, "Họ và tên", ttk.Entry(form, textvariable=self.v["ho_ten"], width=26))
        row(2, "Đơn vị", ttk.Entry(form, textvariable=self.v["don_vi"], width=26))
        row(3, "Cấp bậc", ttk.Combobox(form, textvariable=self.v["cap_bac"],
                                       values=[""] + cand_data.CAP_BAC, state="readonly", width=24))
        row(4, "Cấp đơn vị", ttk.Combobox(form, textvariable=self.v["cap_don_vi"],
                                          values=[""] + cand_data.CAP_DON_VI, state="readonly", width=24))
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
        shell = DialogShell(self, title, width=640, height=700)
        self.vars = {k: tk.StringVar() for k, _l, _t in ALL_FIELDS}
        self.compound_widgets = {}
        self.widgets = _build_form_fields(shell.body, self.vars, self.compound_widgets, self._on_rank_change)

        section_label(shell.body, "Quá trình công tác").pack(fill="x", pady=(10, 4))
        self.cong_tac = CongTacSection(shell.body, self.db, can_bo_id=(row["id"] if is_edit else None))
        self.cong_tac.pack(fill="x")

        if is_edit:
            for k in self.vars:
                self.vars[k].set(row[k] or "")
            for (tc, xc), w in self.compound_widgets.items():
                w.set(row[tc] or "", row[xc] or "")

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Thêm mới"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self, 640, 700)
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
                self.cong_tac.flush_to_db(new_id)
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
        tk.Label(head, text=row["ho_ten"], bg=C["primary"], fg=C["gold"],
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 0))
        tk.Label(head, text=f"Mã cán bộ: {row['ma_cb']}", bg=C["primary"], fg="white",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 12))

        scroll = ScrollableFrame(self, width=600)
        scroll.pack(fill="both", expand=True, padx=14, pady=10)
        body = scroll.body
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

        ct_sec = ttk.Frame(body, style="Card.TFrame", padding=(4, 8))
        ct_sec.pack(fill="x")
        ttk.Label(ct_sec, text="Quá trình công tác", style="Section.TLabel").pack(anchor="w")
        self.cong_tac = CongTacSection(ct_sec, self.app.db, can_bo_id=row["id"], height=6)
        self.cong_tac.pack(fill="x", pady=(4, 4))

        btns = ttk.Frame(self, padding=(14, 8))
        btns.pack(fill="x")
        RoundedButton(btns, text="🖨  Xuất hồ sơ (HTML để in)", command=self.export_html, variant="primary").pack(side="left")
        RoundedButton(btns, text="Đóng", command=self.destroy, variant="secondary").pack(side="right")

    def export_html(self):
        import core.report as report
        sections = [(sec, [(lbl.replace(" *", ""), self.row[key] or "") for key, lbl, _t in fields])
                   for sec, fields in SECTIONS_FLAT]
        meta = [f"Đơn vị: {self.row['don_vi'] or '—'}",
               f"Người xuất: {self.app.user['ho_ten'] or self.app.user['username']}"]
        ct_rows = self.app.db.conn.execute(
            "SELECT tu_ngay, den_ngay, don_vi_cong_tac FROM qua_trinh_cong_tac "
            "WHERE can_bo_id=? ORDER BY (tu_ngay=='' OR tu_ngay IS NULL), tu_ngay", (self.row["id"],)).fetchall()
        ct_cols = [("tu_ngay", "Từ ngày"), ("den_ngay", "Đến ngày"), ("don_vi_cong_tac", "Đơn vị công tác")]
        ct_display = [{"tu_ngay": r["tu_ngay"] or "—", "den_ngay": r["den_ngay"] or "(hiện tại)",
                      "don_vi_cong_tac": r["don_vi_cong_tac"]} for r in ct_rows]
        extra = [("Quá trình công tác", ct_cols, ct_display)] if ct_display else []
        html_str = report.build_profile_html(f"Hồ sơ cán bộ: {self.row['ho_ten']}", sections, meta, extra_tables=extra)
        path = report.open_html(html_str, f"ho_so_{self.row['ma_cb']}.html")
        self.app.db.log(self.app.user["username"], "In hồ sơ cán bộ",
                        f"{self.row['ma_cb']} - {self.row['ho_ten']}")
        messagebox.showinfo("Đã xuất", f"Đã mở hồ sơ trong trình duyệt.\nFile: {path}", parent=self)
