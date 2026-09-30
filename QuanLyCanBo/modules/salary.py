# -*- coding: utf-8 -*-
"""Module: Nâng lương - Thăng cấp bậc hàm.

Nâng lương và thăng cấp bậc hàm là MỘT quá trình không tách rời: mỗi bản
ghi là một quyết định, ghi cấp bậc mới và hệ số lương mới của cán bộ (có
thể chỉ thay đổi một trong hai). Tất cả nằm trong một bảng, quyết định mới
nhất lên đầu. Dữ liệu từ bản cũ (loại "Nâng lương định kỳ / trước hạn",
"Thăng cấp bậc hàm") vẫn hiển thị nguyên như trước trong cột Hình thức."""
from PySide6.QtWidgets import QCheckBox, QLineEdit

from core import attachments, cand_data
from ui.widgets import (DateField, EmployeePicker, FilePicker, FormDialog, ListPage, SearchDialog, SuggestCombo,
                        ask, choice, date_key, label, sql_date_key, text_edit, valid_date, warn)

MODULE_ID = "salary"
TABLE = "qua_trinh_luong"
HINH_THUC = ["Định kỳ", "Trước hạn", "Khác"]
HINH_THUC_KHAC = "Khác"
COLS = [("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160), ("loai", "Hình thức", 100),
        ("ngay_quyet_dinh", "Ngày QĐ", 100), ("so_quyet_dinh", "Số quyết định", 130),
        ("cap_bac_moi", "Cấp bậc mới", 110), ("he_so_luong_moi", "Hệ số lương mới", 120),
        ("nguoi_ky", "Người ký", 130), ("ly_do_ngoai_le", "Lý do (ngoài quy định)", 180),
        ("noi_dung", "Nội dung", 180), ("file_dinh_kem", "File", 70)]


def ngoai_quy_dinh(hinh_thuc, cap_bac, he_so):
    """Trả về mô tả điểm khác quy định (cần ghi lý do), hoặc None nếu đúng quy định:
    - hình thức "Khác";
    - hệ số lương không khớp bảng hệ số theo cấp bậc (Nghị định 204/2004/NĐ-CP)."""
    reasons = []
    if hinh_thuc == HINH_THUC_KHAC:
        reasons.append("hình thức Khác")
    chuan = cand_data.HE_SO_LUONG_THEO_CAP_BAC.get(cap_bac or "")
    if chuan and he_so:
        try:
            if abs(float(he_so) - float(chuan)) > 1e-9:
                reasons.append(f"hệ số {he_so} khác hệ số theo cấp bậc {cap_bac} ({chuan})")
        except ValueError:
            pass
    return "; ".join(reasons) or None


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Nâng lương - Thăng cấp bậc hàm", COLS,
                         subtitle="Mỗi quyết định ghi cấp bậc mới và hệ số lương mới của cán bộ")
        self.add_action("➕  Thêm quyết định", self.open_add, "primary", perm="add")
        self.add_action("✏  Sửa", self.open_edit, perm="edit", needs_selection=True)
        self.add_action("🗑  Xóa", self.on_delete, "danger", perm="delete", needs_selection=True)
        self.add_action("📎  Mở file đính kèm", self.open_attachment, needs_selection=True,
                        check=lambda r: r and r.get("file_dinh_kem"))
        self.add_action("📊  Xuất Excel", lambda: self.export_excel(
            "Danh sách quyết định nâng lương - thăng cấp bậc hàm", "nang_luong_thang_cap",
            columns=[(k, lbl) for k, lbl, _w in COLS if k != "file_dinh_kem"]), perm="export", right=True)
        self.add_action("🖨  In PDF", lambda: self.print_pdf(
            "Danh sách quyết định nâng lương - thăng cấp bậc hàm", "nang_luong_thang_cap",
            columns=[(k, lbl) for k, lbl, _w in COLS if k not in ("file_dinh_kem", "noi_dung")]),
            perm="export", right=True)
        self.table.set_display("file_dinh_kem", lambda v, r: "📎 Có" if v else "—")
        from ui.theme import C
        self.table.set_row_color(lambda r: C["amber"] if r.get("ly_do_ngoai_le") else None)
        self.table.activated_row.connect(self.open_edit)
        self.table.delete_pressed.connect(self.on_delete)
        self.refresh()

    def load_rows(self):
        sql = ("SELECT q.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM qua_trinh_luong q "
               "JOIN can_bo c ON c.id = q.can_bo_id WHERE 1=1")
        params = []
        f = self.adv_filters
        if f:
            if f.get("ho_ten"):
                sql += " AND c.ho_ten LIKE ?"; params.append(f"%{f['ho_ten']}%")
            if f.get("tu_ngay"):
                sql += f" AND {sql_date_key('q.ngay_quyet_dinh')} >= ?"; params.append(date_key(f["tu_ngay"]))
            if f.get("so_quyet_dinh"):
                sql += " AND q.so_quyet_dinh LIKE ?"; params.append(f"%{f['so_quyet_dinh']}%")
            if f.get("cap_bac_moi"):
                sql += " AND q.cap_bac_moi = ?"; params.append(f["cap_bac_moi"])
        elif self.search_text():
            like = f"%{self.search_text()}%"
            sql += (" AND (c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR q.noi_dung LIKE ? OR q.so_quyet_dinh LIKE ?"
                    " OR q.cap_bac_moi LIKE ? OR q.nguoi_ky LIKE ?)")
            params.extend([like] * 6)
        sql += (" ORDER BY (q.ngay_quyet_dinh IS NULL OR q.ngay_quyet_dinh==''), "
                f"{sql_date_key('q.ngay_quyet_dinh')} DESC, q.id DESC")
        return self.db.conn.execute(sql, params).fetchall()

    def refresh(self):
        rows = self.load_rows()
        self.table.set_rows(rows)
        self.count_lbl.setText(f"Tổng số: {len(rows)} quyết định")
        self.update_actions()

    def open_advanced(self):
        SearchDialog(self, [("ho_ten", "Họ và tên cán bộ", QLineEdit()),
                            ("tu_ngay", "Quyết định từ ngày (dd/mm/yyyy)", QLineEdit()),
                            ("so_quyet_dinh", "Số quyết định", QLineEdit()),
                            ("cap_bac_moi", "Cấp bậc mới", choice([""] + cand_data.CAP_BAC))],
                     validate=lambda v: "Từ ngày phải theo dạng dd/mm/yyyy." if v.get("tu_ngay") and not
                     valid_date(v["tu_ngay"]) else None).exec()

    def open_add(self):
        if not self.deny("add") and EntryDialog(self, None).exec():
            self.refresh()

    def open_edit(self):
        if self.deny("edit"):
            return
        row = self.need_selection("một quyết định")
        if row and EntryDialog(self, self.db.fetch_one(TABLE, row["id"])).exec():
            self.refresh()

    def open_attachment(self):
        row = self.table.selected_row()
        if row and row["file_dinh_kem"] and not attachments.open_file(self.app.app_dir, row["file_dinh_kem"]):
            warn(self, "Không tìm thấy hoặc không mở được file đính kèm.", "Không mở được file")

    def on_delete(self):
        if self.deny("delete"):
            return
        row = self.need_selection("một quyết định")
        if not row or not ask(self, "Xóa quyết định này?\nThao tác không thể hoàn tác.", yes="Xóa", danger=True):
            return
        if row["file_dinh_kem"]:
            attachments.delete_attachment(self.app.app_dir, row["file_dinh_kem"])
        self.db.delete(TABLE, row["id"])
        self.db.log(self.app.user["username"], "Xóa quyết định nâng lương - thăng cấp",
                    f"{row['ma_cb']} - {row['ho_ten']}: {row['so_quyet_dinh'] or 'id=' + str(row['id'])}")
        self.app.set_status("Đã xóa quyết định.")
        self.refresh()

