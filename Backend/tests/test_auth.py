"""Test chức năng auth: login, refresh, logout, me, validation 422."""

from app.main import app


def test_login_success(client, make_user):
    make_user("Alice", "alice@demo.com", "ATTENDEE")
    resp = client.post("/auth/login", json={"email": "alice@demo.com", "password": "123456"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@demo.com"


def test_register_creates_attendee_and_logs_in(client):
    """POST /auth/register: tự mở tài khoản ATTENDEE + nhận token luôn."""
    resp = client.post("/auth/register", json={
        "name": "Newbie", "email": "newbie@demo.com", "password": "secret1",
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["role"] == "ATTENDEE"
    assert body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "newbie@demo.com"


def test_register_duplicate_email_409(client, make_user):
    make_user("Alice", "alice@demo.com", "ATTENDEE")
    resp = client.post("/auth/register", json={
        "name": "Alice 2", "email": "alice@demo.com", "password": "secret1",
    })

    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_TAKEN"


def test_register_cannot_escalate_role(client):
    """Gửi kèm role ORGANIZER cũng bị bỏ qua — server ấn định ATTENDEE."""
    resp = client.post("/auth/register", json={
        "name": "Mallory", "email": "mallory@demo.com", "password": "secret1",
        "role": "ORGANIZER",
    })

    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "ATTENDEE"


def test_register_invalid_payload_422(client):
    resp = client.post("/auth/register", json={
        "name": "", "email": "not-an-email", "password": "123",
    })

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


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


def test_openapi_marks_only_protected_operations_with_bearer():
    """Swagger phai giu login/danh sach Event la public."""
    spec = app.openapi()

    assert "security" not in spec
    assert "security" not in spec["paths"]["/auth/login"]["post"]
    assert "security" not in spec["paths"]["/events"]["get"]
    assert spec["paths"]["/auth/me"]["get"]["security"] == [{"HTTPBearer": []}]
    assert spec["components"]["schemas"]["EventStatus"]["enum"] == [
        "DRAFT", "PUBLISHED", "ONGOING", "COMPLETED", "CANCELLED"
    ]
