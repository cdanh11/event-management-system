"""Concurrency test FOR UPDATE trên PostgreSQL thật (Phase 2).

SQLite không có row lock nên test này bỏ qua mặc định. Chạy tay:

    TEST_POSTGRES_URL=postgresql+psycopg://evently:evently@localhost:5433/evently \\
        python -m pytest tests/test_concurrency_pg.py -q

Kịch bản: event capacity=1, 5 attendee đăng ký đồng thời -> đúng 1 vé
201, 4 vé còn lại 409 (chứng minh with_for_update + unique hoạt động).
"""

import os
import threading
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url

from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

PG_URL = os.getenv("TEST_POSTGRES_URL")
needs_pg = pytest.mark.skipif(not PG_URL, reason="cần TEST_POSTGRES_URL (PostgreSQL thật)")


def _payload():
    return {
        "title": "Race",
        "description": "Concurrency demo",
        "location": "HCMC",
        "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "end_time": (datetime.now() + timedelta(days=5, hours=2)).isoformat(),
        "capacity": 1,
        "category": "Test",
        "banner_image": "https://example.com/b.png",
    }


@needs_pg
def test_concurrent_register_capacity_one(monkeypatch):
    assert make_url(PG_URL).database != "evently", "Dùng database kiểm thử riêng, không dùng DB demo evently"
    engine = create_engine(PG_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    import app.services.lifecycle as lifecycle
    real_sweep = lifecycle.sweep_due_events
    monkeypatch.setattr(lifecycle, "sweep_due_events", lambda: real_sweep(Session))

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # Email duy nhất mỗi lần chạy để test idempotent (chạy lại không trùng).
    tag = uuid.uuid4().hex[:8]
    org_email = f"org-{tag}@demo.com"
    att_emails = [f"att{i}-{tag}@demo.com" for i in range(5)]
    try:
        with TestClient(app) as client:
            # Seed: 1 organizer + 5 attendee trực tiếp vào PG.
            db = Session()
            try:
                org = User(name="Org", email=org_email, role="ORGANIZER",
                           avatar_url="", password_hash=hash_password("123456"))
                db.add(org)
                attendees = []
                for i in range(5):
                    u = User(name=f"Att{i}", email=att_emails[i], role="ATTENDEE",
                             avatar_url="", password_hash=hash_password("123456"))
                    db.add(u)
                    attendees.append(u)
                db.commit()
            finally:
                db.close()

            def login(email):
                r = client.post("/auth/login", json={"email": email, "password": "123456"})
                assert r.status_code == 200, r.text
                return {"Authorization": f"Bearer {r.json()['access_token']}"}

            org_h = login(org_email)
            att_h = [login(e) for e in att_emails]

            event_id = client.post("/events", json=_payload(), headers=org_h).json()["id"]
            client.post(f"/events/{event_id}/transition",
                        json={"status": "PUBLISHED"}, headers=org_h)

            results: list[int] = []

            def race(headers):
                # Dùng chung portal của app; không mở 5 lifespan/sweeper riêng.
                r = client.post(f"/events/{event_id}/register", headers=headers)
                results.append(r.status_code)

            threads = [threading.Thread(target=race, args=(h,)) for h in att_h]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert sorted(results) == [201, 409, 409, 409, 409]
            assert client.get(f"/events/{event_id}").json()["registered_count"] == 1

    finally:
        # Dọn theo email UUID của riêng lần chạy, kể cả assertion thất bại.
        from sqlalchemy import delete, select
        from app.models import Event, Registration, RefreshToken, Ticket

        app.dependency_overrides.clear()
        with Session.begin() as db:
            user_ids = select(User.id).where(User.email.in_([org_email] + att_emails))
            event_ids = select(Event.id).where(Event.organizer_id.in_(user_ids))
            reg_ids = select(Registration.id).where(Registration.event_id.in_(event_ids))
            db.execute(delete(Ticket).where(Ticket.registration_id.in_(reg_ids)))
            db.execute(delete(Registration).where(Registration.event_id.in_(event_ids)))
            db.execute(delete(Event).where(Event.organizer_id.in_(user_ids)))
            db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.email.in_([org_email] + att_emails)))
        engine.dispose()


@needs_pg
def test_refresh_token_can_only_rotate_once_under_race(monkeypatch):
    """Hai request dùng cùng cookie: FOR UPDATE cho đúng một lần refresh thành công."""
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import delete
    from app.models import RefreshToken

    assert make_url(PG_URL).database != "evently", "Dùng database kiểm thử riêng"
    engine = create_engine(PG_URL)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    import app.services.lifecycle as lifecycle
    real_sweep = lifecycle.sweep_due_events
    monkeypatch.setattr(lifecycle, "sweep_due_events", lambda: real_sweep(sessions))
    with sessions() as db:
        user = User(name="Refresh race", email=f"refresh-{uuid.uuid4().hex}@demo.com",
                    role="ATTENDEE", avatar_url="", password_hash=hash_password("123456"))
        db.add(user)
        db.commit()
        user_id, email = user.id, user.email

    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post("/auth/login", json={"email": email, "password": "123456"})
            cookie = response.cookies["evently_refresh"]
            gate = threading.Barrier(2)

            def rotate(_):
                gate.wait(timeout=10)
                return client.post("/auth/refresh", headers={"Cookie": f"evently_refresh={cookie}"}).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                assert sorted(pool.map(rotate, range(2))) == [200, 401]
    finally:
        app.dependency_overrides.clear()
        with sessions.begin() as db:
            db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
        engine.dispose()
