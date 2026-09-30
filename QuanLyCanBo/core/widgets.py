# -*- coding: utf-8 -*-
"""Thành phần giao diện tái sử dụng giữa các module."""
import tkinter as tk
from tkinter import ttk

from core.theme import C, FONT


class ScrollableFrame(ttk.Frame):
    """Khung có thanh cuộn dọc, dùng cho biểu mẫu nhiều trường (cán bộ)."""

    def __init__(self, parent, bg=None, width=360):
        super().__init__(parent, style="Card.TFrame")
        bg = bg or C["card"]
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, width=width)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas, style="Card.TFrame")
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        def on_body_config(_e=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def on_canvas_config(e):
            self.canvas.itemconfigure(self._win, width=e.width)

        self.body.bind("<Configure>", on_body_config)
        self.canvas.bind("<Configure>", on_canvas_config)

        def wheel(e):
            delta = -1 if e.delta > 0 else 1
            if e.num == 4:
                delta = -1
            elif e.num == 5:
                delta = 1
            self.canvas.yview_scroll(delta, "units")

        for widget in (self.canvas, self.body):
            widget.bind("<MouseWheel>", wheel)
            widget.bind("<Button-4>", wheel)
            widget.bind("<Button-5>", wheel)


def section_label(parent, text):
    frm = ttk.Frame(parent, style="Card.TFrame")
    ttk.Label(frm, text=text, style="Section.TLabel").pack(anchor="w")
    tk.Frame(frm, height=2, width=36, bg=C["gold"]).pack(anchor="w", pady=(2, 6))
    return frm


class BorderedTable(ttk.Frame):
    """Bảng dữ liệu tự vẽ bằng Canvas, có VIỀN RÕ TỪNG Ô (ttk.Treeview mặc
    định của Tkinter không hỗ trợ việc này). Cung cấp lại phần lớn các
    phương thức của ttk.Treeview mà phần mềm đang dùng (insert/delete/
    get_children/selection/item/set/move/heading/column/tag_configure/
    configure/bind) nên các module khác không cần sửa gì thêm - chỉ cần
    make_tree() trả về BorderedTable thay vì ttk.Treeview.

    Tiêu đề cố định phía trên (không cuộn dọc theo bảng), cuộn ngang đồng
    bộ giữa tiêu đề và phần dữ liệu. Bấm vào tiêu đề cột để sắp xếp (nếu
    sortable=True), bấm một dòng để chọn, bấm đúp để mở (Double-1), phím
    Delete để xóa (Delete) - giống hệt cách ttk.Treeview hoạt động trước
    đây.
    """

    ROW_H = 28
    HEAD_H = 32

    def __init__(self, parent, columns, sortable=True):
        super().__init__(parent, style="Card.TFrame")
        self._cols = [c[0] for c in columns]
        self._col_text = {c[0]: c[1] for c in columns}
        self._col_width = {c[0]: c[2] for c in columns}
        self._sortable = sortable
        self._rows = {}
        self._order = []
        self._tags = {}
        self._selected = None
        self._hover = None
        self._select_cbs, self._dbl_cbs, self._del_cbs = [], [], []
        self._sort_state = {"col": None, "reverse": False}
        self._auto_n = 0
        self._redraw_pending = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(self, height=self.HEAD_H, bg=C["primary"], highlightthickness=0)
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.body_canvas = tk.Canvas(self, bg="white", highlightthickness=0, takefocus=1)
        self.body_canvas.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.body_canvas.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._xview_both)
        hsb.grid(row=2, column=0, sticky="ew")
        self.body_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.header_canvas.configure(xscrollcommand=lambda *_a: None)

        self.body_canvas.bind("<Button-1>", self._on_click)
        self.body_canvas.bind("<Double-Button-1>", self._on_dblclick)
        self.body_canvas.bind("<Delete>", self._on_delete_key)
        self.body_canvas.bind("<Motion>", self._on_motion)
        self.body_canvas.bind("<Leave>", lambda e: self._set_hover(None))
        self.body_canvas.bind("<Configure>", lambda e: self._schedule_redraw())
        self.body_canvas.bind("<MouseWheel>", self._on_wheel)
        self.header_canvas.bind("<Button-1>", self._on_header_click)

        self.tag_configure("odd", background=C["zebra"])
        self.tag_configure("even", background="white")
        self._draw_header()
        self._schedule_redraw()

    # ---------------------------------------------------- cuộn
    def _xview_both(self, *args):
        self.body_canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _on_wheel(self, e):
        self.body_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    # ---------------------------------------------------- vẽ
    def _total_width(self):
        return sum(self._col_width[c] for c in self._cols) or 1

    def _draw_header(self):
        self.header_canvas.delete("all")
        w = self._total_width()
        self.header_canvas.configure(scrollregion=(0, 0, w, self.HEAD_H))
        x = 0
        for key in self._cols:
            cw = self._col_width[key]
            text = self._col_text[key]
            self.header_canvas.create_rectangle(x, 0, x + cw, self.HEAD_H, fill=C["primary"],
                                                outline=C["primary_dark"], width=1)
            self.header_canvas.create_text(x + 6, self.HEAD_H // 2, text=text, anchor="w",
                                           fill="white", font=(FONT, 10, "bold"))
            x += cw
        self.header_canvas.xview_moveto(self.body_canvas.xview()[0] if self._order or True else 0)

    def _row_colors(self, iid):
        bg, fg = "white", C["text"]
        for t in self._rows[iid]["tags"]:
            st = self._tags.get(t, {})
            if "background" in st:
                bg = st["background"]
            if "foreground" in st:
                fg = st["foreground"]
        if iid == self._hover and iid != self._selected:
            bg = C["neutral_lighter"]
        if iid == self._selected:
            bg, fg = C["sel"], C["text"]
        return bg, fg

    def _schedule_redraw(self):
        if not self._redraw_pending:
            self._redraw_pending = True
            self.after_idle(self._redraw)

    def _redraw(self):
        self._redraw_pending = False
        if not self.winfo_exists():
            return
        self.body_canvas.delete("all")
        total_w = self._total_width()
        vis_w = max(self.body_canvas.winfo_width(), 1)
        w = max(total_w, vis_w)
        h = max(len(self._order) * self.ROW_H, 1)
        self.body_canvas.configure(scrollregion=(0, 0, w, h))
        y = 0
        for iid in self._order:
            vals = self._rows[iid]["values"]
            bg, fg = self._row_colors(iid)
            x = 0
            for j, key in enumerate(self._cols):
                cw = self._col_width[key]
                val = vals[j] if j < len(vals) else ""
                self.body_canvas.create_rectangle(x, y, x + cw, y + self.ROW_H, fill=bg,
                                                  outline=C["border"], width=1)
                self.body_canvas.create_text(x + 6, y + self.ROW_H // 2, text="" if val is None else str(val),
                                             anchor="w", fill=fg, font=(FONT, 10))
                x += cw
            if total_w < vis_w:
                self.body_canvas.create_rectangle(total_w, y, vis_w, y + self.ROW_H, fill=bg, outline=bg)
            y += self.ROW_H

    # ---------------------------------------------------- tương tác chuột/phím
    def _row_at(self, y):
        cy = self.body_canvas.canvasy(y)
        idx = int(cy // self.ROW_H)
        return self._order[idx] if 0 <= idx < len(self._order) else None

    def _on_click(self, e):
        self.body_canvas.focus_set()
        self._selected = self._row_at(e.y)
        self._schedule_redraw()
        for cb in self._select_cbs:
            cb(None)

    def _on_dblclick(self, e):
        for cb in self._dbl_cbs:
            cb(None)

    def _on_delete_key(self, _e):
        for cb in self._del_cbs:
            cb(None)

    def _on_motion(self, e):
        self._set_hover(self._row_at(e.y))

    def _set_hover(self, iid):
        if iid != self._hover:
            self._hover = iid
            self._schedule_redraw()

    def _on_header_click(self, e):
        if not self._sortable:
            return
        cx = self.header_canvas.canvasx(e.x)
        x = 0
        for key in self._cols:
            cw = self._col_width[key]
            if x <= cx < x + cw:
                self._sort_by(key)
                return
            x += cw

    @staticmethod
    def _sort_key(val):
        val = (val or "").strip() if isinstance(val, str) else val
        if val in (None, ""):
            return (1, "")
        try:
            return (0, float(str(val).replace(",", "")))
        except (ValueError, TypeError):
            pass
        try:
            import datetime as _dt
            return (0, _dt.datetime.strptime(str(val), "%d/%m/%Y"))
        except (ValueError, TypeError):
            pass
        return (1, str(val).casefold())

    def _sort_by(self, col):
        reverse = (not self._sort_state["reverse"]) if self._sort_state["col"] == col else False
        j = self._cols.index(col)
        self._order.sort(key=lambda iid: self._sort_key(self._rows[iid]["values"][j]
                                                        if j < len(self._rows[iid]["values"]) else ""),
                         reverse=reverse)
        for idx, iid in enumerate(self._order):
            tags = [t for t in self._rows[iid]["tags"] if t not in ("odd", "even")]
            tags.append("odd" if idx % 2 else "even")
            self._rows[iid]["tags"] = tuple(tags)
        self._sort_state = {"col": col, "reverse": reverse}
        for key in self._cols:
            arrow = (" ▾" if reverse else " ▴") if key == col else ""
            base = self._col_text[key].rstrip(" ▾▴")
            self._col_text[key] = base + arrow
        self._draw_header()
        self._schedule_redraw()

    # ---------------------------------------------------- API tương thích ttk.Treeview
    def get_children(self, parent=""):
        return tuple(self._order)

    def insert(self, _parent, index, iid=None, values=(), tags=()):
        if iid is None:
            iid = f"__auto{self._auto_n}"
            self._auto_n += 1
        iid = str(iid)
        self._rows[iid] = {"values": tuple(values), "tags": tuple(tags)}
        if index == "end" or index is None:
            self._order.append(iid)
        else:
            self._order.insert(int(index), iid)
        self._schedule_redraw()
        return iid

    def delete(self, *iids):
        for iid in iids:
            iid = str(iid)
            self._rows.pop(iid, None)
            if iid in self._order:
                self._order.remove(iid)
            if self._selected == iid:
                self._selected = None
            if self._hover == iid:
                self._hover = None
        self._schedule_redraw()

    def selection(self):
        return (self._selected,) if self._selected is not None else ()

    def selection_set(self, iid):
        self._selected = str(iid) if iid is not None else None
        self._schedule_redraw()
        for cb in self._select_cbs:
            cb(None)

    def selection_remove(self, iid=None):
        if iid is None or str(iid) == self._selected:
            self._selected = None
        self._schedule_redraw()

    def exists(self, iid):
        return str(iid) in self._rows

    def item(self, iid, option=None, **kw):
        iid = str(iid)
        if kw:
            if "tags" in kw:
                self._rows[iid]["tags"] = tuple(kw["tags"])
            if "values" in kw:
                self._rows[iid]["values"] = tuple(kw["values"])
            self._schedule_redraw()
            return None
        if iid not in self._rows:
            return None
        if option == "values":
            return self._rows[iid]["values"]
        if option == "tags":
            return self._rows[iid]["tags"]
        return {"values": self._rows[iid]["values"], "tags": self._rows[iid]["tags"]}

    def set(self, iid, column):
        j = self._cols.index(column)
        vals = self._rows[str(iid)]["values"]
        return vals[j] if j < len(vals) else ""

    def move(self, iid, _parent, index):
        iid = str(iid)
        if iid in self._order:
            self._order.remove(iid)
        self._order.insert(int(index), iid)
        self._schedule_redraw()

    def heading(self, col, text=None, command=None):
        if text is None and command is None:
            return {"text": self._col_text.get(col, "")}
        if text is not None:
            self._col_text[col] = text
        self._draw_header()
        return None

    def column(self, col, **kw):
        if "width" in kw:
            self._col_width[col] = kw["width"]
        if not kw:
            return {"width": self._col_width.get(col, 0)}
        self._draw_header()
        self._schedule_redraw()
        return None

    def tag_configure(self, tag, **kw):
        self._tags.setdefault(tag, {}).update(kw)
        self._schedule_redraw()

    def configure(self, **kw):
        if "height" in kw:
            n = kw.pop("height")
            self.body_canvas.configure(height=max(n, 1) * self.ROW_H)
        if kw:
            super().configure(**kw)

    config = configure

    def __getitem__(self, key):
        if key == "columns":
            return tuple(self._cols)
        return super().__getitem__(key)

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<TreeviewSelect>>":
            self._select_cbs.append(func)
        elif sequence == "<Double-1>":
            self._dbl_cbs.append(func)
        elif sequence == "<Delete>":
            self._del_cbs.append(func)
        else:
            return super().bind(sequence, func, add)
        return None


def make_tree(parent, columns, sortable=True):
    """columns: list of (key, label, width). Trả về (tree, wrap) - cùng một
    đối tượng BorderedTable (đã tự quản lý cuộn/viền/tiêu đề bên trong nên
    không cần khung bọc riêng như ttk.Treeview trước đây). Khi sortable=
    True, bấm vào tiêu đề cột để sắp xếp (nhận diện số và ngày dd/mm/yyyy,
    còn lại sắp xếp theo chữ cái); bấm lại để đảo chiều tăng/giảm."""
    bt = BorderedTable(parent, columns, sortable=sortable)
    return bt, bt


def fill_tree(tree, rows, columns_keys):
    tree.delete(*tree.get_children())
    for i, r in enumerate(rows):
        tree.insert("", "end", iid=str(r["id"]), values=[r[c] if r[c] is not None else "" for c in columns_keys],
                    tags=("odd" if i % 2 else "even",))


class BarChart(tk.Canvas):
    """Biểu đồ cột ngang đơn giản vẽ bằng Canvas - không phụ thuộc thư viện
    ngoài nên luôn hoạt động ngoại tuyến trên mọi máy Windows."""

    def __init__(self, parent, width=440, row_height=26, bar_color=None, label_width=185):
        super().__init__(parent, width=width, height=row_height, bg=C["card"], highlightthickness=0)
        self.bar_color = bar_color or C["primary"]
        # LƯU Ý: không đặt tên các thuộc tính này là "_w" - Tkinter đã dùng
        # sẵn "_w" nội bộ để lưu đường dẫn widget; ghi đè sẽ làm hỏng mọi
        # lệnh pack/grid/place gọi sau đó.
        self._chart_width, self._row_h, self._label_w = width, row_height, label_width

    def set_data(self, items, value_suffix=""):
        """items: danh sách (nhãn, giá trị số), nên sắp từ lớn đến nhỏ trước khi truyền vào."""
        self.delete("all")
        n = len(items)
        self.configure(height=max(self._row_h * max(n, 1), self._row_h))
        if not items:
            self.create_text(self._chart_width // 2, self._row_h // 2, text="Chưa có dữ liệu",
                             fill=C["muted"], font=("Segoe UI", 9))
            return
        max_val = max((v for _l, v in items)) or 1
        bar_area = max(self._chart_width - self._label_w - 60, 40)
        for i, (label, val) in enumerate(items):
            y0 = i * self._row_h
            yc = y0 + self._row_h / 2
            bar_w = (val / max_val) * bar_area if max_val else 0
            disp = label if len(label) <= 27 else label[:26] + "…"
            self.create_text(self._label_w - 8, yc, text=disp, anchor="e",
                             font=("Segoe UI", 9), fill=C["text"])
            self.create_rectangle(self._label_w, y0 + self._row_h * 0.22,
                                  self._label_w + max(bar_w, 2), y0 + self._row_h * 0.78,
                                  fill=self.bar_color, outline="")
            self.create_text(self._label_w + bar_w + 8, yc, text=f"{val}{value_suffix}",
                             anchor="w", font=("Segoe UI", 9, "bold"), fill=C["text"])


def stat_card(parent, value, label, color=None):
    """Thẻ số liệu nhỏ (vd '128' / 'Tổng số cán bộ') dùng ở trang Tổng quan."""
    color = color or C["primary"]
    outer = tk.Frame(parent, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
    inner = ttk.Frame(outer, style="Card.TFrame", padding=(16, 12))
    inner.pack(fill="both", expand=True)
    tk.Frame(inner, height=3, width=28, bg=color).pack(anchor="w", pady=(0, 6))
    tk.Label(inner, text=str(value), bg=C["card"], fg=color, font=("Segoe UI", 22, "bold")).pack(anchor="w")
    ttk.Label(inner, text=label, style="CardMuted.TLabel", wraplength=125, justify="left").pack(anchor="w")
    return outer


class FilterCombo(ttk.Frame):
    """Combobox gõ để lọc trong một danh sách giá trị cho trước (dùng cho
    chức vụ, hệ số lương, tỉnh, xã...). editable=True cho phép gõ giá trị
    không có sẵn trong danh sách; editable=False bắt buộc chọn đúng một
    giá trị có sẵn. Truyền textvariable để gắn trực tiếp vào một StringVar
    có sẵn (vd self.vars[key]) thay vì tạo biến nội bộ riêng."""

    def __init__(self, parent, values=None, width=28, editable=True, on_change=None, textvariable=None):
        super().__init__(parent, style="Card.TFrame")
        self.var = textvariable if textvariable is not None else tk.StringVar()
        self._all = list(values or [])
        self._on_change = on_change
        self.combo = ttk.Combobox(self, textvariable=self.var, width=width,
                                  values=self._all, state="normal" if editable else "readonly")
        self.combo.pack(fill="x")
        if editable:
            self.combo.bind("<KeyRelease>", self._on_type)
        self.combo.bind("<<ComboboxSelected>>", self._on_pick)

    def set_values(self, values):
        self._all = list(values or [])
        self.combo.configure(values=self._all)

    def _on_type(self, _e=None):
        text = self.var.get().strip().lower()
        self.combo.configure(values=self._all if not text else
                             [v for v in self._all if text in v.lower()])

    def _on_pick(self, _e=None):
        if self._on_change:
            self._on_change(self.var.get())

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set(value or "")

    def configure_state(self, state):
        self.combo.configure(state=state)


_THANG_TEN = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
             "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
_THU_TEN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


class DateEntry(ttk.Frame):
    """Ô nhập ngày (dd/mm/yyyy) kèm nút lịch để chọn - dùng chung cho mọi
    trường ngày tháng trong phần mềm. Vẫn cho gõ tay để nhập nhanh."""

    def __init__(self, parent, textvariable, width=20):
        super().__init__(parent, style="Card.TFrame")
        self.var = textvariable
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.btn = RoundedButton(self, text="📅", command=self._open_picker, variant="secondary")
        self.btn.pack(side="left", padx=(4, 0))

    def _open_picker(self):
        import datetime
        year, month = datetime.date.today().year, datetime.date.today().month
        text = self.var.get().strip()
        if text:
            try:
                d = datetime.datetime.strptime(text, "%d/%m/%Y")
                year, month = d.year, d.month
            except ValueError:
                pass
        _CalendarPopup(self, self.var, year, month)

    def configure(self, **kw):
        state = kw.pop("state", None)
        if state is not None:
            self.entry.configure(state=state)
            self.btn.configure(state=("disabled" if state == "disabled" else "normal"))
        if kw:
            super().configure(**kw)


class _CalendarPopup(tk.Toplevel):
    def __init__(self, anchor_widget, var, year, month):
        super().__init__(anchor_widget)
        self.var = var
        self.year, self.month = year, month
        self.overrideredirect(True)
        self.configure(bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        x = anchor_widget.winfo_rootx()
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
        self.geometry(f"+{x}+{y}")
        self._build()
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(10, lambda: (self.focus_force(), self.grab_set()))

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        head = ttk.Frame(self, style="Card.TFrame", padding=(8, 6))
        head.pack(fill="x")
        RoundedButton(head, text="«", command=lambda: self._shift(years=-1), variant="secondary").pack(side="left")
        RoundedButton(head, text="‹", command=lambda: self._shift(months=-1), variant="secondary").pack(side="left")
        ttk.Label(head, text=f"{_THANG_TEN[self.month - 1]} / {self.year}",
                 style="Card.TLabel", font=("Segoe UI", 10, "bold"), width=14, anchor="center"
                 ).pack(side="left", padx=4)
        RoundedButton(head, text="›", command=lambda: self._shift(months=1), variant="secondary").pack(side="left")
        RoundedButton(head, text="»", command=lambda: self._shift(years=1), variant="secondary").pack(side="left")

        grid = ttk.Frame(self, style="Card.TFrame", padding=(8, 0))
        grid.pack()
        for i, lbl in enumerate(_THU_TEN):
            ttk.Label(grid, text=lbl, style="CardMuted.TLabel", width=4, anchor="center"
                     ).grid(row=0, column=i, pady=(0, 2))

        import calendar
        cal = calendar.Calendar(firstweekday=0)  # Thứ 2 đầu tuần
        row = 1
        for week in cal.monthdayscalendar(self.year, self.month):
            for col, day in enumerate(week):
                if day == 0:
                    ttk.Label(grid, text="", width=4).grid(row=row, column=col)
                else:
                    b = tk.Button(grid, text=str(day), width=3, relief="flat",
                                 bg=C["card"], activebackground=C["sel"],
                                 command=lambda d=day: self._pick(d))
                    b.grid(row=row, column=col, padx=1, pady=1)
            row += 1

        foot = ttk.Frame(self, style="Card.TFrame", padding=(8, 6))
        foot.pack(fill="x")
        RoundedButton(foot, text="Hôm nay", command=self._today, variant="secondary").pack(side="left")
        RoundedButton(foot, text="Xóa", command=self._clear, variant="secondary").pack(side="left", padx=4)
        RoundedButton(foot, text="Đóng", command=self.destroy, variant="secondary").pack(side="right")

    def _shift(self, months=0, years=0):
        self.month += months
        self.year += years
        if self.month < 1:
            self.month, self.year = 12, self.year - 1
        elif self.month > 12:
            self.month, self.year = 1, self.year + 1
        self._build()

    def _pick(self, day):
        self.var.set(f"{day:02d}/{self.month:02d}/{self.year:04d}")
        self.destroy()

    def _today(self):
        import datetime
        t = datetime.date.today()
        self.var.set(t.strftime("%d/%m/%Y"))
        self.destroy()

    def _clear(self):
        self.var.set("")
        self.destroy()


class ProvinceWardPicker(ttk.Frame):
    """Cặp ô chọn Tỉnh/Thành phố -> Xã/Phường (xã lọc theo tỉnh đã chọn),
    theo địa giới hành chính hiện hành (34 tỉnh/thành, sau sắp xếp 01/7/2025)."""

    def __init__(self, parent, width_tinh=20, width_xa=22):
        super().__init__(parent, style="Card.TFrame")
        import core.dia_gioi_hanh_chinh as dgh
        self._dgh = dgh
        self.tinh = FilterCombo(self, values=dgh.danh_sach_tinh(), width=width_tinh, editable=True)
        self.tinh.pack(side="left")
        ttk.Label(self, text=" – ", style="Card.TLabel").pack(side="left")
        self.xa = FilterCombo(self, values=[], width=width_xa, editable=True)
        self.xa.pack(side="left", fill="x", expand=True)
        self.tinh.combo.bind("<<ComboboxSelected>>", self._reload_xa, add="+")
        self.tinh.combo.bind("<KeyRelease>", self._reload_xa, add="+")

    def _reload_xa(self, _e=None):
        self.xa.set_values(self._dgh.danh_sach_xa(self.tinh.get()))

    def get(self):
        return self.tinh.get(), self.xa.get()

    def set(self, tinh, xa):
        self.tinh.set(tinh or "")
        self._reload_xa()
        self.xa.set(xa or "")

    def configure_state(self, state):
        self.tinh.configure_state(state)
        self.xa.configure_state(state)


class RoundedButton(tk.Canvas):
    """Nút bấm góc bo tròn, có hiệu ứng hover/nhấn - theo phong cách Fluent
    Design (Microsoft). Tương thích API với ttk.Button ở đúng những gì
    phần mềm đang dùng: .state(["disabled"]/["!disabled"]), .instate([...]),
    .configure(text=..., command=...) - nên có thể thay thế trực tiếp
    ttk.Button ở mọi nơi mà KHÔNG cần sửa logic bật/tắt nút theo quyền hay
    theo đã chọn dòng hay chưa.

    variant: "primary" (màu nhấn thương hiệu, dùng cho 1 hành động chính
    mỗi màn hình) | "secondary" (trung tính, viền mảnh, nền trắng - phần
    lớn các nút) | "danger" (đỏ, CHỈ dùng cho Xóa) | "header" (đặt trên
    nền đỏ đậm của thanh tiêu đề, vd nút Đăng xuất).
    """

    _VARIANTS = {
        "primary": dict(bg=C["primary"], hover=C["primary_dark"], pressed=C["primary_dark"],
                        fg="white", border=None),
        "secondary": dict(bg="#FFFFFF", hover=C["neutral_lighter"], pressed=C["neutral_light"],
                          fg=C["neutral_text"], border=C["neutral_border"],
                          border_hover=C["neutral_border_hover"]),
        "danger": dict(bg=C["danger"], hover=C["danger_hover"], pressed=C["danger_pressed"],
                       fg="white", border=None),
        "header": dict(bg=C["primary_dark"], hover=C["primary_light"], pressed=C["primary_light"],
                       fg="white", border=None),
    }

    def __init__(self, parent, text="", command=None, variant="secondary",
                width=None, height=32, radius=6, font=None, parent_bg=None):
        self._variant = variant
        self._text = text
        self.command = command
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._radius = radius
        self._font = font or (FONT, 10, "bold")
        import tkinter.font as tkfont
        weight = "bold" if (len(self._font) > 2 and self._font[2] == "bold") else "normal"
        self._tkfont = tkfont.Font(family=self._font[0], size=self._font[1], weight=weight)
        text_w = self._tkfont.measure(self._text)
        self._min_w = text_w + 28
        bg = parent_bg or C["card"]
        super().__init__(parent, width=(width or self._min_w), height=height,
                         bg=bg, highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._draw()

    # ---- vẽ
    def _round_points(self, x1, y1, x2, y2, r):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        cfg = self._VARIANTS[self._variant]
        if not self._enabled:
            bg, fg, border = C["neutral_disabled_bg"], C["neutral_disabled_fg"], C["neutral_light"]
        elif self._pressed:
            bg, fg, border = cfg["pressed"], cfg["fg"], cfg.get("border_hover", cfg.get("border"))
        elif self._hover:
            bg, fg, border = cfg["hover"], cfg["fg"], cfg.get("border_hover", cfg.get("border"))
        else:
            bg, fg, border = cfg["bg"], cfg["fg"], cfg.get("border")
        pts = self._round_points(0.5, 0.5, w - 0.5, h - 0.5, self._radius)
        self.create_polygon(pts, smooth=True, splinesteps=8, fill=bg,
                            outline=(border or bg), width=1)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)
        cursor = "hand2" if self._enabled else "arrow"
        try:
            self.configure(cursor=cursor)
        except tk.TclError:
            pass

    # ---- API tương thích ttk.Button
    def configure(self, **kw):
        redraw = False
        if "text" in kw:
            self._text = kw.pop("text")
            self._min_w = self._tkfont.measure(self._text) + 28
            redraw = True
        if "command" in kw:
            self.command = kw.pop("command")
        if "state" in kw:
            self._enabled = kw.pop("state") != "disabled"
            redraw = True
        if kw:
            super().configure(**kw)
        if redraw:
            self._draw()

    config = configure

    def state(self, states=None):
        if states is None:
            return ("disabled",) if not self._enabled else ()
        for s in states:
            if s == "disabled":
                self._enabled = False
            elif s == "!disabled":
                self._enabled = True
        self._draw()
        return self.state()

    def instate(self, states, callback=None):
        result = (not self._enabled) if "disabled" in states else self._enabled
        if "!disabled" in states:
            result = self._enabled
        if callback and result:
            callback()
        return result

    # ---- tương tác chuột
    def _on_press(self, _e):
        if self._enabled:
            self._pressed = True
            self._draw()

    def _on_release(self, e):
        if not self._enabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._hover = inside
        self._draw()
        if was_pressed and inside and self.command:
            self.command()

    def _on_enter(self, _e):
        self._hover = True
        if self._enabled:
            self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._pressed = False
        if self._enabled:
            self._draw()


class DialogShell:
    """Khung chuẩn cho hộp thoại popup Thêm/Sửa: kéo thả đổi kích thước
    được, phần thân cuộn riêng, thanh nút cố định phía dưới. Dùng:
        shell = DialogShell(toplevel, "Thêm cán bộ", width=620, height=680)
        # dựng các trường vào shell.body (một ScrollableFrame.body)
        # đặt nút Lưu/Hủy vào shell.footer
    """

    def __init__(self, win, title, width=560, height=620, min_width=440, min_height=360):
        win.title(title)
        win.configure(bg=C["bg"])
        win.resizable(True, True)
        win.minsize(min_width, min_height)
        win.geometry(f"{width}x{height}")

        # Không vẽ thêm thanh tiêu đề riêng ở đây - dùng đúng thanh tiêu đề
        # thật của Windows (đã có tên cửa sổ, nút đóng, và có thể kéo góc/
        # cạnh để đổi kích thước hay kéo cả cửa sổ theo con trỏ chuột như
        # mọi cửa sổ khác). Chỉ giữ một vạch vàng mảnh để nhận diện thương
        # hiệu, tránh chồng hai "tiêu đề" nhìn rối mắt.
        tk.Frame(win, height=4, bg=C["gold"]).pack(fill="x", side="top")

        self.scroll = ScrollableFrame(win, width=width - 24)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=(10, 4))
        self.footer = ttk.Frame(win, padding=(12, 8))
        self.footer.pack(fill="x", side="bottom")

        self.win = win
        self.body = self.scroll.body


class EmployeePicker(ttk.Frame):
    """Combobox gõ để lọc, chọn một cán bộ theo 'Mã - Họ tên'."""

    def __init__(self, parent, db, width=30):
        super().__init__(parent, style="Card.TFrame")
        self.db = db
        self.selected_id = None
        self._map = {}
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.var, width=width)
        self.combo.pack(fill="x")
        self.reload()
        self.combo.bind("<KeyRelease>", self._on_type)
        self.combo.bind("<<ComboboxSelected>>", self._on_pick)

    def reload(self):
        rows = self.db.employees_for_picker()
        self._map = {f"{r['ma_cb']} - {r['ho_ten']}": r["id"] for r in rows}
        self.combo.configure(values=list(self._map.keys()))

    def _on_type(self, _e=None):
        text = self.var.get().strip().lower()
        if not text:
            self.combo.configure(values=list(self._map.keys()))
            return
        self.combo.configure(values=[k for k in self._map if text in k.lower()])
        self.selected_id = self._map.get(self.var.get())

    def _on_pick(self, _e=None):
        self.selected_id = self._map.get(self.var.get())

    def get(self):
        self.selected_id = self._map.get(self.var.get())
        return self.selected_id

    def set_by_id(self, emp_id):
        if emp_id is None:
            self.var.set("")
            self.selected_id = None
            return
        label = self.db.employee_label(emp_id)
        self.var.set(label)
        self.selected_id = emp_id
        if label not in self._map:
            self._map[label] = emp_id

    def clear(self):
        self.var.set("")
        self.selected_id = None
