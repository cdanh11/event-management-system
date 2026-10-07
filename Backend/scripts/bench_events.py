"""Benchmark PostgreSQL trên DB test; rollback dữ liệu và index tạm khi xong.

Chạy từ Backend: DATABASE_URL trỏ DB *_test hoặc *_audit, rồi
python scripts/bench_events.py --rows 3000 --iters 20.
DROP/CREATE index khóa bảng trong lúc đo; không dùng DB đang phục vụ demo.
"""
import argparse
import os
import statistics
import time
from datetime import datetime, timedelta
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--iters", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit < args.rows or args.iters < 1:
        parser.error("Cần rows > limit >= 1 và iters >= 1")
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    if not dsn or not conninfo_to_dict(dsn).get("dbname", "").endswith(("_test", "_audit")):
        parser.error("DATABASE_URL phải trỏ PostgreSQL *_test hoặc *_audit riêng")
    with psycopg.connect(dsn) as connection:
        try:
            with connection.cursor() as cursor:
                organizer_id = str(uuid4())
                base = datetime.now() + timedelta(days=30)
                cursor.execute(
                    "INSERT INTO users (id,name,email,password_hash,role,avatar_url,created_at,updated_at) "
                    "VALUES (%s,'bench',%s,'unused','ORGANIZER','',%s,%s)",
                    (organizer_id, f"bench-{organizer_id}@demo.com", base, base),
                )
                cursor.executemany(
                    "INSERT INTO events (id,organizer_id,title,description,location,start_time,end_time,"
                    "capacity,registered_count,status,category,banner_url,created_at) "
                    "VALUES (%s,%s,%s,'benchmark','HCMC',%s,%s,1000,0,'PUBLISHED','__BENCH__','',%s)",
                    [(str(uuid4()), organizer_id, f"bench-{n}", base + timedelta(seconds=n),
                      base + timedelta(seconds=n, hours=2), base) for n in range(args.rows)],
                )
                cursor.execute("ANALYZE events")
                query = "FROM events WHERE status = 'PUBLISHED'"
                cursor.execute(f"SELECT count(*) {query}")
                total = cursor.fetchone()[0]
                offset = total - args.limit
                cursor.execute(f"SELECT start_time,id {query} ORDER BY start_time,id LIMIT 1 OFFSET %s", (offset - 1,))
                anchor = cursor.fetchone()

                def explain():
                    cursor.execute(f"EXPLAIN ANALYZE SELECT id {query} ORDER BY start_time,id LIMIT %s", (args.limit,))
                    return "\n".join(row[0] for row in cursor.fetchall())

                cursor.execute("DROP INDEX IF EXISTS ix_events_status_start_time")
                before = explain()
                cursor.execute("CREATE INDEX ix_events_status_start_time ON events (status,start_time)")
                after = explain()

                def measure(sql, params):
                    durations = []
                    for _ in range(args.iters):
                        started = time.perf_counter()
                        cursor.execute(sql, params)
                        cursor.fetchall()
                        durations.append((time.perf_counter() - started) * 1000)
                    return statistics.mean(durations)

                offset_ms = measure(f"SELECT id {query} ORDER BY start_time,id LIMIT %s OFFSET %s", (args.limit, offset))
                cursor_ms = measure(f"SELECT id {query} AND (start_time,id) > (%s,%s) ORDER BY start_time,id LIMIT %s", (*anchor, args.limit))
                print(f"temporary_rows={args.rows}, published_rows={total}, limit={args.limit}, iterations={args.iters}")
                print("Without composite index:\n" + before)
                print("With composite index:\n" + after)
                print(f"Offset average: {offset_ms:.3f} ms; cursor average: {cursor_ms:.3f} ms")
        finally:
            # Rollback INSERT và DDL, kể cả khi query hoặc đo bị lỗi.
            connection.rollback()
            print("Rolled back benchmark data and index changes")


if __name__ == "__main__":
    main()
