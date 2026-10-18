"""Controlled PostgreSQL races; never run against the application database.

Set TEST_POSTGRES_URL to a separate *_test or *_audit database. The main test
observes actual PostgreSQL lock waits, rather than hoping thread starts overlap.
The unlocked control demonstrates lost updates: five tickets, counter still 1.
"""
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Checkin, Event, RefreshToken, Registration, StaffEventAssignment, Ticket, User
from app.security import hash_password
from app.timeutils import utc_now

PG_URL = os.getenv("TEST_POSTGRES_URL")
needs_pg = pytest.mark.skipif(not PG_URL, reason="requires a separate TEST_POSTGRES_URL")


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
