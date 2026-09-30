# -*- coding: utf-8 -*-
"""Bảng màu và giao diện (Qt Style Sheet) dùng chung cho toàn phần mềm:
đỏ CAND làm màu nhấn trên nền trung tính, thanh bên tối."""
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPolygonF
from PySide6.QtCore import QPointF

FONT = "Segoe UI"

C = dict(
    primary="#A11D21", primary_dark="#7F1518", primary_light="#C0282D", primary_soft="#FBEDED",
    gold="#C99A2E",
    bg="#F3F5F8", card="#FFFFFF", text="#1F2937", muted="#6B7280", border="#E4E7EC", line="#EEF0F3",
    sidebar="#1C2330", sidebar_hover="#2A3342", sidebar_text="#C7CDD8", sidebar_muted="#7D8696",
    sidebar_line="#2E3746",
    green="#15803D", blue="#1D4ED8", red="#B91C1C", amber="#B45309",
    sel="#FCE8E8", hover_row="#F5F7FA", table_head="#F3F4F6", table_head_text="#374151",
    input_border="#D0D5DD", disabled_bg="#F3F4F6", disabled_fg="#A0A6B1",
)


def app_font():
    f = QFont(FONT, 10)
    f.setStyleHint(QFont.SansSerif)
    return f


QSS = f"""
* {{ font-family: "{FONT}"; font-size: 10pt; color: {C['text']}; }}
QMainWindow, QDialog, #Page {{ background: {C['bg']}; }}
QToolTip {{ background: {C['text']}; color: white; border: none; padding: 5px 8px; border-radius: 4px; }}

/* ---------- thẻ, tiêu đề ---------- */
#Card {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px; }}
#Card QLabel, #Card QCheckBox, #Card QRadioButton {{ background: transparent; }}
#PageTitle {{ font-size: 16pt; font-weight: 700; }}
#CardTitle {{ font-size: 12pt; font-weight: 700; }}
#Muted {{ color: {C['muted']}; font-size: 9pt; }}
#Note {{ color: {C['primary']}; font-size: 9pt; }}
#SectionTitle {{ color: {C['primary']}; font-weight: 700; font-size: 9pt; letter-spacing: 0.5px; }}
#SectionBar {{ background: {C['primary']}; border-radius: 1px; }}
#Rule {{ background: {C['border']}; max-height: 1px; min-height: 1px; border: none; }}
#StatValue {{ font-size: 22pt; font-weight: 700; }}
#Badge {{ background: {C['border']}; color: {C['muted']}; border-radius: 9px; padding: 1px 8px;
          font-size: 8pt; font-weight: 700; }}
#Badge[active="true"] {{ background: {C['primary']}; color: white; }}

/* ---------- nút ---------- */
QPushButton {{ background: white; border: 1px solid {C['input_border']}; border-radius: 6px;
               padding: 7px 14px; min-height: 18px; }}
QPushButton:hover {{ background: {C['table_head']}; border-color: {C['primary']}; }}
QPushButton:pressed {{ background: {C['border']}; }}
QPushButton:disabled {{ background: {C['disabled_bg']}; color: {C['disabled_fg']}; border-color: {C['border']}; }}
QPushButton[variant="primary"] {{ background: {C['primary']}; color: white; border: 1px solid {C['primary']};
                                  font-weight: 600; }}
QPushButton[variant="primary"]:hover {{ background: {C['primary_dark']}; border-color: {C['primary_dark']}; }}
QPushButton[variant="primary"]:disabled {{ background: {C['disabled_bg']}; color: {C['disabled_fg']};
                                           border-color: {C['border']}; }}
QPushButton[variant="danger"] {{ background: #C62828; color: white; border: 1px solid #C62828; font-weight: 600; }}
QPushButton[variant="danger"]:hover {{ background: #A61E1E; }}
QPushButton[variant="danger"]:disabled {{ background: {C['disabled_bg']}; color: {C['disabled_fg']};
                                          border-color: {C['border']}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; }}
QPushButton[variant="ghost"]:hover {{ background: {C['table_head']}; border-color: {C['border']}; }}
QToolButton {{ background: white; border: 1px solid {C['input_border']}; border-radius: 6px; padding: 4px; }}
QToolButton:hover {{ border-color: {C['primary']}; }}

/* ---------- ô nhập ---------- */
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox {{
    background: white; border: 1px solid {C['input_border']}; border-radius: 6px; padding: 6px 8px;
    selection-background-color: {C['primary']}; selection-color: white; }}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {C['primary']}; }}
QLineEdit:disabled, QComboBox:disabled {{ background: {C['disabled_bg']}; color: {C['disabled_fg']}; }}
QLineEdit[readOnly="true"] {{ background: {C['table_head']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url(icons:chevron.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ border: 1px solid {C['border']}; background: white; outline: none;
                               selection-background-color: {C['sel']}; selection-color: {C['text']}; padding: 4px; }}
QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QCheckBox::indicator {{ border: 1px solid {C['input_border']}; border-radius: 4px; background: white; }}
QCheckBox::indicator:checked {{ background: {C['primary']}; border-color: {C['primary']};
    image: url(icons:check.svg); }}
QCheckBox::indicator:disabled {{ background: {C['disabled_bg']}; border-color: {C['border']}; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border: 1px solid {C['input_border']}; border-radius: 8px;
                           background: white; }}
QRadioButton::indicator:checked {{ width: 8px; height: 8px; border: 4px solid {C['primary']}; border-radius: 8px;
                                   background: white; }}

/* ---------- bảng ---------- */
QTableView {{ background: white; border: 1px solid {C['border']}; border-radius: 8px;
              gridline-color: {C['line']}; alternate-background-color: #FAFBFC;
              selection-background-color: {C['sel']}; selection-color: {C['text']}; outline: none; }}
QTableView::item {{ padding: 0 10px; border-bottom: 1px solid {C['line']}; }}
QTableView::item:hover {{ background: {C['hover_row']}; }}
QTableView::item:selected {{ background: {C['sel']}; color: {C['text']}; }}
QHeaderView::section {{ background: {C['table_head']}; color: {C['table_head_text']}; font-weight: 700;
    font-size: 8.5pt; padding: 9px 10px; border: none; border-bottom: 1px solid {C['input_border']};
    border-right: 1px solid {C['border']}; }}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{ background: {C['table_head']}; border: none; }}

/* ---------- thanh cuộn mảnh ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C9CED6; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #A9B0BB; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C9CED6; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ---------- tab gạch chân ---------- */
#TabButton {{ background: transparent; border: none; border-bottom: 3px solid transparent;
              border-radius: 0; padding: 8px 2px; color: {C['muted']}; font-size: 10.5pt; }}
#TabButton:hover {{ color: {C['text']}; border-bottom-color: {C['input_border']}; background: transparent; }}
#TabButton:checked {{ color: {C['primary']}; font-weight: 700; border-bottom-color: {C['primary']}; }}

/* ---------- đầu trang ---------- */
#Header {{ background: white; border-bottom: 1px solid {C['border']}; }}
#Header QLabel {{ background: transparent; }}
#AppTitle {{ color: {C['primary']}; font-size: 14pt; font-weight: 800; }}
#UserName {{ font-weight: 700; }}

/* ---------- thanh bên ---------- */
#Sidebar {{ background: {C['sidebar']}; }}
#Sidebar QLabel {{ background: transparent; }}
#NavGroup {{ color: {C['sidebar_muted']}; font-size: 8pt; font-weight: 700; padding: 14px 0 4px 18px; }}
#NavButton {{ background: transparent; border: none; border-radius: 8px; color: {C['sidebar_text']};
              text-align: left; padding: 10px 14px; font-size: 10pt; }}
#NavButton:hover {{ background: {C['sidebar_hover']}; color: white; }}
#NavButton:checked {{ background: {C['primary']}; color: white; font-weight: 700; }}
#SidebarFoot {{ color: {C['sidebar_muted']}; font-size: 8pt; }}
#MenuToggle {{ background: transparent; border: 1px solid transparent; border-radius: 8px; font-size: 14pt;
               padding: 2px 8px; color: {C['text']}; }}
#MenuToggle:hover {{ background: {C['table_head']}; border-color: {C['border']}; }}

/* ---------- đăng nhập ---------- */
#LoginPage {{ background: {C['sidebar']}; }}
#LoginCard {{ background: white; border-radius: 12px; border-top: 4px solid {C['primary']}; }}
#LoginCard QLabel, #LoginCard QCheckBox {{ background: transparent; }}
#LoginTitle {{ color: {C['primary']}; font-size: 18pt; font-weight: 800; }}
#Error {{ color: {C['red']}; font-size: 9pt; }}

/* ---------- hộp thoại ---------- */
#DialogHead {{ background: white; border-top: 3px solid {C['primary']}; border-bottom: 1px solid {C['border']}; }}
#DialogTitle {{ font-size: 13pt; font-weight: 700; background: transparent; }}
#DialogBody {{ background: white; }}
#DialogFoot {{ background: {C['bg']}; border-top: 1px solid {C['border']}; }}
QStatusBar {{ background: white; border-top: 1px solid {C['border']}; color: {C['muted']}; font-size: 9pt; }}
QStatusBar QLabel {{ color: {C['muted']}; font-size: 9pt; padding: 0 8px; }}
QMessageBox {{ background: white; }}
QMenu {{ background: white; border: 1px solid {C['border']}; padding: 4px; }}
QCalendarWidget QToolButton {{ border: none; padding: 4px 8px; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {C['table_head']}; }}
QCalendarWidget QAbstractItemView {{ selection-background-color: {C['primary']}; selection-color: white; }}
"""


