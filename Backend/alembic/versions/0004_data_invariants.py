"""Protect domain values in DB and align index with keyset ordering.

Invalid existing rows stop the migration; no user data is silently corrected.
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_data_invariants"
down_revision = "0003_event_utc"
branch_labels = None
depends_on = None

CHECKS = {
    "users": {"ck_users_role": "role IN ('ORGANIZER','STAFF','ATTENDEE')"},
    "events": {
        "ck_events_status": "status IN ('DRAFT','PUBLISHED','ONGOING','STARTED','COMPLETED','CANCELLED')",
        "ck_events_capacity": "capacity > 0",
        "ck_events_registered_count": "registered_count >= 0 AND registered_count <= capacity",
        "ck_events_time_order": "end_time > start_time",
    },
    "registrations": {"ck_registrations_status": "status IN ('REGISTERED','CANCELLED')"},
    "tickets": {"ck_tickets_status": "status IN ('VALID','USED','CANCELLED')"},
    "checkins": {"ck_checkins_status": "status = 'SUCCESS'"},
}


def upgrade():
    connection = op.get_bind()
    for table, checks in CHECKS.items():
        for name, condition in checks.items():
            invalid = connection.execute(sa.text(f"SELECT id FROM {table} WHERE NOT ({condition}) LIMIT 1")).first()
            if invalid:
                raise RuntimeError(f"Cannot apply {name}: {table} row {invalid[0]} violates the constraint")
        with op.batch_alter_table(table) as batch:
            for name, condition in checks.items():
                batch.create_check_constraint(name, condition)
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_status_start_time", table_name="events")
    op.create_index("ix_events_status_start_time_id", "events", ["status", "start_time", "id"])


def downgrade():
    op.drop_index("ix_events_status_start_time_id", table_name="events")
    op.create_index("ix_events_status_start_time", "events", ["status", "start_time"])
    op.create_index("ix_events_status", "events", ["status"])
    for table, checks in reversed(list(CHECKS.items())):
        with op.batch_alter_table(table) as batch:
            for name in checks:
                batch.drop_constraint(name, type_="check")
