# -*- coding: utf-8 -*-
"""Khung chính: thanh bên (sidebar) liệt kê module theo quyền, vùng nội dung bên phải."""
import importlib
import tkinter as tk
from tkinter import ttk

from core import registry
from core.app import ChangePasswordDialog, ROLES
from core.theme import C, FONT
from core.widgets import RoundedButton


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
        self.content = ttk.Frame(body, padding=14)
        self.content.pack(side="left", fill="both", expand=True)
        self._build_status()

        self.open_module("dashboard")

    # ---- đầu trang
    def _build_header(self):
        u = self.app.user
        h = ttk.Frame(self, style="Header.TFrame", padding=(18, 12))
        h.pack(fill="x")
        h.configure(style="TFrame")
        bar = tk.Frame(h, bg=C["primary"])
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=C["primary"])
        inner.pack(fill="x", padx=18, pady=12)
        tk.Label(inner, text="🛡  " + "QUẢN LÝ CÁN BỘ", bg=C["primary"], fg=C["gold"],
                 font=(FONT, 16, "bold")).pack(side="left")
        right = tk.Frame(inner, bg=C["primary"])
        right.pack(side="right")
        tk.Label(right, text=f"👤  {u['ho_ten'] or u['username']}   •   {ROLES.get(u['role'], u['role'])}",
                 bg=C["primary"], fg="white", font=(FONT, 10)).pack(side="left", padx=(0, 16))
        RoundedButton(right, text="🔑  Đổi mật khẩu", command=self.change_password, variant="header").pack(side="left", padx=3)
        RoundedButton(right, text="ℹ  Giới thiệu", command=self.show_about, variant="header").pack(side="left", padx=3)
        RoundedButton(right, text="⏻  Đăng xuất", command=self.app.logout, variant="header").pack(side="left", padx=3)
        tk.Frame(self, height=3, bg=C["gold"]).pack(fill="x")

    # ---- thanh bên (thu gọn mặc định, tự mở rộng khi trỏ chuột vào)
    SIDEBAR_COLLAPSED_W = 64
    SIDEBAR_EXPANDED_W = 250

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=C["sidebar"], width=self.SIDEBAR_COLLAPSED_W)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.sidebar = side
        self._sidebar_w = self.SIDEBAR_COLLAPSED_W
        self._sidebar_expanded = False
        self._sidebar_anim_after = None
        self._sidebar_leave_after = None
        self._nav_meta = []     # (button, icon, title) - đổi chữ khi mở rộng
        self._hide_when_collapsed = {}  # label -> chữ gốc; rỗng chữ khi thu gọn (KHÔNG pack_forget,
                                        # để không bị Tkinter đẩy lệch vị trí khi pack() lại)

        for mod_id, title, icon, *_ in registry.HOME_MODULES:
            self._add_nav(side, mod_id, icon, title)
        tk.Frame(side, height=1, bg="#453A63").pack(fill="x", padx=18, pady=(10, 0))

        lbl = tk.Label(side, text="MODULE", bg=C["sidebar"], fg="#8F86A8", font=(FONT, 9, "bold"))
        lbl.pack(anchor="w", padx=18, pady=(18, 4))
        self._hide_when_collapsed[lbl] = "MODULE"

        disabled = self.db.disabled_modules()
        biz = [m for m in registry.BUSINESS_MODULES if m[0] not in disabled and self.app.can(m[0], "view")]
        for mod_id, title, icon, *_ in biz:
            self._add_nav(side, mod_id, icon, title)

        if self.app.user["role"] == "admin":
            lbl2 = tk.Label(side, text="QUẢN TRỊ HỆ THỐNG", bg=C["sidebar"], fg="#8F86A8", font=(FONT, 9, "bold"))
            lbl2.pack(anchor="w", padx=18, pady=(18, 4))
            self._hide_when_collapsed[lbl2] = "QUẢN TRỊ HỆ THỐNG"
            for mod_id, title, icon, *_ in registry.ADMIN_MODULES:
                self._add_nav(side, mod_id, icon, title)

        if not biz and self.app.user["role"] != "admin":
            lbl3 = tk.Label(side, text="Tài khoản của bạn chưa được\ncấp quyền truy cập module nào.\n"
                                       "Vui lòng liên hệ quản trị viên.",
                            bg=C["sidebar"], fg="#C9C2DE", font=(FONT, 9), justify="left", wraplength=210)
            lbl3.pack(anchor="w", padx=18, pady=18)
            self._hide_when_collapsed[lbl3] = lbl3.cget("text")

        spacer = tk.Frame(side, bg=C["sidebar"])
        spacer.pack(fill="both", expand=True)
        lbl4 = tk.Label(side, text="Phiên bản 3.1", bg=C["sidebar"], fg="#6E6486", font=(FONT, 8))
        lbl4.pack(anchor="w", padx=18, pady=(0, 14))
        self._hide_when_collapsed[lbl4] = "Phiên bản 3.1"

        for w in self._hide_when_collapsed:
            w.configure(text="")  # bắt đầu ở trạng thái thu gọn: rỗng chữ (giữ nguyên vị trí đóng gói)

        self._bind_hover_recursive(side)

    def _add_nav(self, parent, mod_id, icon, title):
        btn = ttk.Button(parent, text=icon, style="Nav.TButton",
                         command=lambda: self.open_module(mod_id))
        btn.pack(fill="x")
        self.nav_buttons[mod_id] = btn
        self._nav_meta.append((btn, icon, title))

    def _bind_hover_recursive(self, widget):
        widget.bind("<Enter>", self._on_sidebar_enter, add="+")
        widget.bind("<Leave>", self._on_sidebar_leave, add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)

    def _on_sidebar_enter(self, _e=None):
        if self._sidebar_leave_after:
            self.sidebar.after_cancel(self._sidebar_leave_after)
            self._sidebar_leave_after = None
        if not self._sidebar_expanded:
            self._sidebar_expanded = True
            for btn, icon, title in self._nav_meta:
                btn.configure(text=f"{icon}  {title}")
            self._reflow_labels(show=True)
            self._animate_sidebar(self.SIDEBAR_EXPANDED_W)

    def _on_sidebar_leave(self, _e=None):
        # Con tro co the dang di chuyen giua cac widget con ben trong sidebar
        # (Leave/Enter rieng cho tung widget) - doi 80ms roi kiem tra CON TRO
        # co thuc su con nam trong vung sidebar hay khong truoc khi thu gon,
        # tranh nhap nhay khi di chuyen qua lai giua cac nut.
        if self._sidebar_leave_after:
            self.sidebar.after_cancel(self._sidebar_leave_after)
        self._sidebar_leave_after = self.sidebar.after(80, self._check_really_left)

    def _check_really_left(self):
        self._sidebar_leave_after = None
        try:
            x, y = self.sidebar.winfo_pointerxy()
            under = self.sidebar.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            under = None
        w, still_inside = under, False
        while w is not None:
            if w == self.sidebar:
                still_inside = True
                break
            w = w.master
        if still_inside:
            return
        self._sidebar_expanded = False
        for btn, icon, _title in self._nav_meta:
            btn.configure(text=icon)
        self._reflow_labels(show=False)
        self._animate_sidebar(self.SIDEBAR_COLLAPSED_W)

    def _reflow_labels(self, show):
        for w, orig_text in self._hide_when_collapsed.items():
            w.configure(text=orig_text if show else "")

    def _animate_sidebar(self, target_w, steps=8, delay=12):
        if self._sidebar_anim_after:
            self.sidebar.after_cancel(self._sidebar_anim_after)
            self._sidebar_anim_after = None
        start_w = self._sidebar_w

        def step(i):
            w = target_w if i >= steps else int(start_w + (target_w - start_w) * (i / steps))
            self._sidebar_w = w
            try:
                self.sidebar.configure(width=w)
            except tk.TclError:
                return
            if i < steps:
                self._sidebar_anim_after = self.sidebar.after(delay, lambda: step(i + 1))
            else:
                self._sidebar_anim_after = None
        step(1)

    def _build_status(self):
        bar = tk.Frame(self, bg=C["status"])
        bar.pack(side="bottom", fill="x")
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
        tk.Label(frm, text="🛡", font=("Segoe UI Emoji", 36), bg=C["card"], fg=C["primary"]).pack()
        ttk.Label(frm, text="PHẦN MỀM QUẢN LÝ CÁN BỘ", style="CardTitle.TLabel",
                 font=(FONT, 13, "bold")).pack(pady=(4, 0))
        ttk.Label(frm, text="Phiên bản 3.1  •  Kiến trúc module", style="CardMuted.TLabel").pack(pady=(2, 10))
        tk.Frame(frm, height=2, width=50, bg=C["gold"]).pack(pady=(0, 10))
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
