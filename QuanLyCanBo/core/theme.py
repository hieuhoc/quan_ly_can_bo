# -*- coding: utf-8 -*-
"""Bảng màu và kiểu dáng chung cho toàn phần mềm (đỏ CAND trên nền trung tính)."""
import tkinter as tk
from tkinter import ttk

FONT = "Segoe UI"

C = dict(
    # Màu thương hiệu: đỏ CAND trầm, dùng tiết chế cho hành động chính và
    # điểm nhấn; phần còn lại là thang xám trung tính để giao diện gọn, sạch.
    primary="#A11D21", primary_dark="#7F1518", primary_light="#C0282D", primary_soft="#FBEDED",
    gold="#C99A2E",
    bg="#F3F5F8", card="#FFFFFF", text="#1F2937", muted="#6B7280", border="#E4E7EC",
    line="#EEF0F3",
    # Thanh bên tối (slate) - chữ sáng, mục đang chọn tô màu thương hiệu.
    sidebar="#1C2330", sidebar_hover="#2A3342", sidebar_active="#A11D21",
    sidebar_text="#C7CDD8", sidebar_muted="#7D8696", sidebar_line="#2E3746",
    header="#FFFFFF",
    green="#15803D", green_h="#166534", blue="#1D4ED8", blue_h="#1E40AF",
    red="#B91C1C", red_h="#991B1B", gray="#667085", gray_h="#4B5468",
    zebra="#FAFBFC", sel="#FCE8E8", hover_row="#F5F7FA", status="#FFFFFF",
    table_head="#F3F4F6", table_head_text="#374151",
    # Nút bấm kiểu Fluent: một màu nhấn duy nhất cho hành động chính, còn
    # lại trung tính; đỏ tươi CHỈ dành cho xóa.
    neutral_lighter="#F3F4F6", neutral_light="#E5E7EB", neutral_border="#D0D5DD",
    neutral_border_hover="#A11D21",
    neutral_text="#1F2937", neutral_disabled_bg="#F3F4F6", neutral_disabled_fg="#A0A6B1",
    danger="#C62828", danger_hover="#A61E1E", danger_pressed="#8E1600",
)


