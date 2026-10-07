"""Hồi quy các bất biến khi chốt MVP: quyền tài nguyên, trạng thái và dữ liệu."""
from datetime import datetime, timedelta

import pytest

from app.models import Event
from app.services.lifecycle import sweep_due_events
from tests.conftest import TestSession


def event_payload():
    return {
        "title": "FastAPI demo", "description": "Review", "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=2)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=2, hours=2)).isoformat(),
        "capacity": 5, "category": "Technology",
    }


def booking(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att = auth_headers(role="ATTENDEE", email="att@demo.com")
    event_id = client.post("/events", json=event_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)
    result = client.post(f"/events/{event_id}/register", headers=att).json()
    return org, att, event_id, result


@pytest.mark.parametrize("role", ["STAFF", "ORGANIZER", "ATTENDEE"])
def test_unrelated_user_cannot_read_booking(client, auth_headers, role):
    _, _, _, result = booking(client, auth_headers)
    outsider = auth_headers(role=role, email="outsider@demo.com")
    reg_id, ticket_id = result["registration"]["id"], result["ticket"]["id"]
    for path in [f"/registrations/{reg_id}", f"/registrations/{reg_id}/ticket", f"/tickets/{ticket_id}"]:
        assert client.get(path, headers=outsider).status_code == 403


def test_owner_and_assigned_staff_can_read_ticket(client, auth_headers):
    org, _, event_id, result = booking(client, auth_headers)
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    staff_id = client.get("/auth/me", headers=staff).json()["id"]
    client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)
    for headers in [org, staff]:
        assert client.get(f"/tickets/{result['ticket']['id']}", headers=headers).status_code == 200


def test_cancel_after_checkin_keeps_ticket_and_count(client, auth_headers):
    org, att, event_id, result = booking(client, auth_headers)
    client.post(f"/events/{event_id}/transition", json={"status": "STARTED"}, headers=org)
    assert client.post("/checkins", json={"ticket_code": result["ticket"]["ticket_code"]}, headers=org).status_code == 201
    response = client.post(f"/registrations/{result['registration']['id']}/cancel", headers=att)
    assert response.status_code == 400
    assert response.json()["code"] == "CANCELLATION_CLOSED"
    assert client.get(f"/tickets/{result['ticket']['id']}", headers=att).json()["status"] == "USED"
    assert client.get(f"/events/{event_id}").json()["registered_count"] == 1


def test_patch_capacity_and_null_are_rejected(client, auth_headers):
    org, _, event_id, _ = booking(client, auth_headers)
    second = auth_headers(role="ATTENDEE", email="second@demo.com")
    client.post(f"/events/{event_id}/register", headers=second)
    assert client.patch(f"/events/{event_id}", json={"capacity": 1}, headers=org).json()["code"] == "CAPACITY_TOO_SMALL"
    assert client.patch(f"/events/{event_id}", json={"start_time": None}, headers=org).status_code == 422
    client.post(f"/events/{event_id}/transition", json={"status": "STARTED"}, headers=org)
    assert client.patch(f"/events/{event_id}", json={"title": "Changed"}, headers=org).json()["code"] == "EVENT_NOT_EDITABLE"


def test_delete_draft_with_staff_assignment(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    event_id = client.post("/events", json=event_payload(), headers=org).json()["id"]
    staff_id = client.get("/auth/me", headers=staff).json()["id"]
    client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)
    assert client.delete(f"/events/{event_id}", headers=org).status_code == 204
    assert client.get("/staff/events", headers=staff).json() == []


def test_sweep_catches_up_after_downtime(client, auth_headers, db):
    _, _, event_id, _ = booking(client, auth_headers)
    event = db.get(Event, event_id)
    event.start_time = datetime.now() - timedelta(hours=3)
    event.end_time = datetime.now() - timedelta(hours=1)
    db.commit()
    frames = sweep_due_events(TestSession)
    assert [(frame["event_id"], frame["status"]) for frame in frames] == [(event_id, "COMPLETED")]


def test_mixed_timezone_payload_and_cors_headers(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    payload = event_payload()
    payload["start_time"] = (datetime.now() + timedelta(days=2)).astimezone().isoformat()
    assert client.post("/events", json=payload, headers=org).status_code == 201
    response = client.get("/events", headers={"Origin": "http://localhost:5173"})
    assert "X-Next-Cursor" in response.headers["access-control-expose-headers"]
    response = client.get("/auth/me")
    assert response.headers["www-authenticate"] == "Bearer"


def test_checkin_selected_event_is_checked_before_commit(client, auth_headers):
    org, att, event_id, result = booking(client, auth_headers)
    client.post(f"/events/{event_id}/transition", json={"status": "STARTED"}, headers=org)
    response = client.post("/checkins", json={
        "ticket_code": result["ticket"]["ticket_code"], "event_id": "another-event",
    }, headers=org)
    assert response.status_code == 400
    assert response.json()["code"] == "WRONG_EVENT"
    assert client.get(f"/tickets/{result['ticket']['id']}", headers=att).json()["status"] == "VALID"
    assert client.get(f"/events/{event_id}/checkins", headers=org).json() == []
