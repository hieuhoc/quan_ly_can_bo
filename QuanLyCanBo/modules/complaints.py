# -*- coding: utf-8 -*-
"""Module: Đơn thư, khiếu nại, tố cáo liên quan đến cán bộ."""
import csv
import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import attachments
from core.theme import C, center, make_card
from core.widgets import DialogShell, EmployeePicker, RoundedButton, make_tree

MODULE_ID = "complaints"
TABLE = "don_thu"
LOAI_OPTIONS = ["Đơn thư", "Khiếu nại", "Tố cáo", "Phản ánh"]
TRANG_THAI_OPTIONS = ["Mới tiếp nhận", "Đang xác minh", "Đang xử lý", "Đã giải quyết", "Tồn đọng"]

COLS = [("tieu_de", "Tiêu đề", 170), ("loai", "Loại", 85), ("ho_ten", "Cán bộ liên quan", 130),
        ("nguoi_gui", "Người gửi", 100), ("ngay_nhan", "Ngày nhận", 85),
        ("trang_thai", "Trạng thái", 110), ("file_dinh_kem", "File", 70)]


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
        ttk.Label(top, text="Đơn thư - Khiếu nại", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.count_var, style="CardMuted.TLabel").pack(side="right")
        tk.Frame(card, height=2, width=44, bg=C["gold"]).pack(anchor="w", pady=(4, 10))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="🔍", style="Card.TLabel").pack(side="left")
        ttk.Entry(bar, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=8)
        RoundedButton(bar, text="Xóa lọc", command=lambda: self.search_var.set(""), variant="secondary").pack(side="left")
        RoundedButton(bar, text="🔎  Tìm nâng cao", command=self.open_advanced_search, variant="secondary").pack(side="left", padx=(6, 0))
        self.search_var.trace_add("write", self._on_simple_search_typed)

        note_row = ttk.Frame(card, style="Card.TFrame")
        note_row.pack(fill="x", pady=(0, 8))
        ttk.Label(note_row, textvariable=self.adv_note, style="Error.TLabel").pack(side="left")

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.btn_add = RoundedButton(toolbar, text="➕  Thêm mới", command=self.open_add, variant="primary")
        self.btn_edit = RoundedButton(toolbar, text="✏  Sửa / Cập nhật", command=self.open_edit, variant="secondary")
        self.btn_del = RoundedButton(toolbar, text="🗑  Xóa", command=self.on_delete, variant="danger")
        self.btn_open_file = RoundedButton(toolbar, text="📎  Mở file đính kèm", command=self.open_attachment, variant="secondary")
        self.btn_export = RoundedButton(toolbar, text="📤  Xuất CSV", command=self.export_csv, variant="secondary")
        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_open_file, self.btn_export):
            b.pack(side="left", padx=(0, 6))

        self.tree, wrap = make_tree(card, COLS)
        wrap.pack(fill="both", expand=True)
        self.tree.tag_configure("done", foreground="#1F8A4C")
        self.tree.tag_configure("pending", foreground="#C62828")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.on_delete())
        self.tree.bind("<Double-1>", lambda e: self.open_edit())

    def apply_permissions(self):
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
        self.adv_filters = filters
        self.adv_note.set(f"Đang áp dụng tìm kiếm nâng cao ({len(filters)} tiêu chí) — "
                          "gõ vào ô tìm kiếm thường để bỏ lọc này.")
        self.search_var.set("")
        self.refresh()

    def _rows(self):
        sql = "SELECT d.*, c.ho_ten AS ho_ten FROM don_thu d LEFT JOIN can_bo c ON c.id = d.can_bo_id"
        conds, params = [], []
        if self.adv_filters:
            f = self.adv_filters
            if f.get("tieu_de"):
                conds.append("d.tieu_de LIKE ?"); params.append(f"%{f['tieu_de']}%")
            if f.get("loai"):
                conds.append("d.loai = ?"); params.append(f["loai"])
            if f.get("trang_thai"):
                conds.append("d.trang_thai = ?"); params.append(f["trang_thai"])
            if f.get("nguoi_gui"):
                conds.append("d.nguoi_gui LIKE ?"); params.append(f"%{f['nguoi_gui']}%")
            if f.get("tu_ngay"):
                conds.append("d.ngay_nhan >= ?"); params.append(f["tu_ngay"])
        elif self.search_var.get().strip():
            like = f"%{self.search_var.get().strip()}%"
            conds.append("(d.tieu_de LIKE ? OR d.nguoi_gui LIKE ? OR d.trang_thai LIKE ? "
                         "OR c.ho_ten LIKE ? OR d.noi_dung LIKE ?)")
            params.extend([like] * 5)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY (d.ngay_nhan IS NULL), d.ngay_nhan DESC, d.created_at DESC"
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self._rows()
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            if r["trang_thai"] == "Đã giải quyết":
                tag = "done"
            elif r["trang_thai"] == "Tồn đọng":
                tag = "pending"
            vals = [r[c[0]] or "" for c in COLS[:-1]] + ["📎 Có" if r["file_dinh_kem"] else "—"]
            self.tree.insert("", "end", iid=str(r["id"]), values=vals, tags=(tag,))
        self.count_var.set(f"Tổng số: {len(rows)} đơn")

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
            messagebox.showinfo("Chưa chọn", "Hãy chọn một đơn thư trong danh sách để sửa.")
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
            messagebox.showinfo("Chưa chọn", "Hãy chọn một đơn thư để xóa.")
            return
        row = self._current_row()
        if messagebox.askyesno("Xác nhận xóa", f"Xóa đơn thư '{row['tieu_de']}'?\nThao tác không thể hoàn tác."):
            if row["file_dinh_kem"]:
                attachments.delete_attachment(self.app.app_dir, row["file_dinh_kem"])
            self.db.delete(TABLE, self.selected_id)
            self.db.log(self.app.user["username"], "Xóa đơn thư/khiếu nại", row["tieu_de"])
            self.selected_id = None
            self.refresh()
            self._refresh_button_states()
            self.app.status.set("Đã xóa đơn thư.")

    def export_csv(self):
        if self.deny("export"):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=datetime.datetime.now().strftime("don_thu_khieu_nai_%Y%m%d.csv"))
        if not path:
            return
        rows = self._rows()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Tiêu đề", "Loại", "Cán bộ liên quan", "Người gửi", "Ngày nhận", "Nội dung",
                       "Trạng thái", "Ngày giải quyết", "Kết quả xử lý", "Ghi chú"])
            for r in rows:
                w.writerow([r["tieu_de"], r["loai"], r["ho_ten"] or "", r["nguoi_gui"] or "",
                           r["ngay_nhan"] or "", r["noi_dung"] or "", r["trang_thai"],
                           r["ngay_giai_quyet"] or "", r["ket_qua"] or "", r["ghi_chu"] or ""])
        self.db.log(self.app.user["username"], "Xuất CSV", f"{len(rows)} bản ghi (đơn thư)")
        messagebox.showinfo("Xuất CSV", f"Đã xuất file:\n{path}")


