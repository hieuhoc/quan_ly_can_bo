# -*- coding: utf-8 -*-
"""Module Tổng quan - trang chủ sau khi đăng nhập.

Luôn hiển thị cho mọi tài khoản, nhưng từng phần bên trong tự ẩn theo
quyền xem của người dùng với module dữ liệu tương ứng, và tự ẩn nếu module
đó đang bị quản trị viên tắt."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from core import tham_so as ts
from ui.theme import C
from ui.widgets import BarChart, DataTable, StatCard, card, label, rule
from ui.widgets import sql_date_key

MODULE_ID = "dashboard"


def _ph(values):
    """Chuỗi tham số '?,?,?' cho mệnh đề IN (rỗng thì dùng '' để câu SQL vẫn hợp lệ)."""
    return ",".join("?" * len(values)) or "''"


class Panel(QScrollArea):
    def __init__(self, app):
        super().__init__()
        self.app, self.db = app, app.db
        self.disabled = self.db.disabled_modules()
        self.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("Page")
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 8, 8)
        v.setSpacing(14)
        self.setWidget(body)

        u = app.user
        v.addWidget(label(f"Chào {u['ho_ten'] or u['username']}, chúc một ngày làm việc hiệu quả.", "PageTitle"))
        if not any(self.visible(m) for m in ("employees", "classification", "salary", "complaints")):
            v.addWidget(label("Tài khoản của bạn chưa được cấp quyền xem dữ liệu của module nào. "
                              "Vui lòng liên hệ quản trị viên nếu cần hỗ trợ.", "Muted", wrap=True))
            v.addStretch(1)
            return

        q = lambda sql, *p: self.db.conn.execute(sql, p).fetchone()[0]  # noqa: E731
        cards = QHBoxLayout()
        cards.setSpacing(12)
        if self.visible("employees"):
            cards.addWidget(StatCard(q("SELECT COUNT(*) FROM can_bo"), "Tổng số cán bộ"))
            cards.addWidget(StatCard(q("SELECT COUNT(DISTINCT don_vi) FROM can_bo WHERE don_vi IS NOT NULL "
                                       "AND don_vi<>''"), "Phòng / Công an xã, phường", C["blue"]))
            from core import canh_bao
            alerts, _m, _e = canh_bao.compute(self.db)
            n_qh = sum(1 for r in alerts if r["trang_thai"] == canh_bao.QUA_HAN)
            warn_card = StatCard(len(alerts), f"Cảnh báo đến hạn (quá hạn: {n_qh})",
                                 C["red"] if n_qh else C["amber"])
            warn_card.setCursor(Qt.PointingHandCursor)
            warn_card.setToolTip("Bấm để xem danh sách cảnh báo đến hạn")
            warn_card.mousePressEvent = lambda _e: self.app.shell.open_module("reminders")
            cards.addWidget(warn_card)
        xong, ton = ts.get("trang_thai_da_xong"), ts.get("trang_thai_ton_dong")
        not_done = f"trang_thai NOT IN ({_ph(xong + ton)})"
        if self.visible("complaints"):
            cards.addWidget(StatCard(q(f"SELECT COUNT(*) FROM don_thu WHERE {not_done}", *(xong + ton)),
                                     "Đơn thư đang xử lý", C["gold"]))
            cards.addWidget(StatCard(q(f"SELECT COUNT(*) FROM don_thu WHERE trang_thai IN "
                                       f"({_ph(ton)})", *ton),
                                     "Đơn thư tồn đọng", C["red"]))
        if self.visible("salary"):
            year = datetime.date.today().year
            cards.addWidget(StatCard(q("SELECT COUNT(*) FROM qua_trinh_luong WHERE substr(ngay_quyet_dinh,7,4)=?",
                                       str(year)), f"Quyết định nâng lương - thăng cấp {year}", C["green"]))
        v.addLayout(cards)

        grid = QGridLayout()
        grid.setSpacing(14)
        charts = []
        if self.visible("employees"):
            charts.append(("Cán bộ theo đơn vị", self._group("COALESCE(NULLIF(don_vi,''),'(chưa rõ đơn vị)')",
                                                               "can_bo")))
            charts.append(("Cán bộ theo cấp bậc", self._group("COALESCE(NULLIF(cap_bac,''),'(chưa rõ cấp bậc)')",
                                                                "can_bo")))
        if self.visible("classification"):
            charts.append(("Tổng hợp xếp loại cán bộ (tất cả các kỳ)", self._group("xep_loai", "phan_loai_can_bo")))
        if self.visible("complaints"):
            charts.append(("Đơn thư theo trạng thái", self._group("trang_thai", "don_thu")))
        for i, (title, data) in enumerate(charts):
            f, lay = card(16)
            lay.addWidget(label(title, "CardTitle"))
            lay.addWidget(rule())
            lay.addWidget(BarChart(data))
            lay.addStretch(1)
            grid.addWidget(f, i // 2, i % 2)
        v.addLayout(grid)

        if self.visible("employees"):
            f, lay = card(16)
            lay.addWidget(label("Dữ liệu cán bộ cần bổ sung", "CardTitle"))
            lay.addWidget(rule())
            row = QHBoxLayout()
            for text, col in (("Thiếu số điện thoại", "sdt"), ("Thiếu số CCCD", "so_cccd"),
                              ("Thiếu ngày sinh", "ngay_sinh"), ("Thiếu đơn vị", "don_vi")):
                n = q(f"SELECT COUNT(*) FROM can_bo WHERE {col} IS NULL OR {col}=''")
                box = QVBoxLayout()
                val = label(str(n), "StatValue")
                val.setStyleSheet(f"color: {C['red'] if n else C['green']}; font-size: 18pt;")
                box.addWidget(val)
                box.addWidget(label(text, "Muted"))
                row.addLayout(box)
                row.addSpacing(30)
            row.addStretch(1)
            lay.addLayout(row)
            v.addWidget(f)

        if self.visible("complaints"):
            rows = self.db.conn.execute(
                "SELECT d.id, d.tieu_de, d.trang_thai, d.ngay_nhan, c.ho_ten FROM don_thu d "
                "LEFT JOIN can_bo c ON c.id=d.can_bo_id "
                f"WHERE d.trang_thai NOT IN ({_ph(xong)}) "
                f"ORDER BY (d.ngay_nhan IS NULL OR d.ngay_nhan=''), {sql_date_key('d.ngay_nhan')} ASC LIMIT 6",
                xong).fetchall()
            f, lay = card(16)
            lay.addWidget(label("Đơn thư chưa giải quyết, nhận lâu nhất", "CardTitle"))
            lay.addWidget(rule())
            if not rows:
                lay.addWidget(label("Không có đơn thư nào đang chờ xử lý.", "Muted"))
            else:
                t = DataTable([("tieu_de", "Tiêu đề", 240), ("ho_ten", "Cán bộ liên quan", 170),
                               ("ngay_nhan", "Ngày nhận", 100), ("trang_thai", "Trạng thái", 120)], sortable=False)
                t.set_rows(rows)
                t.setFixedHeight(46 + 36 * len(rows))
                lay.addWidget(t)
            v.addWidget(f)
        v.addStretch(1)

    def visible(self, mod_id):
        return mod_id not in self.disabled and self.app.can(mod_id, "view")

    def _group(self, expr, table):
        rows = self.db.conn.execute(f"SELECT {expr} AS k, COUNT(*) c FROM {table} GROUP BY k "
                                    "ORDER BY c DESC LIMIT 8").fetchall()
        return [(r["k"], r["c"]) for r in rows]
