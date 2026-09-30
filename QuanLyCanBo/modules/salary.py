# -*- coding: utf-8 -*-
"""Module: Nâng lương và Thăng cấp bậc hàm.

Hai loại quyết định này vẫn là hai quá trình độc lập (có thể lệch năm,
không bắt buộc đi cùng nhau) nhưng được hiển thị chung trong MỘT bảng duy
nhất, sắp theo ngày quyết định - xem được toàn bộ diễn biến lương/cấp bậc
của cán bộ theo thời gian. Bộ lọc nhanh phía trên cho phép chỉ xem riêng
Nâng lương hoặc riêng Thăng cấp bậc hàm khi cần."""
import csv
import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import attachments, cand_data
from core.theme import C, center, make_card
from core.widgets import DateEntry, DialogShell, EmployeePicker, RoundedButton, TabBar, make_tree

MODULE_ID = "salary"
TABLE = "qua_trinh_luong"
TITLE = "Nâng lương - Thăng cấp"
LOAI_NANG_LUONG = ["Nâng lương định kỳ", "Nâng lương trước hạn"]
LOAI_THANG_CAP = ["Thăng cấp bậc hàm"]
LOAI_OPTIONS = LOAI_NANG_LUONG + LOAI_THANG_CAP

# Bộ lọc nhanh: (khóa, nhãn, danh sách loại được hiển thị)
QUICK_FILTERS = [("all", "Tất cả", LOAI_OPTIONS),
                 ("luong", "Nâng lương", LOAI_NANG_LUONG),
                 ("capbac", "Thăng cấp bậc hàm", LOAI_THANG_CAP)]

