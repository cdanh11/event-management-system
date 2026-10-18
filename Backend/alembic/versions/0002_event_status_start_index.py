"""Phase 2 (Tầng 3): composite index cho GET /events.

Revision ID: 0002_event_status_start_index
"""
from alembic import op

revision = '0002_event_status_start_index'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # 0001 là snapshot schema cố định. if_not_exists tương thích cả database
    # cũ từng được tạo trực tiếp bằng ORM trước khi có migration.
    op.create_index(
        "ix_events_status_start_time", "events", ["status", "start_time"],
        if_not_exists=True,
    )


def downgrade():
    op.drop_index("ix_events_status_start_time", table_name="events")
