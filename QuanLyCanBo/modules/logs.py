# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): nhật ký hoạt động của toàn hệ thống."""
from tkinter import ttk

from core.theme import C, make_card
from core.widgets import RoundedButton, make_tree

MODULE_ID = "logs"
COLS = [("thoi_gian", "Thời gian", 150), ("username", "Tài khoản", 120),
        ("hanh_dong", "Hành động", 220), ("chi_tiet", "Chi tiết", 380)]


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self._build()
        self.refresh()

    def _build(self):
        lo, card = make_card(self, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Nhật ký hoạt động (500 dòng gần nhất)", style="CardTitle.TLabel").pack(side="left")
        RoundedButton(top, text="↻  Làm mới", command=self.refresh, variant="secondary").pack(side="right")
        self.tree, wrap = make_tree(card, COLS)
        wrap.pack(fill="both", expand=True)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.db.recent_logs()):
            self.tree.insert("", "end", tags=("odd" if i % 2 else "even",),
                             values=(r["thoi_gian"], r["username"], r["hanh_dong"], r["chi_tiet"] or ""))
