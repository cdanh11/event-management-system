"""Phase 2 (Tầng 3): benchmark GET /events trên PostgreSQL thật.

- Seed N event PUBLISHED (category='__BENCH__'), đo rồi xóa sạch.
- So sánh: EXPLAIN ANALYZE trước/sau composite index + timing
  offset deep-page vs cursor keyset.
- Chạy:  docker compose up -d db
-         DATABASE_URL=... python scripts/bench_events.py --rows 3000

KHÔNG chạy trên DB có dữ liệu thật quan trọng (script DROP/CREATE index).
"""

import argparse
import os
import statistics
import time
import uuid
from datetime import datetime, timedelta

import psycopg

DSN = os.getenv("DATABASE_URL", "postgresql://evently:evently@localhost:5433/evently")
DSN = DSN.replace("postgresql+psycopg://", "postgresql://")
INDEX = "ix_events_status_start_time"


def q(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3000)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--iters", type=int, default=20)
    args = ap.parse_args()

    conn = psycopg.connect(DSN, autocommit=True)
    cur = conn.cursor()
    base = datetime(2027, 1, 1)
    uid = str(uuid.uuid4())

    now = datetime(2027, 1, 1)
    cur.execute("INSERT INTO users (id, name, email, password_hash, role, avatar_url,"
                " created_at, updated_at) "
                "VALUES (%s, 'bench', %s, 'x', 'ORGANIZER', '', %s, %s)",
                (uid, f"bench-{uid[:8]}@demo.com", now, now))
    cur.executemany(
        "INSERT INTO events (id, organizer_id, title, description, location,"
        " start_time, end_time, capacity, registered_count, status, category, banner_url,"
        " created_at)"
        " VALUES (%s, %s, %s, 'b', 'HCMC', %s, %s, 1000, 0, 'PUBLISHED', '__BENCH__', '', %s)",
        [(str(uuid.uuid4()), uid, f"bench-{i}", base + timedelta(seconds=i),
          base + timedelta(seconds=i, hours=2), now) for i in range(args.rows)],
    )
    print(f"seeded {args.rows} bench events")
    cur.execute("ANALYZE events")  # thống kê mới để planner chọn plan trung thực

    # Đo đúng shape query của GET /events (lọc status + sắp xếp start_time).
    filt = "FROM events WHERE status = 'PUBLISHED'"
    anchor = q(cur, f"SELECT start_time, id {filt} ORDER BY start_time, id"
                    f" LIMIT 1 OFFSET {args.rows - args.limit - 1}")[0]
    offset_sql = (f"SELECT id {filt} ORDER BY start_time, id"
                  f" LIMIT {args.limit} OFFSET {args.rows - args.limit}")
    cursor_sql = (f"SELECT id {filt} AND (start_time, id) > (%s, %s)"
                  f" ORDER BY start_time, id LIMIT {args.limit}")

    def explain():
        return "\n".join(r[0] for r in q(cur, f"EXPLAIN ANALYZE SELECT id {filt}"
                                              " ORDER BY start_time, id LIMIT 20"))

    cur.execute(f"DROP INDEX IF EXISTS {INDEX}")
    plan_before = explain()
    cur.execute(f"CREATE INDEX {INDEX} ON events (status, start_time)")
    plan_after = explain()

    def bench(sql, params=()):
        ts = []
        for _ in range(args.iters):
            t = time.perf_counter()
            q(cur, sql, params)
            ts.append((time.perf_counter() - t) * 1000)
        return statistics.mean(ts)

    t_offset = bench(offset_sql)
    t_cursor = bench(cursor_sql, anchor)

    cur.execute("DELETE FROM events WHERE category = '__BENCH__'")
    cur.execute("DELETE FROM users WHERE id = %s", (uid,))
    conn.close()

    print("\n--- EXPLAIN ANALYZE (no index) ---")
    print(plan_before)
    print("\n--- EXPLAIN ANALYZE (with ix_events_status_start_time) ---")
    print(plan_after)
    print(f"\nrows={args.rows} limit={args.limit} iters={args.iters}")
    print(f"offset deep-page avg: {t_offset:.2f} ms")
    print(f"cursor keyset    avg: {t_cursor:.2f} ms")
    print("bench rows cleaned up (index kept, from migration 0002)")


if __name__ == "__main__":
    main()
