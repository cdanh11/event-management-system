"""Bảo mật: băm mật khẩu (Argon2), JWT access token, refresh token.

- Mật khẩu: dùng pwdlib với thuật toán Argon2 (khuyến nghị OWASP).
- Access token: JWT HS256, ngắn hạn (mặc định 15 phút).
- Refresh token: chuỗi ngẫu nhiên 48 byte URL-safe; chỉ lưu *hash* SHA-256
  trong DB nên không có rủi ro nếu DB bị lộ.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from pwdlib import PasswordHash

from .config import settings

# Thuật toán băm mật khẩu: PasswordHash.recommended() chọn Argon2id.
pwd = PasswordHash.recommended()


def hash_password(value: str) -> str:
    """Băm mật khẩu trước khi lưu vào DB. Trả chuỗi có kèm tham số (phormat PHC)."""
    return pwd.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    """So sánh mật khẩu người dùng nhập với chuỗi băm đã lưu."""
    return pwd.verify(value, hashed)


def access_token(user_id: str, role: str) -> str:
    """Tạo JWT access token chứa ``sub`` (user id) và ``role``.

    ``exp`` được đặt trong claim để jwt tự kiểm tra hết hạn khi decode.
    """
    claims = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def decode_access(token: str) -> dict:
    """Giải mã + xác thực chữ ký JWT. Ném exception nếu token sai/hết hạn."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def new_refresh() -> str:
    """Sinh refresh token ngẫu nhiên (48 byte URL-safe)."""
    return secrets.token_urlsafe(48)


def digest(token: str) -> str:
    """Băm refresh token bằng SHA-256; lưu hash thay vì bản rõ trong DB."""
    return hashlib.sha256(token.encode()).hexdigest()