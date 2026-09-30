# -*- coding: utf-8 -*-
"""Khung chính: thanh bên (sidebar) liệt kê module theo quyền, vùng nội dung bên phải."""
import importlib
import tkinter as tk
from tkinter import ttk

from core import registry
from core.app import APP_TITLE, VERSION, ChangePasswordDialog, ROLES
from core.theme import C, FONT, draw_shield
from core.widgets import RoundedButton


def _initials(name):
    """'Nguyễn Văn An' -> 'NA' (chữ cái đầu của họ và tên) để vẽ ảnh đại diện."""
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


class Shell(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.current_id = None
        self.current_panel = None
        self.nav_buttons = {}

        self._build_header()
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self.content = ttk.Frame(body, padding=(20, 18))
        self.content.pack(side="left", fill="both", expand=True)
        self._build_status()

        self.open_module("dashboard")

    # ---- đầu trang: nền trắng, tên phần mềm bên trái, người dùng bên phải
    def _build_header(self):
        u = self.app.user
        bar = tk.Frame(self, bg=C["header"])
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=C["header"])
        inner.pack(fill="x", padx=20, pady=10)

        brand = tk.Frame(inner, bg=C["header"])
        brand.pack(side="left")
        badge = tk.Canvas(brand, width=38, height=38, bg=C["header"], highlightthickness=0)
        badge.pack(side="left", padx=(0, 12))
        draw_shield(badge, 38)
        titles = tk.Frame(brand, bg=C["header"])
        titles.pack(side="left")
        tk.Label(titles, text=APP_TITLE, bg=C["header"], fg=C["primary"],
                 font=(FONT, 14, "bold")).pack(anchor="w")
        tk.Label(titles, text="Hệ thống quản lý hồ sơ cán bộ", bg=C["header"], fg=C["muted"],
                 font=(FONT, 9)).pack(anchor="w")

        right = tk.Frame(inner, bg=C["header"])
        right.pack(side="right")
        RoundedButton(right, text="Đăng xuất", command=self.app.logout, variant="header").pack(side="right", padx=(6, 0))
        RoundedButton(right, text="Giới thiệu", command=self.show_about, variant="header").pack(side="right", padx=(6, 0))
        RoundedButton(right, text="Đổi mật khẩu", command=self.change_password, variant="header").pack(side="right", padx=(6, 0))
        tk.Frame(right, width=1, height=30, bg=C["border"]).pack(side="right", padx=16)

        who = tk.Frame(right, bg=C["header"])
        who.pack(side="right")
        name = u["ho_ten"] or u["username"]
        avatar = tk.Canvas(who, width=34, height=34, bg=C["header"], highlightthickness=0)
        avatar.pack(side="left", padx=(0, 10))
        avatar.create_oval(1, 1, 33, 33, fill=C["primary_soft"], outline="")
        avatar.create_text(17, 17, text=_initials(name), fill=C["primary"], font=(FONT, 10, "bold"))
        info = tk.Frame(who, bg=C["header"])
        info.pack(side="left")
        tk.Label(info, text=name, bg=C["header"], fg=C["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(info, text=ROLES.get(u["role"], u["role"]), bg=C["header"], fg=C["muted"],
                 font=(FONT, 9)).pack(anchor="w")
        tk.Frame(self, height=1, bg=C["border"]).pack(fill="x")

    # ---- thanh bên: luôn mở rộng, nhóm theo Tổng quan / Nghiệp vụ / Quản trị
    SIDEBAR_W = 256

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=C["sidebar"], width=self.SIDEBAR_W)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.sidebar = side
        tk.Frame(side, height=12, bg=C["sidebar"]).pack(fill="x")

        for mod_id, title, icon, *_ in registry.HOME_MODULES:
            self._add_nav(side, mod_id, icon, title)

        disabled = self.db.disabled_modules()
        biz = [m for m in registry.BUSINESS_MODULES if m[0] not in disabled and self.app.can(m[0], "view")]
        if biz:
            self._nav_group(side, "NGHIỆP VỤ")
            for mod_id, title, icon, *_ in biz:
                self._add_nav(side, mod_id, icon, title)

        if self.app.user["role"] == "admin":
            self._nav_group(side, "QUẢN TRỊ HỆ THỐNG")
            for mod_id, title, icon, *_ in registry.ADMIN_MODULES:
                self._add_nav(side, mod_id, icon, title)

        if not biz and self.app.user["role"] != "admin":
            tk.Label(side, text="Tài khoản của bạn chưa được cấp quyền truy cập module nào. "
                                "Vui lòng liên hệ quản trị viên.",
                     bg=C["sidebar"], fg=C["sidebar_text"], font=(FONT, 9), justify="left",
                     wraplength=self.SIDEBAR_W - 40).pack(anchor="w", padx=18, pady=18)

        tk.Frame(side, bg=C["sidebar"]).pack(fill="both", expand=True)
        tk.Frame(side, height=1, bg=C["sidebar_line"]).pack(fill="x", padx=18)
        tk.Label(side, text=f"Phiên bản {VERSION}  •  Ngoại tuyến", bg=C["sidebar"], fg=C["sidebar_muted"],
                 font=(FONT, 8)).pack(anchor="w", padx=18, pady=12)

    def _nav_group(self, parent, text):
        tk.Label(parent, text=text, bg=C["sidebar"], fg=C["sidebar_muted"],
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=20, pady=(18, 6))

    def _add_nav(self, parent, mod_id, icon, title):
        btn = ttk.Button(parent, text=f"{icon}   {title}", style="Nav.TButton",
                         command=lambda: self.open_module(mod_id))
        btn.pack(fill="x", padx=8, pady=1)
        self.nav_buttons[mod_id] = btn

    def _build_status(self):
        bar = tk.Frame(self, bg=C["status"])
        bar.pack(side="bottom", fill="x")
        tk.Frame(bar, height=1, bg=C["border"]).pack(fill="x", side="top")
        ttk.Label(bar, textvariable=self.app.status, style="Status.TLabel").pack(side="left")
        u = self.app.user
        from core.db import parse_perms
        if u["role"] == "admin":
            txt = "Quyền: Quản trị viên - toàn quyền"
        else:
            perms = parse_perms(u["perms"])
            parts = []
            for mod_id, title, _icon, *_ in registry.BUSINESS_MODULES:
                acts = perms.get(mod_id, set())
                if acts:
                    labels = [lbl for key, lbl in registry.ACTIONS if key in acts]
                    parts.append(f"{title}: {', '.join(labels)}")
            txt = "Quyền: " + ("; ".join(parts) if parts else "chưa được cấp quyền")
        ttk.Label(bar, text=txt, style="Status.TLabel").pack(side="right")

    # ---- mở module
    def open_module(self, mod_id):
        for mid, btn in self.nav_buttons.items():
            btn.configure(style="NavActive.TButton" if mid == mod_id else "Nav.TButton")
        for w in self.content.winfo_children():
            w.destroy()
        info = registry.module_by_id(mod_id)
        if not info:
            return
        _id, _title, _icon, pymod, cls_name = info
        try:
            mod = importlib.import_module(pymod)
            importlib.reload(mod)
            panel_cls = getattr(mod, cls_name)
            panel = panel_cls(self.content, self.app)
            panel.pack(fill="both", expand=True)
            self.current_id = mod_id
            self.current_panel = panel
        except Exception as e:  # noqa
            tk.Label(self.content, text=f"Không thể tải module '{mod_id}':\n{e}",
                     fg=C["red"], bg=C["bg"], justify="left").pack(anchor="w", pady=20)

    def change_password(self):
        ChangePasswordDialog(self.app, self.db, self.app.user, forced=False)

    def show_about(self):
        win = tk.Toplevel(self)
        win.title("Giới thiệu")
        win.configure(bg=C["card"])
        win.resizable(False, False)
        from core.theme import center
        frm = ttk.Frame(win, style="Card.TFrame", padding=26)
        frm.pack()
        logo = tk.Canvas(frm, width=56, height=56, bg=C["card"], highlightthickness=0)
        logo.pack()
        draw_shield(logo, 56)
        ttk.Label(frm, text="PHẦN MỀM QUẢN LÝ CÁN BỘ", style="CardTitle.TLabel",
                 font=(FONT, 13, "bold")).pack(pady=(4, 0))
        ttk.Label(frm, text=f"Phiên bản {VERSION}  •  Kiến trúc module", style="CardMuted.TLabel").pack(pady=(2, 10))
        tk.Frame(frm, height=1, width=260, bg=C["border"]).pack(pady=(0, 10))
        ttk.Label(frm, style="Card.TLabel", justify="left", wraplength=340,
                 text="Quản lý thông tin cán bộ, phân loại cán bộ, nâng lương - thăng cấp bậc hàm, "
                      "đơn thư - khiếu nại. Hoạt động hoàn toàn ngoại tuyến, dữ liệu lưu trữ cục bộ "
                      "bằng SQLite, tự động sao lưu định kỳ."
                 ).pack()
        ttk.Label(frm, style="CardMuted.TLabel", justify="left", wraplength=340,
                 text="Thiết kế theo dạng module: có thể bật/tắt hoặc bổ sung module nghiệp vụ mới "
                      "mà không ảnh hưởng tới dữ liệu hay module khác."
                 ).pack(pady=(8, 0))
        RoundedButton(frm, text="Đóng", command=win.destroy, variant="primary").pack(pady=(16, 0), fill="x")
        center(win)
        try:
            win.wait_visibility()
            win.grab_set()
        except tk.TclError:
            pass
