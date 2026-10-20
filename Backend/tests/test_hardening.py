"""Regression tests for time, DB invariants, query counts and stable cursors."""
from contextlib import contextmanager
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event as sql_event, text
from sqlalchemy.exc import IntegrityError

from app.models import Event
from app.services.lifecycle import sweep_due_events
from app.timeutils import utc_now
from tests.conftest import TestSession, test_engine
from tests.test_final_review import event_payload


@pytest.mark.parametrize("stamp", ["2030-02-01T09:00:00", "2030-02-01T09:00:00+07:00", "2030-02-01T02:00:00Z"])
def test_event_input_represents_same_utc_instant(client, auth_headers, stamp, monkeypatch):
    monkeypatch.setattr("app.routers.events.utc_now", lambda: datetime(2029, 1, 1, tzinfo=timezone.utc))
    org = auth_headers(role="ORGANIZER", email="time@example.com")
    response = client.post("/events", headers=org, json={**event_payload(), "start_time": stamp, "end_time": "2030-02-01T05:00:00Z"})
    assert response.status_code == 201
    value = datetime.fromisoformat(response.json()["start_time"])
    assert value == datetime(2030, 2, 1, 2, tzinfo=timezone.utc)
    assert value.utcoffset() == timedelta(0)


def test_lifecycle_clock_boundaries_are_utc(client, auth_headers, monkeypatch):
    import app.services.lifecycle as lifecycle
    monkeypatch.setattr("app.routers.events.utc_now", lambda: datetime(2029, 1, 1, tzinfo=timezone.utc))
    org = auth_headers(role="ORGANIZER", email="clock@example.com")
    start = datetime(2030, 2, 1, 2, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    response = client.post("/events", headers=org, json={**event_payload(), "start_time": start.isoformat(), "end_time": end.isoformat()})
    event_id = response.json()["id"]
    client.post(f"/events/{event_id}/transition", headers=org, json={"status": "PUBLISHED"})
    monkeypatch.setattr(lifecycle, "_now", lambda: start - timedelta(minutes=16))
    assert sweep_due_events(TestSession) == []
    monkeypatch.setattr(lifecycle, "_now", lambda: start - timedelta(minutes=15))
    assert sweep_due_events(TestSession)[0]["status"] == "STARTED"
    monkeypatch.setattr(lifecycle, "_now", lambda: end)
    assert sweep_due_events(TestSession)[0]["status"] == "COMPLETED"


@pytest.mark.skipif(test_engine.dialect.name != "postgresql", reason="PostgreSQL session timezone test")
def test_pg_session_timezone_does_not_change_event_instant(db, make_user):
    org = make_user("Org", "zone@example.com", "ORGANIZER")
    stamp = datetime(2030, 2, 1, 2, tzinfo=timezone.utc)
    row = Event(organizer_id=org.id, title="Zone", description="d", location="VN", start_time=stamp,
                end_time=stamp + timedelta(hours=2), capacity=10, registered_count=0, status="DRAFT", category="Test", banner_url="")
    db.add(row); db.commit()
    event_id = row.id
    for zone in ("UTC", "Asia/Ho_Chi_Minh", "America/New_York"):
        db.connection().exec_driver_sql(f"SET LOCAL TIME ZONE '{zone}'")
        db.expire_all()
        assert db.get(Event, event_id).start_time == stamp
        assert db.get(Event, event_id).start_time.utcoffset() == timedelta(0)


@pytest.mark.parametrize("field,value", [
    ("capacity", 0), ("registered_count", -1), ("registered_count", 999), ("status", "NOT_A_STATUS"),
])
def test_database_rejects_invalid_event_values(client, auth_headers, db, field, value):
    org = auth_headers(role="ORGANIZER", email="constraint@example.com")
    event_id = client.post("/events", headers=org, json=event_payload()).json()["id"]
    setattr(db.get(Event, event_id), field, value)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_database_rejects_invalid_role_and_time_order(db, make_user):
    org = make_user("Org", "constraint-role@example.com", "ORGANIZER")
    org.role = "ADMIN"
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    stamp = utc_now() + timedelta(days=2)
    db.add(Event(organizer_id=org.id, title="Bad", description="d", location="VN", start_time=stamp,
                 end_time=stamp, capacity=10, status="DRAFT", registered_count=0, category="Test", banner_url=""))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@contextmanager
def select_queries():
    queries = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        # Exclude only the lifecycle sweep, which uses a separate background session.
        if statement.lstrip().upper().startswith("SELECT") and "events.status IN" not in statement:
            queries.append(statement)

    sql_event.listen(test_engine, "before_cursor_execute", capture)
    try:
        yield queries
    finally:
        sql_event.remove(test_engine, "before_cursor_execute", capture)


def test_staff_and_history_query_counts_do_not_grow_with_rows(client, auth_headers, make_user):
    org = auth_headers(role="ORGANIZER", email="query-org@example.com")
    event_id = client.post("/events", headers=org, json=event_payload()).json()["id"]
    client.post(f"/events/{event_id}/transition", headers=org, json={"status": "PUBLISHED"})
    tickets = []
    for number in range(4):
        staff = make_user(f"Staff {number}", f"query-staff{number}@example.com", "STAFF")
        assert client.post(f"/events/{event_id}/staff", headers=org, json={"staff_id": staff.id}).status_code == 201
        att = auth_headers(email=f"query-att{number}@example.com")
        tickets.append(client.post(f"/events/{event_id}/register", headers=att).json()["ticket"]["ticket_code"])
        with select_queries() as queries:
            rows = client.get(f"/events/{event_id}/staff", headers=org).json()
        assert len(rows) == number + 1
        assert len(queries) == 3
    client.post(f"/events/{event_id}/transition", headers=org, json={"status": "STARTED"})
    for number, code in enumerate(tickets):
        assert client.post("/checkins", headers=org, json={"ticket_code": code, "event_id": event_id}).status_code == 201
        with select_queries() as queries:
            rows = client.get(f"/events/{event_id}/checkins?limit=100", headers=org).json()
        assert len(rows) == number + 1
        assert len(queries) == 3


def test_cursor_survives_deleted_anchor_and_handles_identical_times(client, auth_headers):
    org = auth_headers(role="ORGANIZER", email="cursor@example.com")
    payload = event_payload()
    ids = {client.post("/events", headers=org, json={**payload, "title": f"Same {n}"}).json()["id"] for n in range(4)}
    first = client.get("/events?limit=2")
    anchor = first.json()[-1]["id"]
    cursor = first.headers["X-Next-Cursor"]
    assert client.delete(f"/events/{anchor}", headers=org).status_code == 204
    second = client.get("/events", params={"limit": 2, "cursor": cursor})
    assert second.status_code == 200
    assert {row["id"] for row in first.json() + second.json()} == ids
    assert client.get("/events", params={"cursor": anchor}).status_code == 404
    assert client.get("/events?cursor=e30").json()["code"] == "INVALID_CURSOR"


def test_routing_errors_use_common_contract(client):
    for response in (client.get("/missing-route"), client.get("/auth/login")):
        assert response.status_code in (404, 405)
        assert set(response.json()) == {"status", "code", "message"}
        assert response.json()["status"] == response.status_code


@pytest.mark.parametrize("changes", [{"id": 12}, {"id": None}, {"v": True}, {"v": 1.0}, {"time": []}])
def test_malformed_cursor_field_types_return_400(client, changes):
    payload = {"v": 1, "time": "2030-02-01T02:00:00Z", "id": "9fc897c8-598b-4f1d-bb44-c59dbe781101", **changes}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    response = client.get("/events", params={"cursor": cursor})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CURSOR"


@pytest.mark.parametrize("revision", [None, "0002_event_status_start_index", "0004_data_invariants"])
def test_startup_requires_migrated_event_schema(monkeypatch, revision):
    import app.db as database
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            if revision is not None:
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
                connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision})
        monkeypatch.setattr(database, "engine", engine)
        if revision == "0004_data_invariants":
            database.assert_schema_ready()
        else:
            with pytest.raises(RuntimeError, match="alembic upgrade head"):
                database.assert_schema_ready()
    finally:
        engine.dispose()
