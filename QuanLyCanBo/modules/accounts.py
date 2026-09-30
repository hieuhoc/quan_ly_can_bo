# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): tạo tài khoản, phân quyền theo từng module nghiệp vụ."""
import datetime
import re
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QInputDialog, QLineEdit, QWidget

from core import registry
from core.db import parse_perms
from core.security import check_password_policy
from ui.theme import C
from ui.widgets import FormDialog, ListPage, button, choice, info, label, ask, warn

MODULE_ID = "accounts"
ROLES = {"admin": "Quản trị viên", "user": "Người dùng"}
ROLE_FROM_LABEL = {v: k for k, v in ROLES.items()}
PRESETS = {
    "Không có quyền nào": [],
    "Chỉ xem": ["view"],
    "Xem, Thêm, Sửa": ["view", "add", "edit"],
    "Toàn quyền dữ liệu": ["view", "add", "edit", "delete", "export"],
}
COLS = [("username", "Tài khoản", 110), ("ho_ten", "Họ và tên", 160), ("role_text", "Vai trò", 110),
        ("perms_text", "Quyền", 280), ("status", "Trạng thái", 100), ("last_login", "Đăng nhập cuối", 140)]


def perms_summary(role, perms_text):
    if role == "admin":
        return "Toàn quyền (Quản trị viên)"
    perms = parse_perms(perms_text)
    parts = []
    for mod_id, title, _icon, *_ in registry.BUSINESS_MODULES:
        acts = perms.get(mod_id, set())
        if acts:
            parts.append(f"{title}: {', '.join(lbl for key, lbl in registry.ACTIONS if key in acts)}")
    return "; ".join(parts) if parts else "Chưa được cấp quyền"


class Panel(ListPage):
    MODULE_ID = MODULE_ID

    def __init__(self, app):
        super().__init__(app, "Quản trị tài khoản", COLS, subtitle="Tạo tài khoản và phân quyền theo từng module",
                         searchable=False)
        self.add_action("➕  Tạo tài khoản", self.open_add, "primary")
        self.add_action("✏  Sửa / Phân quyền", self.open_edit, needs_selection=True)
        self.add_action("🔑  Đặt lại mật khẩu", self.reset_pw, needs_selection=True)
        self.add_action("🗑  Xóa tài khoản", self.delete, "danger", needs_selection=True)
        self.table.activated_row.connect(self.open_edit)
        self.table.set_row_color(lambda r: C["disabled_fg"] if not r["active"] else None)
        self.refresh()

    def refresh(self):
        now = datetime.datetime.now()
        rows = []
        for u in self.db.list_users():
            locked = u["locked_until"] and datetime.datetime.strptime(u["locked_until"], "%Y-%m-%d %H:%M:%S") > now
            u["status"] = "Vô hiệu" if not u["active"] else ("Tạm khóa" if locked else "Hoạt động")
            u["role_text"] = ROLES.get(u["role"], u["role"])
            u["perms_text"] = perms_summary(u["role"], u["perms"])
            u["last_login"] = u["last_login"] or "—"
            rows.append(u)
        self.table.set_rows(rows)
        self.count_lbl.setText(f"{len(rows)} tài khoản")
        self.update_actions()

    def open_add(self):
        if AccountDialog(self, None).exec():
            self.refresh()

    def open_edit(self):
        row = self.need_selection("một tài khoản")
        if row and AccountDialog(self, self.db.get_user(row["id"])).exec():
            self.refresh()

    def reset_pw(self):
        row = self.need_selection("một tài khoản")
        if not row:
            return
        pw, ok = QInputDialog.getText(self, "Đặt lại mật khẩu",
                                      f"Mật khẩu tạm thời cho '{row['username']}'\n"
                                      "(≥ 8 ký tự, gồm chữ và số; người dùng sẽ phải đổi khi đăng nhập):",
                                      QLineEdit.Password)
        if not ok:
            return
        problem = check_password_policy(pw)
        if problem:
            warn(self, problem, "Mật khẩu")
            return
        self.db.set_password(row["id"], pw, must_change=True)
        self.db.log(self.app.user["username"], "Đặt lại mật khẩu", row["username"])
        self.refresh()
        info(self, "Đã đặt mật khẩu tạm thời và mở khóa tài khoản (nếu đang bị khóa).", "Đã đặt lại")

    def delete(self):
        row = self.need_selection("một tài khoản")
        if not row:
            return
        if row["id"] == self.app.user["id"]:
            warn(self, "Bạn không thể xóa tài khoản đang đăng nhập.", "Không thể thực hiện")
            return
        if not ask(self, f"Xóa tài khoản '{row['username']}'?\nThao tác không thể hoàn tác.", yes="Xóa", danger=True):
            return
        try:
            self.db.delete_user(row["id"])
        except ValueError as e:
            warn(self, str(e), "Không thể thực hiện")
            return
        self.db.log(self.app.user["username"], "Xóa tài khoản", row["username"])
        self.refresh()