class AdvancedSearchDialog(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel.app)
        self.panel = panel
        shell = DialogShell(self, "Tìm kiếm nâng cao", width=440, height=440, min_height=400)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar(value=panel.adv_filters.get(k, "")) for k in
                 ("tieu_de", "loai", "trang_thai", "nguoi_gui", "tu_ngay")}

        def row(r, label, widget):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Tiêu đề", ttk.Entry(form, textvariable=self.v["tieu_de"], width=24))
        row(1, "Loại", ttk.Combobox(form, textvariable=self.v["loai"], values=[""] + LOAI_OPTIONS,
                                    state="readonly", width=22))
        row(2, "Trạng thái", ttk.Combobox(form, textvariable=self.v["trang_thai"], values=[""] + TRANG_THAI_OPTIONS,
                                          state="readonly", width=22))
        row(3, "Người gửi", ttk.Entry(form, textvariable=self.v["nguoi_gui"], width=24))
        row(4, "Nhận từ ngày (dd/mm/yyyy)", ttk.Entry(form, textvariable=self.v["tu_ngay"], width=24))

        RoundedButton(shell.footer, text="Áp dụng", command=self.apply, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Xóa bộ lọc", command=self.clear, variant="secondary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Đóng", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)
        center(self, 440, 440)
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


class EntryFormDialog(tk.Toplevel):
    def __init__(self, panel, row=None):
        super().__init__(panel.app)
        self.panel, self.db, self.row = panel, panel.db, row
        is_edit = row is not None
        self.pending_file = None

        shell = DialogShell(self, "Sửa đơn thư/khiếu nại" if is_edit else "Thêm đơn thư/khiếu nại mới",
                            width=560, height=680)
        form = shell.body
        form.columnconfigure(1, weight=1)

        r = 0

        def add_row(label, widget, sticky="ew"):
            nonlocal r
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="nw", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, pady=6, sticky=sticky)
            r += 1

        self.v_title = tk.StringVar()
        add_row("Tiêu đề *", ttk.Entry(form, textvariable=self.v_title, width=28))

        self.v_loai = tk.StringVar(value=LOAI_OPTIONS[0])
        add_row("Loại *", ttk.Combobox(form, textvariable=self.v_loai, values=LOAI_OPTIONS, state="readonly", width=26))

        self.picker = EmployeePicker(form, self.db, width=27)
        add_row("Cán bộ liên quan", self.picker)

        self.v_nguoigui = tk.StringVar()
        add_row("Người gửi đơn", ttk.Entry(form, textvariable=self.v_nguoigui, width=28))

        self.v_ngaynhan = tk.StringVar()
        add_row("Ngày nhận (dd/mm/yyyy)", ttk.Entry(form, textvariable=self.v_ngaynhan, width=28))

        self.txt_noidung = tk.Text(form, width=23, height=4, font=("Segoe UI", 10), wrap="word",
                                   highlightthickness=1, highlightbackground=C["border"], relief="flat")
        add_row("Nội dung", self.txt_noidung)

        self.v_status = tk.StringVar(value=TRANG_THAI_OPTIONS[0])
        add_row("Trạng thái *", ttk.Combobox(form, textvariable=self.v_status, values=TRANG_THAI_OPTIONS,
                                             state="readonly", width=26))

        self.v_ngaygq = tk.StringVar()
        add_row("Ngày giải quyết (dd/mm/yyyy)", ttk.Entry(form, textvariable=self.v_ngaygq, width=28))

        self.txt_ketqua = tk.Text(form, width=23, height=3, font=("Segoe UI", 10), wrap="word",
                                  highlightthickness=1, highlightbackground=C["border"], relief="flat")
        add_row("Kết quả xử lý", self.txt_ketqua)

        self.v_note = tk.StringVar()
        add_row("Ghi chú", ttk.Entry(form, textvariable=self.v_note, width=28))

        file_row = ttk.Frame(form, style="Card.TFrame")
        self.v_filename = tk.StringVar(value="(chưa có file)")
        ttk.Label(file_row, textvariable=self.v_filename, style="CardMuted.TLabel", wraplength=180).pack(side="left")
        RoundedButton(file_row, text="📎  Chọn file...", command=self._pick_file, variant="secondary").pack(side="left", padx=(8, 0))
        add_row("File đính kèm", file_row)

        if is_edit:
            self.v_title.set(row["tieu_de"])
            self.v_loai.set(row["loai"])
            self.picker.set_by_id(row["can_bo_id"])
            self.v_nguoigui.set(row["nguoi_gui"] or "")
            self.v_ngaynhan.set(row["ngay_nhan"] or "")
            self.txt_noidung.insert("1.0", row["noi_dung"] or "")
            self.v_status.set(row["trang_thai"])
            self.v_ngaygq.set(row["ngay_giai_quyet"] or "")
            self.txt_ketqua.insert("1.0", row["ket_qua"] or "")
            self.v_note.set(row["ghi_chu"] or "")
            if row["file_dinh_kem"]:
                self.v_filename.set(attachments.display_name(row["file_dinh_kem"]))

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Thêm mới"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self, 560, 680)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file đính kèm",
            filetypes=[("Tài liệu", "*.pdf *.doc *.docx *.jpg *.jpeg *.png"), ("Tất cả file", "*.*")])
        if path:
            self.pending_file = path
            self.v_filename.set(os.path.basename(path) + "  (chưa lưu)")

    def _validate(self):
        if not self.v_title.get().strip():
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Tiêu đề.", parent=self)
            return False
        for label, val in (("Ngày nhận", self.v_ngaynhan.get().strip()),
                           ("Ngày giải quyết", self.v_ngaygq.get().strip())):
            if val:
                try:
                    datetime.datetime.strptime(val, "%d/%m/%Y")
                except ValueError:
                    messagebox.showwarning("Sai định dạng", f"{label} phải theo dạng dd/mm/yyyy.", parent=self)
                    return False
        return True

    def save(self):
        if not self._validate():
            return
        data = dict(
            tieu_de=self.v_title.get().strip(), loai=self.v_loai.get(),
            can_bo_id=self.picker.get(), nguoi_gui=self.v_nguoigui.get().strip(),
            ngay_nhan=self.v_ngaynhan.get().strip(),
            noi_dung=self.txt_noidung.get("1.0", "end").strip(),
            trang_thai=self.v_status.get(), ngay_giai_quyet=self.v_ngaygq.get().strip(),
            ket_qua=self.txt_ketqua.get("1.0", "end").strip(), ghi_chu=self.v_note.get().strip(),
        )
        if self.pending_file:
            new_rel = attachments.save_attachment(self.panel.app.app_dir, TABLE, self.pending_file)
            if self.row is not None and self.row["file_dinh_kem"]:
                attachments.delete_attachment(self.panel.app.app_dir, self.row["file_dinh_kem"])
            data["file_dinh_kem"] = new_rel
        if self.row is None:
            data.setdefault("file_dinh_kem", None)
            data["created_by"] = self.panel.app.user["username"]
            self.db.insert(TABLE, data)
            self.db.log(self.panel.app.user["username"], "Tạo đơn thư/khiếu nại", data["tieu_de"])
            self.panel.app.status.set("Đã lưu đơn thư mới.")
        else:
            self.db.update(TABLE, self.row["id"], data)
            self.db.log(self.panel.app.user["username"], "Cập nhật đơn thư/khiếu nại",
                        f"{data['tieu_de']} -> {data['trang_thai']}")
            self.panel.app.status.set("Đã cập nhật đơn thư.")
        self.panel.refresh()
        self.destroy()
