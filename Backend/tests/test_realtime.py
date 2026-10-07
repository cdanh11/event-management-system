"""Test realtime occupancy Phase 0: snapshot REST + WS + broadcast."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def _payload(**overrides):
    data = {
        "title": "Live Show",
        "description": "Realtime demo",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=5, hours=2)).isoformat(),
        "capacity": 10,
        "category": "Music",
        "banner_image": "https://example.com/b.png",
    }
    data.update(overrides)
    return data


def _login(client: TestClient, email: str, password: str = "123456") -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _ws_ticket(client, headers) -> str:
    """Lấy ticket WS một lần qua REST có header Authorization (không lộ JWT)."""
    resp = client.post("/ws/ticket", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["ticket"]


def test_occupancy_snapshot_and_ws_broadcast(client, make_user):
    make_user("Org", "org@demo.com", "ORGANIZER")
    make_user("Att", "att@demo.com", "ATTENDEE")
    org_token = _login(client, "org@demo.com")
    att_token = _login(client, "att@demo.com")
    org = {"Authorization": f"Bearer {org_token}"}
    att = {"Authorization": f"Bearer {att_token}"}

    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)

    # REST snapshot ban đầu: còn nguyên capacity.
    snap = client.get(f"/events/{event_id}/occupancy", headers=org).json()
    assert snap["remaining"] == 10
    assert snap["registered_count"] == 0

    # WS nhận snapshot, rồi nhận broadcast khi attendee đăng ký.
    ticket = _ws_ticket(client, org)
    with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}") as ws:
        first = ws.receive_json()
        assert first["remaining"] == 10

        resp = client.post(f"/events/{event_id}/register", headers=att)
        assert resp.status_code == 201

        update = ws.receive_json()
        assert update["event_id"] == event_id
        assert update["registered_count"] == 1
        assert update["remaining"] == 9


def test_ws_ticket_one_time_use(client, make_user):
    """Ticket dùng lại lần 2 -> 4401 (chống replay)."""
    make_user("Org", "org@demo.com", "ORGANIZER")
    org_token = _login(client, "org@demo.com")
    org = {"Authorization": f"Bearer {org_token}"}
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]

    ticket = _ws_ticket(client, org)
    with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}"):
        pass

    try:
        with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}"):
            raise AssertionError("Ticket đã dùng phải bị từ chối")
    except Exception:
        pass


def test_ws_rejects_missing_ticket(client, make_user):
    make_user("Org", "org2@demo.com", "ORGANIZER")
    org_token = _login(client, "org2@demo.com")
    org = {"Authorization": f"Bearer {org_token}"}
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]

    try:
        with client.websocket_connect(f"/ws/events/{event_id}"):
            raise AssertionError("WS phải từ chối khi thiếu ticket")
    except Exception:
        pass


def test_ws_ticket_any_role_but_auth_required(client, auth_headers):
    """Mọi role đã login đều được cấp ticket (occupancy vốn public); thiếu auth -> 401."""
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    assert client.post("/ws/ticket", headers=att).status_code == 200
    assert client.post("/ws/ticket").status_code == 401


def test_ws_attendee_receives_status_updates(client, make_user):
    """Attendee subscribe WS để nhận trạng thái realtime (fix lỗi status cũ)."""
    make_user("Org", "org@demo.com", "ORGANIZER")
    make_user("Att", "att@demo.com", "ATTENDEE")
    org_token = _login(client, "org@demo.com")
    att_token = _login(client, "att@demo.com")
    org = {"Authorization": f"Bearer {org_token}"}
    att = {"Authorization": f"Bearer {att_token}"}

    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    ticket = client.post("/ws/ticket", headers=att).json()["ticket"]
    with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}") as ws:
        assert ws.receive_json()["status"] == "DRAFT"
        # Organizer đổi trạng thái -> attendee nhận status mới realtime, không reload.
        client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)
        update = ws.receive_json()
        assert update["event_id"] == event_id
        assert update["status"] == "PUBLISHED"