COLS = [("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160), ("loai", "Loại", 180),
        ("ngay_quyet_dinh", "Ngày QĐ", 112), ("so_quyet_dinh", "Số quyết định", 140),
        ("cap_bac_moi", "Cấp bậc mới", 120), ("noi_dung", "Nội dung", 200), ("file_dinh_kem", "File", 70)]


def _date_key(col):
    """Biểu thức SQL đổi 'dd/mm/yyyy' thành 'yyyymmdd' để so sánh/sắp xếp
    đúng theo thời gian (so sánh chuỗi dd/mm/yyyy trực tiếp sẽ sai)."""
    return f"(substr({col},7,4)||substr({col},4,2)||substr({col},1,2))"


def _to_key(text):
    """'05/03/2026' -> '20260305'; trả về None nếu sai định dạng."""
    try:
        return datetime.datetime.strptime(text.strip(), "%d/%m/%Y").strftime("%Y%m%d")
    except ValueError:
        return None


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.title = TITLE
        self.selected_id = None
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.adv_filters = {}
        self.adv_note = tk.StringVar()
        self.quick = "all"
        self._build()
        self._refresh_button_states()
        self.refresh()

    @property
    def loai_values(self):
        return next(v for k, _l, v in QUICK_FILTERS if k == self.quick)

    def _build(self):
        lo, card = make_card(self, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Nâng lương - Thăng cấp bậc hàm", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.count_var, style="CardMuted.TLabel").pack(side="right")

        self.tabs = TabBar(card, [(k, label) for k, label, _v in QUICK_FILTERS],
                           command=self.set_quick, selected=self.quick)
        self.tabs.pack(fill="x", pady=(12, 14))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="🔍", style="Card.TLabel").pack(side="left")
        ttk.Entry(bar, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=8)
        RoundedButton(bar, text="Xóa lọc", command=lambda: self.search_var.set(""), variant="secondary").pack(side="left")
        RoundedButton(bar, text="🔎  Tìm nâng cao", command=self.open_advanced_search,
                      variant="secondary").pack(side="left", padx=(6, 0))
        self.search_var.trace_add("write", self._on_simple_search_typed)

        note_row = ttk.Frame(card, style="Card.TFrame")
        note_row.pack(fill="x", pady=(0, 8))
        ttk.Label(note_row, textvariable=self.adv_note, style="Error.TLabel").pack(side="left")

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.btn_add = RoundedButton(toolbar, text="➕  Thêm quyết định", command=self.open_add, variant="primary")
        self.btn_edit = RoundedButton(toolbar, text="✏  Sửa", command=self.open_edit, variant="secondary")
        self.btn_del = RoundedButton(toolbar, text="🗑  Xóa", command=self.on_delete, variant="danger")
        self.btn_open_file = RoundedButton(toolbar, text="📎  Mở file đính kèm", command=self.open_attachment,
                                           variant="secondary")
        self.btn_export = RoundedButton(toolbar, text="📤  Xuất CSV", command=self.export_csv, variant="secondary")
        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_open_file, self.btn_export):
            b.pack(side="left", padx=(0, 6))

        self.tree, wrap = make_tree(card, COLS)
        wrap.pack(fill="both", expand=True)
        self.tree.tag_configure("promo", foreground=C["blue"])
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.on_delete())
        self.tree.bind("<Double-1>", lambda e: self.open_edit())

    def set_quick(self, key):
        self.quick = key
        self.tabs.select(key)
        self.selected_id = None
        self.refresh()
        self._refresh_button_states()

    def _refresh_button_states(self):
        has_sel = self.selected_id is not None
        row = self._current_row()
        has_file = has_sel and bool(row and row["file_dinh_kem"])

        def st(b, ok):
            b.state(["!disabled"] if ok else ["disabled"])

        st(self.btn_add, self.app.can(MODULE_ID, "add"))
        st(self.btn_edit, self.app.can(MODULE_ID, "edit") and has_sel)
        st(self.btn_del, self.app.can(MODULE_ID, "delete") and has_sel)
        st(self.btn_open_file, has_file)
        st(self.btn_export, self.app.can(MODULE_ID, "export"))

    def _current_row(self):
        return self.db.fetch_one(TABLE, self.selected_id) if self.selected_id else None

    def deny(self, action):
        if self.app.can(MODULE_ID, action):
            return False
        from core.registry import ACTION_LABEL
        messagebox.showwarning("Không đủ quyền", f"Tài khoản của bạn không có quyền «{ACTION_LABEL[action]}».")
        return True

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
        self.adv_note.set(f"Đang áp dụng tìm kiếm nâng cao ({len(filters)} tiêu chí) — "
                          "gõ vào ô tìm kiếm thường để bỏ lọc này.")
        self.refresh()

    def _rows(self):
        """Các bản ghi của nhóm (tab) đang chọn, đã áp bộ lọc tìm kiếm."""
        return [r for r in self._rows_all() if r["loai"] in self.loai_values]

    def _rows_all(self):
        """Mọi loại quyết định, đã áp bộ lọc tìm kiếm - dùng để đếm từng tab."""
        placeholders = ",".join("?" * len(LOAI_OPTIONS))
        sql = (f"SELECT q.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM qua_trinh_luong q "
               f"JOIN can_bo c ON c.id = q.can_bo_id WHERE q.loai IN ({placeholders})")
        params = list(LOAI_OPTIONS)
        if self.adv_filters:
            f = self.adv_filters
            if f.get("ho_ten"):
                sql += " AND c.ho_ten LIKE ?"; params.append(f"%{f['ho_ten']}%")
            if f.get("tu_ngay") and _to_key(f["tu_ngay"]):
                sql += f" AND {_date_key('q.ngay_quyet_dinh')} >= ?"; params.append(_to_key(f["tu_ngay"]))
            if f.get("so_quyet_dinh"):
                sql += " AND q.so_quyet_dinh LIKE ?"; params.append(f"%{f['so_quyet_dinh']}%")
            if f.get("cap_bac_moi"):
                sql += " AND q.cap_bac_moi = ?"; params.append(f["cap_bac_moi"])
        elif self.search_var.get().strip():
            like = f"%{self.search_var.get().strip()}%"
            sql += " AND (c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR q.noi_dung LIKE ? OR q.so_quyet_dinh LIKE ?)"
            params.extend([like] * 4)
        sql += (" ORDER BY (q.ngay_quyet_dinh IS NULL OR q.ngay_quyet_dinh==''), "
                f"{_date_key('q.ngay_quyet_dinh')} DESC, q.created_at DESC")
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        all_rows = self._rows_all()
        for key, _label, loai in QUICK_FILTERS:
            self.tabs.set_count(key, sum(1 for r in all_rows if r["loai"] in loai))
        rows = [r for r in all_rows if r["loai"] in self.loai_values]
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            vals = [r[c[0]] or "" for c in COLS[:-1]] + ["📎 Có" if r["file_dinh_kem"] else "—"]
            tags = ["odd" if i % 2 else "even"] + (["promo"] if r["loai"] in LOAI_THANG_CAP else [])
            self.tree.insert("", "end", iid=str(r["id"]), values=vals, tags=tags)
        self.count_var.set(f"Đang hiển thị {len(rows)} quyết định")

    def on_select(self, _=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        self._refresh_button_states()

    def open_add(self):
        if self.deny("add"):
            return
        EntryFormDialog(self, row=None)

    def open_edit(self):
        if self.deny("edit"):
            return
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một bản ghi để sửa.")
            return
        row = self.db.fetch_one(TABLE, self.selected_id)
        if row:
            EntryFormDialog(self, row=row)

    def open_attachment(self):
        row = self._current_row()
        if row and row["file_dinh_kem"]:
            if not attachments.open_file(self.app.app_dir, row["file_dinh_kem"]):
                messagebox.showwarning("Không mở được file", "Không tìm thấy hoặc không mở được file đính kèm.")

    def on_delete(self):
        if self.deny("delete"):
            return
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một bản ghi để xóa.")
            return
        row = self._current_row()
        if messagebox.askyesno("Xác nhận xóa", "Xóa bản ghi này?\nThao tác không thể hoàn tác."):
            if row and row["file_dinh_kem"]:
                attachments.delete_attachment(self.app.app_dir, row["file_dinh_kem"])
            self.db.delete(TABLE, self.selected_id)
            self.db.log(self.app.user["username"], f"Xóa quyết định {(row['loai'] if row else '').lower()}",
                        f"id={self.selected_id}")
            self.selected_id = None
            self.refresh()
            self._refresh_button_states()
            self.app.status.set("Đã xóa bản ghi.")

    def export_csv(self):
        if self.deny("export"):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=datetime.datetime.now().strftime("nang_luong_thang_cap_%Y%m%d.csv"))
        if not path:
            return
        rows = self._rows()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Mã cán bộ", "Họ và tên", "Loại", "Ngày quyết định", "Số quyết định",
                        "Cấp bậc mới", "Nội dung", "Ghi chú"])
            for r in rows:
                w.writerow([r["ma_cb"], r["ho_ten"], r["loai"], r["ngay_quyet_dinh"] or "",
                            r["so_quyet_dinh"] or "", r["cap_bac_moi"] or "", r["noi_dung"] or "", r["ghi_chu"] or ""])
        self.db.log(self.app.user["username"], "Xuất CSV", f"{len(rows)} bản ghi ({TITLE})")
        messagebox.showinfo("Xuất CSV", f"Đã xuất file:\n{path}")


