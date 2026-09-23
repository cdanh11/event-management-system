"""Kết nối database (engine + session) và dependency ``get_db``.

- ``engine``: connection pool SQLAlchemy, tạo một lần lúc import.
- ``SessionLocal``: factory tạo Session mới cho mỗi "vùng làm việc".
- ``Base``: lớp cơ sở cho mọi model ORM, được Alembic dùng để đọc schema.
- ``get_db``: dependency dạng generator (yield) cung cấp 1 Session mỗi request.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# pool_pre_ping=True: kiểm tra kết nối còn sống trước khi mượn từ pool,
# tránh lỗi "connection stale" khi DB đóng kết nối tạm thời.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# autocommit=False: giao dịch do lập trình viên commit một cách tường minh.
# autoflush=False: kiểm soát thời điểm SQL được phát ra (rõ ràng hơn).
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Lớp cơ sở của mọi model; Alembic dựa vào đây để sinh migration."""


def get_db():
    """Dependency: mở 1 phiên (Session) cho mỗi request.

    Cách hoạt động của dependency dạng generator (yield):
      1. FastAPI gọi hàm này khi bắt đầu xử lý request.
      2. Phần trước ``yield`` chạy -> trả ra ``db`` cho endpoint.
      3. Sau khi endpoint trả response, code phía sau ``yield`` chạy
         (ở đây là ``db.close()``) -> giải phóng tài nguyên.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()