def install(app):
    """Áp giao diện cho QApplication (gọi một lần khi khởi động)."""
    from PySide6.QtCore import QDir
    from core.paths import resource
    QDir.setSearchPaths("icons", [resource("assets")])
    app.setStyle("Fusion")
    app.setFont(app_font())
    app.setStyleSheet(QSS)


def draw_shield(painter: QPainter, x, y, size):
    """Vẽ logo khiên đỏ sao vàng (không phụ thuộc font emoji của máy)."""
    s = size / 38.0
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(0, 0, 0, 0))
    path = QPainterPath()
    pts = [(19, 2), (34, 7), (34, 18), (31, 27), (19, 36), (7, 27), (4, 18), (4, 7)]
    path.addPolygon(QPolygonF([QPointF(x + px * s, y + py * s) for px, py in pts]))
    path.closeSubpath()
    painter.fillPath(path, QColor(C["primary"]))
    star = [(19, 10), (21.2, 16), (27.5, 16), (22.4, 19.8), (24.4, 26), (19, 22.2), (13.6, 26),
            (15.6, 19.8), (10.5, 16), (16.8, 16)]
    sp = QPainterPath()
    sp.addPolygon(QPolygonF([QPointF(x + px * s, y + py * s) for px, py in star]))
    sp.closeSubpath()
    painter.fillPath(sp, QColor(C["gold"]))
    painter.restore()
