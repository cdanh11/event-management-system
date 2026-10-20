"""Hồi quy quyền tài nguyên: bản nháp, danh bạ staff và thứ tự check-in."""
import pytest
from sqlalchemy import event as sql_event, func, select
from starlette.websockets import WebSocketDisconnect

from app.models import Checkin, Event, Registration, Ticket
from tests.conftest import test_engine
from tests.test_final_review import booking, event_payload


def _actors(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="owner@example.com")
    other = auth_headers(role="ORGANIZER", email="other@example.com")
    attendee = auth_headers(email="attendee@example.com")
    assigned = auth_headers(role="STAFF", email="assigned@example.com")
    outsider = auth_headers(role="STAFF", email="outsider@example.com")
    event_id = client.post("/events", headers=owner, json=event_payload()).json()["id"]
    staff_id = client.get("/auth/me", headers=assigned).json()["id"]
    assert client.post(f"/events/{event_id}/staff", headers=owner, json={"staff_id": staff_id}).status_code == 201
    return event_id, owner, other, attendee, assigned, outsider


def test_draft_visibility_is_consistent_in_rest_and_scoped_lists(client, auth_headers):
    event_id, owner, other, attendee, assigned, outsider = _actors(client, auth_headers)
    for headers in ({}, other, attendee, outsider):
        response = client.get(f"/events/{event_id}", headers=headers)
        assert (response.status_code, response.json()["code"]) == (404, "EVENT_NOT_FOUND")
        assert response.json() == client.get("/events/missing", headers=headers).json()
    for headers in (owner, assigned):
        response = client.get(f"/events/{event_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "DRAFT"

    assert client.get(f"/events/{event_id}/occupancy", headers=owner).status_code == 200
    assert client.get(f"/events/{event_id}/occupancy", headers=other).status_code == 404
    assert client.get("/organizer/events?status=DRAFT", headers=owner).json()["items"][0]["id"] == event_id
    assert client.get("/organizer/events", headers=other).json()["items"] == []
    assert client.get("/staff/events", headers=assigned).json()[0]["id"] == event_id
    assert client.get("/staff/events", headers=outsider).json() == []

    # Không thể dùng status, q, cursor hoặc token chủ sở hữu để lộ DRAFT ở list công khai.
    for headers in ({}, owner, attendee):
        for query in ("", "?status=DRAFT", "?q=FastAPI", "?limit=1&offset=0"):
            response = client.get(f"/events{query}", headers=headers)
            assert response.status_code == 200 and response.json() == []
            assert response.headers["X-Next-Cursor"] == ""
    legacy = client.get("/events", params={"cursor": event_id})
    assert (legacy.status_code, legacy.json()["code"]) == (404, "CURSOR_NOT_FOUND")


def test_draft_websocket_only_allows_owner_or_assigned_staff(client, auth_headers):
    event_id, owner, other, attendee, assigned, outsider = _actors(client, auth_headers)
    for headers in (other, attendee, outsider):
        ticket = client.post("/ws/ticket", headers=headers).json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}"):
                pytest.fail("DRAFT must not send a snapshot to an unrelated user")
        assert rejected.value.code == 4404
        # Từ chối quyền vẫn tiêu thụ ticket một lần, không cho replay.
        with pytest.raises(WebSocketDisconnect) as replay:
            with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}"):
                pytest.fail("Rejected ticket must not be reusable")
        assert replay.value.code == 4401
    for headers in (owner, assigned):
        ticket = client.post("/ws/ticket", headers=headers).json()["ticket"]
        with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}") as ws:
            snapshot = ws.receive_json()
            assert (snapshot["type"], snapshot["status"]) == ("snapshot", "DRAFT")


def test_public_pagination_filters_drafts_before_limit_and_cursor(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="page-owner@example.com")
    public_ids = set()
    for number in range(4):
        event_id = client.post("/events", headers=owner, json={**event_payload(), "title": f"Page {number}"}).json()["id"]
        if number % 2:
            assert client.post(f"/events/{event_id}/transition", headers=owner, json={"status": "PUBLISHED"}).status_code == 200
            public_ids.add(event_id)
    first = client.get("/events?limit=1")
    offset_page = client.get("/events?limit=1&offset=1")
    cursor_page = client.get("/events", params={"limit": 1, "cursor": first.headers["X-Next-Cursor"]})
    assert {row["id"] for row in first.json() + cursor_page.json()} == public_ids
    assert offset_page.json() == cursor_page.json()
    assert client.get("/events?status=DRAFT").json() == []


