# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): sao lưu và khôi phục dữ liệu.

- Phần mềm tự sao lưu khi mở, mỗi 30 phút và khi thoát (giữ 20 bản gần nhất
  trong thư mục backup/ cạnh file chạy).
- Tại đây: sao lưu ngay, sao lưu ra thư mục khác (USB, ổ mạng), khôi phục từ
  một bản sao lưu. Trước khi khôi phục, phần mềm tự sao lưu dữ liệu hiện tại
  để có thể quay lại nếu chọn nhầm.
"""
import datetime
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from core.db import Database
from ui.widgets import ListPage, ask, info, open_file_dialog, warn

MODULE_ID = "backup"
COLS = [("thoi_gian", "Thời điểm sao lưu", 170), ("ten", "Tên file", 240), ("kich_thuoc", "Dung lượng", 110),
        ("noi_dung", "Nội dung", 160)]


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Sao lưu - Khôi phục dữ liệu", COLS, searchable=False,
                         subtitle="Tự động sao lưu khi mở phần mềm, mỗi 30 phút và khi thoát; giữ 20 bản gần nhất")
        self.add_action("💾  Sao lưu ngay", self.backup_now, "primary")
        self.add_action("📤  Sao lưu ra thư mục khác (USB...)", self.backup_to)
        self.add_action("♻  Khôi phục bản đã chọn", self.restore_selected, "danger", needs_selection=True)
        self.add_action("📂  Khôi phục từ file khác...", self.restore_file, right=True)
        self.add_action("🗁  Mở thư mục sao lưu", self.open_folder, right=True)
        self.table.activated_row.connect(self.restore_selected)
        self.refresh()

    def deny(self, action):
        return False    # chỉ quản trị viên mới thấy module này

    def refresh(self):
        folder = self.app.backup_dir
        rows = []
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder), reverse=True):
                if not name.endswith(".db"):
                    continue
                path = os.path.join(folder, name)
                ok, desc = Database.check_backup_file(path)
                ts = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                rows.append(dict(id=path, path=path, ten=name, thoi_gian=ts.strftime("%d/%m/%Y %H:%M:%S"),
                                 kich_thuoc=f"{os.path.getsize(path) / 1024:.0f} KB",
                                 noi_dung=desc if ok else f"⚠ {desc}"))
        self.table.set_rows(rows)
        self.count_lbl.setText(f"{len(rows)} bản sao lưu  •  {folder}")
        self.update_actions()

    def backup_now(self):
        self.app.auto_backup(silent=False)
        self.refresh()

    def backup_to(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục (vd ổ USB) để lưu bản sao lưu")
        if not folder:
            return
        try:
            path = self.db.backup(folder, keep=10_000)
        except Exception as e:  # noqa
            warn(self, f"Không sao lưu được vào thư mục đã chọn:\n{e}", "Lỗi sao lưu")
            return
        self.db.log(self.app.user["username"], "Sao lưu ra thư mục khác", path)
        info(self, f"Đã sao lưu vào:\n{path}", "Sao lưu")

    def open_folder(self):
        os.makedirs(self.app.backup_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.app.backup_dir))

    def restore_selected(self):
        row = self.need_selection("một bản sao lưu")
        if row:
            self._restore(row["path"])

    def restore_file(self):
        path = open_file_dialog(self, "Chọn file sao lưu (.db)", "CSDL (*.db);;Tất cả file (*.*)")
        if path:
            self._restore(path)

    def _restore(self, path):
        ok, desc = Database.check_backup_file(path)
        if not ok:
            warn(self, desc, "Không khôi phục được")
            return
        if not ask(self, f"Khôi phục dữ liệu từ:\n{os.path.basename(path)} ({desc})\n\n"
                         "TOÀN BỘ dữ liệu hiện tại sẽ được thay bằng dữ liệu trong bản sao lưu này.\n"
                         "Phần mềm sẽ tự sao lưu dữ liệu hiện tại trước để có thể quay lại nếu cần.",
                   "Xác nhận khôi phục", yes="Khôi phục", danger=True):
            return
        try:
            safety = self.db.backup(self.app.backup_dir, prefix="truoc_khoi_phuc_")
            self.db.restore_from(path)
        except Exception as e:  # noqa
            warn(self, f"Khôi phục thất bại:\n{e}", "Lỗi khôi phục")
            return
        user = self.app.user["username"]
        self.db.log(user, "Khôi phục dữ liệu", f"Từ {os.path.basename(path)}; bản an toàn: {os.path.basename(safety)}")
        info(self, f"Đã khôi phục dữ liệu.\nDữ liệu trước khi khôi phục được lưu tại:\n{safety}\n\n"
                   "Vui lòng đăng nhập lại.", "Khôi phục xong")
        self.app.logout("Đăng xuất sau khi khôi phục dữ liệu")
