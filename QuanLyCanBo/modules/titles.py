# -*- coding: utf-8 -*-
"""Module: Chức danh - quyết định bổ nhiệm, bổ nhiệm lại, điều động, miễn nhiệm
chức danh của cán bộ. Cùng cách làm với module Nâng lương - Thăng cấp:

- mỗi bản ghi là một quyết định (hình thức, ngày, số QĐ, người ký, chức danh,
  thời hạn giữ chức danh, file đính kèm);
- tùy chọn đồng bộ "Chức danh hiện tại" trong hồ sơ cán bộ (cần quyền Sửa hồ sơ);
- trường hợp ngoài quy định (hình thức bắt buộc ghi lý do, thời hạn khác thời
  hạn mặc định) phải ghi lý do;
- danh mục chức danh, hình thức, thời hạn mặc định chỉnh ở Tham số nghiệp vụ;
- hết thời hạn giữ chức danh được nhắc ở Cảnh báo đến hạn.
"""
from PySide6.QtWidgets import QCheckBox, QLineEdit

from core import attachments
from core import tham_so as ts
from ui.widgets import (DateField, EmployeePicker, FilePicker, FormDialog, ListPage, SearchDialog, SuggestCombo,
                        ask, choice, date_key, label, sql_date_key, text_edit, valid_date, warn)

MODULE_ID = "titles"
TABLE = "qua_trinh_chuc_danh"
COLS = [("ma_cb", "Mã CB", 80), ("ho_ten", "Cán bộ", 160), ("loai", "Hình thức", 120),
        ("chuc_danh", "Chức danh", 180), ("ngay_quyet_dinh", "Ngày QĐ", 100), ("so_quyet_dinh", "Số quyết định", 130),
        ("thoi_han_nam", "Thời hạn (năm)", 100), ("het_han", "Hết hạn", 100), ("nguoi_ky", "Người ký", 130),
        ("ly_do_ngoai_le", "Lý do (ngoài quy định)", 180), ("noi_dung", "Nội dung", 180), ("file_dinh_kem", "File", 70)]


def het_han(ngay, thoi_han):
    """Ngày hết thời hạn giữ chức danh (dd/mm/yyyy) hoặc chuỗi rỗng."""
    from core import canh_bao
    d = canh_bao.parse(ngay)
    try:
        years = float(str(thoi_han).replace(",", ".")) if thoi_han not in (None, "") else 0
    except ValueError:
        years = 0
    return canh_bao.add_years(d, years).strftime("%d/%m/%Y") if d and years > 0 else ""


