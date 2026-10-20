"""SQL benchmark on a migrated, dedicated PostgreSQL *_test / *_audit DB.

From Backend: python scripts/bench_events.py --rows 100000 --iters 100
DATABASE_URL must point at the dedicated DB. Default rolls back all seed/DDL.
--keep-data explicitly commits the dataset for a later HTTP benchmark. Remove
it with --cleanup-organizer <printed UUID> when finished. Do not run while a
test suite or another writer is using that database.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID, uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cursors import encode_event_cursor
from scripts.benchmark_utils import summarize_ms

INDEX = "ix_events_status_start_time_id"
# Complete ORM projection of GET /events, rather than SELECT id.
PROJECTION = "id,organizer_id,title,description,location,start_time,end_time,capacity,registered_count,status,category,banner_url,created_at"
FILTER = "FROM events WHERE status = 'PUBLISHED'"


def seed(cursor, rows: int, organizer: str) -> None:
    base = datetime.now(timezone.utc) + timedelta(days=30)
    audit = base.replace(tzinfo=None)
    cursor.execute(
        "INSERT INTO users (id,name,email,password_hash,role,avatar_url,created_at,updated_at) "
        "VALUES (%s,'SQL benchmark',%s,'unused','ORGANIZER','',%s,%s)",
        (organizer, f"bench-{organizer}@example.com", audit, audit),
    )
    sql = ("INSERT INTO events (id,organizer_id,title,description,location,start_time,end_time,"
           "capacity,registered_count,status,category,banner_url,created_at) "
           "VALUES (%s,%s,%s,'Benchmark only','HCMC',%s,%s,1000,0,%s,'__BENCH__','',%s)")
    for begin in range(0, rows, 2000):
        batch = []
        for number in range(begin, min(begin + 2000, rows)):
            # Mixed status, ten equal timestamps per group, bounded batches.
            start = base + timedelta(minutes=number // 10)
            batch.append((str(uuid4()), organizer, f"bench-{number}", start,
                          start + timedelta(hours=2), "DRAFT" if number % 4 == 0 else "PUBLISHED", audit))
        cursor.executemany(sql, batch)


def cleanup(cursor, organizer: str) -> int:
    organizer = str(UUID(organizer))
    cursor.execute("SELECT email,password_hash FROM users WHERE id=%s", (organizer,))
    if cursor.fetchone() != (f"bench-{organizer}@example.com", "unused"):
        raise ValueError("Not an organizer created by this benchmark")
    cursor.execute("SELECT count(*) FROM events WHERE organizer_id=%s AND category <> '__BENCH__'", (organizer,))
    if cursor.fetchone()[0]:
        raise ValueError("Organizer owns non-benchmark events; refusing cleanup")
    # FK constraints also refuse removal if registrations were added later.
    cursor.execute("DELETE FROM events WHERE organizer_id=%s AND category='__BENCH__'", (organizer,))
    count = cursor.rowcount
    cursor.execute("DELETE FROM users WHERE id=%s", (organizer,))
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--offset", type=int, help="Default: last full PUBLISHED page")
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--cleanup-organizer")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or args.rows < args.limit * 2 or args.iters < 1 or args.warmup < 0:
        parser.error("rows >= 2*limit, limit 1..100, iters >= 1, warmup >= 0 required")
    dsn = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    if not dsn or not conninfo_to_dict(dsn).get("dbname", "").endswith(("_test", "_audit")):
        parser.error("DATABASE_URL must point to a dedicated PostgreSQL *_test or *_audit DB")
    with psycopg.connect(dsn) as connection:
        committed = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '120s'")
                cursor.execute("SELECT version_num FROM alembic_version")
                if cursor.fetchone() != ("0004_data_invariants",):
                    raise RuntimeError("Migrate the dedicated benchmark DB to head first")
                if args.cleanup_organizer:
                    removed = cleanup(cursor, args.cleanup_organizer)
                    connection.commit()
                    committed = True
                    print(json.dumps({"removed_benchmark_events": removed}))
                    return
                organizer = str(uuid4())
                seed(cursor, args.rows, organizer)
                cursor.execute("ANALYZE events")
                cursor.execute(f"SELECT count(*) {FILTER}")
                total = cursor.fetchone()[0]
                offset = args.offset if args.offset is not None else total - args.limit
                if not 1 <= offset <= total - args.limit:
                    raise ValueError("OFFSET must leave a full page and be at least 1")
                cursor.execute(f"SELECT start_time,id {FILTER} ORDER BY start_time,id LIMIT 1 OFFSET %s", (offset - 1,))
                anchor = cursor.fetchone()
                queries = {
                    "offset": (f"SELECT {PROJECTION} {FILTER} ORDER BY start_time,id LIMIT %s OFFSET %s", (args.limit, offset)),
                    "cursor": (f"SELECT {PROJECTION} {FILTER} AND (start_time,id) > (%s,%s) ORDER BY start_time,id LIMIT %s", (*anchor, args.limit)),
                }
                cursor.execute("SELECT current_setting('server_version')")
                print(json.dumps({"postgresql": cursor.fetchone()[0], "seed_rows": args.rows,
                                  "published_rows": total, "offset": offset, "limit": args.limit,
                                  "iterations": args.iters, "warmup": args.warmup,
                                  "projection": PROJECTION, "clock": "client perf_counter; DB round-trip and fetch"}))

                def plans(label):
                    for name, (sql, params) in queries.items():
                        cursor.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
                        print(f"\n{label} / {name}\n" + "\n".join(row[0] for row in cursor.fetchall()))

                # Roll back to the saved index, even if EXPLAIN fails. This
                # restores its exact definition, including with --keep-data.
                cursor.execute("SAVEPOINT index_comparison")
                try:
                    cursor.execute(f"DROP INDEX {INDEX}")
                    plans("without composite index")
                finally:
                    cursor.execute("ROLLBACK TO SAVEPOINT index_comparison")
                    cursor.execute("RELEASE SAVEPOINT index_comparison")
                plans("with composite index")
                ids = []
                samples = {name: [] for name in queries}
                for number in range(args.warmup + args.iters):
                    names = list(queries) if number % 2 == 0 else list(reversed(queries))
                    for name in names:
                        sql, params = queries[name]
                        start = time.perf_counter()
                        cursor.execute(sql, params)
                        result = cursor.fetchall()
                        elapsed = (time.perf_counter() - start) * 1000
                        if number == 0:
                            ids.append([row[0] for row in result])
                        if number >= args.warmup:
                            samples[name].append(elapsed)
                if ids[0] != ids[1]:
                    raise AssertionError("Offset and cursor did not return the same page")
                print(json.dumps({name: summarize_ms(values) for name, values in samples.items()}))
                print("EXPLAIN Planning/Execution Time exclude client network and HTTP; samples are warm, not a load test.")
                if args.keep_data:
                    connection.commit()
                    committed = True
                    print(json.dumps({"kept_organizer": organizer, "http_offset": offset,
                                      "http_cursor": encode_event_cursor(*anchor)}))
        finally:
            if not committed:
                connection.rollback()
                print("Rolled back benchmark data and DDL")


if __name__ == "__main__":
    main()
