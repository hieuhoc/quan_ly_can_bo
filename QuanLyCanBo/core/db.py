# -*- coding: utf-8 -*-
"""
Lớp truy cập CSDL (SQLite) cho toàn bộ phần mềm.
Mỗi module nghiệp vụ (cán bộ, phân loại, nâng lương, đơn thư...) dùng chung
một file CSDL nhưng có bảng riêng, để việc bật/tắt module không ảnh hưởng
tới dữ liệu của module khác.
"""
import datetime
import os
import sqlite3

from core.security import hash_password

TS = "%Y-%m-%d %H:%M:%S"
ALL_ACTIONS = ["view", "add", "edit", "delete", "export"]
BUSINESS_MODULES = ["employees", "classification", "salary", "complaints"]
DEFAULT_ADMIN = ("admin", "admin@123")


def now_str():
    return datetime.datetime.now().strftime(TS)


def parse_perms(text):
    """'employees:view,add;salary:view' -> {'employees': {'view','add'}, 'salary': {'view'}}"""
    out = {}
    if not text:
        return out
    for part in text.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        mod, acts = part.split(":", 1)
        acts = {a for a in acts.split(",") if a}
        if mod:
            out[mod] = acts
    return out


def serialize_perms(perms):
    return ";".join(f"{m}:{','.join(sorted(a))}" for m, a in perms.items() if a)


