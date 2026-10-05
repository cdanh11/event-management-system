"""Test /users lọc theo role và /events/{id}/staff xem danh sách staff đã gán."""
from datetime import datetime, timedelta


def _payload(**overrides):
    data = {
        "title": "Design Sprint", "description": "A hands-on sprint", "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=4)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=4, hours=3)).isoformat(),
        "capacity": 20, "category": "Workshop", "banner_image": "https://example.com/d.png",
    }
    data.update(overrides)
    return data


def test_list_users_requires_organizer(client, auth_headers):
    staff = auth_headers(role="STAFF", email="staff@demo.com")
    assert client.get("/users?role=STAFF", headers=staff).status_code == 403


def test_list_users_filters_by_role(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    auth_headers(role="STAFF", email="staff1@demo.com")
    auth_headers(role="STAFF", email="staff2@demo.com")
    auth_headers(role="ATTENDEE", email="att@demo.com")

    resp = client.get("/users?role=STAFF", headers=org)
    assert resp.status_code == 200
    assert {u["email"] for u in resp.json()} == {"staff1@demo.com", "staff2@demo.com"}


def test_list_event_staff_returns_assigned(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    staff_headers = auth_headers(role="STAFF", email="staff@demo.com")
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    staff_id = client.get("/auth/me", headers=staff_headers).json()["id"]
    client.post(f"/events/{event_id}/staff", json={"staff_id": staff_id}, headers=org)

    resp = client.get(f"/events/{event_id}/staff", headers=org)
    assert resp.status_code == 200
    assert resp.json()[0]["staff_id"] == staff_id
    assert resp.json()[0]["staff_email"] == "staff@demo.com"


def test_list_event_staff_requires_ownership(client, auth_headers):
    org1 = auth_headers(role="ORGANIZER", email="org1@demo.com")
    org2 = auth_headers(role="ORGANIZER", email="org2@demo.com")
    event_id = client.post("/events", json=_payload(), headers=org1).json()["id"]
    assert client.get(f"/events/{event_id}/staff", headers=org2).status_code == 403


def test_dashboard_counts_registrations_and_checkins(client, auth_headers):
    """Dashboard đếm bằng SQL (1 REGISTERED + 1 CANCELLED -> total 1)."""
    org = auth_headers(role="ORGANIZER", email="org@demo.com")
    att1 = auth_headers(role="ATTENDEE", email="att1@demo.com")
    att2 = auth_headers(role="ATTENDEE", email="att2@demo.com")
    event_id = client.post("/events", json=_payload(), headers=org).json()["id"]
    client.post(f"/events/{event_id}/transition", json={"status": "PUBLISHED"}, headers=org)

    client.post(f"/events/{event_id}/register", headers=att1)
    reg2 = client.post(f"/events/{event_id}/register", headers=att2).json()["registration"]["id"]
    client.post(f"/registrations/{reg2}/cancel", headers=att2)

    body = client.get("/organizer/dashboard", headers=org).json()
    assert body["total_registrations"] == 1
    assert body["total_checkins"] == 0
    assert len(body["events"]) == 1