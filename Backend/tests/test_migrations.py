"""Exercise legacy data conversion and downgrade on isolated databases/schemas."""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_migrations_preserve_legacy_event_time_and_data(tmp_path, backend):
    if backend == "postgresql":
        url = os.getenv("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("requires a separate TEST_POSTGRES_URL")
        assert (make_url(url).database or "").endswith(("_test", "_audit"))
    else:
        url = f"sqlite:///{(tmp_path / 'migration.sqlite').as_posix()}"
    engine = create_engine(url)
    schema = f"migration_{uuid.uuid4().hex}"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    stamp = datetime(2026, 10, 20, 9)
    with engine.connect() as connection:
        if backend == "postgresql":
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET search_path TO "{schema}"')
            connection.commit()
            # Never reuse the public version table created by CI's upgrade head.
            config.attributes["version_table_schema"] = schema
        config.attributes["connection"] = connection
        try:
            command.upgrade(config, "0002_event_status_start_index")
            connection.execute(text("INSERT INTO users (id,name,email,password_hash,role,avatar_url,created_at,updated_at) VALUES (:id,'Org','legacy@example.com','unused','ORGANIZER','',:stamp,:stamp)"), {"id": "legacy-organizer", "stamp": stamp})
            connection.execute(text("INSERT INTO events (id,organizer_id,title,description,location,start_time,end_time,capacity,registered_count,status,category,banner_url,created_at) VALUES ('legacy-event',:org,'Legacy','d','VN',:start,:end,10,0,'DRAFT','Test','https://example.com/banner.webp',:start)"), {"org": "legacy-organizer", "start": stamp, "end": datetime(2026, 10, 20, 12)})
            connection.commit()
            command.upgrade(config, "head")
            row = connection.execute(text("SELECT start_time,banner_url,title FROM events WHERE id='legacy-event'")).one()
            value = datetime.fromisoformat(row.start_time) if isinstance(row.start_time, str) else row.start_time
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            assert value == datetime(2026, 10, 20, 2, tzinfo=timezone.utc)
            assert (row.banner_url, row.title) == ("https://example.com/banner.webp", "Legacy")
            indexes = inspect(connection).get_indexes("events")
            assert any(index["column_names"] == ["status", "start_time", "id"] for index in indexes)
            assert not any(index["name"] in {"ix_events_status", "ix_events_status_start_time"} for index in indexes)
            assert {check["name"] for check in inspect(connection).get_check_constraints("events")} == {
                "ck_events_capacity", "ck_events_registered_count", "ck_events_status", "ck_events_time_order",
            }
            connection.commit()
            command.downgrade(config, "0002_event_status_start_index")
            old = connection.execute(text("SELECT start_time FROM events WHERE id='legacy-event'")).scalar()
            assert (datetime.fromisoformat(old) if isinstance(old, str) else old) == stamp
            connection.commit()
            command.upgrade(config, "head")
            command.downgrade(config, "base")
            assert set(inspect(connection).get_table_names()) <= {"alembic_version"}
        finally:
            connection.rollback()
            if backend == "postgresql":
                connection.exec_driver_sql("SET search_path TO public")
                # Only the unique schema this test just created is removed.
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
                connection.commit()
    engine.dispose()
