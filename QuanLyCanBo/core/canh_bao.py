# -*- coding: utf-8 -*-
"""
Tính cảnh báo đến hạn cho từng cán bộ, theo tham số nghiệp vụ (core/tham_so.py):

  thang_cap  Xét thăng cấp bậc hàm   = ngày QĐ lên cấp bậc hiện tại + niên hạn của cấp bậc đó
  nang_luong Xét nâng lương          = ngày QĐ nâng lương / thăng cấp gần nhất + chu kỳ nâng lương
  nghi_huu   Nghỉ hưu (hết hạn tuổi) = ngày sinh + hạn tuổi theo cấp bậc và giới tính
  dang       Chuyển Đảng chính thức  = ngày vào Đảng + thời gian dự bị (khi chưa có ngày chính thức)

Mỗi loại được báo "Sắp đến hạn" khi còn trong khoảng báo trước (tham số) và
"Quá hạn" khi đã qua ngày. Cán bộ thiếu dữ liệu để tính (chưa có ngày sinh, chưa
có quyết định lên cấp bậc hiện tại...) được liệt kê riêng để bổ sung.

Ngoại lệ (bảng ngoai_le_canh_bao, bắt buộc có lý do): dời hạn sang ngày khác,
hoặc không nhắc loại cảnh báo đó cho cán bộ đó nữa.
"""
import calendar
import datetime

from core import tham_so as ts

LOAI = {
    "thang_cap": "Xét thăng cấp bậc hàm",
    "nang_luong": "Xét nâng lương",
    "nghi_huu": "Nghỉ hưu (hết hạn tuổi phục vụ)",
    "dang": "Chuyển Đảng chính thức",
}
QUA_HAN, SAP_DEN, THIEU = "Quá hạn", "Sắp đến hạn", "Thiếu dữ liệu"
FMT = "%d/%m/%Y"


def parse(text):
    try:
        return datetime.datetime.strptime((text or "").strip(), FMT).date()
    except ValueError:
        return None


def add_months(d, months):
    y, m = divmod(d.month - 1 + int(months), 12)
    y, m = d.year + y, m + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def add_years(d, years):
    return add_months(d, round(float(years) * 12))


def _latest_decisions(db):
    """{can_bo_id: [(ngày, cấp bậc mới), ...]} - mọi quyết định có ngày hợp lệ."""
    out = {}
    for r in db.conn.execute("SELECT can_bo_id, ngay_quyet_dinh, cap_bac_moi FROM qua_trinh_luong"):
        d = parse(r["ngay_quyet_dinh"])
        if d:
            out.setdefault(r["can_bo_id"], []).append((d, r["cap_bac_moi"] or ""))
    return out


def exceptions(db):
    return {(r["can_bo_id"], r["loai"]): dict(r) for r in db.conn.execute("SELECT * FROM ngoai_le_canh_bao")}


