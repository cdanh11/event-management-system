"""Router: xác thực (login, refresh, logout, me).

Lưu ý async: các endpoint ở đây dùng SQLAlchemy **sync** Session nên khai báo
``def`` (sync) — FastAPI sẽ chạy chúng trong threadpool, không chặn event loop.
Đây chính là "biết khi nào KHÔNG cần async".
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import RefreshToken, User
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import access_token, digest, new_refresh, verify_password
from ..serializers import to_user

router = APIRouter()


def issue_refresh_cookie(response: Response, db: Session, user: User) -> None:
    """Sinh refresh token mới, lưu hash vào DB và đặt cookie HttpOnly cho client.

    Cookie HttpOnly (không cho JS đọc) + SameSite=lax giảm rủi ro XSS/CSRF.
    """
    raw = new_refresh()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest(raw),
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_days),
        )
    )
    db.flush()
    response.set_cookie(
        key="evently_refresh",
        value=raw,
        httponly=True,
        secure=False,  # bật True khi chạy HTTPS production
        samesite="lax",
        max_age=settings.refresh_days * 86400,
    )


def _token_body(user: User, access: str) -> dict:
    """Body chuẩn của login/refresh: access token mới + thông tin user."""
    return {"access_token": access, "user": to_user(user)}


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    """Đăng nhập bằng email + mật khẩu -> trả access token và đặt refresh cookie.

    Lưu ý: đây là endpoint **sync** hợp lệ vì công việc chính là truy vấn
    DB đồng bộ (verify) và tạo JWT (thuần CPU) — không có gì để await.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if user is None or not verify_password(payload.password, user.password_hash):
        from ..errors import api_error

        api_error(401, "INVALID_CREDENTIALS", "Email or password is incorrect")

    issue_refresh_cookie(response, db, user)
    db.commit()
    return _token_body(user, access_token(user.id, user.role))


@router.post("/auth/refresh", response_model=TokenOut, tags=["auth"])
def refresh(
    response: Response,
    evently_refresh: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Đổi refresh token (xoay vòng): vô hiệu token cũ, cấp cặp mới."""
    from ..errors import api_error

    if evently_refresh is None:
        api_error(401, "UNAUTHORIZED", "Refresh token missing")

    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest(evently_refresh)))
    if row is None or row.revoked_at is not None or row.expires_at < datetime.utcnow():
        api_error(401, "UNAUTHORIZED", "Refresh token expired")

    user = db.get(User, row.user_id)
    row.revoked_at = datetime.utcnow()  # vô hiệu token vừa dùng

    issue_refresh_cookie(response, db, user)
    db.commit()
    return _token_body(user, access_token(user.id, user.role))


@router.post("/auth/logout", status_code=204, tags=["auth"])
def logout(
    response: Response,
    evently_refresh: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Đăng xuất: thu hồi refresh token (nếu có) và xóa cookie."""
    if evently_refresh:
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest(evently_refresh)))
        if row is not None:
            row.revoked_at = datetime.utcnow()
        db.commit()
    response.delete_cookie("evently_refresh")


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)):
    """Thông tin user hiện tại (ứng dụng dependency current_user)."""
    return to_user(user)