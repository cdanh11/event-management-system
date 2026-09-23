"""Test sự kiện: create, reschedule, states, notify (async)."""

from datetime import datetime, timedelta


def _event_payload(**overrides) -> dict:
    payload = {
        "title": "Tech Meetup",
        "description": "A demo event",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=3)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=3, hours=2)).isoformat(),
        "capacity": 20,
        "category": "Technology",
        "banner_image": "https://example.com/banner.png",
    }
    payload.update(overrides)
    return payload


def test_create_event_requires_organizer(client, auth_headers):
    headers = auth_headers(role="ATTENDEE")
    resp = client.post("/events", json=_event_payload(), headers=headers)

    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_create_event_success(client, auth_headers):
    headers = auth_headers(role="ORGANIZER", email="org@demo.com")
    resp = client.post("/events", json=_event_payload(), headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "DRAFT"
    assert body["title"] == "Tech Meetup"
    assert body["registered_count"] == 0


def test_create_event_invalid_time(client, auth_headers):
    headers = auth_headers(role="ORGANIZER", email="org@demo.com")
    # start sau end -> INVALID_EVENT_TIME
    resp = client.post(
        "/events",
        json=_event_payload(
            start_time=(datetime.now() + timedelta(days=3)).isoformat(),
            end_time=(datetime.now() + timedelta(days=1)).isoformat(),
        ),
        headers=headers,
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_EVENT_TIME"


def test_create_event_invalid_payload_422(client, auth_headers):
    headers = auth_headers(role="ORGANIZER", email="org@demo.com")
    resp = client.post("/events", json={"title": ""}, headers=headers)  # thiếu field

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_full_lifecycle_create_to_complete(client, auth_headers):
    """Create -> Publish -> Ongoing -> Complete (tổ hợp với Reschedule)."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")

    # 1. Create
    resp = client.post("/events", json=_event_payload(), headers=org)
    event_id = resp.json()["id"]

    # 2. Publish
    resp = client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)
    assert resp.json()["status"] == "PUBLISHED"

    # 3. Reschedule (PATCH): dời lịch + đổi tên
    new_start = (datetime.now() + timedelta(days=10)).isoformat()
    new_end = (datetime.now() + timedelta(days=10, hours=3)).isoformat()
    resp = client.patch(
        f"/events/{event_id}",
        json={"title": "Tech Meetup v2", "start_time": new_start, "end_time": new_end},
        headers=org,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Tech Meetup v2"
    assert resp.json()["start_time"].startswith(new_start[:19])

    # 4. Ongoing
    resp = client.post(f"/events/{event_id}/transition", json={"status": "ONGOING"}, headers=org)
    assert resp.json()["status"] == "ONGOING"

    # 5. Complete
    resp = client.post(f"/events/{event_id}/transition", json={"status": "COMPLETED"}, headers=org)
    assert resp.json()["status"] == "COMPLETED"


def test_invalid_transition(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=org).json()["id"]

    # DRAFT -> COMPLETED là state chuyển bất hợp lệ
    resp = client.post(f"/events/{event_id}/transition", json={"status": "COMPLETED"}, headers=org)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_TRANSITION"


def test_reschedule_requires_owner(client, auth_headers):
    org1 = auth_headers(role="ORGANIZER", email="org1@demo.com")
    org2 = auth_headers(role="ORGANIZER", email="org2@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=org1).json()["id"]

    resp = client.patch(f"/events/{event_id}", json={"title": "Hijack"}, headers=org2)
    assert resp.status_code == 403


def test_notify_async_endpoint(client, auth_headers, make_user):
    """POST /events/{id}/notify: endpoint async gửi thông báo cho attendee."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)

    att = auth_headers(role="ATTENDEE", email="attendee@demo.com")
    client.post(f"/events/{event_id}/register", headers=att)

    resp = client.post(f"/events/{event_id}/notify", headers=org)

    assert resp.status_code == 200
    body = resp.json()
    assert body["event_id"] == event_id
    assert body["emails_sent"] == 1  # đúng 1 attendee đã đăng ký
    assert body["mode"] in {"webhook", "simulated"}