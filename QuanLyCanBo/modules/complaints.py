# -*- coding: utf-8 -*-
"""Module: Đơn thư, khiếu nại, tố cáo liên quan đến cán bộ."""
import csv
import datetime

from PySide6.QtWidgets import QLineEdit

from core import attachments
from ui.theme import C
from ui.widgets import (DateField, EmployeePicker, FilePicker, FormDialog, ListPage, SearchDialog, ask, choice,
                        date_key, info, save_file_dialog, sql_date_key, text_edit, valid_date, warn)

MODULE_ID = "complaints"
TABLE = "don_thu"
LOAI_OPTIONS = ["Đơn thư", "Khiếu nại", "Tố cáo", "Phản ánh"]
TRANG_THAI_OPTIONS = ["Mới tiếp nhận", "Đang xác minh", "Đang xử lý", "Đã giải quyết", "Tồn đọng"]
COLS = [("tieu_de", "Tiêu đề", 200), ("loai", "Loại", 90), ("ho_ten", "Cán bộ liên quan", 150),
        ("nguoi_gui", "Người gửi", 120), ("ngay_nhan", "Ngày nhận", 100), ("trang_thai", "Trạng thái", 120),
        ("ngay_giai_quyet", "Ngày giải quyết", 110), ("file_dinh_kem", "File", 70)]


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Đơn thư - Khiếu nại", COLS, subtitle="Đơn thư, khiếu nại, tố cáo, phản ánh liên quan đến cán bộ")
        self.add_action("➕  Thêm mới", self.open_add, "primary", perm="add")
        self.add_action("✏  Sửa / Cập nhật", self.open_edit, perm="edit", needs_selection=True)
        self.add_action("🗑  Xóa", self.on_delete, "danger", perm="delete", needs_selection=True)
        self.add_action("📎  Mở file đính kèm", self.open_attachment, needs_selection=True,
                        check=lambda r: r and r.get("file_dinh_kem"))
        self.add_action("📤  Xuất CSV", self.export_csv, perm="export", right=True)
        self.table.set_display("file_dinh_kem", lambda v, r: "📎 Có" if v else "—")
        self.table.set_row_color(lambda r: C["green"] if r["trang_thai"] == "Đã giải quyết"
                                 else (C["red"] if r["trang_thai"] == "Tồn đọng" else None))
        self.table.activated_row.connect(self.open_edit)
        self.table.delete_pressed.connect(self.on_delete)
        self.refresh()

    def load_rows(self):
        sql = "SELECT d.*, c.ho_ten AS ho_ten FROM don_thu d LEFT JOIN can_bo c ON c.id = d.can_bo_id"
        conds, params = [], []
        f = self.adv_filters
        if f:
            if f.get("tieu_de"):
                conds.append("d.tieu_de LIKE ?"); params.append(f"%{f['tieu_de']}%")
            if f.get("loai"):
                conds.append("d.loai = ?"); params.append(f["loai"])
            if f.get("trang_thai"):
                conds.append("d.trang_thai = ?"); params.append(f["trang_thai"])
            if f.get("nguoi_gui"):
                conds.append("d.nguoi_gui LIKE ?"); params.append(f"%{f['nguoi_gui']}%")
            if f.get("tu_ngay"):
                conds.append(f"{sql_date_key('d.ngay_nhan')} >= ?"); params.append(date_key(f["tu_ngay"]))
        elif self.search_text():
            like = f"%{self.search_text()}%"
            conds.append("(d.tieu_de LIKE ? OR d.nguoi_gui LIKE ? OR d.trang_thai LIKE ? OR c.ho_ten LIKE ? "
                         "OR d.noi_dung LIKE ?)")
            params.extend([like] * 5)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += f" ORDER BY (d.ngay_nhan IS NULL OR d.ngay_nhan=''), {sql_date_key('d.ngay_nhan')} DESC, d.id DESC"
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self.load_rows()
        self.table.set_rows(rows)
        self.count_lbl.setText(f"Tổng số: {len(rows)} đơn")
        self.update_actions()

    def open_advanced(self):
        SearchDialog(self, [("tieu_de", "Tiêu đề", QLineEdit()),
                            ("loai", "Loại", choice([""] + LOAI_OPTIONS)),
                            ("trang_thai", "Trạng thái", choice([""] + TRANG_THAI_OPTIONS)),
                            ("nguoi_gui", "Người gửi", QLineEdit()),
                            ("tu_ngay", "Nhận từ ngày (dd/mm/yyyy)", QLineEdit())],
                     validate=lambda v: "Từ ngày phải theo dạng dd/mm/yyyy." if v.get("tu_ngay") and not
                     valid_date(v["tu_ngay"]) else None).exec()

    def open_add(self):
        if not self.deny("add") and EntryDialog(self, None).exec():
            self.refresh()

    def open_edit(self):
        if self.deny("edit"):
            return
        row = self.need_selection("một đơn thư")
        if row and EntryDialog(self, self.db.fetch_one(TABLE, row["id"])).exec():
            self.refresh()

    def open_attachment(self):
        row = self.table.selected_row()
        if row and row["file_dinh_kem"] and not attachments.open_file(self.app.app_dir, row["file_dinh_kem"]):
            warn(self, "Không tìm thấy hoặc không mở được file đính kèm.", "Không mở được file")

    def on_delete(self):
        if self.deny("delete"):
            return
        row = self.need_selection("một đơn thư")
        if not row or not ask(self, f"Xóa đơn thư '{row['tieu_de']}'?\nThao tác không thể hoàn tác.",
                              yes="Xóa", danger=True):
            return
        if row["file_dinh_kem"]:
            attachments.delete_attachment(self.app.app_dir, row["file_dinh_kem"])
        self.db.delete(TABLE, row["id"])
        self.db.log(self.app.user["username"], "Xóa đơn thư/khiếu nại", row["tieu_de"])
        self.app.set_status("Đã xóa đơn thư.")
        self.refresh()

    def export_csv(self):
        if self.deny("export"):
            return
        path = save_file_dialog(self, datetime.datetime.now().strftime("don_thu_khieu_nai_%Y%m%d.csv"))
        if not path:
            return
        rows = self.table.rows()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Tiêu đề", "Loại", "Cán bộ liên quan", "Người gửi", "Ngày nhận", "Nội dung", "Trạng thái",
                        "Ngày giải quyết", "Kết quả", "Ghi chú"])
            for r in rows:
                w.writerow([r["tieu_de"], r["loai"], r["ho_ten"] or "", r["nguoi_gui"] or "", r["ngay_nhan"] or "",
                            r["noi_dung"] or "", r["trang_thai"], r["ngay_giai_quyet"] or "", r["ket_qua"] or "",
                            r["ghi_chu"] or ""])
        self.db.log(self.app.user["username"], "Xuất CSV", f"{len(rows)} bản ghi (đơn thư)")
        info(self, f"Đã xuất file:\n{path}", "Xuất CSV")