class AccountDialog(FormDialog):
    def __init__(self, panel, user):
        is_edit = user is not None
        super().__init__(panel, f"Sửa & phân quyền: {user['username']}" if is_edit else "Tạo tài khoản mới", 640, 640)
        self.panel, self.db, self.user_row = panel, panel.db, user
        f = self.form()
        self.e_user = QLineEdit(user["username"] if is_edit else "")
        self.e_user.setReadOnly(is_edit)
        self.e_name = QLineEdit((user["ho_ten"] or "") if is_edit else "")
        self.e_pw = QLineEdit()
        self.e_pw.setEchoMode(QLineEdit.Password)
        self.e_pw.setEnabled(not is_edit)
        self.c_role = choice(list(ROLES.values()), ROLES.get(user["role"]) if is_edit else ROLES["user"])
        self.c_role.currentTextChanged.connect(self._role_changed)
        self.active = QCheckBox("Tài khoản đang hoạt động")
        self.active.setChecked(bool(user["active"]) if is_edit else True)
        f.addRow("Tên đăng nhập" + ("" if is_edit else " *"), self.e_user)
        f.addRow("Họ và tên", self.e_name)
        f.addRow("Mật khẩu ban đầu *" if not is_edit else "Mật khẩu", self.e_pw)
        f.addRow("Vai trò", self.c_role)
        f.addRow("", self.active)

        from ui.widgets import section
        self.body.addWidget(section("Phân quyền theo module"))
        pr = QHBoxLayout()
        pr.addWidget(label("Áp dụng nhanh:"))
        self.c_preset = choice(list(PRESETS))
        pr.addWidget(self.c_preset, 1)
        pr.addWidget(button("Áp dụng", self._apply_preset))
        self.body.addLayout(pr)
        gw = QWidget()
        g = QGridLayout(gw)
        g.setHorizontalSpacing(18)
        g.addWidget(label("Module", "SectionTitle"), 0, 0)
        for j, (_a, lbl) in enumerate(registry.ACTIONS):
            g.addWidget(label(lbl, "SectionTitle"), 0, j + 1, Qt.AlignHCenter)
        have = parse_perms(user["perms"]) if is_edit else {"employees": {"view"}}
        self.checks = {}
        for i, (mid, mtitle, icon, *_x) in enumerate(registry.BUSINESS_MODULES, start=1):
            g.addWidget(label(f"{icon}  {mtitle}"), i, 0)
            for j, (a, _l) in enumerate(registry.ACTIONS):
                cb = QCheckBox()
                cb.setChecked(a in have.get(mid, set()))
                g.addWidget(cb, i, j + 1, Qt.AlignHCenter)
                self.checks[(mid, a)] = cb
        self.body.addWidget(gw)
        self.body.addStretch(1)
        self._role_changed()
        self.add_buttons("💾  Lưu thay đổi" if is_edit else "➕  Tạo tài khoản", self.save)

    def _role_changed(self, *_):
        is_admin = ROLE_FROM_LABEL.get(self.c_role.currentText()) == "admin"
        for cb in self.checks.values():
            cb.setEnabled(not is_admin)

    def _apply_preset(self):
        acts = PRESETS[self.c_preset.currentText()]
        for (_mid, a), cb in self.checks.items():
            cb.setChecked(a in acts)

    def save(self):
        role = ROLE_FROM_LABEL.get(self.c_role.currentText(), "user")
        active = self.active.isChecked()
        perms = {}
        if role != "admin":
            for (mid, a), cb in self.checks.items():
                if cb.isChecked():
                    perms.setdefault(mid, set()).add(a)
        me = self.panel.app.user
        if self.user_row is None:
            username = self.e_user.text().strip()
            if not re.fullmatch(r"[A-Za-z0-9_.\-]{3,30}", username):
                warn(self, "Tên đăng nhập gồm 3–30 ký tự: chữ không dấu, số, dấu . _ -", "Tên đăng nhập")
                return
            problem = check_password_policy(self.e_pw.text())
            if problem:
                warn(self, problem, "Mật khẩu")
                return
            try:
                self.db.add_user(username, self.e_name.text().strip(), self.e_pw.text(), role, perms, must_change=True)
            except sqlite3.IntegrityError:
                warn(self, f"Tên đăng nhập '{username}' đã tồn tại.", "Trùng tên")
                return
            self.db.log(me["username"], "Tạo tài khoản", f"{username} ({ROLES[role]})")
            info(self, f"Đã tạo tài khoản '{username}'.\nNgười dùng sẽ phải đổi mật khẩu ở lần đăng nhập đầu tiên.",
                 "Đã tạo")
        else:
            if self.user_row["id"] == me["id"] and (role != "admin" or not active):
                warn(self, "Bạn không thể tự hạ quyền hoặc tự vô hiệu hóa tài khoản đang đăng nhập.",
                     "Không thể thực hiện")
                return
            try:
                self.db.update_user(self.user_row["id"], self.e_name.text().strip(), role, perms, active)
            except ValueError as e:
                warn(self, str(e), "Không thể thực hiện")
                return
            self.db.log(me["username"], "Cập nhật tài khoản", f"{self.user_row['username']}: {ROLES[role]}")
        self.accept()