class AdvancedSearchDialog(tk.Toplevel):
    def __init__(self, tab):
        super().__init__(tab.app)
        self.tab = tab
        shell = DialogShell(self, "Tìm kiếm nâng cao", width=440, height=400, min_height=360)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar(value=tab.adv_filters.get(k, "")) for k in
                 ("ho_ten", "tu_ngay", "so_quyet_dinh", "cap_bac_moi")}

        def row(r, label, widget):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Họ và tên cán bộ", ttk.Entry(form, textvariable=self.v["ho_ten"], width=24))
        row(1, "Từ ngày (dd/mm/yyyy)", ttk.Entry(form, textvariable=self.v["tu_ngay"], width=24))
        row(2, "Số quyết định", ttk.Entry(form, textvariable=self.v["so_quyet_dinh"], width=24))
        row(3, "Cấp bậc (mới)", ttk.Combobox(form, textvariable=self.v["cap_bac_moi"],
                                             values=[""] + cand_data.CAP_BAC, state="readonly", width=22))

        RoundedButton(shell.footer, text="Áp dụng", command=self.apply, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Xóa bộ lọc", command=self.clear, variant="secondary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Đóng", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)
        center(self, 440, 400)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def apply(self):
        filters = {k: v.get().strip() for k, v in self.v.items() if v.get().strip()}
        if filters.get("tu_ngay") and not _to_key(filters["tu_ngay"]):
            messagebox.showwarning("Sai định dạng", "Từ ngày phải theo dạng dd/mm/yyyy.", parent=self)
            return
        self.tab.apply_advanced(filters)
        self.destroy()

    def clear(self):
        self.tab.adv_filters = {}
        self.tab.adv_note.set("")
        self.tab.refresh()
        self.destroy()


class EntryFormDialog(tk.Toplevel):
    def __init__(self, tab, row=None):
        super().__init__(tab.app)
        self.tab, self.db, self.row = tab, tab.db, row
        is_edit = row is not None
        self.pending_file = None

        shell = DialogShell(self, "Sửa quyết định nâng lương / thăng cấp" if is_edit
                            else "Thêm quyết định nâng lương / thăng cấp",
                            width=520, height=600, min_height=520)
        form = shell.body
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Cán bộ *", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.picker = EmployeePicker(form, self.db, width=27)
        self.picker.grid(row=0, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Loại *", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_loai = tk.StringVar(value=tab.loai_values[0])
        c_loai = ttk.Combobox(form, textvariable=self.v_loai, values=LOAI_OPTIONS, state="readonly", width=25)
        c_loai.grid(row=1, column=1, pady=6, sticky="ew")
        c_loai.bind("<<ComboboxSelected>>", lambda e: self._on_loai_change())

        ttk.Label(form, text="Ngày quyết định (dd/mm/yyyy)", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_ngay = tk.StringVar()
        DateEntry(form, textvariable=self.v_ngay, width=22).grid(row=2, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Số quyết định", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_soqd = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_soqd, width=27).grid(row=3, column=1, pady=6, sticky="ew")

        self.v_cap_label = tk.StringVar()
        ttk.Label(form, textvariable=self.v_cap_label, style="Card.TLabel").grid(
            row=4, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_capmoi = tk.StringVar()
        ttk.Combobox(form, textvariable=self.v_capmoi, values=[""] + cand_data.CAP_BAC,
                    state="readonly", width=25).grid(row=4, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Nội dung (không bắt buộc)", style="Card.TLabel").grid(
            row=5, column=0, sticky="nw", pady=6, padx=(0, 10))
        self.txt_noidung = tk.Text(form, width=22, height=3, font=("Segoe UI", 10), wrap="word",
                                   highlightthickness=1, highlightbackground=C["border"], relief="flat")
        self.txt_noidung.grid(row=5, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Ghi chú", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_note = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_note, width=27).grid(row=6, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="File đính kèm", style="Card.TLabel").grid(row=7, column=0, sticky="w", pady=6, padx=(0, 10))
        file_row = ttk.Frame(form, style="Card.TFrame")
        file_row.grid(row=7, column=1, pady=6, sticky="ew")
        self.v_filename = tk.StringVar(value="(chưa có file)")
        ttk.Label(file_row, textvariable=self.v_filename, style="CardMuted.TLabel", wraplength=180).pack(side="left")
        RoundedButton(file_row, text="📎  Chọn file...", command=self._pick_file, variant="secondary").pack(
            side="left", padx=(8, 0))

        self.v_sync = tk.BooleanVar()
        ttk.Checkbutton(form, text="Cập nhật cấp bậc hiện tại của cán bộ theo lựa chọn này",
                        variable=self.v_sync, style="Card.TCheckbutton").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))

        if is_edit:
            self.picker.set_by_id(row["can_bo_id"])
            self.v_loai.set(row["loai"])
            self.v_ngay.set(row["ngay_quyet_dinh"] or "")
            self.v_soqd.set(row["so_quyet_dinh"] or "")
            self.v_capmoi.set(row["cap_bac_moi"] or "")
            self.txt_noidung.insert("1.0", row["noi_dung"] or "")
            self.v_note.set(row["ghi_chu"] or "")
            if row["file_dinh_kem"]:
                self.v_filename.set(attachments.display_name(row["file_dinh_kem"]))

        self._on_loai_change(set_sync=not is_edit)

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Thêm"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)

        center(self, 520, 600)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _is_promotion(self):
        return self.v_loai.get() in LOAI_THANG_CAP

    def _on_loai_change(self, set_sync=True):
        promo = self._is_promotion()
        self.v_cap_label.set("Cấp bậc mới *" if promo else "Cấp bậc mới (nếu có)")
        if set_sync:
            self.v_sync.set(promo)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file đính kèm",
            filetypes=[("Tài liệu", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"), ("Tất cả file", "*.*")])
        if path:
            self.pending_file = path
            self.v_filename.set(os.path.basename(path) + "  (chưa lưu)")

    def _validate_date(self):
        d = self.v_ngay.get().strip()
        if not d:
            return True
        try:
            datetime.datetime.strptime(d, "%d/%m/%Y")
            return True
        except ValueError:
            messagebox.showwarning("Sai định dạng", "Ngày quyết định phải theo dạng dd/mm/yyyy.", parent=self)
            return False

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn một cán bộ.", parent=self)
            return
        if self._is_promotion() and not self.v_capmoi.get():
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn Cấp bậc mới.", parent=self)
            return
        if not self._validate_date():
            return
        data = dict(can_bo_id=emp_id, loai=self.v_loai.get(), ngay_quyet_dinh=self.v_ngay.get().strip(),
                   so_quyet_dinh=self.v_soqd.get().strip(), cap_bac_moi=self.v_capmoi.get().strip() or None,
                   noi_dung=self.txt_noidung.get("1.0", "end").strip(), ghi_chu=self.v_note.get().strip())
        if self.pending_file:
            new_rel = attachments.save_attachment(self.tab.app.app_dir, TABLE, self.pending_file)
            if self.row is not None and self.row["file_dinh_kem"]:
                attachments.delete_attachment(self.tab.app.app_dir, self.row["file_dinh_kem"])
            data["file_dinh_kem"] = new_rel
        if self.row is None:
            data.setdefault("file_dinh_kem", None)
            data["created_by"] = self.tab.app.user["username"]
            self.db.insert(TABLE, data)
            self.db.log(self.tab.app.user["username"], "Thêm quyết định nâng lương/thăng cấp",
                        f"{self.db.employee_label(emp_id)} - {data['loai']}")
            self.tab.app.status.set("Đã lưu.")
        else:
            self.db.update(TABLE, self.row["id"], data)
            self.db.log(self.tab.app.user["username"], "Sửa quyết định nâng lương/thăng cấp",
                        f"{self.db.employee_label(emp_id)} - {data['loai']}")
            self.tab.app.status.set("Đã cập nhật.")
        if self.v_sync.get() and data["cap_bac_moi"]:
            self.db.update("can_bo", emp_id, {"cap_bac": data["cap_bac_moi"]})
            self.db.log(self.tab.app.user["username"], "Đồng bộ cấp bậc cán bộ",
                        f"{self.db.employee_label(emp_id)} -> {data['cap_bac_moi']}")
        self.tab.refresh()
        self.destroy()
