# -*- coding: utf-8 -*-
"""Bảng màu và kiểu dáng chung cho toàn phần mềm (tông đỏ - vàng kim, hiện đại)."""
import tkinter as tk
from tkinter import ttk

FONT = "Segoe UI"

C = dict(
    primary="#7A1B1B", primary_dark="#5E1414", primary_light="#93302F", gold="#F0B429",
    bg="#EEF1F6", sidebar="#2B2340", sidebar_hover="#3B2F57", sidebar_active="#F0B429",
    card="#FFFFFF", text="#1F2430", muted="#6B7280", border="#E1E5EC",
    green="#1F8A4C", green_h="#186F3D", blue="#2563EB", blue_h="#1D4ED8",
    red="#C62828", red_h="#A61E1E", gray="#667085", gray_h="#4B5468",
    zebra="#F7F5FA", sel="#FBE3C8", status="#E7EAF3",
    # Bảng màu nút bấm theo Fluent Design System (Microsoft) - dùng đúng mã
    # màu chuẩn của Fluent UI để nút bấm có cảm giác quen thuộc như phần
    # mềm Windows/Office: một màu nhấn (thương hiệu) duy nhất cho hành
    # động chính, còn lại trung tính, đỏ CHỈ dành cho xóa/hủy.
    neutral_lighter="#F3F2F1", neutral_light="#EDEBE9", neutral_border="#8A8886",
    neutral_border_hover="#7A1B1B",
    neutral_text="#201F1E", neutral_disabled_bg="#F3F2F1", neutral_disabled_fg="#A19F9D",
    danger="#C42B1C", danger_hover="#A80000", danger_pressed="#8E1600",
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
    st.configure("CardTitle.TLabel", background=C["card"], foreground=C["primary"], font=(FONT, 13, "bold"))
    st.configure("Section.TLabel", background=C["card"], foreground=C["primary_dark"], font=(FONT, 10, "bold"))
    st.configure("HeaderTitle.TLabel", background=C["primary"], foreground=C["gold"], font=(FONT, 16, "bold"))
    st.configure("HeaderUser.TLabel", background=C["primary"], foreground="white", font=(FONT, 10))
    st.configure("Error.TLabel", background=C["card"], foreground=C["red"], font=(FONT, 9))
    st.configure("Status.TLabel", background=C["status"], foreground=C["muted"], padding=(12, 5), font=(FONT, 9))
    st.configure("TEntry", padding=6, fieldbackground="white", bordercolor=C["border"])
    st.map("TEntry", bordercolor=[("focus", C["primary"])])
    st.configure("TCombobox", padding=5, fieldbackground="white", arrowsize=14)
    st.map("TCombobox", fieldbackground=[("readonly", "white"), ("disabled", "#EEF0F4")])
    st.configure("Card.TCheckbutton", background=C["card"])
    st.map("Card.TCheckbutton", background=[("active", C["card"])])
    st.configure("TNotebook", background=C["bg"], borderwidth=0)
    st.configure("TNotebook.Tab", padding=(14, 8), font=(FONT, 10, "bold"))
    st.map("TNotebook.Tab", background=[("selected", C["card"])], foreground=[("selected", C["primary"])])

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

    st.configure("Treeview", rowheight=27, background="white", fieldbackground="white",
                 foreground=C["text"], font=(FONT, 10), borderwidth=1, relief="solid", bordercolor=C["border"])
    st.configure("Treeview.Heading", background=C["primary"], foreground="white",
                 font=(FONT, 10, "bold"), padding=(6, 8), relief="solid", borderwidth=1,
                 bordercolor=C["primary_dark"])
    st.map("Treeview.Heading", background=[("active", C["primary_dark"])])
    st.map("Treeview", background=[("selected", C["sel"])], foreground=[("selected", C["text"])])
    # 'clam' không hỗ trợ kẻ ô lưới từng ô như Excel; đây là mức viền rõ
    # nhất mà ttk.Treeview cho phép - viền ngoài rõ nét + đường phân cách
    # tiêu đề, kết hợp màu xen kẽ dòng (zebra) để dễ đọc theo hàng.

    # Nút điều hướng ở thanh bên (sidebar)
    st.configure("Nav.TButton", background=C["sidebar"], foreground="#E7E3F5",
                 borderwidth=0, anchor="w", padding=(16, 10), font=(FONT, 10, "bold"),
                 wraplength=200)
    st.map("Nav.TButton", background=[("active", C["sidebar_hover"])])
    st.configure("NavActive.TButton", background=C["sidebar_hover"], foreground=C["gold"],
                 borderwidth=0, anchor="w", padding=(16, 10), font=(FONT, 10, "bold"),
                 wraplength=200)
    st.map("NavActive.TButton", background=[("active", C["sidebar_hover"])])
    st.configure("Sidebar.TFrame", background=C["sidebar"])
    st.configure("SidebarTitle.TLabel", background=C["sidebar"], foreground=C["gold"], font=(FONT, 12, "bold"))
    st.configure("SidebarMuted.TLabel", background=C["sidebar"], foreground="#B9B2CF", font=(FONT, 8))
    return st
