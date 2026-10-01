# -*- coding: utf-8 -*-
"""Cửa sổ chính: đăng nhập, đổi mật khẩu, tự đăng xuất khi không thao
tác, tự sao lưu định kỳ; khung làm việc nằm ở ui/shell.py."""
import datetime
import os
import time

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from core.paths import resource
from core.security import check_password_policy
from ui.theme import draw_shield
from ui.widgets import FormDialog, button, info, label

APP_TITLE = "QUẢN LÝ CÁN BỘ"
VERSION = "4.3"
BACKUP_INTERVAL_MIN = 30
IDLE_TIMEOUT_MIN = 15
ROLES = {"admin": "Quản trị viên", "user": "Người dùng"}


class Logo(QWidget):
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.size_ = size
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        draw_shield(QPainter(self), 0, 0, self.size_)


class _ActivityFilter(QObject):
    """Ghi nhận mọi thao tác chuột / bàn phím để tính thời gian không thao tác."""

    def __init__(self, app):
        super().__init__()
        self.app = app

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.Wheel):
            self.app.last_activity = time.time()
        return False


class App(QMainWindow):
    def __init__(self, db, app_dir):
        super().__init__()
        self.db = db
        from core import tham_so
        tham_so.bind(db)
        self.app_dir = app_dir
        self.backup_dir = os.path.join(app_dir, "backup")
        self.user = None
        self.shell = None
        self.last_activity = time.time()
        self.setWindowTitle(APP_TITLE)
        ico = resource("assets", "app.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.status_left = QLabel("Sẵn sàng")
        self.status_right = QLabel("")
        self.statusBar().addWidget(self.status_left, 1)
        self.statusBar().addPermanentWidget(self.status_right)
        self.statusBar().setSizeGripEnabled(False)

        self._filter = _ActivityFilter(self)
        QApplication.instance().installEventFilter(self._filter)
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._idle_check)
        self._idle_timer.start(30_000)
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(lambda: self.auto_backup(silent=True))
        self._backup_timer.start(BACKUP_INTERVAL_MIN * 60 * 1000)

        self.show_login()
        self.auto_backup(silent=True)

    # ------------------------------------------------------------ chung
    def can(self, module_id, action="view"):
        u = self.user
        if not u:
            return False
        if u["role"] == "admin":
            return True
        from core.db import parse_perms
        return action in parse_perms(u["perms"]).get(module_id, set())

    def set_status(self, text):
        self.status_left.setText(text)

    def _set_page(self, w):
        old = self.stack.currentWidget()
        self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)
        if old is not None:
            self.stack.removeWidget(old)
            old.deleteLater()

    def _center(self, w, h):
        scr = self.screen().availableGeometry()
        w, h = min(w, scr.width()), min(h, scr.height())
        self.setGeometry(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2, w, h)

    # ------------------------------------------------------------ đăng nhập / đăng xuất
    def show_login(self):
        self.user = None
        self.shell = None
        self.statusBar().hide()
        self._set_page(LoginPage(self))
        if self.isMaximized():
            self.showNormal()
        self.setMinimumSize(480, 600)
        self._center(560, 700)

    def on_login_success(self, user, remember=False, password=None):
        final_password = password
        if user["must_change"]:
            dlg = ChangePasswordDialog(self, self.db, user, forced=True)
            if dlg.exec() != QDialog.Accepted:
                self.db.log(user["username"], "Hủy đổi mật khẩu bắt buộc")
                return
            user = self.db.get_user(user["id"])
            final_password = dlg.new_password
        import core.credentials as creds
        if remember and final_password:
            creds.save(self.app_dir, user["username"], final_password)
        else:
            creds.clear(self.app_dir)
        self.user = user
        self.last_activity = time.time()
        self._build_shell()
        self.setMinimumSize(1100, 660)
        self.statusBar().show()
        self.showMaximized()

    def _build_shell(self, open_module=None):
        from ui.shell import Shell
        self.shell = Shell(self)
        self._set_page(self.shell)
        self.shell.open_module(open_module or "dashboard")

    def reload_shell(self, open_module=None):
        """Vẽ lại khung chính - dùng sau khi quyền hoặc cấu hình module thay đổi."""
        self.user = self.db.get_user(self.user["id"])
        self._build_shell(open_module)

    def _close_dialogs(self):
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible():
                w.reject()

    def logout(self, reason="Đăng xuất"):
        if self.user:
            self.db.log(self.user["username"], reason)
        self._close_dialogs()
        self.show_login()

    def _idle_check(self):
        if self.user and time.time() - self.last_activity > IDLE_TIMEOUT_MIN * 60:
            self.logout("Tự động đăng xuất (không thao tác)")
            info(self, f"Đã tự động đăng xuất sau {IDLE_TIMEOUT_MIN} phút không thao tác.", "Hết phiên làm việc")

    # ------------------------------------------------------------ sao lưu / thoát
    def auto_backup(self, silent=False):
        try:
            p = self.db.backup(self.backup_dir)
            self.set_status(f"Đã sao lưu: {os.path.basename(p)}  ({datetime.datetime.now():%H:%M:%S})")
            if not silent:
                info(self, f"Đã sao lưu vào:\n{p}", "Sao lưu")
        except Exception as e:  # noqa
            self.set_status(f"Lỗi sao lưu: {e}")

    def closeEvent(self, ev):
        self.auto_backup(silent=True)
        if self.user:
            self.db.log(self.user["username"], "Thoát chương trình (đăng xuất)")
        self.db.close()
        ev.accept()


