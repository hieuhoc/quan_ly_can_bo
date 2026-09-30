# -*- coding: utf-8 -*-
"""Module: Phân loại, đánh giá, chấm điểm cán bộ theo tháng / quý / năm."""
import csv
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.theme import C, center, make_card
from core.widgets import DialogShell, EmployeePicker, RoundedButton, make_tree

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

COLS = [("ho_ten", "Cán bộ", 150), ("loai", "Loại kỳ", 65), ("ky", "Kỳ đánh giá", 105),
        ("xep_loai", "Xếp loại", 170), ("diem", "Điểm", 60), ("ghi_chu", "Ghi chú", 130)]


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


def _ky_trong_nam_tu_ky_so(loai, ky_so):
    if loai == "Tháng" and ky_so:
        return THANG_LABELS[ky_so - 1]
    if loai == "Quý" and ky_so:
        return QUY_LABELS[ky_so - 1]
    return ""


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.selected_id = None
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.adv_filters = {}
        self.adv_note = tk.StringVar()
        self.grid_tree = None
        self._build()
        self.apply_permissions()
        self.refresh()

    def _build(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        tab_list = ttk.Frame(self.nb, padding=(0, 10, 0, 0))
        tab_grid = ttk.Frame(self.nb, padding=(0, 10, 0, 0))
        self.nb.add(tab_list, text="  📋  Danh sách chi tiết  ")
        self.nb.add(tab_grid, text="  📊  Bảng tổng hợp theo kỳ  ")
        self._build_list_tab(tab_list)
        self._build_grid_tab(tab_grid)
        # Hai tab cùng đọc từ một bảng dữ liệu nên luôn khớp nhau, nhưng để
        # chắc chắn người dùng không bao giờ thấy số liệu cũ, tự làm mới
        # bảng tổng hợp mỗi khi chuyển sang đúng tab đó.
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, _e=None):
        if self.nb.index(self.nb.select()) == 1:
            self.refresh_grid()
        else:
            self.refresh()

    # ---------------------------------------------------------- tab danh sách
    def _build_list_tab(self, parent):
        lo, card = make_card(parent, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Danh sách chi tiết phân loại", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.count_var, style="CardMuted.TLabel").pack(side="right")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="🔍", style="Card.TLabel").pack(side="left")
        ttk.Entry(bar, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=8)
        RoundedButton(bar, text="Xóa lọc", command=lambda: self.search_var.set(""), variant="secondary").pack(side="left")
        RoundedButton(bar, text="🔎  Tìm nâng cao", command=self.open_advanced_search, variant="secondary").pack(
            side="left", padx=(6, 0))
        self.search_var.trace_add("write", self._on_simple_search_typed)

        note_row = ttk.Frame(card, style="Card.TFrame")
        note_row.pack(fill="x", pady=(0, 8))
        ttk.Label(note_row, textvariable=self.adv_note, style="Error.TLabel").pack(side="left")

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.btn_add = RoundedButton(toolbar, text="➕  Thêm mới", command=self.open_add, variant="primary")
        self.btn_del = RoundedButton(toolbar, text="🗑  Xóa", command=self.on_delete, variant="danger")
        self.btn_export = RoundedButton(toolbar, text="📤  Xuất CSV", command=self.export_csv, variant="secondary")
        for b in (self.btn_add, self.btn_del, self.btn_export):
            b.pack(side="left", padx=(0, 6))

        self.tree, wrap = make_tree(card, COLS)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda e: self.on_delete())

    # ---------------------------------------------------------- tab bảng tổng hợp
    def _build_grid_tab(self, parent):
        lo, card = make_card(parent, padding=16)
        lo.pack(fill="both", expand=True)
        ttk.Label(card, text="Bảng tổng hợp xếp loại theo kỳ", style="CardTitle.TLabel").pack(anchor="w")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Xem theo:", style="Card.TLabel").pack(side="left")
        self.v_grid_loai = tk.StringVar(value="Tháng")
        c1 = ttk.Combobox(bar, textvariable=self.v_grid_loai, values=["Tháng", "Quý"], state="readonly", width=8)
        c1.pack(side="left", padx=(4, 16))
        c1.bind("<<ComboboxSelected>>", lambda e: self._grid_loai_changed())
        ttk.Label(bar, text="Năm:", style="Card.TLabel").pack(side="left")
        self.v_grid_nam = tk.StringVar(value=str(_current_year()))
        ttk.Combobox(bar, textvariable=self.v_grid_nam, values=_nam_values(), width=8).pack(side="left", padx=(4, 16))
        RoundedButton(bar, text="↻  Xem", command=self.refresh_grid, variant="primary").pack(side="left")
        RoundedButton(bar, text="📤  Xuất CSV", command=self.export_grid_csv, variant="secondary").pack(
            side="left", padx=(10, 0))

        bar2 = ttk.Frame(card, style="Card.TFrame")
        bar2.pack(fill="x", pady=(0, 10))
        ttk.Label(bar2, text="Tính điểm trung bình từ:", style="Card.TLabel").pack(side="left")
        self.v_range_from = tk.StringVar()
        self.c_range_from = ttk.Combobox(bar2, textvariable=self.v_range_from, values=THANG_LABELS,
                                         state="readonly", width=10)
        self.c_range_from.pack(side="left", padx=(4, 8))
        ttk.Label(bar2, text="đến:", style="Card.TLabel").pack(side="left")
        self.v_range_to = tk.StringVar()
        self.c_range_to = ttk.Combobox(bar2, textvariable=self.v_range_to, values=THANG_LABELS,
                                       state="readonly", width=10)
        self.c_range_to.pack(side="left", padx=(4, 8))
        RoundedButton(bar2, text="Tính điểm TB", command=self.refresh_grid, variant="secondary").pack(side="left")
        ttk.Label(bar2, text="   (mặc định tính trung bình toàn bộ các kỳ đang hiển thị)",
                 style="CardMuted.TLabel").pack(side="left", padx=(10, 0))
        ttk.Label(card, text="Xuất sắc / Tốt / HT / Không HT / — (chưa có) — số trong ngoặc là điểm đã chấm",
                 style="CardMuted.TLabel").pack(anchor="w", pady=(0, 6))

        self.grid_wrap = ttk.Frame(card, style="Card.TFrame")
        self.grid_wrap.pack(fill="both", expand=True)
        self._grid_periods = []
        self._grid_loai_changed()
        self.refresh_grid()

    def _grid_loai_changed(self):
        labels = THANG_LABELS if self.v_grid_loai.get() == "Tháng" else QUY_LABELS
        self.c_range_from.configure(values=labels)
        self.c_range_to.configure(values=labels)
        if self.v_range_from.get() not in labels:
            self.v_range_from.set(labels[0])
        if self.v_range_to.get() not in labels:
            self.v_range_to.set(labels[-1])

    def refresh_grid(self):
        loai = self.v_grid_loai.get()
        try:
            nam = int(self.v_grid_nam.get())
        except ValueError:
            messagebox.showwarning("Sai định dạng", "Năm không hợp lệ.")
            return
        all_periods = list(range(1, 13)) if loai == "Tháng" else list(range(1, 5))
        labels = THANG_LABELS if loai == "Tháng" else QUY_LABELS
        self._grid_periods = all_periods

        rng_from = labels.index(self.v_range_from.get()) + 1 if self.v_range_from.get() in labels else all_periods[0]
        rng_to = labels.index(self.v_range_to.get()) + 1 if self.v_range_to.get() in labels else all_periods[-1]
        if rng_from > rng_to:
            rng_from, rng_to = rng_to, rng_from
        avg_periods = [p for p in all_periods if rng_from <= p <= rng_to]

        for w in self.grid_wrap.winfo_children():
            w.destroy()
        cols = ([("stt", "STT", 40), ("ho_ten", "Họ và tên", 150), ("cap_bac", "Cấp bậc", 90),
                ("chuc_vu", "Chức vụ", 110), ("don_vi", "Đơn vị", 120)] +
               [(f"k{p}", labels[p - 1].replace("Tháng ", "Th.").replace("Quý ", "Q."), 62) for p in all_periods] +
               [("diem_tb", f"Điểm TB ({labels[rng_from-1].replace('Tháng ','Th.').replace('Quý ','Q.')}"
                           f"–{labels[rng_to-1].replace('Tháng ','Th.').replace('Quý ','Q.')})", 100)])
        tree, wrap = make_tree(self.grid_wrap, cols)
        wrap.pack(fill="both", expand=True)
        self.grid_tree = tree

        emps = self.db.conn.execute(
            "SELECT id, ho_ten, cap_bac, chuc_vu, don_vi FROM can_bo ORDER BY ho_ten COLLATE NOCASE").fetchall()
        data_rows = self.db.conn.execute(
            "SELECT can_bo_id, ky_so, xep_loai, diem FROM phan_loai_can_bo WHERE loai=? AND nam=? ORDER BY id",
            (loai, nam)).fetchall()
        by_emp = {}
        for r in data_rows:
            by_emp.setdefault(r["can_bo_id"], {})[r["ky_so"]] = (r["xep_loai"], r["diem"])

        for i, emp in enumerate(emps, start=1):
            emp_data = by_emp.get(emp["id"], {})
            vals = [i, emp["ho_ten"], emp["cap_bac"] or "—", emp["chuc_vu"] or "—", emp["don_vi"] or "—"]
            for p in all_periods:
                xep, diem = emp_data.get(p, (None, None))
                if xep is None:
                    vals.append("—")
                elif diem is not None:
                    vals.append(f"{XEP_LOAI_TAT.get(xep, xep)} ({diem:g})")
                else:
                    vals.append(XEP_LOAI_TAT.get(xep, xep))
            scores = [emp_data[p][1] for p in avg_periods if p in emp_data and emp_data[p][1] is not None]
            vals.append(f"{sum(scores)/len(scores):.1f}" if scores else "—")
            tree.insert("", "end", values=vals, tags=("odd" if i % 2 else "even",))

    def export_grid_csv(self):
        if self.deny("export"):
            return
        if self.grid_tree is None:
            return
        cols_text = [self.grid_tree.heading(c)["text"] for c in self.grid_tree["columns"]]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"bang_tong_hop_phan_loai_{self.v_grid_loai.get().lower()}_{self.v_grid_nam.get()}.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols_text)
            for iid in self.grid_tree.get_children():
                w.writerow(self.grid_tree.item(iid, "values"))
        self.db.log(self.app.user["username"], "Xuất CSV", "Bảng tổng hợp phân loại")
        messagebox.showinfo("Xuất CSV", f"Đã xuất file:\n{path}")

    # ---------------------------------------------------------- chung
    def apply_permissions(self):
        self._refresh_button_states()

    def _refresh_button_states(self):
        has_sel = self.selected_id is not None

        def st(b, ok):
            b.state(["!disabled"] if ok else ["disabled"])

        st(self.btn_add, self.app.can(MODULE_ID, "add"))
        st(self.btn_del, self.app.can(MODULE_ID, "delete") and has_sel)
        st(self.btn_export, self.app.can(MODULE_ID, "export"))

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
        sql = ("SELECT p.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM phan_loai_can_bo p "
              "JOIN can_bo c ON c.id = p.can_bo_id")
        conds, params = [], []
        if self.adv_filters:
            f = self.adv_filters
            if f.get("ho_ten"):
                conds.append("c.ho_ten LIKE ?"); params.append(f"%{f['ho_ten']}%")
            if f.get("loai"):
                conds.append("p.loai = ?"); params.append(f["loai"])
            if f.get("nam"):
                conds.append("p.nam = ?"); params.append(f["nam"])
            if f.get("xep_loai"):
                conds.append("p.xep_loai = ?"); params.append(f["xep_loai"])
        elif self.search_var.get().strip():
            like = f"%{self.search_var.get().strip()}%"
            conds.append("(c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR p.ky LIKE ? OR p.xep_loai LIKE ?)")
            params.extend([like] * 4)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY p.created_at DESC"
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self._rows()
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            vals = [r[c[0]] if r[c[0]] not in (None, "") else "" for c in COLS]
            self.tree.insert("", "end", iid=str(r["id"]), values=vals, tags=("odd" if i % 2 else "even",))
        self.count_var.set(f"Tổng số: {len(rows)} bản ghi")

    def on_select(self, _=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        self._refresh_button_states()

    def open_add(self):
        if self.deny("add"):
            return
        EntryFormDialog(self)

    def on_delete(self):
        if self.deny("delete"):
            return
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một bản ghi để xóa.")
            return
        if messagebox.askyesno("Xác nhận xóa", "Xóa bản ghi phân loại này?\nThao tác không thể hoàn tác."):
            self.db.delete(TABLE, self.selected_id)
            self.db.log(self.app.user["username"], "Xóa phân loại cán bộ", f"id={self.selected_id}")
            self.selected_id = None
            self.refresh()
            self.refresh_grid()
            self._refresh_button_states()
            self.app.status.set("Đã xóa bản ghi.")

    def export_csv(self):
        if self.deny("export"):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=datetime.datetime.now().strftime("phan_loai_can_bo_%Y%m%d.csv"))
        if not path:
            return
        rows = self._rows()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Mã cán bộ", "Họ và tên", "Loại kỳ", "Năm", "Kỳ đánh giá", "Xếp loại", "Điểm", "Ghi chú"])
            for r in rows:
                w.writerow([r["ma_cb"], r["ho_ten"], r["loai"], r["nam"] or "", r["ky"], r["xep_loai"],
                           r["diem"] if r["diem"] is not None else "", r["ghi_chu"] or ""])
        self.db.log(self.app.user["username"], "Xuất CSV", f"{len(rows)} bản ghi (phân loại)")
        messagebox.showinfo("Xuất CSV", f"Đã xuất file:\n{path}")


