"""Controlled PostgreSQL races; never run against the application database.

Set TEST_POSTGRES_URL to a separate *_test or *_audit database. The main test
observes actual PostgreSQL lock waits, rather than hoping thread starts overlap.
The unlocked control demonstrates lost updates: five tickets, counter still 1.
"""
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event as sql_event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Checkin, Event, RefreshToken, Registration, StaffEventAssignment, Ticket, User
from app.security import hash_password
from app.timeutils import utc_now

PG_URL = os.getenv("TEST_POSTGRES_URL")
needs_pg = pytest.mark.skipif(not PG_URL, reason="requires a separate TEST_POSTGRES_URL")
logger = logging.getLogger("evently.tests.checkin_race")


@pytest.fixture
def pg_app(monkeypatch):
    url = make_url(PG_URL)
    assert url.get_backend_name() == "postgresql" and (url.database or "").endswith(("_test", "_audit"))
    engine = create_engine(PG_URL)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    user_ids = []
    password_hash = hash_password("123456")

    def create_user(client, role):
        with sessions() as db:
            user = User(name=role, email=f"race-{uuid.uuid4().hex}@example.com", role=role,
                        avatar_url="", password_hash=password_hash)
            db.add(user); db.commit()
            user_ids.append(user.id)
            email = user.email
        response = client.post("/auth/login", json={"email": email, "password": "123456"})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def override_db():
        with sessions() as db:
            yield db

    import app.services.lifecycle as lifecycle
    real_sweep = lifecycle.sweep_due_events
    monkeypatch.setattr(lifecycle, "sweep_due_events", lambda: real_sweep(sessions))
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client, sessions, engine, create_user
    finally:
        app.dependency_overrides.clear()
        with sessions.begin() as db:
            event_ids = select(Event.id).where(Event.organizer_id.in_(user_ids))
            reg_ids = select(Registration.id).where(Registration.event_id.in_(event_ids))
            db.execute(delete(Checkin).where(Checkin.event_id.in_(event_ids)))
            db.execute(delete(Ticket).where(Ticket.registration_id.in_(reg_ids)))
            db.execute(delete(Registration).where(Registration.event_id.in_(event_ids)))
            db.execute(delete(StaffEventAssignment).where(StaffEventAssignment.event_id.in_(event_ids)))
            db.execute(delete(Event).where(Event.organizer_id.in_(user_ids)))
            db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
        engine.dispose()


def prepare_capacity_one(pg_app):
    client, sessions, engine, create_user = pg_app
    org = create_user(client, "ORGANIZER")
    attendees = [create_user(client, "ATTENDEE") for _ in range(5)]
    start = utc_now() + timedelta(days=5)
    response = client.post("/events", headers=org, json={
        "title": "Race", "description": "Controlled concurrency", "location": "HCMC",
        "start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat(),
        "capacity": 1, "category": "Test", "banner_image": "",
    })
    assert response.status_code == 201
    event_id = response.json()["id"]
    assert client.post(f"/events/{event_id}/transition", headers=org, json={"status": "PUBLISHED"}).status_code == 200
    return client, sessions, engine, attendees, event_id


def counts(sessions, event_id):
    with sessions() as db:
        return (
            db.get(Event, event_id).registered_count,
            db.scalar(select(func.count()).select_from(Registration).where(Registration.event_id == event_id)),
            db.scalar(select(func.count()).select_from(Ticket).join(Registration).where(Registration.event_id == event_id)),
        )