# ------------------------------------------------------------ màn hình đăng nhập
class LoginPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("LoginPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        cardw = QFrame()
        cardw.setObjectName("LoginCard")
        cardw.setFixedWidth(420)
        row.addWidget(cardw)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)

        v = QVBoxLayout(cardw)
        v.setContentsMargins(40, 30, 40, 30)
        v.setSpacing(8)
        v.addWidget(Logo(60), 0, Qt.AlignHCenter)
        t = label(APP_TITLE, "LoginTitle")
        t.setAlignment(Qt.AlignHCenter)
        v.addWidget(t)
        s = label("Đăng nhập để tiếp tục làm việc", "Muted")
        s.setAlignment(Qt.AlignHCenter)
        v.addWidget(s)
        v.addSpacing(10)

        v.addWidget(QLabel("Tên đăng nhập"))
        self.e_user = QLineEdit()
        v.addWidget(self.e_user)
        v.addWidget(QLabel("Mật khẩu"))
        self.e_pass = QLineEdit()
        self.e_pass.setEchoMode(QLineEdit.Password)
        v.addWidget(self.e_pass)

        opts = QHBoxLayout()
        self.show_pw = QCheckBox("Hiện mật khẩu")
        self.show_pw.toggled.connect(
            lambda on: self.e_pass.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        self.remember = QCheckBox("Ghi nhớ trên máy này")
        self.remember.setChecked(True)
        self.remember.toggled.connect(self._on_remember)
        opts.addWidget(self.show_pw)
        opts.addStretch(1)
        opts.addWidget(self.remember)
        v.addLayout(opts)

        self.err = label("", "Error", wrap=True)
        v.addWidget(self.err)
        self.btn = button("Đăng nhập", self.submit, "primary")
        self.btn.setMinimumHeight(40)
        v.addWidget(self.btn)

        import core.credentials as creds
        note = f"Phiên bản {VERSION}  •  Hoạt động ngoại tuyến"
        if not creds.available():
            note += "\n(Ghi nhớ mật khẩu chỉ hỗ trợ trên Windows)"
        n = label(note, "Muted")
        n.setAlignment(Qt.AlignHCenter)
        v.addSpacing(6)
        v.addWidget(n)

        self.e_user.returnPressed.connect(self.e_pass.setFocus)
        self.e_pass.returnPressed.connect(self.submit)
        saved = creds.load(app.app_dir)
        if saved:
            self.e_user.setText(saved[0])
            self.e_pass.setText(saved[1])
            QTimer.singleShot(0, self.e_pass.setFocus)
        else:
            QTimer.singleShot(0, self.e_user.setFocus)

    def _on_remember(self, on):
        if not on:
            import core.credentials as creds
            creds.clear(self.app.app_dir)

    def submit(self):
        username, pw = self.e_user.text().strip(), self.e_pass.text()
        if not username or not pw:
            self.err.setText("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            return
        user, err = self.app.db.authenticate(username, pw)
        if err:
            self.err.setText(err)
            self.e_pass.clear()
            self.e_pass.setFocus()
            return
        self.app.on_login_success(user, remember=self.remember.isChecked(), password=pw)


# ------------------------------------------------------------ đổi mật khẩu
class ChangePasswordDialog(FormDialog):
    def __init__(self, parent, db, user, forced=False):
        super().__init__(parent, "Đổi mật khẩu", 460, 440 if forced else 400)
        self.db, self.user, self.new_password = db, user, None
        if forced:
            self.body.addWidget(label("Bạn đăng nhập lần đầu hoặc mật khẩu vừa được đặt lại. "
                                      "Hãy đặt mật khẩu mới để tiếp tục sử dụng.", "Muted", wrap=True))
        f = self.form()
        self.edits = []
        for text in ("Mật khẩu hiện tại", "Mật khẩu mới", "Nhập lại mật khẩu mới"):
            e = QLineEdit()
            e.setEchoMode(QLineEdit.Password)
            e.returnPressed.connect(self.submit)
            f.addRow(text, e)
            self.edits.append(e)
        show = QCheckBox("Hiện mật khẩu")
        show.toggled.connect(lambda on: [e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for e in self.edits])
        f.addRow("", show)
        self.body.addWidget(label("Tối thiểu 8 ký tự, gồm cả chữ và số.", "Muted"))
        self.err = label("", "Error", wrap=True)
        self.body.addWidget(self.err)
        self.body.addStretch(1)
        self.add_buttons("Lưu mật khẩu", self.submit)

    def submit(self):
        old, new, cf = (e.text() for e in self.edits)
        if not self.db.check_user_password(self.user["id"], old):
            self.err.setText("Mật khẩu hiện tại không đúng.")
            return
        problem = check_password_policy(new)
        if problem:
            self.err.setText(problem)
            return
        if new == old:
            self.err.setText("Mật khẩu mới phải khác mật khẩu hiện tại.")
            return
        if new != cf:
            self.err.setText("Hai lần nhập mật khẩu mới không khớp.")
            return
        self.db.set_password(self.user["id"], new, must_change=False)
        self.db.log(self.user["username"], "Đổi mật khẩu")
        self.new_password = new
        try:
            import core.credentials as creds
            app_dir = self.parent().app_dir
            saved = creds.load(app_dir)
            if saved and saved[0] == self.user["username"]:
                creds.save(app_dir, self.user["username"], new)
        except Exception:  # noqa
            pass
        info(self, "Đã đổi mật khẩu.", "Thành công")
        self.accept()
