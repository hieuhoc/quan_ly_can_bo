# -*- coding: utf-8 -*-
"""
PHẦN MỀM QUẢN LÝ CÁN BỘ - Phiên bản 3.0 (kiến trúc module)
------------------------------------------------------------
Chạy:            python quan_ly_can_bo.py
Đặt lại mật khẩu admin (khi quên):  python quan_ly_can_bo.py --reset-admin
Xem mã máy này (để xin cấp phép):   python quan_ly_can_bo.py --ma-may

Cấu trúc thư mục:
  quan_ly_can_bo.py   điểm khởi chạy (file này)
  core/               phần lõi dùng chung: CSDL, đăng nhập, giao diện khung
  modules/            từng module nghiệp vụ - thêm/bớt module tại core/registry.py
  canbo.db            CSDL (tự tạo khi chạy lần đầu)
  backup/             các bản sao lưu tự động
"""
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

DB_PATH = os.path.join(APP_DIR, "canbo.db")


def main():
    from core.db import Database

    if "--ma-may" in sys.argv:
        from core.machine_lock import compute_code
        code = compute_code()
        print(f"Mã máy này: {code or '(không xác định được)'}")
        return

    from core.machine_lock import check as check_machine
    allowed, code, reason = check_machine(APP_DIR)
    if not allowed:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Máy chưa được cấp phép",
            "Máy tính này chưa được cấp phép cài đặt / sử dụng phần mềm Quản lý cán bộ.\n\n"
            f"Mã máy này là:\n{code or '(không xác định được)'}\n\n"
            f"Lý do: {reason}\n\n"
            "Vui lòng gửi mã máy này cho quản trị viên để được bổ sung vào "
            "danh sách máy được duyệt.")
        root.destroy()
        sys.exit(1)

    if "--reset-admin" in sys.argv:
        db = Database(DB_PATH)
        db.reset_admin()
        db.close()
        from core.db import DEFAULT_ADMIN
        print(f"Đã đặt lại tài khoản {DEFAULT_ADMIN[0]} / {DEFAULT_ADMIN[1]} "
              "(sẽ phải đổi mật khẩu khi đăng nhập).")
        return

    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    db = Database(DB_PATH)
    from core.app import App
    entry_path = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    App(db, APP_DIR, entry_path).mainloop()


if __name__ == "__main__":
    main()