@pytest.mark.parametrize("status", ["PUBLISHED", "ONGOING", "STARTED", "COMPLETED", "CANCELLED"])
def test_public_events_remain_visible_to_guests_and_attendee_ws(client, auth_headers, status):
    owner = auth_headers(role="ORGANIZER", email="public-owner@example.com")
    attendee = auth_headers(email="public-attendee@example.com")
    event_id = client.post("/events", headers=owner, json=event_payload()).json()["id"]
    transitions = ["PUBLISHED"]
    if status == "COMPLETED":
        transitions += ["STARTED", "COMPLETED"]
    elif status != "PUBLISHED":
        transitions.append(status)
    for target in transitions:
        assert client.post(f"/events/{event_id}/transition", headers=owner, json={"status": target}).status_code == 200
    for headers in ({}, attendee):
        assert client.get(f"/events/{event_id}", headers=headers).json()["status"] == status
    assert client.get("/events").json()[0]["id"] == event_id
    ticket = client.post("/ws/ticket", headers=attendee).json()["ticket"]
    with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}") as ws:
        assert ws.receive_json()["status"] == status


def test_event_detail_optional_auth_is_explicit_and_rejects_bad_tokens(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="optional-auth@example.com")
    event_id = client.post("/events", headers=owner, json=event_payload()).json()["id"]
    response = client.get(f"/events/{event_id}", headers={"Authorization": "Bearer invalid"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHORIZED")
    operation = client.get("/openapi.json").json()["paths"]["/events/{event_id}"]["get"]
    assert {} in operation["security"]  # Khách vẫn xem được sự kiện công khai.
    assert {"OAuth2PasswordBearer": []} in operation["security"]
    assert {"401", "404"} <= operation["responses"].keys()


def test_users_directory_cannot_be_expanded_beyond_staff(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="directory-owner@example.com")
    attendee = auth_headers(email="private-attendee@example.com")
    staff = auth_headers(role="STAFF", email="directory-staff@example.com")
    for path in ("/users", "/users?role=STAFF"):
        response = client.get(path, headers=owner)
        assert response.status_code == 200
        assert [(row["email"], row["role"]) for row in response.json()] == [("directory-staff@example.com", "STAFF")]
        assert client.get(path).status_code == 401
        for headers in (attendee, staff):
            assert client.get(path, headers=headers).status_code == 403
    for role in ("ATTENDEE", "ORGANIZER", "ADMIN", "ALL", "staff", ""):
        response = client.get("/users", params={"role": role}, headers=owner)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


@pytest.mark.parametrize("state", ["VALID", "USED", "CANCELLED", "CLOSED"])
def test_checkin_denies_unrelated_users_before_state_errors_or_locks(client, auth_headers, db, state):
    owner, attendee, event_id, result = booking(client, auth_headers)
    outsiders = [auth_headers(role=role, email=f"unrelated-{role.lower()}@example.com")
                 for role in ("STAFF", "ORGANIZER")]
    ticket_id = result["ticket"]["id"]
    code = result["ticket"]["ticket_code"]
    if state == "CANCELLED":
        assert client.post(f"/registrations/{result['registration']['id']}/cancel", headers=attendee).status_code == 200
    elif state != "CLOSED":
        assert client.post(f"/events/{event_id}/transition", headers=owner, json={"status": "STARTED"}).status_code == 200
        if state == "USED":
            assert client.post("/checkins", headers=owner, json={"ticket_code": code}).status_code == 201

    def snapshot():
        db.expire_all()
        return (
            db.get(Ticket, ticket_id).status,
            db.get(Event, event_id).registered_count,
            db.get(Registration, result["registration"]["id"]).status,
            db.scalar(select(func.count(Checkin.id)).where(Checkin.ticket_id == ticket_id)),
        )

    before = snapshot()
    statements = []

    def capture(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)

    sql_event.listen(test_engine, "before_cursor_execute", capture)
    try:
        for headers in outsiders:
            # Không truyền event_id và giả event_id đều không vượt qua quyền event thật.
            for event_fields in ({}, {"event_id": event_id}, {"event_id": "spoofed-event"}):
                response = client.post("/checkins", headers=headers, json={"ticket_code": code, **event_fields})
                assert response.status_code == 403, response.text
                assert response.json() == {"status": 403, "code": "FORBIDDEN", "message": "You cannot check in this event"}
    finally:
        sql_event.remove(test_engine, "before_cursor_execute", capture)
    assert not any("FOR UPDATE" in statement.upper() for statement in statements)
    assert snapshot() == before

    # Người có quyền vẫn nhận lỗi nghiệp vụ cụ thể; vé không tồn tại vẫn là 404.
    missing = client.post("/checkins", headers=outsiders[0], json={"ticket_code": "UNKNOWN"})
    assert (missing.status_code, missing.json()["code"]) == (404, "INVALID_TICKET")
    response = client.post("/checkins", headers=owner, json={"ticket_code": code, "event_id": event_id})
    expected = {"VALID": (201, None), "USED": (409, "TICKET_ALREADY_USED"),
                "CANCELLED": (400, "TICKET_CANCELLED"), "CLOSED": (400, "CHECKIN_CLOSED")}[state]
    assert response.status_code == expected[0], response.text
    if expected[1]:
        assert response.json()["code"] == expected[1]