def ngoai_quy_dinh(hinh_thuc, thoi_han):
    """Mô tả điểm khác quy định (cần ghi lý do), hoặc None."""
    reasons = []
    if hinh_thuc in ts.get("hinh_thuc_chuc_danh_can_ly_do"):
        reasons.append(f"hình thức {hinh_thuc}")
    mac_dinh = ts.as_int("thoi_han_chuc_danh")
    if hinh_thuc not in ts.get("hinh_thuc_chuc_danh_mien") and mac_dinh and str(thoi_han).strip():
        try:
            if abs(float(str(thoi_han).replace(",", ".")) - mac_dinh) > 1e-9:
                reasons.append(f"thời hạn {thoi_han} năm khác thời hạn mặc định {mac_dinh} năm")
        except ValueError:
            pass
    return "; ".join(reasons) or None


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Chức danh", COLS,
                         subtitle="Quyết định bổ nhiệm, bổ nhiệm lại, điều động, miễn nhiệm chức danh của cán bộ")
        self.add_action("➕  Thêm quyết định", self.open_add, "primary", perm="add")
        self.add_action("✏  Sửa", self.open_edit, perm="edit", needs_selection=True)
        self.add_action("🗑  Xóa", self.on_delete, "danger", perm="delete", needs_selection=True)
        self.add_action("📎  Mở file đính kèm", self.open_attachment, needs_selection=True,
                        check=lambda r: r and r.get("file_dinh_kem"))
        self.add_action("📊  Xuất Excel", lambda: self.export_excel(
            "Danh sách quyết định chức danh", "chuc_danh",
            columns=[(k, lbl) for k, lbl, _w in COLS if k != "file_dinh_kem"]), perm="export", right=True)
        self.add_action("🖨  In PDF", lambda: self.print_pdf(
            "Danh sách quyết định chức danh", "chuc_danh",
            columns=[(k, lbl) for k, lbl, _w in COLS if k not in ("file_dinh_kem", "noi_dung")]),
            perm="export", right=True)
        self.table.set_display("file_dinh_kem", lambda v, r: "📎 Có" if v else "—")
        from ui.theme import C
        self.table.set_row_color(lambda r: C["amber"] if r.get("ly_do_ngoai_le") else None)
        self.table.activated_row.connect(self.open_edit)
        self.table.delete_pressed.connect(self.on_delete)
        self.refresh()

    def load_rows(self):
        sql = ("SELECT q.*, c.ho_ten AS ho_ten, c.ma_cb AS ma_cb FROM qua_trinh_chuc_danh q "
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
            if f.get("chuc_danh"):
                sql += " AND q.chuc_danh LIKE ?"; params.append(f"%{f['chuc_danh']}%")
            if f.get("loai"):
                sql += " AND q.loai = ?"; params.append(f["loai"])
        elif self.search_text():
            like = f"%{self.search_text()}%"
            sql += (" AND (c.ho_ten LIKE ? OR c.ma_cb LIKE ? OR q.noi_dung LIKE ? OR q.so_quyet_dinh LIKE ?"
                    " OR q.chuc_danh LIKE ? OR q.nguoi_ky LIKE ? OR q.loai LIKE ?)")
            params.extend([like] * 7)
        sql += (" ORDER BY (q.ngay_quyet_dinh IS NULL OR q.ngay_quyet_dinh==''), "
                f"{sql_date_key('q.ngay_quyet_dinh')} DESC, q.id DESC")
        rows = []
        for r in self.db.conn.execute(sql, params).fetchall():
            d = dict(r)
            d["het_han"] = het_han(d["ngay_quyet_dinh"], d["thoi_han_nam"])
            rows.append(d)
        return rows

    def refresh(self):
        rows = self.load_rows()
        self.table.set_rows(rows)
        self.count_lbl.setText(f"Tổng số: {len(rows)} quyết định")
        self.update_actions()

    def open_advanced(self):
        SearchDialog(self, [("ho_ten", "Họ và tên cán bộ", QLineEdit()),
                            ("chuc_danh", "Chức danh", QLineEdit()),
                            ("loai", "Hình thức", choice([""] + ts.get("hinh_thuc_chuc_danh"))),
                            ("tu_ngay", "Quyết định từ ngày (dd/mm/yyyy)", QLineEdit()),
                            ("so_quyet_dinh", "Số quyết định", QLineEdit())],
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
        self.db.log(self.app.user["username"], "Xóa quyết định chức danh",
                    f"{row['ma_cb']} - {row['ho_ten']}: {row['chuc_danh']} ({row['so_quyet_dinh'] or 'id=' + str(row['id'])})")
        self.app.set_status("Đã xóa quyết định.")
        self.refresh()


class EntryDialog(FormDialog):
    """Thêm / sửa MỘT quyết định về chức danh."""

    def __init__(self, panel, row):
        super().__init__(panel, "Sửa quyết định chức danh" if row else "Thêm quyết định chức danh", 600, 720)
        self.panel, self.db, self.row = panel, panel.db, row
        r = dict(row) if row else {}
        f = self.form()
        self.picker = EmployeePicker(self.db)
        if r.get("can_bo_id"):
            self.picker.set_by_id(r["can_bo_id"])
        self.c_loai = choice(ts.get("hinh_thuc_chuc_danh"), r.get("loai"))
        self.c_cd = SuggestCombo(ts.get("chuc_danh_goi_y"), text=r.get("chuc_danh") or "")
        self.d_ngay = DateField(r.get("ngay_quyet_dinh") or "")
        self.e_so = QLineEdit(r.get("so_quyet_dinh") or "")
        self.e_ky = QLineEdit(r.get("nguoi_ky") or "")
        mac_dinh = ts.as_int("thoi_han_chuc_danh")
        self.e_han = QLineEdit(r.get("thoi_han_nam") if row else (str(mac_dinh) if mac_dinh else ""))
        self.e_han.setPlaceholderText("Số năm; để trống nếu không thời hạn")
        self.lbl_het = label("", "Muted")
        self.e_lydo = QLineEdit(r.get("ly_do_ngoai_le") or "")
        self.e_lydo.setPlaceholderText("Bắt buộc khi hình thức cần lý do hoặc thời hạn khác mặc định")
        self.lbl_lydo = label("", "Note", wrap=True)
        self.c_loai.currentTextChanged.connect(self._check_rule)
        self.e_han.textChanged.connect(self._check_rule)
        self.d_ngay.edit.textChanged.connect(self._check_rule)
        self.t_nd = text_edit(r.get("noi_dung"), 70)
        self.e_note = QLineEdit(r.get("ghi_chu") or "")
        self.file = FilePicker(attachments.display_name(r.get("file_dinh_kem")))
        self.sync = QCheckBox("Cập nhật chức danh hiện tại vào hồ sơ cán bộ")
        self.sync.setChecked(row is None)
        if not panel.app.can("employees", "edit"):
            self.sync.setChecked(False)
            self.sync.setEnabled(False)
            self.sync.setToolTip("Cần quyền Sửa ở module Thông tin cán bộ")
        for text, w in (("Cán bộ *", self.picker), ("Hình thức *", self.c_loai), ("Chức danh *", self.c_cd),
                        ("Ngày quyết định", self.d_ngay), ("Số quyết định", self.e_so), ("Người ký", self.e_ky),
                        ("Thời hạn giữ chức danh (năm)", self.e_han), ("", self.lbl_het),
                        ("Lý do (ngoài quy định)", self.e_lydo), ("", self.lbl_lydo), ("Nội dung", self.t_nd),
                        ("Ghi chú", self.e_note), ("File đính kèm", self.file), ("", self.sync)):
            f.addRow(text, w)
        self.body.addStretch(1)
        self._check_rule()
        self.add_buttons("💾  Lưu thay đổi" if row else "➕  Thêm", self.save)

    def _check_rule(self, *_):
        why = ngoai_quy_dinh(self.c_loai.currentText(), self.e_han.text())
        self.lbl_lydo.setText(f"⚠ Ngoài quy định: {why} - vui lòng ghi lý do." if why else "")
        self.lbl_lydo.setVisible(bool(why))
        hh = het_han(self.d_ngay.text(), self.e_han.text())
        self.lbl_het.setText(f"Hết thời hạn ngày {hh}" if hh else "")
        self.lbl_het.setVisible(bool(hh))

    def save(self):
        emp_id = self.picker.get()
        if not emp_id:
            warn(self, "Vui lòng chọn một cán bộ.", "Thiếu thông tin")
            return
        cd = self.c_cd.text()
        if not cd:
            warn(self, "Vui lòng nhập Chức danh.", "Thiếu thông tin")
            return
        han = self.e_han.text().strip().replace(",", ".")
        if han:
            try:
                if float(han) < 0:
                    raise ValueError
            except ValueError:
                warn(self, "Thời hạn phải là số năm, vd 5.", "Sai định dạng")
                return
        ngay = self.d_ngay.text()
        if ngay and not valid_date(ngay):
            warn(self, "Ngày quyết định phải theo dạng dd/mm/yyyy.", "Sai định dạng")
            return
        loai = self.c_loai.currentText()
        why = ngoai_quy_dinh(loai, han)
        lydo = self.e_lydo.text().strip()
        if why and not lydo:
            warn(self, f"Quyết định này ngoài quy định ({why}).\nVui lòng ghi rõ lý do.", "Cần ghi lý do")
            return
        data = dict(can_bo_id=emp_id, loai=loai, chuc_danh=cd, ngay_quyet_dinh=ngay, thoi_han_nam=han or None,
                    so_quyet_dinh=self.e_so.text().strip(), nguoi_ky=self.e_ky.text().strip(),
                    ly_do_ngoai_le=lydo or None, noi_dung=self.t_nd.toPlainText().strip(),
                    ghi_chu=self.e_note.text().strip())
        app = self.panel.app
        user = app.user["username"]
        if self.file.pending:
            data["file_dinh_kem"] = attachments.save_attachment(app.app_dir, TABLE, self.file.pending)
            if self.row and self.row["file_dinh_kem"]:
                attachments.delete_attachment(app.app_dir, self.row["file_dinh_kem"])
        label_ = self.db.employee_label(emp_id)
        if self.row is None:
            data["created_by"] = user
            self.db.insert(TABLE, data)
            self.db.log(user, "Thêm quyết định chức danh", f"{label_}: {loai} {cd}")
        else:
            self.db.update(TABLE, self.row["id"], data, touch_updated=False)
            self.db.log(user, "Sửa quyết định chức danh", f"{label_}: {loai} {cd}")
        if self.sync.isChecked():
            if loai in ts.get("hinh_thuc_chuc_danh_mien"):
                cur = self.db.fetch_one("can_bo", emp_id)["chuc_danh_hien_tai"] or ""
                if cur.strip().lower() == cd.strip().lower():
                    self.db.update("can_bo", emp_id, {"chuc_danh_hien_tai": ""})
                    self.db.log(user, "Đồng bộ chức danh cán bộ", f"{label_}: thôi giữ {cd}")
            else:
                self.db.update("can_bo", emp_id, {"chuc_danh_hien_tai": cd})
                self.db.log(user, "Đồng bộ chức danh cán bộ", f"{label_} -> {cd}")
        app.set_status("Đã lưu quyết định chức danh.")
        self.accept()
