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


def test_create_event_end_before_start_422(client, auth_headers):
    """Phase 1: end <= start do Pydantic model_validator chặn -> 422 VALIDATION_ERROR."""
    headers = auth_headers(role="ORGANIZER", email="org@demo.com")
    resp = client.post(
        "/events",
        json=_event_payload(
            start_time=(datetime.now() + timedelta(days=3)).isoformat(),
            end_time=(datetime.now() + timedelta(days=1)).isoformat(),
        ),
        headers=headers,
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_create_event_past_start_400(client, auth_headers):
    """Start trong quá khứ (nhưng end sau start) vẫn là rule nghiệp vụ -> 400."""
    headers = auth_headers(role="ORGANIZER", email="org@demo.com")
    resp = client.post(
        "/events",
        json=_event_payload(
            start_time=(datetime.now() - timedelta(days=1)).isoformat(),
            end_time=(datetime.now() + timedelta(days=1)).isoformat(),
        ),
        headers=headers,
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_EVENT_TIME"


def test_reschedule_end_before_start_422(client, auth_headers):
    """PATCH gửi cả 2 mốc mà end <= start -> 422 tại tầng bind body."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=org).json()["id"]

    resp = client.patch(
        f"/events/{event_id}",
        json={
            "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=4)).isoformat(),
        },
        headers=org,
    )

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


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

    # 4. Ongoing (đóng đăng ký, organizer chuẩn bị)
    resp = client.post(f"/events/{event_id}/transition", json={"status": "ONGOING"}, headers=org)
    assert resp.json()["status"] == "ONGOING"

    # 5. Started (mở check-in)
    resp = client.post(f"/events/{event_id}/transition", json={"status": "STARTED"}, headers=org)
    assert resp.json()["status"] == "STARTED"

    # 6. Complete
    resp = client.post(f"/events/{event_id}/transition", json={"status": "COMPLETED"}, headers=org)
    assert resp.status_code == 200
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


def test_notify_requires_event_owner(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="owner@demo.com")
    other_organizer = auth_headers(role="ORGANIZER", email="other@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=owner).json()["id"]

    resp = client.post(f"/events/{event_id}/notify", headers=other_organizer)

    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_list_events_pagination(client, auth_headers):
    """Phase 1: GET /events hỗ trợ limit/offset."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    for i in range(3):
        client.post("/events", json=_event_payload(title=f"E{i}"), headers=org)

    page1 = client.get("/events?limit=2&offset=0")
    page2 = client.get("/events?limit=2&offset=2")
    assert page1.status_code == 200 and len(page1.json()) == 2
    assert page2.status_code == 200 and len(page2.json()) == 1

    # limit ngoài biên -> Pydantic/Query chặn 422
    assert client.get("/events?limit=0").status_code == 422


def test_list_events_cursor_walk(client, auth_headers):
    """Phase 2: cursor keyset đi hết 3 event qua 2 trang + header X-Next-Cursor."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    for i in range(3):
        client.post("/events", json=_event_payload(title=f"C{i}"), headers=org)

    page1 = client.get("/events?limit=2")
    assert page1.status_code == 200 and len(page1.json()) == 2
    nxt = page1.headers.get("x-next-cursor")
    assert nxt  # còn trang nữa nên header có cursor

    page2 = client.get(f"/events?limit=2&cursor={nxt}")
    assert page2.status_code == 200 and len(page2.json()) == 1
    assert page2.headers.get("x-next-cursor") == ""  # hết dữ liệu

    # cursor + offset dùng chung -> 400; cursor lạ -> 404
    assert client.get(f"/events?limit=2&offset=2&cursor={nxt}").status_code == 400
    assert client.get("/events?cursor=no-such-id").status_code == 404


def test_delete_event_draft_only(client, auth_headers):
    """Phase 1: chỉ chủ sở hữu được xóa event còn DRAFT."""
    owner = auth_headers(role="ORGANIZER", email="owner@demo.com")
    other = auth_headers(role="ORGANIZER", email="other@demo.com")
    event_id = client.post("/events", json=_event_payload(), headers=owner).json()["id"]

    # Người khác không xóa được
    resp = client.delete(f"/events/{event_id}", headers=other)
    assert resp.status_code == 403

    # Publish rồi thì không xóa cứng được -> dùng CANCELLED
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=owner)
    resp = client.delete(f"/events/{event_id}", headers=owner)
    assert resp.status_code == 400
    assert resp.json()["code"] == "EVENT_NOT_DELETABLE"

    # Event DRAFT khác xóa được -> 204 và GET lại 404
    draft_id = client.post("/events", json=_event_payload(), headers=owner).json()["id"]
    assert client.delete(f"/events/{draft_id}", headers=owner).status_code == 204
    assert client.get(f"/events/{draft_id}").status_code == 404


def test_openapi_error_contract_phase1(client):
    """Phase 1: Swagger mô tả error responses cho endpoint quan trọng."""
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]

    register_resps = paths["/events/{event_id}/register"]["post"]["responses"]
    assert "409" in register_resps  # ALREADY_REGISTERED / EVENT_FULL

    delete_resps = paths["/events/{event_id}"]["delete"]["responses"]
    assert "401" in delete_resps and "403" in delete_resps and "404" in delete_resps

    list_params = {p["name"] for p in paths["/events"]["get"]["parameters"]}
    assert {"limit", "offset"} <= list_params
