# -*- coding: utf-8 -*-
"""
Xuất tài liệu ra HTML định dạng trang trọng (có quốc hiệu, tiêu ngữ theo
đúng thể thức văn bản hành chính Việt Nam) để người dùng in hoặc lưu PDF
ngay từ trình duyệt (Ctrl+P -> Save as PDF). Không dùng thư viện ngoài nên
luôn hoạt động ngoại tuyến trên mọi máy đã cài Python + trình duyệt mặc định.
"""
import datetime
import html
import os
import tempfile
import webbrowser

CSS = """
@page { size: A4; margin: 20mm 18mm; }
* { box-sizing: border-box; }
body { font-family: "Times New Roman", Georgia, serif; color: #1a1a1a;
       max-width: 800px; margin: 24px auto; padding: 0 16px; line-height: 1.5; }
.letterhead { text-align: center; margin-bottom: 18px; }
.letterhead .quochieu { font-weight: bold; text-transform: uppercase; font-size: 13pt; }
.letterhead .tieungu { font-weight: bold; font-size: 12pt; }
.letterhead .tieungu-line { display: inline-block; border-bottom: 1px solid #000; margin-top: 2px; }
.doc-title { text-align: center; margin: 22px 0 4px; }
.doc-title h1 { font-size: 15pt; text-transform: uppercase; margin: 0; }
.doc-sub { text-align: center; color: #444; font-size: 10.5pt; margin-bottom: 20px; }
.section-title { font-weight: bold; text-transform: uppercase; font-size: 11pt;
                  margin: 18px 0 8px; padding-bottom: 3px; border-bottom: 1px solid #999; }
table.info { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
table.info td { padding: 4px 6px; vertical-align: top; font-size: 11pt; }
table.info td.label { width: 220px; color: #333; }
table.info td.value { font-weight: bold; border-bottom: 1px dotted #bbb; }
table.list { width: 100%; border-collapse: collapse; font-size: 10.5pt; margin-top: 8px; }
table.list th { background: #7A1B1B; color: #fff; padding: 6px 8px; text-align: left; }
table.list td { padding: 5px 8px; border-bottom: 1px solid #ddd; }
table.list tr:nth-child(even) td { background: #f7f5fa; }
.footer { margin-top: 28px; font-size: 9.5pt; color: #555; display: flex; justify-content: space-between; }
.print-bar { text-align: center; margin: 14px 0; }
.print-bar button { font-size: 11pt; padding: 8px 18px; background: #7A1B1B; color: #fff;
                     border: none; border-radius: 4px; cursor: pointer; }
@media print { .print-bar { display: none; } }
"""


def _esc(v):
    return html.escape("" if v is None else str(v))


def _letterhead():
    return (
        '<div class="letterhead">'
        '<div class="quochieu">Cộng hòa xã hội chủ nghĩa Việt Nam</div>'
        '<div class="tieungu">Độc lập &ndash; Tự do &ndash; Hạnh phúc<div class="tieungu-line">&nbsp;</div></div>'
        "</div>"
    )


def build_profile_html(title, sections, meta_lines, extra_tables=None):
    """sections: [(tên nhóm, [(nhãn, giá_trị), ...]), ...]; mỗi nhóm có thể
    kèm phần tử thứ ba (cột, hàng) để vẽ thêm bảng kẻ dòng ngay dưới các
    trường của nhóm đó (vd Quá trình công tác: ngày vào ngành + các mốc).
    extra_tables: [(tên nhóm, [(khóa, nhãn), ...cột...], [hàng...]), ...] - vẽ
    thêm bảng kẻ dòng sau các nhóm thông tin chính."""
    rows_html = []
    for sec in sections:
        sec_title, fields = sec[0], sec[1]
        table = sec[2] if len(sec) > 2 else None
        rows_html.append(f'<div class="section-title">{_esc(sec_title)}</div>')
        if fields:
            rows_html.append('<table class="info">')
            for label, value in fields:
                rows_html.append(
                    f'<tr><td class="label">{_esc(label)}</td>'
                    f'<td class="value">{_esc(value) if value else "&nbsp;"}</td></tr>')
            rows_html.append("</table>")
        if table is not None:
            columns, table_rows = table
            rows_html.append(_render_table(columns, table_rows) if table_rows else
                             '<p style="color:#666;font-size:10.5pt;">(chưa có)</p>')
    for sec_title, columns, table_rows in (extra_tables or []):
        rows_html.append(f'<div class="section-title">{_esc(sec_title)}</div>')
        rows_html.append(_render_table(columns, table_rows))
    body = "\n".join(rows_html)
    return _wrap(title, meta_lines, body)


def _render_table(columns, rows):
    head = "".join(f"<th>{_esc(lbl)}</th>" for _k, lbl in columns)
    body_rows = []
    for r in rows:
        cells = "".join(f"<td>{_esc(r[k])}</td>" for k, _lbl in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return (f'<table class="list"><thead><tr>{head}</tr></thead>'
           f'<tbody>{"".join(body_rows)}</tbody></table>')


def build_list_html(title, meta_lines, columns, rows):
    """columns: [(khóa, nhãn), ...]; rows: list các dict/sqlite Row."""
    body = (_render_table(columns, rows) +
           f'<p style="margin-top:10px;font-size:10.5pt;color:#555;">Tổng số: {len(rows)} bản ghi</p>')
    return _wrap(title, meta_lines, body)


def _wrap(title, meta_lines, body_html):
    meta = "".join(f"<div>{_esc(m)}</div>" for m in meta_lines)
    now = datetime.datetime.now().strftime("%H:%M ngày %d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>{_esc(title)}</title>
<style>{CSS}</style></head><body>
<div class="print-bar"><button onclick="window.print()">🖨 In / Lưu PDF</button></div>
{_letterhead()}
<div class="doc-title"><h1>{_esc(title)}</h1></div>
<div class="doc-sub">{meta}</div>
{body_html}
<div class="footer"><span>Xuất từ phần mềm Quản lý cán bộ</span><span>Thời điểm xuất: {now}</span></div>
</body></html>"""


def open_html(html_str, filename_hint):
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename_hint)
    path = os.path.join(tempfile.gettempdir(), safe)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
    webbrowser.open("file://" + path.replace(os.sep, "/"))
    return path