class EntryDialog(FormDialog):
    def __init__(self, panel, row):
        super().__init__(panel, "Sửa đơn thư / khiếu nại" if row else "Thêm đơn thư / khiếu nại", 600, 720)
        self.panel, self.db, self.row = panel, panel.db, row
        r = dict(row) if row else {}
        f = self.form()
        self.e_title = QLineEdit(r.get("tieu_de") or "")
        self.c_loai = choice(LOAI_OPTIONS, r.get("loai"))
        self.picker = EmployeePicker(self.db)
        if r.get("can_bo_id"):
            self.picker.set_by_id(r["can_bo_id"])
        self.e_gui = QLineEdit(r.get("nguoi_gui") or "")
        self.d_nhan = DateField(r.get("ngay_nhan") or "")
        self.t_noidung = text_edit(r.get("noi_dung"), 90)
        self.c_status = choice(TRANG_THAI_OPTIONS, r.get("trang_thai"))
        self.d_gq = DateField(r.get("ngay_giai_quyet") or "")
        self.t_ketqua = text_edit(r.get("ket_qua"), 70)
        self.e_note = QLineEdit(r.get("ghi_chu") or "")
        self.file = FilePicker(attachments.display_name(r.get("file_dinh_kem")))
        for text, w in (("Tiêu đề *", self.e_title), ("Loại *", self.c_loai), ("Cán bộ liên quan", self.picker),
                        ("Người gửi đơn", self.e_gui), ("Ngày nhận", self.d_nhan), ("Nội dung", self.t_noidung),
                        ("Trạng thái *", self.c_status), ("Ngày giải quyết", self.d_gq),
                        ("Kết quả xử lý", self.t_ketqua), ("Ghi chú", self.e_note), ("File đính kèm", self.file)):
            f.addRow(text, w)
        self.body.addStretch(1)
        self.add_buttons("💾  Lưu thay đổi" if row else "➕  Thêm mới", self.save)

    def save(self):
        if not self.e_title.text().strip():
            warn(self, "Vui lòng nhập Tiêu đề.", "Thiếu thông tin")
            return
        for name, w in (("Ngày nhận", self.d_nhan), ("Ngày giải quyết", self.d_gq)):
            if w.text() and not valid_date(w.text()):
                warn(self, f"{name} phải theo dạng dd/mm/yyyy.", "Sai định dạng")
                return
        user = self.panel.app.user["username"]
        data = dict(tieu_de=self.e_title.text().strip(), loai=self.c_loai.currentText(), can_bo_id=self.picker.get(),
                    nguoi_gui=self.e_gui.text().strip(), ngay_nhan=self.d_nhan.text(),
                    noi_dung=self.t_noidung.toPlainText().strip(), trang_thai=self.c_status.currentText(),
                    ngay_giai_quyet=self.d_gq.text(), ket_qua=self.t_ketqua.toPlainText().strip(),
                    ghi_chu=self.e_note.text().strip())
        if self.file.pending:
            data["file_dinh_kem"] = attachments.save_attachment(self.panel.app.app_dir, TABLE, self.file.pending)
            if self.row and self.row["file_dinh_kem"]:
                attachments.delete_attachment(self.panel.app.app_dir, self.row["file_dinh_kem"])
        if self.row is None:
            data["created_by"] = user
            self.db.insert(TABLE, data)
            self.db.log(user, "Tạo đơn thư/khiếu nại", data["tieu_de"])
            self.panel.app.set_status("Đã lưu đơn thư mới.")
        else:
            self.db.update(TABLE, self.row["id"], data)
            self.db.log(user, "Cập nhật đơn thư/khiếu nại", f"{data['tieu_de']} -> {data['trang_thai']}")
            self.panel.app.set_status("Đã cập nhật đơn thư.")
        self.accept()
