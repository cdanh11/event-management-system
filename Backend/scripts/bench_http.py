"""Read-only sequential HTTP latency samples for GET /events.

Run an API against the dedicated benchmark DB with --workers 1 and no reload.
Then: python scripts/bench_http.py --base-url http://127.0.0.1:8001 --offset 74980
Uses the opaque cursor, checks equal pages, and reports warm median/p95. URL is
loopback-only. Verify its API uses the intended test DB yourself; HTTP cannot
discover DATABASE_URL. This is not a throughput/load benchmark.
"""
import argparse
import json
import time
from urllib.parse import urlsplit

import httpx

from benchmark_utils import summarize_ms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if (url.scheme not in {"http", "https"} or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment):
        parser.error("Use a loopback HTTP(S) origin, without credentials/path/query")
    if args.offset < 1 or not 1 <= args.limit <= 100 or args.iters < 1 or args.warmup < 0:
        parser.error("offset >= 1, limit 1..100, iters >= 1, warmup >= 0 required")
    with httpx.Client(base_url=args.base_url, timeout=30, follow_redirects=False, trust_env=False) as client:
        anchor = client.get("/events", params={"status": "PUBLISHED", "limit": 1, "offset": args.offset - 1})
        anchor.raise_for_status()
        token = anchor.headers.get("X-Next-Cursor")
        if len(anchor.json()) != 1 or not token:
            raise RuntimeError("No anchor at this OFFSET; create the benchmark dataset first")
        variants = {
            "offset": {"status": "PUBLISHED", "limit": args.limit, "offset": args.offset},
            "cursor": {"status": "PUBLISHED", "limit": args.limit, "cursor": token},
        }
        samples = {name: [] for name in variants}
        expected_ids = None
        for number in range(args.warmup + args.iters):
            names = list(variants) if number % 2 == 0 else list(reversed(variants))
            for name in names:
                start = time.perf_counter()
                response = client.get("/events", params=variants[name])
                response.raise_for_status()
                rows = response.json()
                elapsed = (time.perf_counter() - start) * 1000
                ids = [row["id"] for row in rows]
                if len(ids) != args.limit:
                    raise RuntimeError("Incomplete page; check OFFSET and dataset")
                if expected_ids is None:
                    expected_ids = ids
                elif ids != expected_ids:
                    raise RuntimeError("Page changed: stop concurrent writers before benchmarking")
                if number >= args.warmup:
                    samples[name].append(elapsed)
        print(json.dumps({"base_url": args.base_url, "offset": args.offset, "limit": args.limit,
                          "iterations": args.iters, "warmup": args.warmup,
                          "clock": "HTTP round-trip plus JSON decode; keep-alive; sequential warm samples",
                          "results": {name: summarize_ms(values) for name, values in samples.items()}}))


if __name__ == "__main__":
    main()
