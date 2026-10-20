"""Event time contract: UTC in storage/API, Vietnam time for legacy naive input.

No conversion relies on the server's timezone. Audit/token columns from the
initial schema remain UTC-naive; event start/end use UTC-aware timestamps.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

EVENT_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def event_utc(value: datetime) -> datetime:
    """Naive values mean Vietnam wall-clock; aware values retain their instant."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=EVENT_TIMEZONE)
    return value.astimezone(timezone.utc)


class EventDateTime(TypeDecorator):
    """PostgreSQL timestamptz; SQLite UTC-naive storage with aware Python values.

    SQLite has no native timezone type. Restore UTC on reads so comparisons
    and API output follow the same contract in both test backends.
    """
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name == "postgresql"))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = event_utc(value)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # A naive value here is already stored in UTC, unlike legacy API input.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
