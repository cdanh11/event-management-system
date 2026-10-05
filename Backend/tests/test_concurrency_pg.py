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
def test_concurrent_register_capacity_one():
    engine = create_engine(PG_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

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
                with TestClient(app) as c:
                    r = c.post(f"/events/{event_id}/register", headers=headers)
                    results.append(r.status_code)

            threads = [threading.Thread(target=race, args=(h,)) for h in att_h]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert sorted(results) == [201, 409, 409, 409, 409]
            assert client.get(f"/events/{event_id}").json()["registered_count"] == 1

            # Dọn dữ liệu test bằng SQL thô theo thứ tự FK:
            # ticket -> registration -> event -> refresh_tokens -> user.
            from sqlalchemy import text
            db = Session()
            try:
                reg_ids = [r[0] for r in db.execute(
                    text("SELECT id FROM registrations WHERE event_id = :eid"),
                    {"eid": event_id}).all()]
                for rid in reg_ids:
                    db.execute(text("DELETE FROM tickets WHERE registration_id = :rid"),
                               {"rid": rid})
                    db.execute(text("DELETE FROM registrations WHERE id = :rid"),
                               {"rid": rid})
                db.execute(text("DELETE FROM events WHERE id = :eid"), {"eid": event_id})
                user_ids = [r[0] for r in db.execute(
                    text("SELECT id FROM users WHERE email = ANY(:emails)"),
                    {"emails": [org_email] + att_emails}).all()]
                for uid in user_ids:
                    db.execute(text("DELETE FROM refresh_tokens WHERE user_id = :uid"),
                               {"uid": uid})
                    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
                db.commit()
            finally:
                db.close()
    finally:
        app.dependency_overrides.clear()
