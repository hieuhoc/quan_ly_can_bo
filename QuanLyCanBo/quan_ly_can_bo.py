# -*- coding: utf-8 -*-
"""
PHẦN MỀM QUẢN LÝ CÁN BỘ - Phiên bản 4.2 (giao diện PySide6 / Qt)
------------------------------------------------------------------
Bản đóng gói:   QuanLyCanBo.exe                (không cần cài Python)
Chạy mã nguồn:  python quan_ly_can_bo.py       (cần: pip install -r requirements.txt)
Đặt lại mật khẩu admin (khi quên):  QuanLyCanBo.exe --reset-admin
Xem mã máy này (để xin cấp phép):   QuanLyCanBo.exe --ma-may
Tự kiểm tra sau khi đóng gói:       QuanLyCanBo.exe --kiem-tra   (không mở cửa sổ, ghi kết quả ra file)

Cấu trúc thư mục mã nguồn:
  quan_ly_can_bo.py   điểm khởi chạy (file này)
  core/               phần lõi: CSDL, bảo mật, khóa máy, dữ liệu tham chiếu
  ui/                 giao diện dùng chung: giao diện màu, bảng, hộp thoại, cửa sổ chính
  modules/            từng module nghiệp vụ - thêm/bớt module tại core/registry.py
Dữ liệu (tự tạo cạnh file chạy): canbo.db, backup/, attachments/, xuat_file/
"""
import os
import sys

if not getattr(sys, "frozen", False):
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)

from core.paths import APP_DIR  # noqa: E402

DB_PATH = os.path.join(APP_DIR, "canbo.db")


def self_test():
    """Mở phần mềm trên một CSDL tạm, đăng nhập, mở lần lượt mọi module rồi
    thoát. Dùng khi đóng gói (máy build Windows) để chắc chắn file .exe chạy
    được. Kết quả ghi vào kiem_tra.txt trong thư mục tạm và mã thoát 0/1."""
    import tempfile
    import traceback
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    tmp = tempfile.mkdtemp()
    out = os.path.join(tempfile.gettempdir(), "kiem_tra_quan_ly_can_bo.txt")
    lines = []
    try:
        from PySide6.QtWidgets import QApplication
        from core import co_cau, registry
        from core.db import Database
        import ui.theme as theme
        qapp = QApplication(sys.argv)
        theme.install(qapp)
        db = Database(os.path.join(tmp, "canbo.db"))
        db.conn.execute("UPDATE nguoi_dung SET must_change=0")
        db.conn.commit()
        db.insert("can_bo", dict(ma_cb="KT1", ho_ten="Kiểm Tra", cong_an_tinh=co_cau.TINH_MAC_DINH,
                                 don_vi="Phòng Tham mưu"))
        assert len(co_cau.danh_sach_cong_an_xa(co_cau.TINH_MAC_DINH)) > 50
        from ui.app import App
        win = App(db, tmp)
        win.on_login_success(db.get_user_by_name("admin"))
        for m in registry.HOME_MODULES + registry.BUSINESS_MODULES + registry.ADMIN_MODULES:
            win.shell.open_module(m[0])
            qapp.processEvents()
            if win.shell.current_id != m[0] or type(win.shell.current_panel).__name__ == "QLabel":
                raise RuntimeError(f"Không mở được module {m[0]}")
            lines.append(f"OK  {m[0]}")
        win.close()
        lines.append("KIEM TRA OK")
        code = 0
    except Exception:  # noqa
        lines.append(traceback.format_exc())
        lines.append("KIEM TRA LOI")
        code = 1
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return code


def main():
    if "--kiem-tra" in sys.argv:
        return self_test()
    from PySide6.QtWidgets import QApplication
    from core.db import Database
    from core.machine_lock import check as check_machine, compute_code
    import ui.theme as theme
    from ui.widgets import error, info

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("QuanLyCanBo")
    theme.install(qapp)

    if "--ma-may" in sys.argv:
        code = compute_code()
        print(f"Mã máy này: {code or '(không xác định được)'}")
        info(None, f"Mã máy này:\n\n{code or '(không xác định được)'}", "Mã máy")
        return 0

    allowed, code, reason = check_machine(APP_DIR)
    if not allowed:
        error(None, "Máy tính này chưa được cấp phép cài đặt / sử dụng phần mềm Quản lý cán bộ.\n\n"
                    f"Mã máy này là:\n{code or '(không xác định được)'}\n\nLý do: {reason}\n\n"
                    "Vui lòng gửi mã máy này cho quản trị viên để được bổ sung vào danh sách máy được duyệt.",
              "Máy chưa được cấp phép")
        return 1

    if "--reset-admin" in sys.argv:
        db = Database(DB_PATH)
        db.reset_admin()
        db.close()
        from core.db import DEFAULT_ADMIN
        msg = (f"Đã đặt lại tài khoản {DEFAULT_ADMIN[0]} / {DEFAULT_ADMIN[1]} "
               "(sẽ phải đổi mật khẩu khi đăng nhập).")
        print(msg)
        info(None, msg, "Đặt lại quản trị viên")
        return 0

    db = Database(DB_PATH)
    from ui.app import App
    win = App(db, APP_DIR)
    win.show()
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
