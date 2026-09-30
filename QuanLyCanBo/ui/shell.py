# -*- coding: utf-8 -*-
"""Khung làm việc: thanh tiêu đề, thanh bên (thu gọn / mở rộng bằng nút ☰,
có hiệu ứng trượt), vùng nội dung hiển thị module đang chọn."""
import importlib

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QSettings, Qt
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from core import registry
from ui.app import APP_TITLE, ROLES, VERSION, ChangePasswordDialog, Logo
from ui.theme import C
from ui.widgets import FormDialog, button, label


def _initials(name):
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


class Avatar(QLabel):
    def __init__(self, name):
        super().__init__(_initials(name))
        self.setFixedSize(36, 36)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background: {C['primary_soft']}; color: {C['primary']}; border-radius: 18px;"
                           "font-weight: 700;")


class Shell(QWidget):
    EXPANDED_W = 260
    COLLAPSED_W = 68

    def __init__(self, app):
        super().__init__()
        self.app, self.db = app, app.db
        self.nav_buttons = {}
        self.current_id = None
        self.current_panel = None
        self.settings = QSettings("QuanLyCanBo", "QuanLyCanBo")
        self.expanded = self.settings.value("sidebar_expanded", True, type=bool)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        content_wrap = QWidget()
        content_wrap.setObjectName("Page")
        content_wrap.setAttribute(Qt.WA_StyledBackground, True)
        self.content = QVBoxLayout(content_wrap)
        self.content.setContentsMargins(22, 18, 22, 18)
        body.addWidget(content_wrap, 1)
        root.addLayout(body, 1)
        self._apply_sidebar_state(animate=False)
        self._update_status_perms()

    # ---- đầu trang
    def _build_header(self):
        u = self.app.user
        h = QFrame()
        h.setObjectName("Header")
        h.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(12, 10, 20, 10)
        lay.setSpacing(12)
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("MenuToggle")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setToolTip("Thu gọn / mở rộng thanh bên")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        lay.addWidget(self.toggle_btn)
        lay.addWidget(Logo(36))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label(APP_TITLE, "AppTitle"))
        titles.addWidget(label("Hệ thống quản lý hồ sơ cán bộ", "Muted"))
        lay.addLayout(titles)
        lay.addStretch(1)

        name = u["ho_ten"] or u["username"]
        lay.addWidget(Avatar(name))
        who = QVBoxLayout()
        who.setSpacing(0)
        who.addWidget(label(name, "UserName"))
        who.addWidget(label(ROLES.get(u["role"], u["role"]), "Muted"))
        lay.addLayout(who)
        sep = QFrame()
        sep.setFixedSize(1, 30)
        sep.setStyleSheet(f"background: {C['border']};")
        lay.addSpacing(6)
        lay.addWidget(sep)
        lay.addSpacing(6)
        for text, slot in (("Đổi mật khẩu", self.change_password), ("Giới thiệu", self.show_about),
                           ("Đăng xuất", lambda: self.app.logout())):
            lay.addWidget(button(text, slot, "ghost"))
        return h

    # ---- thanh bên
    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setAttribute(Qt.WA_StyledBackground, True)
        side.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.sidebar = side
        v = QVBoxLayout(side)
        v.setContentsMargins(10, 12, 10, 12)
        v.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.group_labels = []

        for mod_id, title, icon, *_ in registry.HOME_MODULES:
            self._add_nav(v, mod_id, icon, title)
        disabled = self.db.disabled_modules()
        biz = [m for m in registry.BUSINESS_MODULES if m[0] not in disabled and self.app.can(m[0], "view")]
        if biz:
            self._add_group(v, "NGHIỆP VỤ")
            for mod_id, title, icon, *_ in biz:
                self._add_nav(v, mod_id, icon, title)
        if self.app.user["role"] == "admin":
            self._add_group(v, "QUẢN TRỊ HỆ THỐNG")
            for mod_id, title, icon, *_ in registry.ADMIN_MODULES:
                self._add_nav(v, mod_id, icon, title)
        if not biz and self.app.user["role"] != "admin":
            note = label("Tài khoản của bạn chưa được cấp quyền truy cập module nào. "
                         "Vui lòng liên hệ quản trị viên.", "SidebarFoot", wrap=True)
            v.addWidget(note)
            self.group_labels.append(note)
        v.addStretch(1)
        self.foot = label(f"Phiên bản {VERSION}  •  Ngoại tuyến", "SidebarFoot")
        v.addWidget(self.foot)
        return side

    def _add_group(self, v, text):
        lb = label(text, "NavGroup")
        v.addWidget(lb)
        self.group_labels.append(lb)

    def _add_nav(self, v, mod_id, icon, title):
        b = QPushButton()
        b.setObjectName("NavButton")
        b.setCheckable(True)
        b.setCursor(Qt.PointingHandCursor)
        b.setProperty("icon_text", icon)
        b.setProperty("title_text", title)
        b.clicked.connect(lambda _=False, m=mod_id: self.open_module(m))
        self.group.addButton(b)
        v.addWidget(b)
        self.nav_buttons[mod_id] = b

    def _set_labels(self, expanded):
        for b in self.nav_buttons.values():
            icon, title = b.property("icon_text"), b.property("title_text")
            b.setText(f"{icon}    {title}" if expanded else icon)
            b.setToolTip("" if expanded else title)
        for lb in self.group_labels:
            lb.setVisible(expanded)
        self.foot.setVisible(expanded)

    def _apply_sidebar_state(self, animate=True):
        target = self.EXPANDED_W if self.expanded else self.COLLAPSED_W
        if self.expanded:
            self._set_labels(True)
        if not animate:
            self.sidebar.setFixedWidth(target)
            self._set_labels(self.expanded)
            return
        start = self.sidebar.width()
        grp = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self.sidebar, prop, self)
            a.setDuration(220)
            a.setStartValue(start)
            a.setEndValue(target)
            a.setEasingCurve(QEasingCurve.OutCubic)
            grp.addAnimation(a)
        if not self.expanded:
            grp.finished.connect(lambda: self._set_labels(False))
        grp.start()
        self._anim = grp

    def toggle_sidebar(self):
        self.expanded = not self.expanded
        self.settings.setValue("sidebar_expanded", self.expanded)
        self._apply_sidebar_state(animate=True)

    # ---- thanh trạng thái
    def _update_status_perms(self):
        u = self.app.user
        from core.db import parse_perms
        if u["role"] == "admin":
            txt = "Quyền: Quản trị viên - toàn quyền"
        else:
            perms = parse_perms(u["perms"])
            parts = []
            for mod_id, title, *_ in registry.BUSINESS_MODULES:
                acts = perms.get(mod_id, set())
                if acts:
                    parts.append(f"{title}: {', '.join(lbl for key, lbl in registry.ACTIONS if key in acts)}")
            txt = "Quyền: " + ("; ".join(parts) if parts else "chưa được cấp quyền")
        self.app.status_right.setText(txt)

    # ---- mở module
    def open_module(self, mod_id):
        info_ = registry.module_by_id(mod_id)
        if not info_:
            return
        for mid, b in self.nav_buttons.items():
            b.setChecked(mid == mod_id)
        if self.current_panel is not None:
            self.content.removeWidget(self.current_panel)
            self.current_panel.hide()
            self.current_panel.setParent(None)
            self.current_panel.deleteLater()
            self.current_panel = None
        _id, _title, _icon, pymod, cls_name = info_
        try:
            mod = importlib.import_module(pymod)
            panel = getattr(mod, cls_name)(self.app)
        except Exception as e:  # noqa
            import traceback
            traceback.print_exc()
            panel = label(f"Không thể tải module '{mod_id}':\n{e}", "Error", wrap=True)
        self.content.addWidget(panel)
        self.current_panel = panel
        self.current_id = mod_id

    def change_password(self):
        ChangePasswordDialog(self.app, self.db, self.app.user, forced=False).exec()

    def show_about(self):
        d = FormDialog(self.app, "Giới thiệu", 440, 380)
        d.body.addWidget(Logo(56), 0, Qt.AlignHCenter)
        t = label("PHẦN MỀM QUẢN LÝ CÁN BỘ", "CardTitle")
        t.setAlignment(Qt.AlignHCenter)
        d.body.addWidget(t)
        s = label(f"Phiên bản {VERSION}", "Muted")
        s.setAlignment(Qt.AlignHCenter)
        d.body.addWidget(s)
        d.body.addWidget(label(
            "Quản lý thông tin cán bộ, quá trình công tác - học tập, phân loại cán bộ, nâng lương - "
            "thăng cấp bậc hàm, đơn thư - khiếu nại. Hoạt động hoàn toàn ngoại tuyến, dữ liệu lưu cục "
            "bộ bằng SQLite, tự động sao lưu định kỳ.", wrap=True))
        d.body.addStretch(1)
        ok = button("Đóng", d.accept, "primary")
        d.footer.addWidget(ok, 1)
        d.exec()