@needs_pg
def test_concurrent_register_capacity_one(pg_app, monkeypatch):
    """One transaction holds the row; four competitors must wait for its lock."""
    import app.routers.registrations as registrations
    client, sessions, engine, attendees, event_id = prepare_capacity_one(pg_app)
    original = registrations._locked_event
    held, release, attempted = threading.Event(), threading.Event(), threading.Event()
    guard = threading.Lock()
    pids = []

    def controlled_lock(db, requested_id):
        pid = db.execute(text("SELECT pg_backend_pid()")).scalar()
        with guard:
            first = not pids
            pids.append(pid)
            if len(pids) == 5:
                attempted.set()
        row = original(db, requested_id)
        if first:
            held.set()
            assert release.wait(15), "Test did not release the first transaction"
        return row

    monkeypatch.setattr(registrations, "_locked_event", controlled_lock)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(client.post, f"/events/{event_id}/register", headers=attendees[0])]
        try:
            assert held.wait(10), "First request never acquired the event"
            futures += [pool.submit(client.post, f"/events/{event_id}/register", headers=h) for h in attendees[1:]]
            assert attempted.wait(10)
            deadline = time.monotonic() + 5
            waiting = 0
            while time.monotonic() < deadline:
                with engine.connect() as connection:
                    waiting = connection.execute(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE pid = ANY(:pids) AND wait_event_type = 'Lock'"
                    ), {"pids": pids[1:]}).scalar()
                if waiting == 4:
                    break
                time.sleep(0.02)
            assert waiting == 4, "FOR UPDATE did not block all four competing transactions"
        finally:
            release.set()
        results = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in results) == [201, 409, 409, 409, 409]
    assert all(response.json()["code"] == "EVENT_FULL" for response in results if response.status_code == 409)
    assert counts(sessions, event_id) == (1, 1, 1)


@needs_pg
def test_unlocked_control_exposes_lost_update_and_extra_tickets(pg_app, monkeypatch):
    """Deliberately broken variant, isolated to this test, forces the bad schedule."""
    import app.routers.registrations as registrations
    client, sessions, _, attendees, event_id = prepare_capacity_one(pg_app)
    gate = threading.Barrier(5)

    def unlocked_read(db, requested_id):
        row = db.scalar(select(Event).where(Event.id == requested_id))
        gate.wait(timeout=10)  # All readers see 0 before any request can update it.
        return row

    monkeypatch.setattr(registrations, "_locked_event", unlocked_read)
    with ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(pool.map(lambda h: client.post(f"/events/{event_id}/register", headers=h), attendees))
    assert [response.status_code for response in responses] == [201] * 5
    assert counts(sessions, event_id) == (1, 5, 5)


