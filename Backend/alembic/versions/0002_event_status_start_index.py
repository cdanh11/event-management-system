"""Phase 2 (Tầng 3): composite index cho GET /events.

Revision ID: 0002_event_status_start_index
"""
from alembic import op

revision = '0002_event_status_start_index'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # 0001 dùng Base.metadata.create_all nên DB tạo mới đã có index này
    # từ models; if_not_exists giữ 0002 chạy được cho cả DB mới lẫn DB cũ.
    op.create_index(
        "ix_events_status_start_time", "events", ["status", "start_time"],
        if_not_exists=True,
    )


def downgrade():
    op.drop_index("ix_events_status_start_time", table_name="events")
