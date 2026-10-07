"""Test chuyển trạng thái tự động theo giờ + mail hủy + staff history + tạo staff."""

from datetime import datetime, timedelta

from app.services.lifecycle import sweep_due_events


def _payload(**overrides):
    data = {
        "title": "Auto Show",
        "description": "Auto lifecycle demo",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=5, hours=2)).isoformat(),
        "capacity": 10,
        "category": "Music",
        "banner_image": "https://example.com/a.png",
    }
    data.update(overrides)
    return data


def test_sweep_opens_started_before_start(db):
    """PUBLISHED tới (start - 15 phút) -> STARTED tự động."""
    from app.models import Event, User

    org = User(name="Org", email="org@demo.com", role="ORGANIZER",
               avatar_url="", password_hash="x")
    db.add(org)
    db.flush()
    event = Event(
        organizer_id=org.id, title="Soon", description="d", location="HCMC",
        start_time=datetime.now() + timedelta(minutes=10),
        end_time=datetime.now() + timedelta(hours=2),
        capacity=10, registered_count=0, status="PUBLISHED",
        category="Music", banner_url="",
    )
    db.add(event)
    db.commit()

    from tests.conftest import TestSession
    payloads = sweep_due_events(session_factory=TestSession)

    assert len(payloads) == 1
    assert payloads[0]["event_id"] == event.id
    db.refresh(event)
    assert event.status == "STARTED"


def test_sweep_completes_past_end(db):
    """STARTED quá end_time -> COMPLETED tự động; event tương lai giữ nguyên."""
    from app.models import Event, User
    from tests.conftest import TestSession

    org = User(name="Org", email="org@demo.com", role="ORGANIZER",
               avatar_url="", password_hash="x")
    db.add(org)
    db.flush()
    old = Event(
        organizer_id=org.id, title="Old", description="d", location="HCMC",
        start_time=datetime.now() - timedelta(hours=3),
        end_time=datetime.now() - timedelta(hours=1),
        capacity=10, registered_count=0, status="STARTED",
        category="Music", banner_url="",
    )
    future = Event(
        organizer_id=org.id, title="Future", description="d", location="HCMC",
        start_time=datetime.now() + timedelta(days=5),
        end_time=datetime.now() + timedelta(days=5, hours=2),
        capacity=10, registered_count=0, status="PUBLISHED",
        category="Music", banner_url="",
    )
    db.add_all([old, future])
    db.commit()

    payloads = sweep_due_events(session_factory=TestSession)
    by_id = {p["event_id"]: p for p in payloads}

    assert old.id in by_id and by_id[old.id]["status"] == "COMPLETED"
    assert future.id not in by_id
    db.refresh(old)
    assert old.status == "COMPLETED"


def test_cancel_sends_mail_background(client, auth_headers, monkeypatch):
    """Transition sang CANCELLED lên lịch mail hủy cho attendee (BackgroundTasks)."""
    import app.services.notifier as notifier

    calls: list[tuple] = []

    async def fake_notify(title, emails, subject="update"):
        calls.append((title, emails, subject))
        return len(emails)

    monkeypatch.setattr(notifier, "notify_attendees", fake_notify)

    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)
    client.post(f"/events/{event_id}/register", headers=att)

    resp = client.post(f"/events/{event_id}/transition", json={"status": "CANCELLED"}, headers=org)

    assert resp.status_code == 200
    assert len(calls) == 1
    assert calls[0][2] == "cancelled"
    assert calls[0][1] == ["att@demo.com"]


def test_staff_checkin_history(client, auth_headers):
    """Staff xem lịch sử check-in event được gán (tên + mã vé + giờ)."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")

    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)
    ticket_code = client.post(f"/events/{event_id}/register", headers=att).json()["ticket"]["ticket_code"]
    client.post(f"/events/{event_id}/transition", json={"status": "STARTED"}, headers=org)
    staff_id = client.get("/auth/me", headers=staff).json()["id"]
    client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)
    client.post("/checkins", json={"ticket_code": ticket_code}, headers=staff)

    resp = client.get(f"/events/{event_id}/checkins", headers=staff)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    row = resp.json()[0]
    assert row["ticket_code"] == ticket_code
    assert row["attendee_name"] == "Demo User"
    assert row["checked_in_at"]

    # Attendee không được xem lịch sử event
    assert client.get(f"/events/{event_id}/checkins", headers=att).status_code == 403


def test_organizer_creates_staff(client, auth_headers):
    """Organizer tạo tài khoản STAFF + gán vào event."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")

    resp = client.post("/users/staff", json={
        "name": "New Staff", "email": "newstaff@demo.com", "password": "secret1",
    }, headers=org)

    assert resp.status_code == 201
    assert resp.json()["role"] == "STAFF"

    dup = client.post("/users/staff", json={
        "name": "New Staff", "email": "newstaff@demo.com", "password": "secret1",
    }, headers=org)
    assert dup.status_code == 409
