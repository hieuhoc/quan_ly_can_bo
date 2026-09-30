# -*- coding: utf-8 -*-
"""Module Tổng quan - trang chủ sau khi đăng nhập.

Không nằm trong danh sách module có thể tắt (luôn hiển thị cho mọi tài
khoản), nhưng từng phần bên trong tự ẩn theo đúng quyền xem của người dùng
đối với module dữ liệu tương ứng, và tự ẩn nếu module đó đang bị quản trị
viên tắt trong "Cấu hình module" - không hiện số liệu ngoài phạm vi được
phép xem.
"""
import tkinter as tk
from tkinter import ttk

from core.theme import C, make_card
from core.widgets import BarChart, make_tree, stat_card

MODULE_ID = "dashboard"


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.disabled = self.db.disabled_modules()
        self._build()

    def visible(self, mod_id):
        return mod_id not in self.disabled and self.app.can(mod_id, "view")

    def _build(self):
        outer = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=outer.yview)
        body = ttk.Frame(outer)
        win = outer.create_window((0, 0), window=body, anchor="nw")
        outer.configure(yscrollcommand=vsb.set)
        outer.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        body.bind("<Configure>", lambda e: outer.configure(scrollregion=outer.bbox("all")))
        outer.bind("<Configure>", lambda e: outer.itemconfigure(win, width=e.width))

        def wheel(e):
            outer.yview_scroll(-1 if e.delta > 0 else 1, "units")
        outer.bind_all("<MouseWheel>", wheel, add="+")

        u = self.app.user
        ttk.Label(body, text=f"Chào {u['ho_ten'] or u['username']}, chúc một ngày làm việc hiệu quả.",
                 font=("Segoe UI", 15, "bold"), background=C["bg"], foreground=C["text"]
                 ).pack(anchor="w", padx=16, pady=(16, 4))

        any_visible = any(self.visible(m) for m in ("employees", "classification", "salary", "complaints"))
        if not any_visible:
            ttk.Label(body, background=C["bg"], foreground=C["muted"], wraplength=600, justify="left",
                     text="Tài khoản của bạn chưa được cấp quyền xem dữ liệu của module nào. "
                          "Vui lòng liên hệ quản trị viên nếu cần hỗ trợ."
                     ).pack(anchor="w", padx=16, pady=8)
            return

        # ---- hàng thẻ số liệu
        cards = ttk.Frame(body, style="TFrame")
        cards.pack(fill="x", padx=16, pady=(4, 8))
        col = 0
        if self.visible("employees"):
            n_emp = self.db.conn.execute("SELECT COUNT(*) FROM can_bo").fetchone()[0]
            n_don_vi = self.db.conn.execute(
                "SELECT COUNT(DISTINCT don_vi) FROM can_bo WHERE don_vi IS NOT NULL AND don_vi<>''").fetchone()[0]
            stat_card(cards, n_emp, "Tổng số cán bộ").grid(row=0, column=col, padx=6, sticky="ew"); col += 1
            stat_card(cards, n_don_vi, "Đơn vị đang quản lý", color=C["blue"]).grid(row=0, column=col, padx=6, sticky="ew"); col += 1
        if self.visible("complaints"):
            n_open = self.db.conn.execute(
                "SELECT COUNT(*) FROM don_thu WHERE trang_thai IN ('Mới tiếp nhận','Đang xác minh','Đang xử lý')").fetchone()[0]
            n_pending = self.db.conn.execute(
                "SELECT COUNT(*) FROM don_thu WHERE trang_thai='Tồn đọng'").fetchone()[0]
            stat_card(cards, n_open, "Đơn thư đang xử lý", color=C["gold"]).grid(row=0, column=col, padx=6, sticky="ew"); col += 1
            stat_card(cards, n_pending, "Đơn thư tồn đọng", color=C["red"]).grid(row=0, column=col, padx=6, sticky="ew"); col += 1
        if self.visible("salary"):
            year = __import__("datetime").datetime.now().year
            n_sal = self.db.conn.execute(
                "SELECT COUNT(*) FROM qua_trinh_luong WHERE substr(ngay_quyet_dinh,7,4)=?", (str(year),)).fetchone()[0]
            stat_card(cards, n_sal, f"Nâng lương/thăng cấp năm {year}", color=C["green"]).grid(row=0, column=col, padx=6, sticky="ew"); col += 1
        for c in range(col):
            cards.columnconfigure(c, weight=1, uniform="cards")

        charts_row = ttk.Frame(body, style="TFrame")
        charts_row.pack(fill="x", padx=10)

        if self.visible("employees"):
            self._chart_card(charts_row, "Cán bộ theo đơn vị", self._data_by_unit(), side="left")
            self._chart_card(charts_row, "Cán bộ theo cấp bậc", self._data_by_rank(), side="left")

        charts_row2 = ttk.Frame(body, style="TFrame")
        charts_row2.pack(fill="x", padx=10)
        if self.visible("classification"):
            self._chart_card(charts_row2, "Tổng hợp xếp loại cán bộ (tất cả các kỳ)",
                             self._data_classification(), side="left")
        if self.visible("complaints"):
            self._chart_card(charts_row2, "Đơn thư theo trạng thái", self._data_complaints(), side="left")

        if self.visible("employees"):
            self._data_quality_card(body)
        if self.visible("complaints"):
            self._pending_complaints_card(body)

        tk.Frame(body, height=16, bg=C["bg"]).pack()

    def _chart_card(self, parent, title, data, side="left"):
        lo, card = make_card(parent, padding=14)
        lo.pack(side=side, fill="both", expand=True, padx=6, pady=6)
        ttk.Label(card, text=title, style="CardTitle.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))
        chart = BarChart(card, width=420)
        chart.pack(fill="x")
        chart.set_data(data)
        return card

    # ---- truy vấn dữ liệu
    def _data_by_unit(self):
        rows = self.db.conn.execute(
            "SELECT COALESCE(NULLIF(don_vi,''),'(chưa rõ đơn vị)') AS k, COUNT(*) c "
            "FROM can_bo GROUP BY k ORDER BY c DESC LIMIT 8").fetchall()
        return [(r["k"], r["c"]) for r in rows]

    def _data_by_rank(self):
        rows = self.db.conn.execute(
            "SELECT COALESCE(NULLIF(cap_bac,''),'(chưa rõ cấp bậc)') AS k, COUNT(*) c "
            "FROM can_bo GROUP BY k ORDER BY c DESC LIMIT 8").fetchall()
        return [(r["k"], r["c"]) for r in rows]

    def _data_classification(self):
        rows = self.db.conn.execute(
            "SELECT xep_loai AS k, COUNT(*) c FROM phan_loai_can_bo GROUP BY k ORDER BY c DESC").fetchall()
        return [(r["k"], r["c"]) for r in rows]

    def _data_complaints(self):
        rows = self.db.conn.execute(
            "SELECT trang_thai AS k, COUNT(*) c FROM don_thu GROUP BY k ORDER BY c DESC").fetchall()
        return [(r["k"], r["c"]) for r in rows]

    def _data_quality_card(self, parent):
        missing_sdt = self.db.conn.execute("SELECT COUNT(*) FROM can_bo WHERE sdt IS NULL OR sdt=''").fetchone()[0]
        missing_cccd = self.db.conn.execute("SELECT COUNT(*) FROM can_bo WHERE so_cccd IS NULL OR so_cccd=''").fetchone()[0]
        missing_ns = self.db.conn.execute("SELECT COUNT(*) FROM can_bo WHERE ngay_sinh IS NULL OR ngay_sinh=''").fetchone()[0]
        lo, card = make_card(parent, padding=14)
        lo.pack(fill="x", padx=16, pady=6)
        ttk.Label(card, text="Dữ liệu cán bộ cần bổ sung", style="CardTitle.TLabel",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x")
        for i, (label, n) in enumerate([("Thiếu số điện thoại", missing_sdt),
                                        ("Thiếu số CCCD", missing_cccd),
                                        ("Thiếu ngày sinh", missing_ns)]):
            color = C["red"] if n else C["green"]
            f = ttk.Frame(row, style="Card.TFrame")
            f.grid(row=0, column=i, sticky="w", padx=(0, 28))
            tk.Label(f, text=str(n), bg=C["card"], fg=color, font=("Segoe UI", 16, "bold")).pack(anchor="w")
            ttk.Label(f, text=label, style="CardMuted.TLabel").pack(anchor="w")

    def _pending_complaints_card(self, parent):
        rows = self.db.conn.execute(
            "SELECT d.tieu_de, d.trang_thai, d.ngay_nhan, c.ho_ten FROM don_thu d "
            "LEFT JOIN can_bo c ON c.id=d.can_bo_id "
            "WHERE d.trang_thai IN ('Tồn đọng','Đang xử lý','Đang xác minh','Mới tiếp nhận') "
            "ORDER BY (d.ngay_nhan IS NULL), d.ngay_nhan ASC LIMIT 6").fetchall()
        lo, card = make_card(parent, padding=14)
        lo.pack(fill="x", padx=16, pady=6)
        ttk.Label(card, text="Đơn thư chưa giải quyết, nhận lâu nhất", style="CardTitle.TLabel",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))
        if not rows:
            ttk.Label(card, text="Không có đơn thư nào đang chờ xử lý.", style="CardMuted.TLabel").pack(anchor="w")
            return
        cols = [("tieu_de", "Tiêu đề", 220), ("ho_ten", "Cán bộ liên quan", 150),
               ("ngay_nhan", "Ngày nhận", 90), ("trang_thai", "Trạng thái", 110)]
        tree, wrap = make_tree(card, cols, sortable=False)
        tree.configure(height=min(len(rows), 6))
        wrap.pack(fill="x")
        for i, r in enumerate(rows):
            tree.insert("", "end", values=(r["tieu_de"], r["ho_ten"] or "—", r["ngay_nhan"] or "—", r["trang_thai"]),
                       tags=("odd" if i % 2 else "even",))
