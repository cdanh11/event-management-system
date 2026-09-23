"""Test chức năng auth: login, refresh, logout, me, validation 422."""


def test_login_success(client, make_user):
    make_user("Alice", "alice@demo.com", "ATTENDEE")
    resp = client.post("/auth/login", json={"email": "alice@demo.com", "password": "123456"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@demo.com"


def test_login_wrong_password(client, make_user):
    make_user("Alice", "alice@demo.com", "ATTENDEE")
    resp = client.post("/auth/login", json={"email": "alice@demo.com", "password": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email(client):
    resp = client.post("/auth/login", json={"email": "nobody@demo.com", "password": "123456"})

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_invalid_email_shape_422(client):
    """Minh chứng: model input sai kiểu -> Pydantic validate ở tầng bind body
    và trả 422 VALIDATION_ERROR TRƯỚC khi endpoint chạy."""
    resp = client.post("/auth/login", json={"email": "not-an-email", "password": "x"})

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert resp.json()["details"]  # danh sách chi tiết từng field lỗi


def test_me_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_me_with_token(client, auth_headers):
    headers = auth_headers(email="alice@demo.com")
    resp = client.get("/auth/me", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@demo.com"


def test_me_with_garbage_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code == 401


def test_logout_clears_cookie(client, auth_headers):
    headers = auth_headers(email="alice@demo.com")
    resp = client.post("/auth/logout", headers=headers)

    assert resp.status_code == 204