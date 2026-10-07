"""Dataset demo phải có vé/check-in thật, chạy lại giữ dữ liệu đã thao tác."""
from sqlalchemy import func, select
from app.models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from app.seed import _seed


def test_demo_dataset_counts_links_and_idempotency(db):
    original = User(name="Existing", email="existing@example.com", role="ATTENDEE", password_hash="unchanged", avatar_url="")
    db.add(original)
    db.commit()
    _seed(db)
    assert db.scalar(select(func.count(User.id))) == 108
    assert db.scalar(select(func.count(User.id)).where(User.role == "ORGANIZER")) == 2
    assert db.scalar(select(func.count(User.id)).where(User.role == "STAFF")) == 5
    assert db.scalar(select(func.count(Event.id)).where(Event.status == "PUBLISHED")) == 10
    assert db.scalar(select(func.count(Event.id)).where(Event.status == "COMPLETED")) == 5
    assert db.scalar(select(func.count(Registration.id))) == 278
    assert db.scalar(select(func.count(Ticket.id))) == 278
    assert db.scalar(select(func.count(Checkin.id))) == 75
    for event in db.scalars(select(Event)):
        assert event.registered_count == db.scalar(select(func.count(Registration.id)).where(Registration.event_id == event.id))
        assert event.registered_count < event.capacity
        if event.status == "COMPLETED":
            assert db.scalar(select(func.count(Checkin.id)).where(Checkin.event_id == event.id)) == 15
    for scan in db.scalars(select(Checkin)):
        ticket = db.get(Ticket, scan.ticket_id)
        registration = db.get(Registration, ticket.registration_id)
        assert ticket.status == "USED"
        assert (registration.attendee_id, registration.event_id) == (scan.attendee_id, scan.event_id)
        assert db.scalar(select(StaffEventAssignment.id).where(StaffEventAssignment.event_id == scan.event_id, StaffEventAssignment.staff_id == scan.checked_in_by))
    changed = db.scalar(select(Event).where(Event.status == "PUBLISHED"))
    changed.status = "CANCELLED"
    db.commit()
    _seed(db)
    assert db.scalar(select(func.count(Event.id))) == 15
    assert db.scalar(select(func.count(User.id))) == 108
    assert db.scalar(select(func.count(Checkin.id))) == 75
    assert db.get(Event, changed.id).status == "CANCELLED"
    assert db.get(User, original.id).password_hash == "unchanged"


def test_demo_alias_login_is_same_account_and_signup_still_needs_email(client, make_user):
    staff = make_user("Staff One", "staff1@demo.com", "STAFF")
    for alias in ["staff1", " STAFF1 ", "staff1@demo.com"]:
        response = client.post("/auth/login", json={"email": alias, "password": "123456"})
        assert response.status_code == 200
        assert response.json()["user"]["id"] == staff.id
    response = client.post("/auth/token", data={"username": "staff1", "password": "123456", "grant_type": "password"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "STAFF"
    assert client.post("/auth/login", json={"email": "organizer99", "password": "123456"}).status_code == 401
    assert client.post("/auth/login", json={"email": "staff1", "password": "wrong"}).status_code == 401
    assert client.post("/auth/register", json={"name": "Alias", "email": "staff2", "password": "123456"}).status_code == 422
