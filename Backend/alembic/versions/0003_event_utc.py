"""Convert legacy Vietnam wall-clock event times to UTC instants.

Existing start/end values were entered in Vietnam time, not UTC. PostgreSQL
AT TIME ZONE interprets that wall-clock before converting to timestamptz.
Audit/token columns are already UTC-naive and are intentionally unchanged.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa

revision = "0003_event_utc"
down_revision = "0002_event_status_start_index"
branch_labels = None
depends_on = None
LEGACY_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def _sqlite_convert(to_utc: bool) -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id,start_time,end_time FROM events")).all()
    for event_id, start, end in rows:
        converted = []
        for value in (start, end):
            value = datetime.fromisoformat(value) if isinstance(value, str) else value
            source = LEGACY_ZONE if to_utc else timezone.utc
            target = timezone.utc if to_utc else LEGACY_ZONE
            if value.tzinfo is None:
                value = value.replace(tzinfo=source)
            converted.append(value.astimezone(target).replace(tzinfo=None).isoformat(sep=" "))
        connection.execute(sa.text("UPDATE events SET start_time=:start,end_time=:end WHERE id=:id"),
                           {"start": converted[0], "end": converted[1], "id": event_id})


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        for column in ("start_time", "end_time"):
            op.alter_column("events", column, existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            postgresql_using=f"{column} AT TIME ZONE 'Asia/Ho_Chi_Minh'")
    else:
        _sqlite_convert(to_utc=True)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for column in ("start_time", "end_time"):
            op.alter_column("events", column, existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            postgresql_using=f"{column} AT TIME ZONE 'Asia/Ho_Chi_Minh'")
    else:
        _sqlite_convert(to_utc=False)
