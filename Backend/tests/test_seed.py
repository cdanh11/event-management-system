"""Dữ liệu bảo vệ phải nhất quán và sử dụng được qua các API thật."""
from pathlib import Path

from sqlalchemy import func, select
from app.models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from app.seed import _seed


def test_demo_dataset_counts_links_and_idempotency(db):
    original = User(name="Existing", email="existing@example.com", role="ATTENDEE", password_hash="unchanged", avatar_url="")
    db.add(original)
    db.commit()
    _seed(db)
    assert db.scalar(select(func.count(User.id))) == 38
    assert db.scalar(select(func.count(User.id)).where(User.role == "ORGANIZER")) == 2
    assert db.scalar(select(func.count(User.id)).where(User.role == "STAFF")) == 5
    assert db.scalar(select(func.count(Event.id)).where(Event.status == "PUBLISHED")) == 10
    assert db.scalar(select(func.count(Event.id)).where(Event.status == "COMPLETED")) == 5
    assert db.scalar(select(func.count(Event.id))) == 20
    assert db.scalar(select(func.count(Registration.id))) == 181
    assert db.scalar(select(func.count(Ticket.id))) == 181
    assert db.scalar(select(func.count(Checkin.id))) == 62
    assert db.scalar(select(func.count(StaffEventAssignment.id))) == 40
    assert db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "CANCELLED")) == 17
    assert db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "VALID")) == 102
    for event in db.scalars(select(Event)):
        assert event.registered_count == db.scalar(select(func.count(Registration.id)).where(
            Registration.event_id == event.id, Registration.status == "REGISTERED"))
        assert event.registered_count <= event.capacity
        image = Path(__file__).resolve().parents[2] / "Frontend" / "public" / event.banner_url.lstrip("/")
        assert image.is_file()
        if event.status == "COMPLETED":
            assert db.scalar(select(func.count(Checkin.id)).where(Checkin.event_id == event.id)) == 12
    for ticket in db.scalars(select(Ticket)):
        registration = db.get(Registration, ticket.registration_id)
        assert db.get(User, registration.attendee_id).created_at <= registration.registered_at
        assert db.get(Event, registration.event_id).created_at <= registration.registered_at
        assert ticket.issued_at == registration.registered_at
        assert ticket.qr_value == ticket.ticket_code
        assert ticket.ticket_code.startswith("EV-")
        assert (ticket.status == "CANCELLED") == (registration.status == "CANCELLED")
        assert db.scalar(select(func.count(Checkin.id)).where(Checkin.ticket_id == ticket.id)) == (1 if ticket.status == "USED" else 0)
    for scan in db.scalars(select(Checkin)):
        ticket = db.get(Ticket, scan.ticket_id)
        registration = db.get(Registration, ticket.registration_id)
        assert ticket.status == "USED"
        assert ticket.issued_at <= scan.checked_in_at
        assert (registration.attendee_id, registration.event_id) == (scan.attendee_id, scan.event_id)
        assert db.scalar(select(StaffEventAssignment.id).where(StaffEventAssignment.event_id == scan.event_id, StaffEventAssignment.staff_id == scan.checked_in_by))
    changed = db.scalar(select(Event).where(Event.status == "PUBLISHED"))
    changed.status = "CANCELLED"
    changed.title = f"[Demo] {changed.title}"
    db.commit()
    _seed(db)
    assert db.scalar(select(func.count(Event.id))) == 20
    assert db.scalar(select(func.count(User.id))) == 38
    assert db.scalar(select(func.count(Checkin.id))) == 62
    assert db.get(Event, changed.id).status == "CANCELLED"
    assert not db.get(Event, changed.id).title.startswith("[Demo]")
    assert db.get(User, original.id).password_hash == "unchanged"


def test_seeded_tickets_and_registration_work_through_api(client, db):
    _seed(db)
    db.commit()

    def login(alias):
        response = client.post("/auth/login", json={"email": alias, "password": "123456"})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    staff = login("staff1")
    attendee = login("user1")
    other_staff = login("staff5")
    started = db.scalar(select(Event).where(Event.title == "Check-in Operations Lab"))

    def ticket_for(alias):
        return db.scalar(select(Ticket).join(Registration).join(User, User.id == Registration.attendee_id)
                         .where(Registration.event_id == started.id, User.name == alias))

    valid = ticket_for("user3")
    request = {"ticket_code": valid.ticket_code, "event_id": started.id}
    assert client.post("/checkins", headers=other_staff, json=request).status_code == 403
    assert client.post("/checkins", headers=staff, json=request).status_code == 201
    assert client.post("/checkins", headers=staff, json=request).status_code == 409
    assert client.post("/checkins", headers=staff, json={"ticket_code": ticket_for("user7").ticket_code}).status_code == 400

    full = db.scalar(select(Event).where(Event.title == "Backend Architecture Roundtable"))
    response = client.post(f"/events/{full.id}/register", headers=attendee)
    assert (response.status_code, response.json()["code"]) == (409, "EVENT_FULL")

    available = db.scalar(select(Event).where(Event.title == "Python Async I/O Lab"))
    before = available.registered_count
    response = client.post(f"/events/{available.id}/register", headers=attendee)
    assert response.status_code == 201
    registration_id = response.json()["registration"]["id"]
    assert client.get(f"/events/{available.id}").json()["registered_count"] == before + 1
    assert client.post(f"/registrations/{registration_id}/cancel", headers=attendee).status_code == 200
    assert client.get(f"/events/{available.id}").json()["registered_count"] == before


def test_demo_alias_login_is_same_account_and_signup_still_needs_email(client, make_user):
    staff = make_user("Staff One", "staff1@demo.com", "STAFF")
    for alias in ["staff1", " STAFF1 ", "staff1@demo.com"]:
        response = client.post("/auth/login", json={"email": alias, "password": "123456"})
        assert response.status_code == 200
        assert response.json()["user"]["id"] == staff.id
    response = client.post("/auth/token", data={"username": "staff1", "password": "123456", "grant_type": "password"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "STAFF"
    response = client.post("/auth/login", json={"username": "staff1", "password": "123456"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == staff.id
    assert client.post("/auth/login", json={"email": "organizer99", "password": "123456"}).status_code == 401
    assert client.post("/auth/login", json={"email": "staff1", "password": "wrong"}).status_code == 401
    assert client.post("/auth/register", json={"name": "Alias", "email": "staff2", "password": "123456"}).status_code == 422
