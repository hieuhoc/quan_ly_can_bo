# -*- coding: utf-8 -*-
"""Xuất / nhập Excel (.xlsx) bằng openpyxl.

File xuất ra có sẵn: tên cơ quan, tiêu đề in đậm căn giữa, dòng tiêu đề cột
tô nền, kẻ bảng, cột tự giãn, cố định dòng tiêu đề khi cuộn, khổ in A4 vừa
một trang ngang - mở ra là in được ngay."""
import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

_THIN = Side(style="thin", color="9CA3AF")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HEAD_FILL = PatternFill("solid", fgColor="F3F4F6")
_FONT = "Times New Roman"


def _safe(v):
    """Chặn công thức Excel độc hại: ô bắt đầu bằng = + - @ được ghi như chữ."""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return v
    s = str(v)
    if s[:1] in ("=", "+", "-", "@") and not s.lstrip("+-").replace(".", "", 1).isdigit():
        return "'" + s
    return s


def export_table(path, title, headers, rows, org_lines=(), meta_lines=(), landscape=True, sheet="Danh sách"):
    """headers: [nhãn cột]; rows: [[giá trị, ...], ...]."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    ncol = max(1, len(headers))
    r = 1
    for i, line in enumerate(org_lines):
        ws.cell(row=r, column=1, value=line).font = Font(name=_FONT, size=12, bold=(i == len(org_lines) - 1))
        r += 1
    if org_lines:
        r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)
    c = ws.cell(row=r, column=1, value=title.upper())
    c.font = Font(name=_FONT, size=14, bold=True)
    c.alignment = Alignment(horizontal="center")
    r += 1
    for line in meta_lines:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)
        c = ws.cell(row=r, column=1, value=line)
        c.font = Font(name=_FONT, size=11, italic=True)
        c.alignment = Alignment(horizontal="center")
        r += 1
    r += 1
    head_row = r
    ws.cell(row=r, column=1)
    for j, h in enumerate(["STT"] + list(headers), start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font = Font(name=_FONT, size=11, bold=True)
        c.fill = _HEAD_FILL
        c.border = _BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    widths = [5] + [max(8, len(str(h)) + 2) for h in headers]
    for i, row in enumerate(rows, start=1):
        r += 1
        for j, v in enumerate([i] + list(row), start=1):
            c = ws.cell(row=r, column=j, value=_safe(v))
            c.font = Font(name=_FONT, size=11)
            c.border = _BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True)
            widths[j - 1] = min(45, max(widths[j - 1], len(str(v or "")) + 2))
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(row=head_row + 1, column=3 if len(headers) > 1 else 2)
    ws.print_title_rows = f"{head_row}:{head_row}"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddFooter.center.text = "Trang &P / &N"
    ws.oddFooter.right.text = datetime.datetime.now().strftime("Xuất ngày %d/%m/%Y")
    wb.save(path)


def read_table(path):
    """Đọc sheet đầu tiên: tìm dòng tiêu đề (dòng đầu có >= 2 ô chữ), trả về
    danh sách dict {tiêu đề cột: giá trị chuỗi} cho các dòng bên dưới, kèm số
    dòng Excel tương ứng: [(số_dòng, dict), ...]."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    head_idx = None
    for i, row in enumerate(rows):
        texts = [str(v).strip() for v in row if v not in (None, "")]
        if len(texts) >= 2 and any("họ" in t.lower() or "mã" in t.lower() for t in texts):
            head_idx = i
            break
    if head_idx is None:
        return []
    headers = [("" if v is None else str(v).strip()) for v in rows[head_idx]]
    out = []
    for n, row in enumerate(rows[head_idx + 1:], start=head_idx + 2):
        if all(v in (None, "") for v in row):
            continue
        d = {}
        for h, v in zip(headers, row):
            if not h:
                continue
            if isinstance(v, datetime.datetime):
                v = v.strftime("%d/%m/%Y")
            elif isinstance(v, float) and v.is_integer():
                v = str(int(v))
            d[h] = "" if v is None else str(v).strip().lstrip("'")
        out.append((n, d))
    return out
