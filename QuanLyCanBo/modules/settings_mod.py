# -*- coding: utf-8 -*-
"""Module (chỉ quản trị viên): bật / tắt các module nghiệp vụ của phần mềm.

Đây là nơi triển khai thêm hoặc bớt module mà KHÔNG cần sửa mã nguồn:
tắt module nào thì module đó (và mục tương ứng trên thanh bên) biến mất
với TẤT CẢ tài khoản, kể cả quản trị viên - dữ liệu vẫn được giữ nguyên
trong CSDL và sẽ hiện lại đầy đủ khi bật lại.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from core import registry
from core.theme import C, make_card
from core.widgets import RoundedButton

MODULE_ID = "settings_mod"


class Panel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.vars = {}
        self._build()

    def _build(self):
        lo, card = make_card(self, padding=20)
        lo.pack(fill="both", expand=True)
        ttk.Label(card, text="Cấu hình module hệ thống", style="CardTitle.TLabel").pack(anchor="w")
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(10, 12))
        ttk.Label(card, style="CardMuted.TLabel", justify="left", wraplength=640,
                 text="Bỏ chọn một module để ẩn hoàn toàn khỏi thanh điều hướng của mọi tài khoản. "
                      "Dữ liệu đã nhập của module đó vẫn được lưu giữ và sẽ hiện lại khi bật lại. "
                      "Các mục quản trị hệ thống (Quản trị tài khoản, Cấu hình module, Nhật ký) "
                      "luôn hiển thị với quản trị viên và không thể tắt."
                 ).pack(anchor="w", pady=(0, 14))

        disabled = self.db.disabled_modules()
        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x", pady=(0, 16))
        for i, (mid, title, icon, *_x) in enumerate(registry.BUSINESS_MODULES):
            var = tk.BooleanVar(value=mid not in disabled)
            self.vars[mid] = var
            row = tk.Frame(grid, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
            row.grid(row=i // 2, column=i % 2, sticky="ew", padx=6, pady=6)
            grid.columnconfigure(i % 2, weight=1)
            inner = ttk.Frame(row, style="Card.TFrame", padding=12)
            inner.pack(fill="both", expand=True)
            ttk.Checkbutton(inner, text=f"{icon}  {title}", variable=var,
                           style="Card.TCheckbutton").pack(anchor="w")

        RoundedButton(card, text="💾  Lưu cấu hình", command=self.save, variant="primary").pack(anchor="w")

        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=16)
        ttk.Label(card, text="Khóa theo máy (danh sách máy được duyệt)", style="Section.TLabel").pack(anchor="w")
        from core.machine_lock import check as check_machine
        _allowed, code, reason = check_machine(self.app.app_dir)
        ttk.Label(card, style="CardMuted.TLabel", justify="left", wraplength=640,
                 text=f"Mã máy này: {code or '(không xác định được)'}\n"
                      f"Trạng thái: {reason}\n"
                      "Để bật/sửa danh sách, chỉnh file allowed_machines.txt cạnh quan_ly_can_bo.py "
                      "rồi khởi động lại phần mềm."
                 ).pack(anchor="w", pady=(6, 0))

    def save(self):
        disabled = {mid for mid, var in self.vars.items() if not var.get()}
        if len(disabled) == len(self.vars):
            if not messagebox.askyesno("Xác nhận",
                                       "Bạn sắp tắt TẤT CẢ module nghiệp vụ. Người dùng thường sẽ không "
                                       "thấy mục nào để làm việc. Vẫn tiếp tục?"):
                return
        self.db.set_disabled_modules(disabled)
        self.db.log(self.app.user["username"], "Cấu hình module",
                    f"Tắt: {', '.join(sorted(disabled)) or '(không)'}")
        messagebox.showinfo("Đã lưu", "Đã lưu cấu hình module.")
        self.app.reload_shell(open_module=MODULE_ID)
