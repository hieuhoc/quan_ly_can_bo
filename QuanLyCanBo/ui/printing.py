# -*- coding: utf-8 -*-
"""In ra PDF theo thể thức văn bản hành chính: tên cơ quan (trái) - quốc
hiệu, tiêu ngữ (phải), tiêu đề, bảng / nội dung, địa danh ngày tháng và
khối chữ ký. Dùng QTextDocument + QPdfWriter của Qt (không cần thư viện
ngoài), tự ngắt trang và đánh số trang."""
import datetime
import html
import os

from PySide6.QtCore import QMarginsF, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from core import report

_CSS = """
body { font-family: 'Times New Roman'; font-size: 12pt; }
td, th { font-size: 11pt; }
table.data { border-collapse: collapse; }
table.data th { background: #EEEEEE; font-weight: bold; }
.title { font-size: 15pt; font-weight: bold; }
.sub { font-style: italic; }
.sec { font-weight: bold; font-size: 12pt; }
"""


def _e(v):
    return html.escape("" if v is None else str(v))


def _letterhead(db):
    s = report.settings(db)
    return (
        '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td width="42%" align="center">{_e(s["in_co_quan"].upper())}<br>'
        f'<b><u>{_e(s["in_don_vi"].upper())}</u></b></td>'
        '<td width="58%" align="center"><b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b><br>'
        '<b><u>Độc lập - Tự do - Hạnh phúc</u></b></td></tr></table>')


def _signature(db):
    s = report.settings(db)
    d = datetime.date.today()
    return (
        '<br><table width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td width="50%"></td>'
        f'<td width="50%" align="center"><i>{_e(s["in_dia_danh"])}, ngày {d.day:02d} tháng {d.month:02d} '
        f'năm {d.year}</i></td></tr><tr>'
        f'<td align="center"><b>{_e(s["in_ky_trai"].upper())}</b></td>'
        f'<td align="center"><b>{_e(s["in_ky_phai"].upper())}</b></td></tr></table>')


def _table(columns, rows, stt=True):
    head = ('<th width="36" style="white-space: nowrap">STT</th>' if stt else "") + "".join(f"<th>{_e(lbl)}</th>" for _k, lbl in columns)
    body = []
    for i, r in enumerate(rows, start=1):
        cells = (f'<td align="center">{i}</td>' if stt else "") + "".join(
            f"<td>{_e(r.get(k))}</td>" for k, _l in columns)
        body.append(f"<tr>{cells}</tr>")
    return (f'<table class="data" width="100%" border="1" cellpadding="4" cellspacing="0">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>')


def _write(path, body_html, landscape):
    doc = QTextDocument()
    doc.setDefaultFont(QFont("Times New Roman", 12))
    doc.setDefaultStyleSheet(_CSS)
    doc.setHtml(f"<html><body>{body_html}</body></html>")
    w = QPdfWriter(path)
    w.setResolution(150)
    w.setPageLayout(QPageLayout(QPageSize(QPageSize.A4),
                                QPageLayout.Landscape if landscape else QPageLayout.Portrait,
                                QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter))
    # QTextDocument.print_ tự chừa lề 2 cm mỗi cạnh nên khổ giấy để lề 0.
    w.setTitle(os.path.basename(path))
    w.setCreator("Phần mềm Quản lý cán bộ")
    # Để trống pageSize: QTextDocument tự dàn trang theo khổ giấy của QPdfWriter
    # và quy đổi cỡ chữ (pt) đúng theo độ phân giải máy in.
    doc.print_(w)
    return path


def open_pdf(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def list_pdf(path, db, title, columns, rows, meta_lines=(), landscape=True):
    """In danh sách dạng bảng (vd danh sách trích ngang cán bộ)."""
    meta = "".join(f'<div class="sub" align="center">{_e(m)}</div>' for m in meta_lines)
    body = (_letterhead(db) + f'<br><div class="title" align="center">{_e(title.upper())}</div>{meta}<br>'
            + _table(columns, rows) + f"<p>Tổng số: {len(rows)}</p>" + _signature(db))
    return _write(path, body, landscape)


def profile_pdf(path, db, title, sections, photo_path=None, meta_lines=()):
    """In hồ sơ: sections = [(tên nhóm, [(nhãn, giá trị)], (cột, hàng) | None)]."""
    meta = "".join(f'<div class="sub" align="center">{_e(m)}</div>' for m in meta_lines)
    parts = [_letterhead(db), f'<br><div class="title" align="center">{_e(title.upper())}</div>{meta}<br>']
    first = True
    for sec in sections:
        name, fields = sec[0], sec[1]
        table = sec[2] if len(sec) > 2 else None
        parts.append(f'<p class="sec">{_e(name.upper())}</p>')
        if fields:
            rows = "".join(f'<tr><td width="230">{_e(lbl)}</td><td><b>{_e(val) or "&nbsp;"}</b></td></tr>'
                           for lbl, val in fields)
            info_tbl = f'<table width="100%" cellpadding="3" cellspacing="0">{rows}</table>'
            if first and photo_path and os.path.exists(photo_path):
                url = QUrl.fromLocalFile(photo_path).toString()
                parts.append('<table width="100%" cellpadding="0" cellspacing="0"><tr>'
                             f'<td>{info_tbl}</td><td width="130" align="right" valign="top">'
                             f'<img src="{_e(url)}" width="113" height="151"></td></tr></table>')
            else:
                parts.append(info_tbl)
        first = False if fields else first
        if table is not None:
            cols, trows = table
            parts.append(_table(cols, trows) if trows else "<p><i>(chưa có)</i></p>")
    parts.append(_signature(db))
    return _write(path, "".join(parts), landscape=False)
