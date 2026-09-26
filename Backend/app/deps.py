"""Dependencies chia sẻ: xác thực (current_user) và phân quyền (require).

FastAPI nạp dependency qua ``Depends(...)`` trong tham số hàm; ở đây có 2
tầng:
  - ``current_user``: xác thực "bạn là ai" (401 nếu thiếu/sai token).
  - ``require(*roles)``: kiểm tra "bạn có được phép không" theo role (403).
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_access

# auto_error=False để HTTPBearer KHÔNG tự trả 403 khi thiếu header; chúng ta
# tự xử lý để trả đúng mã 401 (chưa xác thực) — rõ ràng về ngữ nghĩa hơn.
bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: xác thực access token và nạp user hiện tại.

    Dependency graph (được ghi rõ cho báo cáo):
        current_user
         ├── HTTPBearer (đọc header ``Authorization: Bearer <token>``)
         └── get_db (mở Session từ SessionLocal, đóng sau request)
         Sau đó: decode_access(token) -> db.get(User, sub)
    """
    if credentials is None:
        raise HTTPException(
            401, detail={"code": "UNAUTHORIZED", "message": "Authentication required"}
        )

    try:
        claims = decode_access(credentials.credentials)
        user = db.get(User, claims["sub"]) #sub = uID được định nghĩa trong claim
    except Exception:
        user = None

    if user is None:
        raise HTTPException(
            401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"},
        )
    return user


def require(*roles: str):
    """Factory trả về dependency kiểm tra role.

    Cách dùng: ``user: User = Depends(require("ORGANIZER"))``.
    Dependency này *nạp từ trong* current_user, tạo thành chuỗi dependency:
        require(...) -> current_user -> {HTTPBearer, get_db}
    """
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                403,
                detail={"code": "FORBIDDEN", "message": "Insufficient permission"},
            )
        return user

    return check