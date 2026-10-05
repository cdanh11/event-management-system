"""Test đăng ký/hủy (vòng đời Register–Cancel) và vé."""

from datetime import datetime, timedelta


def _payload(**overrides):
    data = {
        "title": "Workshop",
        "description": "Hands-on day",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=5, hours=4)).isoformat(),
        "capacity": 2,
        "category": "Education",
        "banner_image": "https://example.com/b.png",
    }
    data.update(overrides)
    return data


def _published_event(client, org_headers) -> str:
    event_id = client.post("/events", json=_payload(), headers=org_headers).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org_headers)
    return event_id


def test_register_returns_registration_and_ticket(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    resp = client.post(f"/events/{event_id}/register", headers=att)

    assert resp.status_code == 201
    body = resp.json()
    assert body["registration"]["status"] == "REGISTERED"
    assert body["ticket"]["ticket_code"].startswith("EV-")
    assert body["ticket"]["status"] == "VALID"


def test_register_sends_ticket_in_background(client, auth_headers, monkeypatch):
    """Phase 2: register trả 201 ngay + task nền gửi vé/QR (không cần SMTP thật)."""
    import app.routers.registrations as reg_router

    calls: list[tuple] = []

    async def fake_send(to_email, event_title, ticket_code, qr_value):
        calls.append((to_email, event_title, ticket_code, qr_value))
        return ticket_code

    monkeypatch.setattr(reg_router, "send_ticket_email", fake_send)

    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    resp = client.post(f"/events/{event_id}/register", headers=att)

    assert resp.status_code == 201
    assert len(calls) == 1  # task nền đã chạy sau response
    to_email, event_title, ticket_code, _qr = calls[0]
    assert to_email == "att@demo.com"
    assert event_title == "Workshop"
    assert ticket_code == resp.json()["ticket"]["ticket_code"]


def test_register_past_event_400(client, auth_headers, db):
    """Event PUBLISHED nhưng start_time đã qua -> 400 EVENT_STARTED."""
    from app.models import Event

    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    db.query(Event).filter_by(id=event_id).update({
        "start_time": datetime.now() - timedelta(days=1),
        "end_time": datetime.now() - timedelta(hours=20),
    })
    db.commit()

    resp = client.post(f"/events/{event_id}/register", headers=att)
    assert resp.status_code == 400
    assert resp.json()["code"] == "EVENT_STARTED"


def test_register_duplicate_409(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    assert client.post(f"/events/{event_id}/register", headers=att).status_code == 201
    assert client.post(f"/events/{event_id}/register", headers=att).status_code == 409


def test_register_event_full_409(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    event_id = _published_event(client, org)  # capacity = 2

    att1 = auth_headers(role="ATTENDEE", email="att1@demo.com")
    att2 = auth_headers(role="ATTENDEE", email="att2@demo.com")
    att3 = auth_headers(role="ATTENDEE", email="att3@demo.com")

    assert client.post(f"/events/{event_id}/register", headers=att1).status_code == 201
    assert client.post(f"/events/{event_id}/register", headers=att2).status_code == 201
    resp = client.post(f"/events/{event_id}/register", headers=att3)
    assert resp.status_code == 409
    assert resp.json()["code"] == "EVENT_FULL"


def test_register_draft_event_400(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]  # DRAFT

    resp = client.post(f"/events/{event_id}/register", headers=att)
    assert resp.status_code == 400
    assert resp.json()["code"] == "REGISTRATION_CLOSED"


def test_cancel_registration(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    reg_id = client.post(f"/events/{event_id}/register", headers=att).json()["registration"]["id"]

    # Biết registered_count trước khi hủy.
    before = client.get(f"/events/{event_id}").json()["registered_count"]

    resp = client.post(f"/registrations/{reg_id}/cancel", headers=att)

    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
    # Trả lại 1 slot cho sự kiện.
    after = client.get(f"/events/{event_id}").json()["registered_count"]
    assert after == before - 1
    # Ticket tương ứng cũng bị hủy.
    ticket = client.get(f"/registrations/{reg_id}/ticket", headers=att).json()
    assert ticket["status"] == "CANCELLED"


def test_cancel_someone_elses_registration_403(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    other = auth_headers(role="ATTENDEE", email="att2@demo.com")
    event_id = _published_event(client, org)

    reg_id = client.post(f"/events/{event_id}/register", headers=att).json()["registration"]["id"]

    resp = client.post(f"/registrations/{reg_id}/cancel", headers=other)
    assert resp.status_code == 403


def test_my_registrations(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = _published_event(client, org)

    client.post(f"/events/{event_id}/register", headers=att)
    resp = client.get("/registrations/me", headers=att)

    assert resp.status_code == 200
    assert len(resp.json()) == 1