class Database:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._migrate()
        self._ensure_admin()

    # ------------------------------------------------------------ lược đồ
    def _create_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS can_bo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ma_cb TEXT NOT NULL UNIQUE,
                ho_ten TEXT NOT NULL,
                ngay_sinh TEXT, gioi_tinh TEXT,
                que_quan TEXT, noi_o_hien_tai TEXT, so_cccd TEXT, sdt TEXT,
                cap_bac TEXT, chuc_vu TEXT, chuc_danh_hien_tai TEXT, don_vi TEXT,
                he_so_luong TEXT,
                ngay_vao_nganh TEXT, ngay_vao_dang TEXT, ngay_chuyen_dang_chinh_thuc TEXT,
                trinh_do_nghiep_vu TEXT, trinh_do_chinh_tri TEXT, trinh_do_ngoai_ngu TEXT,
                ghi_chu TEXT, ghi_chu_bo_sung TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS phan_loai_can_bo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                can_bo_id INTEGER NOT NULL REFERENCES can_bo(id) ON DELETE CASCADE,
                loai TEXT NOT NULL,           -- Tháng / Quý / Năm
                ky TEXT NOT NULL,             -- vd 03/2026, Quý I/2026, 2026
                xep_loai TEXT NOT NULL,
                ghi_chu TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                created_by TEXT
            );

            CREATE TABLE IF NOT EXISTS qua_trinh_luong (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                can_bo_id INTEGER NOT NULL REFERENCES can_bo(id) ON DELETE CASCADE,
                loai TEXT NOT NULL,           -- Nâng lương định kỳ / trước hạn / Thăng cấp bậc hàm
                ngay_quyet_dinh TEXT,
                so_quyet_dinh TEXT,
                noi_dung TEXT NOT NULL,
                ghi_chu TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                created_by TEXT
            );

            CREATE TABLE IF NOT EXISTS don_thu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                can_bo_id INTEGER REFERENCES can_bo(id) ON DELETE SET NULL,
                tieu_de TEXT NOT NULL,
                loai TEXT NOT NULL,           -- Đơn thư / Khiếu nại / Tố cáo / Phản ánh
                nguoi_gui TEXT,
                ngay_nhan TEXT,
                noi_dung TEXT,
                trang_thai TEXT NOT NULL DEFAULT 'Mới tiếp nhận',
                ngay_giai_quyet TEXT,
                ket_qua TEXT,
                ghi_chu TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                created_by TEXT
            );

            CREATE TABLE IF NOT EXISTS nguoi_dung (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                ho_ten TEXT,
                salt TEXT NOT NULL,
                pw_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                perms TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                must_change INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                last_login TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS nhat_ky (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thoi_gian TEXT, username TEXT, hanh_dong TEXT, chi_tiet TEXT
            );

            CREATE TABLE IF NOT EXISTS cai_dat (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    def _cols(self, table):
        return {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}

    def _migrate(self):
        """Bổ sung cột mới cho CSDL tạo từ phiên bản cũ, không mất dữ liệu."""
        extra_cb = {
            "que_quan": "TEXT", "noi_o_hien_tai": "TEXT", "so_cccd": "TEXT",
            "chuc_danh_hien_tai": "TEXT", "he_so_luong": "TEXT",
            "ngay_vao_dang": "TEXT", "ngay_chuyen_dang_chinh_thuc": "TEXT",
            "trinh_do_nghiep_vu": "TEXT", "trinh_do_chinh_tri": "TEXT",
            "trinh_do_ngoai_ngu": "TEXT", "ghi_chu_bo_sung": "TEXT",
            # Quê quán / nơi ở hiện tại chuẩn hóa theo xã, tỉnh hiện hành (v3.2):
            # cột que_quan, noi_o_hien_tai phía trên được giữ lại (dữ liệu cũ,
            # không tự động phân tích được thành xã/tỉnh) - dữ liệu MỚI dùng
            # các cột theo sau đây.
            "que_quan_xa": "TEXT", "que_quan_tinh": "TEXT",
            "noi_o_chi_tiet": "TEXT", "noi_o_xa": "TEXT", "noi_o_tinh": "TEXT",
        }
        have = self._cols("can_bo")
        for col, typ in extra_cb.items():
            if col not in have:
                self.conn.execute(f"ALTER TABLE can_bo ADD COLUMN {col} {typ}")
        have_pl = self._cols("phan_loai_can_bo")
        for col, typ in {"nam": "INTEGER", "ky_so": "INTEGER", "diem": "REAL"}.items():
            if col not in have_pl:
                self.conn.execute(f"ALTER TABLE phan_loai_can_bo ADD COLUMN {col} {typ}")
        for table in ("qua_trinh_luong", "don_thu"):
            if "file_dinh_kem" not in self._cols(table):
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN file_dinh_kem TEXT")
        if "cap_bac_moi" not in self._cols("qua_trinh_luong"):
            self.conn.execute("ALTER TABLE qua_trinh_luong ADD COLUMN cap_bac_moi TEXT")
        if "cap_don_vi" not in self._cols("can_bo"):
            self.conn.execute("ALTER TABLE can_bo ADD COLUMN cap_don_vi TEXT")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS qua_trinh_cong_tac (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                can_bo_id INTEGER NOT NULL REFERENCES can_bo(id) ON DELETE CASCADE,
                tu_ngay TEXT, den_ngay TEXT, don_vi_cong_tac TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )""")
        # Chuyển định dạng quyền phẳng của bản cũ (vd "add,edit") sang định dạng
        # theo từng module (vd "employees:view,add,edit").
        for u in self.conn.execute("SELECT id, role, perms FROM nguoi_dung").fetchall():
            perms = u["perms"] or ""
            if u["role"] != "admin" and perms and ":" not in perms:
                acts = {a for a in perms.split(",") if a}
                acts.add("view")
                new_perms = serialize_perms({"employees": acts})
                self.conn.execute("UPDATE nguoi_dung SET perms=? WHERE id=?", (new_perms, u["id"]))
        self.conn.commit()

    def _ensure_admin(self):
        if self.conn.execute("SELECT COUNT(*) FROM nguoi_dung").fetchone()[0] == 0:
            self.add_user(DEFAULT_ADMIN[0], "Quản trị hệ thống", DEFAULT_ADMIN[1],
                          "admin", {}, must_change=True)
            self.log("hệ thống", "Khởi tạo", "Tạo tài khoản admin mặc định")

    # ---------------------------------------------------- thao tác chung
    def fetch_all(self, table, order_by, keyword="", search_cols=None, where_extra="", params_extra=()):
        sql = f"SELECT * FROM {table}"
        conds, params = [], []
        if where_extra:
            conds.append(where_extra)
            params.extend(params_extra)
        if keyword and search_cols:
            like = f"%{keyword}%"
            conds.append("(" + " OR ".join(f"{c} LIKE ?" for c in search_cols) + ")")
            params.extend([like] * len(search_cols))
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += f" ORDER BY {order_by}"
        return self.conn.execute(sql, params).fetchall()

    def fetch_one(self, table, rid):
        return self.conn.execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()

    def insert(self, table, data):
        keys = list(data.keys())
        cur = self.conn.execute(
            f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})",
            [data[k] for k in keys])
        self.conn.commit()
        return cur.lastrowid

    def update(self, table, rid, data, touch_updated=True):
        keys = list(data.keys())
        sets = ",".join(f"{k}=?" for k in keys)
        if touch_updated and "updated_at" in self._cols(table):
            sets += ", updated_at=datetime('now','localtime')"
        self.conn.execute(f"UPDATE {table} SET {sets} WHERE id=?", [data[k] for k in keys] + [rid])
        self.conn.commit()

    def delete(self, table, rid):
        self.conn.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
        self.conn.commit()

    # ---------------------------------------------------- cán bộ (dùng chéo module)
    def employees_for_picker(self):
        return self.conn.execute("SELECT id, ma_cb, ho_ten FROM can_bo ORDER BY ho_ten COLLATE NOCASE").fetchall()

    def employee_label(self, can_bo_id):
        r = self.conn.execute("SELECT ma_cb, ho_ten FROM can_bo WHERE id=?", (can_bo_id,)).fetchone()
        return f"{r['ma_cb']} - {r['ho_ten']}" if r else "(đã xóa)"

    # ---------------------------------------------------- tài khoản
    def get_user(self, uid):
        r = self.conn.execute("SELECT * FROM nguoi_dung WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

    def get_user_by_name(self, username):
        r = self.conn.execute("SELECT * FROM nguoi_dung WHERE username=?", (username,)).fetchone()
        return dict(r) if r else None

    def list_users(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM nguoi_dung ORDER BY role, username")]

    def count_active_admins(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM nguoi_dung WHERE role='admin' AND active=1").fetchone()[0]

    def add_user(self, username, ho_ten, password, role, perms_dict, must_change=True):
        salt, h = hash_password(password)
        self.conn.execute(
            "INSERT INTO nguoi_dung (username, ho_ten, salt, pw_hash, role, perms, must_change) "
            "VALUES (?,?,?,?,?,?,?)",
            (username, ho_ten, salt, h, role, serialize_perms(perms_dict), 1 if must_change else 0))
        self.conn.commit()

    def _would_orphan_admin(self, uid, new_role, new_active):
        cur = self.get_user(uid)
        return (cur and cur["role"] == "admin" and cur["active"]
                and (new_role != "admin" or not new_active)
                and self.count_active_admins() <= 1)

    def update_user(self, uid, ho_ten, role, perms_dict, active):
        if self._would_orphan_admin(uid, role, active):
            raise ValueError("Hệ thống phải còn ít nhất một quản trị viên đang hoạt động.")
        if active:
            self.conn.execute("UPDATE nguoi_dung SET fail_count=0, locked_until=NULL WHERE id=?", (uid,))
        self.conn.execute(
            "UPDATE nguoi_dung SET ho_ten=?, role=?, perms=?, active=? WHERE id=?",
            (ho_ten, role, serialize_perms(perms_dict), 1 if active else 0, uid))
        self.conn.commit()

    def delete_user(self, uid):
        if self._would_orphan_admin(uid, "user", False):
            raise ValueError("Không thể xóa quản trị viên cuối cùng.")
        self.conn.execute("DELETE FROM nguoi_dung WHERE id=?", (uid,))
        self.conn.commit()

    def set_password(self, uid, password, must_change):
        salt, h = hash_password(password)
        self.conn.execute(
            "UPDATE nguoi_dung SET salt=?, pw_hash=?, must_change=?, fail_count=0, locked_until=NULL WHERE id=?",
            (salt, h, 1 if must_change else 0, uid))
        self.conn.commit()

    def check_user_password(self, uid, password):
        from core.security import verify_password
        u = self.get_user(uid)
        return bool(u) and verify_password(password, u["salt"], u["pw_hash"])

    def reset_admin(self):
        name, pw = DEFAULT_ADMIN
        row = self.conn.execute("SELECT id FROM nguoi_dung WHERE username=?", (name,)).fetchone()
        if row:
            self.set_password(row["id"], pw, True)
            self.conn.execute("UPDATE nguoi_dung SET role='admin', perms='', active=1 WHERE id=?", (row["id"],))
            self.conn.commit()
        else:
            self.add_user(name, "Quản trị hệ thống", pw, "admin", {}, must_change=True)
        self.log("hệ thống", "Đặt lại admin", "Thực hiện bằng tham số --reset-admin")

    def authenticate(self, username, password):
        from core.security import verify_password
        now = datetime.datetime.now()
        row = self.conn.execute("SELECT * FROM nguoi_dung WHERE username=?", (username,)).fetchone()
        if row is None:
            hash_password(password, b"\0" * 16)
            self.log(username, "Đăng nhập thất bại", "Sai tên đăng nhập")
            return None, "Sai tên đăng nhập hoặc mật khẩu."
        u = dict(row)
        if not u["active"]:
            self.log(username, "Đăng nhập thất bại", "Tài khoản bị vô hiệu hóa")
            return None, "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."
        if u["locked_until"]:
            until = datetime.datetime.strptime(u["locked_until"], TS)
            if until > now:
                return None, f"Tài khoản đang bị tạm khóa đến {until:%H:%M:%S}."
        if not verify_password(password, u["salt"], u["pw_hash"]):
            fails = u["fail_count"] + 1
            if fails >= 5:
                until = (now + datetime.timedelta(minutes=5)).strftime(TS)
                self.conn.execute("UPDATE nguoi_dung SET fail_count=0, locked_until=? WHERE id=?", (until, u["id"]))
                self.conn.commit()
                self.log(username, "Khóa tạm", "Sai mật khẩu 5 lần")
                return None, "Nhập sai 5 lần. Tài khoản bị tạm khóa 5 phút."
            self.conn.execute("UPDATE nguoi_dung SET fail_count=? WHERE id=?", (fails, u["id"]))
            self.conn.commit()
            self.log(username, "Đăng nhập thất bại", "Sai mật khẩu")
            return None, f"Sai tên đăng nhập hoặc mật khẩu. Còn {5 - fails} lần thử."
        self.conn.execute("UPDATE nguoi_dung SET fail_count=0, locked_until=NULL, last_login=? WHERE id=?",
                          (now.strftime(TS), u["id"]))
        self.conn.commit()
        self.log(username, "Đăng nhập")
        return self.get_user(u["id"]), None

    # ---------------------------------------------------- cấu hình / module
    def get_setting(self, key, default=""):
        r = self.conn.execute("SELECT value FROM cai_dat WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key, value):
        self.conn.execute("INSERT INTO cai_dat (key, value) VALUES (?,?) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self.conn.commit()

    def disabled_modules(self):
        raw = self.get_setting("modules_disabled", "")
        return {m for m in raw.split(",") if m}

    def set_disabled_modules(self, mod_ids):
        self.set_setting("modules_disabled", ",".join(sorted(mod_ids)))

    # ---------------------------------------------------- nhật ký
    def log(self, username, action, detail=""):
        self.conn.execute(
            "INSERT INTO nhat_ky (thoi_gian, username, hanh_dong, chi_tiet) VALUES (?,?,?,?)",
            (now_str(), username, action, detail))
        self.conn.commit()

    def recent_logs(self, limit=500):
        return self.conn.execute("SELECT * FROM nhat_ky ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    # ---------------------------------------------------- sao lưu
    def backup(self, backup_dir, keep=20):
        os.makedirs(backup_dir, exist_ok=True)
        name = datetime.datetime.now().strftime("canbo_%Y%m%d_%H%M%S.db")
        dst_path = os.path.join(backup_dir, name)
        dst = sqlite3.connect(dst_path)
        with dst:
            self.conn.backup(dst)
        dst.close()
        files = sorted(f for f in os.listdir(backup_dir) if f.startswith("canbo_") and f.endswith(".db"))
        for old in files[:-keep]:
            try:
                os.remove(os.path.join(backup_dir, old))
            except OSError:
                pass
        return dst_path

    def close(self):
        self.conn.close()