def compute(db, today=None):
    """Trả về (danh_sách_cảnh_báo, danh_sách_thiếu_dữ_liệu, danh_sách_ngoại_lệ)."""
    today = today or datetime.date.today()
    decisions = _latest_decisions(db)
    exc = exceptions(db)
    chu_ky = ts.as_int("chu_ky_nang_luong")
    du_bi = ts.as_int("thoi_gian_du_bi_dang")
    bao_truoc = {"thang_cap": ts.as_int("bao_truoc_thang_cap"), "nang_luong": ts.as_int("bao_truoc_thang_cap"),
                 "nghi_huu": ts.as_int("bao_truoc_nghi_huu"), "dang": ts.as_int("bao_truoc_dang")}
    alerts, missing, excepted = [], [], []

    for cb in db.conn.execute("SELECT * FROM can_bo ORDER BY ho_ten COLLATE NOCASE"):
        cb = dict(cb)
        base = dict(can_bo_id=cb["id"], ma_cb=cb["ma_cb"], ho_ten=cb["ho_ten"], cap_bac=cb["cap_bac"] or "",
                    don_vi=", ".join(x for x in (cb.get("doi_to"), cb.get("don_vi")) if x))
        items = []   # (loại, hạn | None, chi tiết)
        decs = sorted(decisions.get(cb["id"], []), reverse=True)

        nh = ts.nien_han(cb["cap_bac"] or "")
        if nh:
            nxt, years = nh
            lenh = [d for d, cap in decs if cap == cb["cap_bac"]]
            if lenh:
                items.append(("thang_cap", add_years(lenh[0], years),
                              f"{cb['cap_bac']} → {nxt}: niên hạn {years:g} năm từ QĐ {lenh[0]:%d/%m/%Y}"))
            else:
                items.append(("thang_cap", None, f"Chưa có quyết định lên cấp bậc {cb['cap_bac']} để tính niên hạn"))
        if chu_ky > 0:
            if decs:
                items.append(("nang_luong", add_years(decs[0][0], chu_ky),
                              f"Chu kỳ {chu_ky} năm từ QĐ gần nhất {decs[0][0]:%d/%m/%Y}"))
        tuoi = ts.tuoi_nghi_huu(cb["cap_bac"] or "", cb["gioi_tinh"] or "")
        if tuoi:
            ns = parse(cb["ngay_sinh"])
            if ns:
                items.append(("nghi_huu", add_years(ns, tuoi),
                              f"Hạn tuổi {tuoi:g} ({cb['cap_bac']}, {cb['gioi_tinh'] or 'Nam'}), sinh {ns:%d/%m/%Y}"))
            else:
                items.append(("nghi_huu", None, "Chưa có ngày sinh"))
        vd = parse(cb["ngay_vao_dang"])
        if vd and not (cb["ngay_chuyen_dang_chinh_thuc"] or "").strip():
            items.append(("dang", add_months(vd, du_bi), f"Vào Đảng {vd:%d/%m/%Y}, dự bị {du_bi} tháng"))

        for loai, han, chi_tiet in items:
            row = dict(base, loai=loai, loai_text=LOAI[loai], chi_tiet=chi_tiet, ngoai_le="")
            e = exc.get((cb["id"], loai))
            if e:
                row["ngoai_le"] = e["ly_do"]
                if not e["han_moi"]:
                    excepted.append(dict(row, han="(không nhắc)", trang_thai="Ngoại lệ", con_lai=""))
                    continue
                han = parse(e["han_moi"]) or han
                row["chi_tiet"] = f"Hạn dời theo ngoại lệ ({e['han_moi']}). " + chi_tiet
                excepted.append(dict(row, han=e["han_moi"], trang_thai="Ngoại lệ", con_lai=""))
            if han is None:
                missing.append(dict(row, han="", trang_thai=THIEU, con_lai=""))
                continue
            days = (han - today).days
            if days < 0:
                status, con_lai = QUA_HAN, f"quá {-days} ngày"
            elif han <= add_months(today, bao_truoc[loai]):
                status, con_lai = SAP_DEN, f"còn {days} ngày"
            else:
                continue
            alerts.append(dict(row, han=han.strftime(FMT), han_date=han, trang_thai=status, con_lai=con_lai))
    alerts.sort(key=lambda r: r["han_date"])
    return alerts, missing, excepted


def set_exception(db, can_bo_id, loai, han_moi, ly_do, user):
    db.conn.execute(
        "INSERT INTO ngoai_le_canh_bao (can_bo_id, loai, han_moi, ly_do, nguoi_tao, thoi_gian) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(can_bo_id, loai) DO UPDATE SET han_moi=excluded.han_moi, ly_do=excluded.ly_do, "
        "nguoi_tao=excluded.nguoi_tao, thoi_gian=excluded.thoi_gian",
        (can_bo_id, loai, han_moi or None, ly_do, user, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.conn.commit()


def clear_exception(db, can_bo_id, loai):
    db.conn.execute("DELETE FROM ngoai_le_canh_bao WHERE can_bo_id=? AND loai=?", (can_bo_id, loai))
    db.conn.commit()