def center(win, w=None, h=None):
    win.update_idletasks()
    w = min(w or win.winfo_reqwidth(), win.winfo_screenwidth() - 30)
    h = min(h or win.winfo_reqheight(), win.winfo_screenheight() - 80)
    x = max((win.winfo_screenwidth() - w) // 2, 0)
    y = max((win.winfo_screenheight() - h) // 2 - 20, 0)
    win.geometry(f"{w}x{h}+{x}+{y}")


def make_card(parent, padding=16):
    outer = tk.Frame(parent, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
    inner = ttk.Frame(outer, style="Card.TFrame", padding=padding)
    inner.pack(fill="both", expand=True)
    return outer, inner


def draw_shield(canvas, size, color=None):
    """Vẽ biểu tượng khiên (logo phần mềm) lên Canvas - không phụ thuộc
    font emoji của máy nên hiển thị giống nhau trên mọi máy Windows."""
    color = color or C["primary"]
    s = size / 38.0
    pts = [19, 2, 34, 7, 34, 18, 31, 27, 19, 36, 7, 27, 4, 18, 4, 7]
    canvas.create_polygon([p * s for p in pts], fill=color, outline="", smooth=False)
    star = [19, 10, 21.2, 16, 27.5, 16, 22.4, 19.8, 24.4, 26, 19, 22.2, 13.6, 26, 15.6, 19.8, 10.5, 16, 16.8, 16]
    canvas.create_polygon([p * s for p in star], fill=C["gold"], outline="")


def page_rule(parent):
    """Đường kẻ mảnh ngăn tiêu đề trang với nội dung bên dưới."""
    rule = tk.Frame(parent, height=1, bg=C["border"])
    rule.pack(fill="x", pady=(10, 12))
    return rule


def setup_style(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=C["bg"])
    st.configure(".", font=(FONT, 10), background=C["bg"], foreground=C["text"])
    st.configure("TFrame", background=C["bg"])
    st.configure("Card.TFrame", background=C["card"])
    st.configure("TLabel", background=C["bg"])
    st.configure("Card.TLabel", background=C["card"], foreground=C["text"])
    st.configure("CardMuted.TLabel", background=C["card"], foreground=C["muted"], font=(FONT, 9))
    st.configure("CardTitle.TLabel", background=C["card"], foreground=C["text"], font=(FONT, 14, "bold"))
    st.configure("Section.TLabel", background=C["card"], foreground=C["primary"], font=(FONT, 10, "bold"))
    st.configure("HeaderTitle.TLabel", background=C["header"], foreground=C["primary"], font=(FONT, 15, "bold"))
    st.configure("HeaderUser.TLabel", background=C["header"], foreground=C["text"], font=(FONT, 10))
    st.configure("Error.TLabel", background=C["card"], foreground=C["red"], font=(FONT, 9))
    st.configure("Status.TLabel", background=C["status"], foreground=C["muted"], padding=(14, 6), font=(FONT, 9))
    st.configure("TEntry", padding=(8, 6), fieldbackground="white", bordercolor=C["neutral_border"],
                 lightcolor=C["neutral_border"], darkcolor=C["neutral_border"])
    st.map("TEntry", bordercolor=[("focus", C["primary"])], lightcolor=[("focus", C["primary"])],
           darkcolor=[("focus", C["primary"])])
    st.configure("TCombobox", padding=(6, 5), fieldbackground="white", arrowsize=13,
                 bordercolor=C["neutral_border"], lightcolor=C["neutral_border"], darkcolor=C["neutral_border"],
                 background="white", arrowcolor=C["muted"])
    st.map("TCombobox", fieldbackground=[("readonly", "white"), ("disabled", C["neutral_lighter"])],
           bordercolor=[("focus", C["primary"])], lightcolor=[("focus", C["primary"])],
           darkcolor=[("focus", C["primary"])], background=[("active", C["neutral_lighter"])])
    st.configure("Card.TCheckbutton", background=C["card"], indicatorbackground="white",
                 indicatorforeground=C["primary"], bordercolor=C["neutral_border"])
    st.map("Card.TCheckbutton", background=[("active", C["card"])],
           indicatorbackground=[("selected", C["primary_soft"])])
    st.configure("TNotebook", background=C["bg"], borderwidth=0)
    st.configure("TNotebook.Tab", padding=(16, 8), font=(FONT, 10, "bold"), background=C["neutral_lighter"],
                 foreground=C["muted"], bordercolor=C["border"])
    st.map("TNotebook.Tab", background=[("selected", C["card"])], foreground=[("selected", C["primary"])])
    st.configure("TScrollbar", background=C["neutral_light"], troughcolor=C["bg"], bordercolor=C["bg"],
                 lightcolor=C["neutral_light"], darkcolor=C["neutral_light"], arrowcolor=C["muted"],
                 gripcount=0)
    st.map("TScrollbar", background=[("active", C["neutral_border"])])

    def button(name, bg, hover, fg="white", pad=(12, 8), size=10):
        st.configure(name, background=bg, foreground=fg, borderwidth=0, focusthickness=0,
                     padding=pad, font=(FONT, size, "bold"))
        st.map(name, background=[("disabled", "#CBD0D8"), ("active", hover)],
               foreground=[("disabled", "#F3F4F6")])

    button("Primary.TButton", C["primary"], C["primary_dark"])
    button("Login.TButton", C["primary"], C["primary_dark"], pad=(12, 11), size=11)
    button("Success.TButton", C["green"], C["green_h"])
    button("Info.TButton", C["blue"], C["blue_h"])
    button("Danger.TButton", C["red"], C["red_h"])
    button("Neutral.TButton", C["gray"], C["gray_h"])
    button("Header.TButton", C["primary_dark"], C["primary_light"], pad=(12, 7))

    st.configure("Treeview", rowheight=30, background="white", fieldbackground="white",
                 foreground=C["text"], font=(FONT, 10), borderwidth=0)
    st.configure("Treeview.Heading", background=C["table_head"], foreground=C["table_head_text"],
                 font=(FONT, 9, "bold"), padding=(8, 8), relief="flat", borderwidth=0)
    st.map("Treeview.Heading", background=[("active", C["neutral_light"])])
    st.map("Treeview", background=[("selected", C["sel"])], foreground=[("selected", C["text"])])

    # Nút điều hướng ở thanh bên (sidebar)
    nav = dict(borderwidth=0, anchor="w", padding=(14, 9), font=(FONT, 10), focusthickness=0)
    st.configure("Nav.TButton", background=C["sidebar"], foreground=C["sidebar_text"], **nav)
    st.map("Nav.TButton", background=[("active", C["sidebar_hover"])], foreground=[("active", "white")])
    st.configure("NavActive.TButton", background=C["sidebar_active"], foreground="white",
                 **dict(nav, font=(FONT, 10, "bold")))
    st.map("NavActive.TButton", background=[("active", C["sidebar_active"])])
    st.configure("Sidebar.TFrame", background=C["sidebar"])
    st.configure("SidebarTitle.TLabel", background=C["sidebar"], foreground="white", font=(FONT, 12, "bold"))
    st.configure("SidebarMuted.TLabel", background=C["sidebar"], foreground=C["sidebar_muted"], font=(FONT, 8))
    return st