@needs_pg
def test_concurrent_checkin_same_ticket_only_once(pg_app):
    """Hai staff tranh cùng vé: chờ khóa thật, một 201, một 409, một Checkin.

    Listener chỉ giữ transaction đầu tại câu SELECT Event FOR UPDATE của API
    thật. Không thay thuật toán khóa/check-in và không dựa vào sleep để đoán
    hai request có chạy chồng lấn hay không.
    """
    client, sessions, engine, create_user = pg_app
    org = create_user(client, "ORGANIZER")
    attendee = create_user(client, "ATTENDEE")
    staff_headers = [create_user(client, "STAFF") for _ in range(2)]
    staff_ids = []
    for headers in staff_headers:
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        staff_ids.append(response.json()["id"])

    start = utc_now() + timedelta(days=5)
    response = client.post("/events", headers=org, json={
        "title": "Check-in race", "description": "Two assigned staff, one ticket",
        "location": "HCMC", "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=2)).isoformat(),
        "capacity": 1, "category": "Test", "banner_image": "",
    })
    assert response.status_code == 201
    event_id = response.json()["id"]
    assert client.post(f"/events/{event_id}/transition", headers=org, json={"status": "PUBLISHED"}).status_code == 200
    response = client.post(f"/events/{event_id}/register", headers=attendee)
    assert response.status_code == 201
    booking = response.json()
    ticket_id = booking["ticket"]["id"]
    assert booking["ticket"]["status"] == "VALID"
    for staff_id in staff_ids:
        assert client.post(f"/events/{event_id}/staff", headers=org, json={"staff_id": staff_id}).status_code == 201
    assert client.post(f"/events/{event_id}/transition", headers=org, json={"status": "STARTED"}).status_code == 200
    payload = {"event_id": event_id, "ticket_code": booking["ticket"]["ticket_code"]}

    held, release, attempted = threading.Event(), threading.Event(), threading.Event()
    guard = threading.Lock()
    pids = []

    def is_target_lock(statement, parameters):
        sql = " ".join(statement.upper().split())
        return ("FROM EVENTS " in sql and "FOR UPDATE" in sql
                and isinstance(parameters, dict) and event_id in parameters.values())

    def before_lock(connection, cursor, statement, parameters, context, executemany):
        if not is_target_lock(statement, parameters):
            return
        # Truy vấn PID không khớp is_target_lock nên không đệ quy listener.
        pid = connection.exec_driver_sql("SELECT pg_backend_pid()").scalar_one()
        with guard:
            first = not pids
            pids.append(pid)
            if len(pids) == 2:
                attempted.set()
        connection.info["hold_checkin_race"] = first

    def after_lock(connection, cursor, statement, parameters, context, executemany):
        if is_target_lock(statement, parameters) and connection.info.pop("hold_checkin_race", False):
            logger.info("CHECKIN RACE: first request holds the Event row lock")
            held.set()
            assert release.wait(20), "Test did not release the first check-in transaction"

    sql_event.listen(engine, "before_cursor_execute", before_lock)
    sql_event.listen(engine, "after_cursor_execute", after_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.post, "/checkins", headers=staff_headers[0], json=payload)]
            try:
                assert held.wait(10), "First check-in never acquired the Event row lock"
                futures.append(pool.submit(client.post, "/checkins", headers=staff_headers[1], json=payload))
                assert attempted.wait(10), "Second check-in never attempted the Event row lock"
                assert len(pids) == 2 and len(set(pids)) == 2
                deadline = time.monotonic() + 5
                blocked = 0
                while time.monotonic() < deadline:
                    with engine.connect() as connection:
                        blocked = connection.execute(text(
                            "SELECT count(*) FROM pg_stat_activity "
                            "WHERE pid = :waiting AND wait_event_type = 'Lock' "
                            "AND :holder = ANY(pg_blocking_pids(pid))"
                        ), {"waiting": pids[1], "holder": pids[0]}).scalar_one()
                    if blocked == 1:
                        break
                    time.sleep(0.02)
                assert blocked == 1, "Second check-in was not blocked by the first transaction"
                assert not any(future.done() for future in futures)
                logger.info("CHECKIN RACE: PostgreSQL confirms the second request waits for the first")
            finally:
                release.set()
            responses = [future.result(timeout=15) for future in futures]
    finally:
        release.set()
        sql_event.remove(engine, "before_cursor_execute", before_lock)
        sql_event.remove(engine, "after_cursor_execute", after_lock)

    statuses = [response.status_code for response in responses]
    assert sorted(statuses) == [201, 409]
    winner = statuses.index(201)
    rejected = responses[statuses.index(409)]
    assert rejected.json()["code"] == "TICKET_ALREADY_USED"
    with sessions() as db:
        rows = db.scalars(select(Checkin).where(Checkin.event_id == event_id)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.ticket_id == ticket_id
        assert row.attendee_id == booking["registration"]["attendee_id"]
        assert row.checked_in_by == staff_ids[winner]
        assert row.status == "SUCCESS"
        assert responses[winner].json()["id"] == row.id
        assert db.get(Ticket, ticket_id).status == "USED"
        assert db.get(Registration, booking["registration"]["id"]).status == "REGISTERED"
        assert db.get(Event, event_id).registered_count == 1
    logger.info(
        "CHECKIN RACE RESULT: HTTP=%s; code=TICKET_ALREADY_USED; "
        "checkins=1; ticket=USED; registered_count=1; winning staff matches DB",
        sorted(statuses),
    )


@needs_pg
def test_refresh_token_can_only_rotate_once_under_race(pg_app):
    client, _, _, create_user = pg_app
    create_user(client, "ATTENDEE")
    cookie = client.cookies["evently_refresh"]
    gate = threading.Barrier(2)

    def rotate(_):
        gate.wait(timeout=10)
        return client.post("/auth/refresh", headers={"Cookie": f"evently_refresh={cookie}"}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(rotate, range(2))) == [200, 401]
