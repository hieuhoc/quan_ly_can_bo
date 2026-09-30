# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): tạo tài khoản, phân quyền theo từng module nghiệp vụ."""
import datetime
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from core import registry
from core.db import parse_perms
from core.security import check_password_policy
from core.theme import C, center, make_card
from core.widgets import DialogShell, RoundedButton, make_tree

MODULE_ID = "accounts"
ROLES = {"admin": "Quản trị viên", "user": "Người dùng"}
ROLE_FROM_LABEL = {v: k for k, v in ROLES.items()}
GLOBAL_PRESETS = {
    "Tùy chỉnh (giữ nguyên)": None,
    "Không có quyền nào": [],
    "Chỉ xem": ["view"],
    "Xem, Thêm, Sửa": ["view", "add", "edit"],
    "Toàn quyền dữ liệu": ["view", "add", "edit", "delete", "export"],
}
COLS = [("username", "Tài khoản", 110), ("ho_ten", "Họ và tên", 160), ("role", "Vai trò", 100),
        ("perms_text", "Quyền", 260), ("status", "Trạng thái", 90), ("last_login", "Đăng nhập cuối", 130)]


def perms_summary(role, perms_text):
    if role == "admin":
        return "Toàn quyền (Quản trị viên)"
    perms = parse_perms(perms_text)
    parts = []
    for mod_id, title, _icon, *_ in registry.BUSINESS_MODULES:
        acts = perms.get(mod_id, set())
        if acts:
            labels = [lbl for key, lbl in registry.ACTIONS if key in acts]
            parts.append(f"{title}: {', '.join(labels)}")
    return "; ".join(parts) if parts else "Chưa được cấp quyền"


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.selected_id = None
        self._build()
        self.refresh()

    def _build(self):
        lo, card = make_card(self, padding=16)
        lo.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Danh sách tài khoản", style="CardTitle.TLabel").pack(side="left")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.btn_add = RoundedButton(toolbar, text="➕  Tạo tài khoản", command=self.open_add, variant="primary")
        self.btn_edit = RoundedButton(toolbar, text="✏  Sửa / Phân quyền", command=self.open_edit, variant="secondary")
        self.btn_reset = RoundedButton(toolbar, text="🔑  Đặt lại mật khẩu", command=self.reset_pw, variant="secondary")
        self.btn_del = RoundedButton(toolbar, text="🗑  Xóa tài khoản", command=self.delete, variant="danger")
        for b in (self.btn_add, self.btn_edit, self.btn_reset, self.btn_del):
            b.pack(side="left", padx=(0, 6))

        self.tree, wrap = make_tree(card, COLS)
        wrap.pack(fill="both", expand=True)
        self.tree.tag_configure("off", foreground="#9CA3AF")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.open_edit())

        self._refresh_button_states()

    def _refresh_button_states(self):
        has_sel = self.selected_id is not None

        def st(b, ok):
            b.state(["!disabled"] if ok else ["disabled"])

        st(self.btn_edit, has_sel)
        st(self.btn_reset, has_sel)
        st(self.btn_del, has_sel)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        now = datetime.datetime.now()
        for i, u in enumerate(self.db.list_users()):
            locked = u["locked_until"] and datetime.datetime.strptime(u["locked_until"], "%Y-%m-%d %H:%M:%S") > now
            status = "Vô hiệu" if not u["active"] else ("Tạm khóa" if locked else "Hoạt động")
            tags = ["odd" if i % 2 else "even"] + (["off"] if not u["active"] else [])
            self.tree.insert("", "end", iid=str(u["id"]), tags=tags, values=(
                u["username"], u["ho_ten"] or "", ROLES.get(u["role"], u["role"]),
                perms_summary(u["role"], u["perms"]), status, u["last_login"] or "—"))

    def on_select(self, _=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        self._refresh_button_states()

    def open_add(self):
        AccountFormDialog(self, user=None)

    def open_edit(self):
        if self.selected_id is None:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một tài khoản trong danh sách để sửa.")
            return
        user = self.db.get_user(self.selected_id)
        if user:
            AccountFormDialog(self, user=user)

    def reset_pw(self):
        if self.selected_id is None:
            return
        u = self.db.get_user(self.selected_id)
        pw = simpledialog.askstring("Đặt lại mật khẩu",
                                    f"Nhập mật khẩu tạm thời cho '{u['username']}':\n"
                                    "(≥ 8 ký tự, gồm chữ và số; người dùng sẽ phải đổi khi đăng nhập)", show="•")
        if pw is None:
            return
        problem = check_password_policy(pw)
        if problem:
            messagebox.showwarning("Mật khẩu", problem)
            return
        self.db.set_password(self.selected_id, pw, must_change=True)
        self.db.log(self.app.user["username"], "Đặt lại mật khẩu", u["username"])
        self.refresh()
        messagebox.showinfo("Đã đặt lại", "Đã đặt mật khẩu tạm thời và mở khóa tài khoản (nếu đang bị khóa).")

    def delete(self):
        if self.selected_id is None:
            return
        u = self.db.get_user(self.selected_id)
        if self.selected_id == self.app.user["id"]:
            messagebox.showwarning("Không thể thực hiện", "Bạn không thể xóa tài khoản đang đăng nhập.")
            return
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa tài khoản '{u['username']}'?\nThao tác không thể hoàn tác."):
            return
        try:
            self.db.delete_user(self.selected_id)
        except ValueError as e:
            messagebox.showwarning("Không thể thực hiện", str(e))
            return
        self.db.log(self.app.user["username"], "Xóa tài khoản", u["username"])
        self.selected_id = None
        self.refresh()
        self._refresh_button_states()


class AccountFormDialog(tk.Toplevel):
    """Popup Tạo tài khoản mới / Sửa & phân quyền - kéo thả đổi kích thước được."""

    def __init__(self, panel, user=None):
        super().__init__(panel.app)
        self.panel, self.db, self.user_row = panel, panel.db, user
        is_edit = user is not None
        title = f"Sửa & phân quyền: {user['username']}" if is_edit else "Tạo tài khoản mới"
        shell = DialogShell(self, title, width=560, height=680)
        form = shell.body

        self.perm_vars = {mid: {a: tk.BooleanVar() for a, _l in registry.ACTIONS}
                          for mid, *_ in registry.BUSINESS_MODULES}
        self.v_user, self.v_name, self.v_pw = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.v_role = tk.StringVar(value=ROLES["user"])
        self.v_active = tk.BooleanVar(value=True)

        info = ttk.Frame(form, style="Card.TFrame")
        info.pack(fill="x")
        info.columnconfigure(1, weight=1)

        def row(r, label, widget):
            ttk.Label(info, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=5)

        self.e_user = ttk.Entry(info, textvariable=self.v_user, width=28)
        self.e_pw = ttk.Entry(info, textvariable=self.v_pw, width=28, show="•")
        self.c_role = ttk.Combobox(info, textvariable=self.v_role, values=list(ROLES.values()),
                                   state="readonly", width=26)
        row(0, "Tên đăng nhập" + (" *" if not is_edit else ""), self.e_user)
        row(1, "Họ và tên", ttk.Entry(info, textvariable=self.v_name, width=28))
        row(2, "Mật khẩu ban đầu *" if not is_edit else "Mật khẩu", self.e_pw)
        row(3, "Vai trò", self.c_role)
        self.c_role.bind("<<ComboboxSelected>>", lambda e: self._role_changed())
        ttk.Checkbutton(info, text="Tài khoản đang hoạt động", variable=self.v_active,
                        style="Card.TCheckbutton").grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        if is_edit:
            self.e_user.configure(state="readonly")
            self.e_pw.configure(state="disabled")

        section_bar = ttk.Frame(form, style="Card.TFrame")
        section_bar.pack(fill="x", pady=(16, 4))
        ttk.Label(section_bar, text="Phân quyền theo module", style="Section.TLabel").pack(side="left")
        self.v_preset = tk.StringVar(value=list(GLOBAL_PRESETS)[0])
        ttk.Combobox(section_bar, textvariable=self.v_preset, values=list(GLOBAL_PRESETS),
                    state="readonly", width=22).pack(side="left", padx=(16, 6))
        RoundedButton(section_bar, text="Áp dụng", command=self._apply_preset, variant="secondary").pack(side="left")

        grid_wrap = tk.Frame(form, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        grid_wrap.pack(fill="x", pady=(2, 0))
        grid = ttk.Frame(grid_wrap, style="Card.TFrame", padding=10)
        grid.pack(fill="x")
        ttk.Label(grid, text="Module", style="Card.TLabel", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 12))
        for j, (_a, lbl) in enumerate(registry.ACTIONS):
            ttk.Label(grid, text=lbl, style="Card.TLabel", font=("Segoe UI", 9, "bold")).grid(
                row=0, column=j + 1, padx=6)
        for i, (mid, mtitle, icon, *_x) in enumerate(registry.BUSINESS_MODULES, start=1):
            ttk.Label(grid, text=f"{icon} {mtitle}", style="Card.TLabel").grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            for j, (a, _lbl) in enumerate(registry.ACTIONS):
                ttk.Checkbutton(grid, variable=self.perm_vars[mid][a], style="Card.TCheckbutton").grid(
                    row=i, column=j + 1, padx=6)
        self.grid_wrap = grid_wrap

        if is_edit:
            self.v_name.set(user["ho_ten"] or "")
            self.v_role.set(ROLES.get(user["role"], ROLES["user"]))
            self.v_active.set(bool(user["active"]))
            have = parse_perms(user["perms"])
            for mid, acts in self.perm_vars.items():
                for a, var in acts.items():
                    var.set(a in have.get(mid, set()))
        else:
            self.perm_vars["employees"]["view"].set(True)
        self._role_changed()

        save_label = "💾  Lưu thay đổi" if is_edit else "➕  Tạo tài khoản"
        RoundedButton(shell.footer, text=save_label, command=self.save, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(shell.footer, text="Hủy", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self, 560, 680)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _set_grid_state(self, enabled):
        state = "!disabled" if enabled else "disabled"

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton):
                    child.state([state])
                walk(child)
        walk(self.grid_wrap)

    def _role_changed(self):
        is_admin = ROLE_FROM_LABEL.get(self.v_role.get()) == "admin"
        self._set_grid_state(not is_admin)

    def _apply_preset(self):
        acts = GLOBAL_PRESETS.get(self.v_preset.get())
        if acts is None:
            return
        for mid in self.perm_vars:
            for a, var in self.perm_vars[mid].items():
                var.set(a in acts)

    def _perms_from_grid(self):
        return {mid: {a for a, var in acts.items() if var.get()} for mid, acts in self.perm_vars.items()}

    def save(self):
        role = ROLE_FROM_LABEL.get(self.v_role.get(), "user")
        active = self.v_active.get()
        perms = {} if role == "admin" else self._perms_from_grid()
        if self.user_row is None:
            username = self.v_user.get().strip()
            if not re.fullmatch(r"[A-Za-z0-9_.\-]{3,30}", username):
                messagebox.showwarning("Tên đăng nhập", "Tên đăng nhập gồm 3–30 ký tự: chữ không dấu, số, dấu . _ -",
                                       parent=self)
                return
            pw = self.v_pw.get()
            problem = check_password_policy(pw)
            if problem:
                messagebox.showwarning("Mật khẩu", problem, parent=self)
                return
            try:
                self.db.add_user(username, self.v_name.get().strip(), pw, role, perms, must_change=True)
            except sqlite3.IntegrityError:
                messagebox.showerror("Trùng tên", f"Tên đăng nhập '{username}' đã tồn tại.", parent=self)
                return
            self.db.log(self.panel.app.user["username"], "Tạo tài khoản", f"{username} ({ROLES[role]})")
            messagebox.showinfo("Đã tạo", f"Đã tạo tài khoản '{username}'.\n"
                                "Người dùng sẽ phải đổi mật khẩu ở lần đăng nhập đầu tiên.", parent=self)
        else:
            if self.user_row["id"] == self.panel.app.user["id"] and (role != "admin" or not active):
                messagebox.showwarning("Không thể thực hiện",
                                       "Bạn không thể tự hạ quyền hoặc tự vô hiệu hóa tài khoản đang đăng nhập.",
                                       parent=self)
                return
            try:
                self.db.update_user(self.user_row["id"], self.v_name.get().strip(), role, perms, active)
            except ValueError as e:
                messagebox.showwarning("Không thể thực hiện", str(e), parent=self)
                return
            self.db.log(self.panel.app.user["username"], "Cập nhật tài khoản",
                        f"{self.user_row['username']}: {ROLES[role]}")
        self.panel.refresh()
        self.destroy()
