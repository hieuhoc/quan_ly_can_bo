# -*- coding: utf-8 -*-
"""Module: Nâng lương - Thăng cấp bậc hàm.

Nâng lương và thăng cấp bậc hàm là MỘT quá trình không tách rời: mỗi bản
ghi là một quyết định, ghi cấp bậc mới và hệ số lương mới của cán bộ (có
thể chỉ thay đổi một trong hai). Tất cả nằm trong một bảng, sắp theo ngày
quyết định mới nhất lên đầu.

Dữ liệu từ bản cũ (loại "Nâng lương định kỳ / trước hạn", "Thăng cấp bậc
hàm") vẫn hiển thị nguyên như trước trong cột Hình thức."""
import csv
import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import attachments, cand_data
from core.theme import C, center, make_card
from core.widgets import DateEntry, DialogShell, EmployeePicker, FilterCombo, RoundedButton, make_tree

MODULE_ID = "salary"
TABLE = "qua_trinh_luong"
TITLE = "Nâng lương - Thăng cấp"
HINH_THUC = ["Định kỳ", "Trước hạn"]

COLS = [("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160), ("loai", "Hình thức", 100),
        ("ngay_quyet_dinh", "Ngày QĐ", 100), ("so_quyet_dinh", "Số quyết định", 130),
        ("cap_bac_moi", "Cấp bậc mới", 110), ("he_so_luong_moi", "Hệ số lương mới", 110),
        ("nguoi_ky", "Người ký", 120), ("noi_dung", "Nội dung", 180), ("file_dinh_kem", "File", 70)]


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
        self._build()
        self._refresh_button_states()
        self.refresh()

    def _build(self):
        lo, card = make_card(self, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Nâng lương - Thăng cấp bậc hàm", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.count_var, style="CardMuted.TLabel").pack(side="right")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))

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
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.on_delete())
        self.tree.bind("<Double-1>", lambda e: self.open_edit())

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
        sql = ("SELECT q.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM qua_trinh_luong q "
               "JOIN can_bo c ON c.id = q.can_bo_id WHERE 1=1")
        params = []
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
            sql += (" AND (c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR q.noi_dung LIKE ? OR q.so_quyet_dinh LIKE ?"
                    " OR q.cap_bac_moi LIKE ? OR q.nguoi_ky LIKE ?)")
            params.extend([like] * 6)
        sql += (" ORDER BY (q.ngay_quyet_dinh IS NULL OR q.ngay_quyet_dinh==''), "
                f"{_date_key('q.ngay_quyet_dinh')} DESC, q.created_at DESC")
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self._rows()
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            vals = [r[c[0]] or "" for c in COLS[:-1]] + ["📎 Có" if r["file_dinh_kem"] else "—"]
            self.tree.insert("", "end", iid=str(r["id"]), values=vals, tags=("odd" if i % 2 else "even",))
        self.count_var.set(f"Tổng số: {len(rows)} quyết định")

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
            self.db.log(self.app.user["username"], "Xóa quyết định nâng lương - thăng cấp",
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
            w.writerow(["Mã cán bộ", "Họ và tên", "Hình thức", "Ngày quyết định", "Số quyết định",
                        "Cấp bậc mới", "Hệ số lương mới", "Người ký", "Nội dung", "Ghi chú"])
            for r in rows:
                w.writerow([r["ma_cb"], r["ho_ten"], r["loai"], r["ngay_quyet_dinh"] or "",
                            r["so_quyet_dinh"] or "", r["cap_bac_moi"] or "", r["he_so_luong_moi"] or "",
                            r["nguoi_ky"] or "", r["noi_dung"] or "", r["ghi_chu"] or ""])
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
    """Thêm / sửa MỘT quyết định nâng lương - thăng cấp bậc hàm."""

    def __init__(self, tab, row=None):
        super().__init__(tab.app)
        self.tab, self.db, self.row = tab, tab.db, row
        is_edit = row is not None
        self.pending_file = None

        shell = DialogShell(self, "Sửa quyết định nâng lương - thăng cấp" if is_edit
                            else "Thêm quyết định nâng lương - thăng cấp",
                            width=540, height=680, min_height=520)
        form = shell.body
        form.columnconfigure(1, weight=1)
        r = 0

        def label(text, sticky="w"):
            ttk.Label(form, text=text, style="Card.TLabel").grid(row=r, column=0, sticky=sticky, pady=6, padx=(0, 10))

        label("Cán bộ *")
        self.picker = EmployeePicker(form, self.db, width=27)
        self.picker.grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Hình thức *")
        self.v_loai = tk.StringVar(value=HINH_THUC[0])
        ttk.Combobox(form, textvariable=self.v_loai, values=HINH_THUC, state="readonly", width=25).grid(
            row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Ngày quyết định")
        self.v_ngay = tk.StringVar()
        DateEntry(form, textvariable=self.v_ngay, width=22).grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Số quyết định")
        self.v_soqd = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_soqd, width=27).grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Người ký")
        self.v_nguoiky = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_nguoiky, width=27).grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Cấp bậc mới")
        self.v_capmoi = tk.StringVar()
        c_cap = ttk.Combobox(form, textvariable=self.v_capmoi, values=[""] + cand_data.CAP_BAC,
                             state="readonly", width=25)
        c_cap.grid(row=r, column=1, pady=6, sticky="ew")
        c_cap.bind("<<ComboboxSelected>>", lambda e: self._on_rank_change())
        r += 1
        label("Hệ số lương mới")
        self.v_heso = tk.StringVar()
        FilterCombo(form, values=cand_data.HE_SO_LUONG_HOP_LE, width=25, textvariable=self.v_heso).grid(
            row=r, column=1, pady=6, sticky="ew")
        r += 1
        ttk.Label(form, text="Nhập cấp bậc mới, hệ số lương mới hoặc cả hai (hệ số tự điền theo cấp bậc, "
                             "có thể sửa lại).", style="CardMuted.TLabel", wraplength=420).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
        r += 1
        label("Nội dung", sticky="nw")
        self.txt_noidung = tk.Text(form, width=22, height=3, font=("Segoe UI", 10), wrap="word",
                                   highlightthickness=1, highlightbackground=C["border"], relief="flat")
        self.txt_noidung.grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("Ghi chú")
        self.v_note = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_note, width=27).grid(row=r, column=1, pady=6, sticky="ew")
        r += 1
        label("File đính kèm")
        file_row = ttk.Frame(form, style="Card.TFrame")
        file_row.grid(row=r, column=1, pady=6, sticky="ew")
        self.v_filename = tk.StringVar(value="(chưa có file)")
        ttk.Label(file_row, textvariable=self.v_filename, style="CardMuted.TLabel", wraplength=180).pack(side="left")
        RoundedButton(file_row, text="📎  Chọn file...", command=self._pick_file, variant="secondary").pack(
            side="left", padx=(8, 0))
        r += 1
        self.v_sync = tk.BooleanVar(value=not is_edit)
        ttk.Checkbutton(form, text="Cập nhật cấp bậc và hệ số lương hiện tại của cán bộ theo quyết định này",
                        variable=self.v_sync, style="Card.TCheckbutton").grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))

        if is_edit:
            self.picker.set_by_id(row["can_bo_id"])
            self.v_loai.set(row["loai"])
            self.v_ngay.set(row["ngay_quyet_dinh"] or "")
            self.v_soqd.set(row["so_quyet_dinh"] or "")
            self.v_nguoiky.set(row["nguoi_ky"] or "")
            self.v_capmoi.set(row["cap_bac_moi"] or "")
            self.v_heso.set(row["he_so_luong_moi"] or "")
            self.txt_noidung.insert("1.0", row["noi_dung"] or "")
            self.v_note.set(row["ghi_chu"] or "")
            if row["file_dinh_kem"]:
                self.v_filename.set(attachments.display_name(row["file_dinh_kem"]))

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Thêm"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)

        center(self, 540, 680)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _on_rank_change(self):
        coef = cand_data.HE_SO_LUONG_THEO_CAP_BAC.get(self.v_capmoi.get())
        if coef:
            self.v_heso.set(coef)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            parent=self, title="Chọn file đính kèm",
            filetypes=[("Tài liệu", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"), ("Tất cả file", "*.*")])
        if path:
            self.pending_file = path
            self.v_filename.set(os.path.basename(path) + "  (chưa lưu)")

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn một cán bộ.", parent=self)
            return
        cap, heso = self.v_capmoi.get().strip(), self.v_heso.get().strip().replace(",", ".")
        if not cap and not heso:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Cấp bậc mới hoặc Hệ số lương mới.", parent=self)
            return
        if heso:
            try:
                float(heso)
            except ValueError:
                messagebox.showwarning("Sai định dạng", "Hệ số lương phải là số, vd 4.60.", parent=self)
                return
        ngay = self.v_ngay.get().strip()
        if ngay and not _to_key(ngay):
            messagebox.showwarning("Sai định dạng", "Ngày quyết định phải theo dạng dd/mm/yyyy.", parent=self)
            return
        data = dict(can_bo_id=emp_id, loai=self.v_loai.get(), ngay_quyet_dinh=ngay,
                    so_quyet_dinh=self.v_soqd.get().strip(), nguoi_ky=self.v_nguoiky.get().strip(),
                    cap_bac_moi=cap or None, he_so_luong_moi=heso or None,
                    noi_dung=self.txt_noidung.get("1.0", "end").strip(), ghi_chu=self.v_note.get().strip())
        user = self.tab.app.user["username"]
        if self.pending_file:
            new_rel = attachments.save_attachment(self.tab.app.app_dir, TABLE, self.pending_file)
            if self.row is not None and self.row["file_dinh_kem"]:
                attachments.delete_attachment(self.tab.app.app_dir, self.row["file_dinh_kem"])
            data["file_dinh_kem"] = new_rel
        change = " / ".join(x for x in (cap, f"hệ số {heso}" if heso else "") if x)
        if self.row is None:
            data.setdefault("file_dinh_kem", None)
            data["created_by"] = user
            self.db.insert(TABLE, data)
            self.db.log(user, "Thêm quyết định nâng lương - thăng cấp", f"{self.db.employee_label(emp_id)}: {change}")
            self.tab.app.status.set("Đã lưu.")
        else:
            self.db.update(TABLE, self.row["id"], data)
            self.db.log(user, "Sửa quyết định nâng lương - thăng cấp", f"{self.db.employee_label(emp_id)}: {change}")
            self.tab.app.status.set("Đã cập nhật.")
        if self.v_sync.get():
            upd = {}
            if cap:
                upd["cap_bac"] = cap
            if heso:
                upd["he_so_luong"] = heso
            self.db.update("can_bo", emp_id, upd)
            self.db.log(user, "Đồng bộ cấp bậc / hệ số lương cán bộ", f"{self.db.employee_label(emp_id)} -> {change}")
        self.tab.refresh()
        self.destroy()
