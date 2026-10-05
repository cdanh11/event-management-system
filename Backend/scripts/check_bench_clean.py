import sqlalchemy as sa

e = sa.create_engine("postgresql+psycopg://evently:evently@localhost:5433/evently")
with e.connect() as c:
    print("bench events left:", c.exec_driver_sql(
        "SELECT count(*) FROM events WHERE category = '__BENCH__'").scalar())
    print("bench users left:", c.exec_driver_sql(
        "SELECT count(*) FROM users WHERE name = 'bench'").scalar())
    print("events total:", c.exec_driver_sql("SELECT count(*) FROM events").scalar())
