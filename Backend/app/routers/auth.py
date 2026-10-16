"""Router: xác thực (login, refresh, logout, me).

Lưu ý async: các endpoint ở đây dùng SQLAlchemy **sync** Session nên khai báo
``def`` (sync) — FastAPI sẽ chạy chúng trong threadpool, không chặn event loop.
Chọn kiểu hàm theo thư viện đang gọi; không tự đổi I/O sync thành async.
"""
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.security import OAuth2PasswordRequestFormStrict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import RefreshToken, User, utcnow
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut, login_email
from ..security import access_token, digest, hash_password, new_refresh, verify_password
from ..serializers import to_user

router = APIRouter()


def _authenticate(email: str, password: str, db: Session) -> User:
    """Cùng một cơ chế verify cho JSON login và OAuth2 form; role luôn lấy từ DB."""
    from ..errors import api_error

    user = db.scalar(select(User).where(User.email == login_email(email)))
    if user is None or len(password) > 128 or not verify_password(password, user.password_hash):
        api_error(401, "INVALID_CREDENTIALS", "Username, email or password is incorrect")
    return user


@router.post("/auth/token", response_model=TokenOut, tags=["auth"])
def oauth2_token(response: Response, form: OAuth2PasswordRequestFormStrict = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow: username nhận tên tài khoản hoặc email; grant_type=password.

    Quyền dùng RBAC từ DB, không để scope do client gửi lên nâng quyền.
    JSON /auth/login vẫn được giữ để web client hiện tại không bị gián đoạn.
    """
    user = _authenticate(form.username, form.password, db)
    issue_refresh_cookie(response, db, user)
    db.commit()
    return _token_body(user, access_token(user.id, user.role))


def issue_refresh_cookie(response: Response, db: Session, user: User) -> None:
    """Sinh refresh token mới, lưu hash vào DB và đặt cookie HttpOnly cho client.

    Cookie HttpOnly (không cho JS đọc) + SameSite=lax giảm rủi ro XSS/CSRF.
    """
    raw = new_refresh()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest(raw),
            expires_at=utcnow() + timedelta(days=settings.refresh_days),
        )
    )
    db.flush()
    response.set_cookie(
        key="evently_refresh",
        value=raw,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_days * 86400,
    )


def _token_body(user: User, access: str) -> dict:
    """Body chuẩn của login/refresh: access token mới + thông tin user."""
    return {"access_token": access, "user": to_user(user)}


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    """Đăng nhập bằng username hoặc email + mật khẩu -> trả JWT và refresh cookie.

    Lưu ý: đây là endpoint **sync** hợp lệ vì công việc chính là truy vấn
    DB đồng bộ và verify mật khẩu — các lời gọi này chạy trong threadpool.
    Viết async def không tự chuyển các thao tác đó thành bất đồng bộ.
    """
    user = _authenticate(payload.email, payload.password, db)

    issue_refresh_cookie(response, db, user)
    db.commit()
    return _token_body(user, access_token(user.id, user.role))


@router.post("/auth/register", response_model=TokenOut, status_code=201, tags=["auth"])
def register_account(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    """Tự đăng ký tài khoản ATTENDEE mới + đăng nhập luôn (trả token + refresh cookie)."""
    from ..errors import api_error

    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        api_error(409, "EMAIL_TAKEN", "Email is already registered")

    user = User(
        name=payload.name.strip(),
        email=email,
        role="ATTENDEE",
        avatar_url="",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()
        issue_refresh_cookie(response, db, user)
        db.commit()
    except IntegrityError:
        # Hai request cùng email có thể vượt qua SELECT ở trên; UNIQUE là chốt cuối.
        db.rollback()
        api_error(409, "EMAIL_TAKEN", "Email is already registered")
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

    # Khoá dòng để một refresh token chỉ được đổi thành công một lần trên PostgreSQL.
    row = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == digest(evently_refresh))
        .with_for_update()
    )
    if row is None or row.revoked_at is not None or row.expires_at < utcnow():
        api_error(401, "UNAUTHORIZED", "Refresh token expired")

    user = db.get(User, row.user_id)
    row.revoked_at = utcnow()  # vô hiệu token vừa dùng

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
            row.revoked_at = utcnow()
        db.commit()
    response.delete_cookie("evently_refresh")


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)):
    """Thông tin user hiện tại (ứng dụng dependency current_user)."""
    return to_user(user)
