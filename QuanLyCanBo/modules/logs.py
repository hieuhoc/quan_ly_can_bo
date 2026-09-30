# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): nhật ký hoạt động của toàn hệ thống."""
from ui.widgets import ListPage

MODULE_ID = "logs"
COLS = [("thoi_gian", "Thời gian", 150), ("username", "Tài khoản", 120),
        ("hanh_dong", "Hành động", 220), ("chi_tiet", "Chi tiết", 380)]


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Nhật ký hoạt động", COLS, subtitle="500 thao tác gần nhất", advanced=False)
        self.add_action("↻  Làm mới", self.refresh, right=True)
        self.refresh()

    def refresh(self):
        kw = self.search_text().lower()
        rows = [dict(r) for r in self.db.recent_logs()]
        if kw:
            rows = [r for r in rows if kw in " ".join(str(v or "") for v in r.values()).lower()]
        self.table.set_rows(rows)
        self.count_lbl.setText(f"{len(rows)} dòng")
