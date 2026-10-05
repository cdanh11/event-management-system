import sqlalchemy as sa

e = sa.create_engine("postgresql+psycopg://evently:evently@localhost:5433/evently")
with e.connect() as c:
    rows = c.exec_driver_sql(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'events' ORDER BY 1"
    ).all()
    print([r[0] for r in rows])
    print(c.exec_driver_sql("SELECT version_num FROM alembic_version").all())
