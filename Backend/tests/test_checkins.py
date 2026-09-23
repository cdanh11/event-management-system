"""Test check-in: xác thực mã vé, phân quyền staff, cơ chế "dùng một lần"."""

from datetime import datetime, timedelta


def _payload(**overrides):
    data = {
        "title": "Live Concert",
        "description": "Evening show",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=2)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 10,
        "category": "Music",
        "banner_image": "https://example.com/c.png",
    }
    data.update(overrides)
    return data


def _ongoing_event_with_ticket(client, org, staff, att):
    """Tạo event PUBLISHED -> attendee đăng ký (có ticket) -> chuyển ONGOING -> gán staff.

    Đăng ký phải diễn ra khi event còn PUBLISHED (register chỉ mở ở trạng thái đó).
    """
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)

    # Đăng ký trước khi event chuyển ONGOING.
    ticket_code = client.post(f"/events/{event_id}/register", headers=att).json()["ticket"]["ticket_code"]

    client.post(f"/events/{event_id}/transition", json={"status": "ONGOING"}, headers=org)

    staff_id = client.get("/auth/me", headers=staff).json()["id"]
    client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)
    return event_id, ticket_code


def test_checkin_success(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    event_id, ticket_code = _ongoing_event_with_ticket(client, org, staff, att)

    resp = client.post("/checkins", json={"ticket_code": ticket_code}, headers=staff)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "SUCCESS"
    assert body["event_id"] == event_id


def test_checkin_same_ticket_twice_409(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    _, ticket_code = _ongoing_event_with_ticket(client, org, staff, att)

    assert client.post("/checkins", json={"ticket_code": ticket_code}, headers=staff).status_code == 201
    resp = client.post("/checkins", json={"ticket_code": ticket_code}, headers=staff)
    assert resp.status_code == 409
    assert resp.json()["code"] == "TICKET_ALREADY_USED"


def test_checkin_invalid_ticket_404(client, auth_headers):
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    resp = client.post("/checkins", json={"ticket_code": "NOT-A-CODE"}, headers=staff)

    assert resp.status_code == 404
    assert resp.json()["code"] == "INVALID_TICKET"


def test_checkin_requires_assignment_403(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    other_staff = auth_headers(role="STAFF", email="staff2@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    _, ticket_code = _ongoing_event_with_ticket(client, org, staff, att)

    # staff2 chưa được gán vào event này -> 403
    resp = client.post("/checkins", json={"ticket_code": ticket_code}, headers=other_staff)
    assert resp.status_code == 403


def test_checkin_requires_staff_role(client, auth_headers):
    """ATTENDEE không có quyền gọi check-in -> 403 do phân quyền (dep trước khi kiểm tra vé)."""
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    resp = client.post("/checkins", json={"ticket_code": "ANY"}, headers=att)
    assert resp.status_code == 403


def test_assign_staff_duplicate_409(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    event_id, _ = _ongoing_event_with_ticket(client, org, staff, att)

    staff_id = client.get("/auth/me", headers=staff).json()["id"]
    resp = client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)
    assert resp.status_code == 409
    assert resp.json()["code"] == "ALREADY_ASSIGNED"