class EntryDialog(FormDialog):
    """Thêm / sửa MỘT quyết định nâng lương - thăng cấp bậc hàm."""

    def __init__(self, panel, row):
        super().__init__(panel, "Sửa quyết định nâng lương - thăng cấp" if row
                         else "Thêm quyết định nâng lương - thăng cấp", 600, 720)
        self.panel, self.db, self.row = panel, panel.db, row
        r = dict(row) if row else {}
        f = self.form()
        self.picker = EmployeePicker(self.db)
        if r.get("can_bo_id"):
            self.picker.set_by_id(r["can_bo_id"])
        self.c_loai = choice(HINH_THUC, r.get("loai"))
        self.d_ngay = DateField(r.get("ngay_quyet_dinh") or "")
        self.e_so = QLineEdit(r.get("so_quyet_dinh") or "")
        self.e_ky = QLineEdit(r.get("nguoi_ky") or "")
        self.c_cap = choice([""] + cand_data.CAP_BAC, r.get("cap_bac_moi") or "")
        self.c_heso = SuggestCombo(cand_data.HE_SO_LUONG_HOP_LE, text=r.get("he_so_luong_moi") or "")
        self.e_lydo = QLineEdit(r.get("ly_do_ngoai_le") or "")
        self.e_lydo.setPlaceholderText("Bắt buộc khi hình thức Khác hoặc hệ số khác bảng theo cấp bậc")
        self.lbl_lydo = label("", "Note", wrap=True)
        for w in (self.c_loai, self.c_cap):
            w.currentTextChanged.connect(self._check_rule)
        self.c_heso.currentTextChanged.connect(self._check_rule)
        self.c_cap.currentTextChanged.connect(self._on_rank)
        self.t_nd = text_edit(r.get("noi_dung"), 70)
        self.e_note = QLineEdit(r.get("ghi_chu") or "")
        self.file = FilePicker(attachments.display_name(r.get("file_dinh_kem")))
        self.sync = QCheckBox("Cập nhật cấp bậc và hệ số lương hiện tại của cán bộ theo quyết định này")
        self.sync.setChecked(row is None)
        for text, w in (("Cán bộ *", self.picker), ("Hình thức *", self.c_loai), ("Ngày quyết định", self.d_ngay),
                        ("Số quyết định", self.e_so), ("Người ký", self.e_ky), ("Cấp bậc mới", self.c_cap),
                        ("Hệ số lương mới", self.c_heso)):
            f.addRow(text, w)
        f.addRow("", label("Nhập cấp bậc mới, hệ số lương mới hoặc cả hai (hệ số tự điền theo cấp bậc, "
                           "sửa lại được).", "Muted", wrap=True))
        f.addRow("Lý do (ngoài quy định)", self.e_lydo)
        f.addRow("", self.lbl_lydo)
        f.addRow("Nội dung", self.t_nd)
        f.addRow("Ghi chú", self.e_note)
        f.addRow("File đính kèm", self.file)
        f.addRow("", self.sync)
        self.body.addStretch(1)
        self._check_rule()
        self.add_buttons("💾  Lưu thay đổi" if row else "➕  Thêm", self.save)

    def _check_rule(self, *_):
        why = ngoai_quy_dinh(self.c_loai.currentText(), self.c_cap.currentText(),
                             self.c_heso.text().replace(",", "."))
        self.lbl_lydo.setText(f"⚠ Ngoài quy định: {why} - vui lòng ghi lý do." if why else "")
        self.lbl_lydo.setVisible(bool(why))

    def _on_rank(self, text):
        coef = cand_data.HE_SO_LUONG_THEO_CAP_BAC.get(text)
        if coef:
            self.c_heso.setText(coef)

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            warn(self, "Vui lòng chọn một cán bộ.", "Thiếu thông tin")
            return
        cap, heso = self.c_cap.currentText().strip(), self.c_heso.text().replace(",", ".")
        if not cap and not heso:
            warn(self, "Vui lòng nhập Cấp bậc mới hoặc Hệ số lương mới.", "Thiếu thông tin")
            return
        if heso:
            try:
                float(heso)
            except ValueError:
                warn(self, "Hệ số lương phải là số, vd 4.60.", "Sai định dạng")
                return
        ngay = self.d_ngay.text()
        if ngay and not valid_date(ngay):
            warn(self, "Ngày quyết định phải theo dạng dd/mm/yyyy.", "Sai định dạng")
            return
        why = ngoai_quy_dinh(self.c_loai.currentText(), cap, heso)
        lydo = self.e_lydo.text().strip()
        if why and not lydo:
            warn(self, f"Quyết định này ngoài quy định ({why}).\nVui lòng ghi rõ lý do.", "Cần ghi lý do")
            return
        data = dict(can_bo_id=emp_id, loai=self.c_loai.currentText(), ngay_quyet_dinh=ngay,
                    ly_do_ngoai_le=lydo or None,
                    so_quyet_dinh=self.e_so.text().strip(), nguoi_ky=self.e_ky.text().strip(),
                    cap_bac_moi=cap or None, he_so_luong_moi=heso or None,
                    noi_dung=self.t_nd.toPlainText().strip(), ghi_chu=self.e_note.text().strip())
        app = self.panel.app
        user = app.user["username"]
        if self.file.pending:
            data["file_dinh_kem"] = attachments.save_attachment(app.app_dir, TABLE, self.file.pending)
            if self.row and self.row["file_dinh_kem"]:
                attachments.delete_attachment(app.app_dir, self.row["file_dinh_kem"])
        change = " / ".join(x for x in (cap, f"hệ số {heso}" if heso else "") if x)
        label_ = self.db.employee_label(emp_id)
        if self.row is None:
            data["created_by"] = user
            self.db.insert(TABLE, data)
            self.db.log(user, "Thêm quyết định nâng lương - thăng cấp", f"{label_}: {change}")
        else:
            self.db.update(TABLE, self.row["id"], data)
            self.db.log(user, "Sửa quyết định nâng lương - thăng cấp", f"{label_}: {change}")
        if self.sync.isChecked():
            upd = {}
            if cap:
                upd["cap_bac"] = cap
            if heso:
                upd["he_so_luong"] = heso
            self.db.update("can_bo", emp_id, upd)
            self.db.log(user, "Đồng bộ cấp bậc / hệ số lương cán bộ", f"{label_} -> {change}")
        app.set_status("Đã lưu quyết định.")
        self.accept()
