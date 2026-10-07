"""Đọc index/migration version từ DATABASE_URL; không thay đổi database."""
import os
import sqlalchemy as sa

e = sa.create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    rows = c.exec_driver_sql(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'events' ORDER BY 1"
    ).all()
    print([r[0] for r in rows])
    print(c.exec_driver_sql("SELECT version_num FROM alembic_version").all())