class AdvancedSearchDialog(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel.app)
        self.panel = panel
        shell = DialogShell(self, "Tìm kiếm nâng cao", width=440, height=360, min_height=320)
        form = shell.body
        form.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar(value=panel.adv_filters.get(k, "")) for k in
                 ("ho_ten", "loai", "nam", "xep_loai")}

        def row(r, label, widget):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Họ và tên cán bộ", ttk.Entry(form, textvariable=self.v["ho_ten"], width=24))
        row(1, "Loại kỳ", ttk.Combobox(form, textvariable=self.v["loai"], values=[""] + LOAI_OPTIONS,
                                       state="readonly", width=22))
        row(2, "Năm", ttk.Entry(form, textvariable=self.v["nam"], width=24))
        row(3, "Xếp loại", ttk.Combobox(form, textvariable=self.v["xep_loai"], values=[""] + XEP_LOAI_OPTIONS,
                                        state="readonly", width=22))

        RoundedButton(shell.footer, text="Áp dụng", command=self.apply, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Xóa bộ lọc", command=self.clear, variant="secondary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Đóng", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)
        center(self, 440, 360)
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
    """Popup nhập một kết quả phân loại / chấm điểm cán bộ."""

    def __init__(self, panel):
        super().__init__(panel.app)
        self.panel, self.db = panel, panel.db
        shell = DialogShell(self, "Thêm kết quả phân loại", width=480, height=520, min_height=460)
        form = shell.body
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Cán bộ *", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.picker = EmployeePicker(form, self.db, width=25)
        self.picker.grid(row=0, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Loại kỳ *", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_loai = tk.StringVar(value=LOAI_OPTIONS[0])
        self.c_loai = ttk.Combobox(form, textvariable=self.v_loai, values=LOAI_OPTIONS, state="readonly", width=23)
        self.c_loai.grid(row=1, column=1, pady=6, sticky="ew")
        self.c_loai.bind("<<ComboboxSelected>>", lambda e: self._loai_changed())

        ttk.Label(form, text="Năm *", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_nam = tk.StringVar(value=str(_current_year()))
        ttk.Combobox(form, textvariable=self.v_nam, values=_nam_values(), width=23).grid(
            row=2, column=1, pady=6, sticky="ew")

        self.lbl_kytrongnam = ttk.Label(form, text="Tháng *", style="Card.TLabel")
        self.lbl_kytrongnam.grid(row=3, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_kytrongnam = tk.StringVar()
        self.c_kytrongnam = ttk.Combobox(form, textvariable=self.v_kytrongnam, values=THANG_LABELS,
                                         state="readonly", width=23)
        self.c_kytrongnam.grid(row=3, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Xếp loại *", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_xep = tk.StringVar(value=XEP_LOAI_OPTIONS[1])
        ttk.Combobox(form, textvariable=self.v_xep, values=XEP_LOAI_OPTIONS, state="readonly", width=23).grid(
            row=4, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Điểm (0-100)", style="Card.TLabel").grid(row=5, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_diem = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_diem, width=25).grid(row=5, column=1, pady=6, sticky="ew")

        ttk.Label(form, text="Ghi chú", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=6, padx=(0, 10))
        self.v_note = tk.StringVar()
        ttk.Entry(form, textvariable=self.v_note, width=25).grid(row=6, column=1, pady=6, sticky="ew")

        RoundedButton(shell.footer, text="➕  Thêm", command=self.save, variant="primary").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(
            side="left", fill="x", expand=True)

        self._loai_changed()
        center(self, 480, 520)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _loai_changed(self):
        loai = self.v_loai.get()
        if loai == "Tháng":
            self.lbl_kytrongnam.configure(text="Tháng *")
            self.c_kytrongnam.configure(values=THANG_LABELS)
            if self.v_kytrongnam.get() not in THANG_LABELS:
                self.v_kytrongnam.set(THANG_LABELS[datetime.date.today().month - 1])
            self.lbl_kytrongnam.grid()
            self.c_kytrongnam.grid()
        elif loai == "Quý":
            self.lbl_kytrongnam.configure(text="Quý *")
            self.c_kytrongnam.configure(values=QUY_LABELS)
            if self.v_kytrongnam.get() not in QUY_LABELS:
                self.v_kytrongnam.set(QUY_LABELS[0])
            self.lbl_kytrongnam.grid()
            self.c_kytrongnam.grid()
        else:
            self.lbl_kytrongnam.grid_remove()
            self.c_kytrongnam.grid_remove()

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn một cán bộ.", parent=self)
            return
        try:
            nam = int(self.v_nam.get().strip())
            if not (1900 <= nam <= 2200):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Sai định dạng", "Năm không hợp lệ.", parent=self)
            return
        loai = self.v_loai.get()
        if loai in ("Tháng", "Quý") and not self.v_kytrongnam.get():
            messagebox.showwarning("Thiếu thông tin",
                                   f"Vui lòng chọn {self.lbl_kytrongnam.cget('text').replace(' *','')}.", parent=self)
            return
        diem_text = self.v_diem.get().strip()
        diem = None
        if diem_text:
            try:
                diem = float(diem_text.replace(",", "."))
                if not (0 <= diem <= 100):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Sai định dạng", "Điểm phải là số từ 0 đến 100.", parent=self)
                return
        ky_so, ky = _ky_info(loai, nam, self.v_kytrongnam.get())
        data = dict(can_bo_id=emp_id, loai=loai, nam=nam, ky_so=ky_so, ky=ky,
                   xep_loai=self.v_xep.get(), diem=diem, ghi_chu=self.v_note.get().strip(),
                   created_by=self.panel.app.user["username"])
        self.db.insert(TABLE, data)
        self.db.log(self.panel.app.user["username"], "Thêm phân loại cán bộ",
                    f"{self.db.employee_label(emp_id)} - {ky}: {data['xep_loai']}"
                    + (f" ({diem:g} điểm)" if diem is not None else ""))
        self.panel.refresh()
        self.panel.refresh_grid()
        self.panel.app.status.set("Đã lưu kết quả phân loại.")
        self.destroy()
