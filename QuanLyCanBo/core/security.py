# -*- coding: utf-8 -*-
"""Tiện ích bảo mật: băm mật khẩu (PBKDF2) và mã thông báo ghi nhớ đăng nhập."""
import hashlib
import hmac
import os
import re

PBKDF2_ITER = 200_000


def hash_password(password, salt=None):
    salt = salt if salt is not None else os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)
    return salt.hex(), h.hex()


def verify_password(password, salt_hex, hash_hex):
    _, h = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(h, hash_hex)


def check_password_policy(pw):
    if len(pw) < 8:
        return "Mật khẩu phải có ít nhất 8 ký tự."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Mật khẩu phải gồm cả chữ và số."
    return None
