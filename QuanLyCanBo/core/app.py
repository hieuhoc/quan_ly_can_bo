# -*- coding: utf-8 -*-
"""Vỏ ứng dụng: đăng nhập, đổi mật khẩu, khung điều hướng module."""
import datetime
import importlib
import os
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk

from core import registry
from core.security import check_password_policy
from core.theme import C, FONT, center, make_card, setup_style
from core.widgets import RoundedButton

APP_TITLE = "QUẢN LÝ CÁN BỘ"
VERSION = "3.1"
BACKUP_INTERVAL_MIN = 30
IDLE_TIMEOUT_MIN = 15
ROLES = {"admin": "Quản trị viên", "user": "Người dùng"}
ROLE_FROM_LABEL = {v: k for k, v in ROLES.items()}


class App(tk.Tk):
    def __init__(self, db, app_dir, entry_path):
        super().__init__()
        self.db = db
        self.app_dir = app_dir
        self.entry_path = entry_path
        self.backup_dir = os.path.join(app_dir, "backup")
        self.title(APP_TITLE)
        self.user = None
        self.status = tk.StringVar(value="Sẵn sàng")
        self.last_activity = time.time()
        setup_style(self)
        self._set_window_icon()
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        for ev in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(ev, self._touch, add="+")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Luôn hiện màn hình đăng nhập khi mở phần mềm (đăng xuất khi đóng
        # phần mềm) - tài khoản/mật khẩu có thể được điền sẵn nếu người
        # dùng đã chọn "Ghi nhớ mật khẩu" ở lần đăng nhập trước, xem
        # LoginFrame bên dưới.
        self.show_login()

        self.auto_backup(silent=True)
        self.after(BACKUP_INTERVAL_MIN * 60 * 1000, self._backup_loop)
        self.after(30_000, self._idle_check)

    # ------------------------------------------------------------ giao diện chung
    def _set_window_icon(self):
        try:
            ico = os.path.join(self.app_dir, "assets", "app.ico")
            png = os.path.join(self.app_dir, "assets", "app.png")
            if sys.platform.startswith("win") and os.path.exists(ico):
                self.iconbitmap(ico)
            elif os.path.exists(png):
                self._icon_img = tk.PhotoImage(file=png)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    # ------------------------------------------------------------ điều hướng màn hình
    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def can(self, module_id, action="view"):
        u = self.user
        if not u:
            return False
        if u["role"] == "admin":
            return True
        from core.db import parse_perms
        perms = parse_perms(u["perms"])
        return action in perms.get(module_id, set())

    def show_login(self):
        self.user = None
        self.clear()
        self.state("normal")
        self.minsize(480, 640)
        center(self, 520, 680)
        LoginFrame(self.container, self).pack(fill="both", expand=True)

    def on_login_success(self, user, remember=False, password=None):
        final_password = password
        if user["must_change"]:
            dlg = ChangePasswordDialog(self, self.db, user, forced=True)
            self.wait_window(dlg)
            if not dlg.ok:
                self.db.log(user["username"], "Hủy đổi mật khẩu bắt buộc")
                self.show_login()
                return
            user = self.db.get_user(user["id"])
            final_password = dlg.new_password
        import core.credentials as creds
        if remember and final_password:
            creds.save(self.app_dir, user["username"], final_password)
        else:
            creds.clear(self.app_dir)
        self.user = user
        self.clear()
        self.minsize(1180, 680)
        center(self, 1360, 780)
        self.last_activity = time.time()
        from core.shell import Shell
        Shell(self.container, self).pack(fill="both", expand=True)

    def reload_shell(self, open_module=None):
        """Vẽ lại toàn bộ khung chính (thanh bên + nội dung) - dùng sau khi
        quyền tài khoản hoặc cấu hình module thay đổi."""
        self.user = self.db.get_user(self.user["id"])
        self.clear()
        from core.shell import Shell
        shell = Shell(self.container, self)
        shell.pack(fill="both", expand=True)
        if open_module and open_module in shell.nav_buttons:
            shell.open_module(open_module)

    def logout(self, reason="Đăng xuất"):
        """Đăng xuất - mật khẩu đã lưu (nếu có) vẫn được giữ để lần đăng
        nhập kế tiếp tiếp tục được điền sẵn; chỉ xóa khi người dùng bỏ
        chọn "Ghi nhớ mật khẩu" hoặc đổi mật khẩu."""
        if self.user:
            self.db.log(self.user["username"], reason)
        for w in self.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.destroy()
        self.show_login()

    def idle_logout(self):
        if self.user:
            self.db.log(self.user["username"], "Tự động đăng xuất (không thao tác)")
        for w in self.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.destroy()
        self.show_login()

    # ------------------------------------------------------------ tự động
    def _touch(self, _e=None):
        self.last_activity = time.time()

    def _idle_check(self):
        if self.user and time.time() - self.last_activity > IDLE_TIMEOUT_MIN * 60:
            self.idle_logout()
            messagebox.showinfo("Hết phiên làm việc",
                                f"Đã tự động đăng xuất sau {IDLE_TIMEOUT_MIN} phút không thao tác.")
        self.after(30_000, self._idle_check)

    def auto_backup(self, silent=False):
        try:
            p = self.db.backup(self.backup_dir)
            self.status.set(f"Đã sao lưu: {os.path.basename(p)}  ({datetime.datetime.now():%H:%M:%S})")
            if not silent:
                messagebox.showinfo("Sao lưu", f"Đã sao lưu vào:\n{p}")
        except Exception as e:  # noqa
            self.status.set(f"Lỗi sao lưu: {e}")

    def _backup_loop(self):
        self.auto_backup(silent=True)
        self.after(BACKUP_INTERVAL_MIN * 60 * 1000, self._backup_loop)

    def on_close(self):
        """Đóng phần mềm = đăng xuất: lần mở kế tiếp luôn hiện màn hình
        đăng nhập (không tự động vào thẳng bên trong)."""
        self.auto_backup(silent=True)
        if self.user:
            self.db.log(self.user["username"], "Thoát chương trình (đăng xuất)")
        self.db.close()
        self.destroy()


# ------------------------------------------------------------ đăng nhập
class LoginFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["primary"])
        self.app = app
        outer, card = make_card(self, padding=(38, 28))
        outer.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="🛡", font=("Segoe UI Emoji", 40), bg=C["card"], fg=C["primary"]).pack()
        ttk.Label(card, text=APP_TITLE, style="CardTitle.TLabel", font=(FONT, 18, "bold")).pack(pady=(2, 0))
        ttk.Label(card, text="Vui lòng đăng nhập để tiếp tục", style="CardMuted.TLabel").pack(pady=(2, 6))
        tk.Frame(card, height=3, width=56, bg=C["gold"]).pack(pady=(2, 4))

        ttk.Label(card, text="Tên đăng nhập", style="Card.TLabel").pack(anchor="w", pady=(12, 3))
        self.u = tk.StringVar()
        self.e_user = ttk.Entry(card, textvariable=self.u, width=32)
        self.e_user.pack(fill="x")

        ttk.Label(card, text="Mật khẩu", style="Card.TLabel").pack(anchor="w", pady=(10, 3))
        self.p = tk.StringVar()
        self.e_pass = ttk.Entry(card, textvariable=self.p, show="•", width=32)
        self.e_pass.pack(fill="x")

        opts = ttk.Frame(card, style="Card.TFrame")
        opts.pack(fill="x", pady=(8, 0))
        self.show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Hiện mật khẩu", variable=self.show_pw, style="Card.TCheckbutton",
                        command=lambda: self.e_pass.configure(show="" if self.show_pw.get() else "•")
                        ).pack(side="left")
        self.remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Ghi nhớ mật khẩu trên máy này", variable=self.remember,
                        style="Card.TCheckbutton", command=self._on_remember_toggle
                        ).pack(side="left", padx=(16, 0))

        self.err = tk.StringVar()
        ttk.Label(card, textvariable=self.err, style="Error.TLabel", wraplength=310,
                  justify="left").pack(anchor="w", pady=(8, 0))
        RoundedButton(card, text="ĐĂNG NHẬP", command=self.submit, variant="primary").pack(fill="x", pady=(10, 0))

        import core.credentials as creds
        note = f"Phiên bản {VERSION}  •  Hoạt động ngoại tuyến"
        if not creds.available():
            note += "\n(Tự động điền mật khẩu chỉ hỗ trợ trên Windows)"
        ttk.Label(card, text=note, style="CardMuted.TLabel", justify="center").pack(pady=(14, 0))

        self.e_user.bind("<Return>", lambda e: self.e_pass.focus_set())
        self.e_pass.bind("<Return>", lambda e: self.submit())

        saved = creds.load(app.app_dir)
        if saved:
            self.u.set(saved[0])
            self.p.set(saved[1])
            self.e_pass.focus_set()
        else:
            self.e_user.focus_set()

    def _on_remember_toggle(self):
        if not self.remember.get():
            import core.credentials as creds
            creds.clear(self.app.app_dir)

    def submit(self):
        username, pw = self.u.get().strip(), self.p.get()
        if not username or not pw:
            self.err.set("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            return
        user, err = self.app.db.authenticate(username, pw)
        if err:
            self.err.set(err)
            self.p.set("")
            self.e_pass.focus_set()
            return
        self.app.on_login_success(user, remember=self.remember.get(), password=pw)


# ------------------------------------------------------------ đổi mật khẩu
class ChangePasswordDialog(tk.Toplevel):
    def __init__(self, app, db, user, forced=False):
        super().__init__(app)
        self.app_ref, self.db, self.user, self.forced, self.ok = app, db, user, forced, False
        self.new_password = None
        self.title("Đổi mật khẩu")
        self.configure(bg=C["card"])
        self.resizable(False, False)
        self.transient(app)

        frm = ttk.Frame(self, style="Card.TFrame", padding=26)
        frm.pack()
        ttk.Label(frm, text="🔑  Đổi mật khẩu", style="CardTitle.TLabel").pack(anchor="w")
        if forced:
            ttk.Label(frm, style="CardMuted.TLabel", justify="left",
                      text="Bạn đăng nhập lần đầu hoặc mật khẩu vừa được đặt lại.\n"
                           "Hãy đặt mật khẩu mới để tiếp tục sử dụng.").pack(anchor="w", pady=(4, 6))
        self.vars = []
        self.entries = []
        first = None
        for label in ("Mật khẩu hiện tại", "Mật khẩu mới", "Nhập lại mật khẩu mới"):
            ttk.Label(frm, text=label, style="Card.TLabel").pack(anchor="w", pady=(10, 3))
            v = tk.StringVar()
            e = ttk.Entry(frm, textvariable=v, show="•", width=34)
            e.pack(fill="x")
            e.bind("<Return>", lambda ev: self.submit())
            self.vars.append(v)
            self.entries.append(e)
            first = first or e
        self.show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Hiện mật khẩu", variable=self.show_pw, style="Card.TCheckbutton",
                        command=self._toggle_show).pack(anchor="w", pady=(8, 0))
        ttk.Label(frm, text="Tối thiểu 8 ký tự, gồm cả chữ và số.", style="CardMuted.TLabel").pack(anchor="w", pady=(6, 0))
        self.err = tk.StringVar()
        ttk.Label(frm, textvariable=self.err, style="Error.TLabel", wraplength=300).pack(anchor="w", pady=(6, 0))

        row = ttk.Frame(frm, style="Card.TFrame")
        row.pack(fill="x", pady=(10, 0))
        RoundedButton(row, text="Lưu mật khẩu", command=self.submit, variant="primary").pack(side="left", fill="x", expand=True, padx=(0, 6))
        RoundedButton(row, text="Hủy", command=self.destroy, variant="secondary").pack(side="left", fill="x", expand=True)

        center(self)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        first.focus_set()

    def _toggle_show(self):
        show = "" if self.show_pw.get() else "•"
        for e in self.entries:
            e.configure(show=show)

    def submit(self):
        old, new, cf = (v.get() for v in self.vars)
        if not self.db.check_user_password(self.user["id"], old):
            self.err.set("Mật khẩu hiện tại không đúng.")
            return
        problem = check_password_policy(new)
        if problem:
            self.err.set(problem)
            return
        if new == old:
            self.err.set("Mật khẩu mới phải khác mật khẩu hiện tại.")
            return
        if new != cf:
            self.err.set("Hai lần nhập mật khẩu mới không khớp.")
            return
        self.db.set_password(self.user["id"], new, must_change=False)
        self.db.log(self.user["username"], "Đổi mật khẩu")
        self.new_password = new
        # Nếu máy này đang lưu sẵn mật khẩu cho đúng tài khoản này, cập nhật
        # luôn sang mật khẩu mới để lần sau vẫn được điền sẵn đúng.
        try:
            import core.credentials as creds
            saved = creds.load(self.app_ref.app_dir)
            if saved and saved[0] == self.user["username"]:
                creds.save(self.app_ref.app_dir, self.user["username"], new)
        except Exception:
            pass
        self.ok = True
        messagebox.showinfo("Thành công", "Đã đổi mật khẩu.", parent=self)
        self.destroy()
