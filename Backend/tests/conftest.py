"""Cấu hình pytest: fixture chạy app với database SQLite trong bộ nhớ.

Dùng **dependency override** để thay ``get_db`` (PostgreSQL thật) bằng session
SQLite - đúng kỹ thuật "Dependency override phục vụ test" trong yêu cầu:
  app.dependency_overrides[get_db] = override
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

# StaticPool: tái dùng MỘT kết nối duy nhất - phải dùng cho SQLite ":memory:"
# (nếu không, mỗi connection tạo một database rỗng riêng biệt).
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db():
    """Tạo lại toàn bộ bảng trước mỗi test và xóa sau khi test xong."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db):
    """TestClient dùng app thật nhưng thay get_db bằng session SQLite."""

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    """Factory tạo user trực tiếp vào DB và trả về bản ghi."""

    def _create(name: str, email: str, role: str, password: str = "123456") -> User:
        user = User(
            name=name,
            email=email,
            role=role,
            avatar_url="",
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        return user

    return _create


@pytest.fixture()
def auth_headers(client, make_user):
    """Factory: tạo user + đăng nhập qua API thật -> trả Authorization header.

    Token này được sinh và xác thực bằng đúng luồng của ứng dụng
    (POST /auth/login), không "giả token" thủ công.
    """

    def _headers(
        name: str = "Demo User",
        email: str = "attendee@demo.com",
        role: str = "ATTENDEE",
        password: str = "123456",
    ) -> dict:
        make_user(name, email, role, password)
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"login failed: {resp.text}"
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _headers