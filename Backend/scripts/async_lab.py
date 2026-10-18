"""Opt-in one-worker lab: blocking async, sync threadpool, cooperative async.

From Backend: python scripts/async_lab.py --delay 2 --requests 3
Starts its own loopback server, prints timings/logs, then stops only that child.
No product endpoints, database, SMTP or external services are involved. Sleep
illustrates scheduling; it is not a measurement of real network/DB throughput.
"""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import httpx
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Isolated async scheduling lab")
logger = logging.getLogger("evently.async_lab")
delay_seconds = 2.0


def started(mode: str) -> float:
    stamp = time.perf_counter()
    logger.info("START mode=%s thread=%s monotonic=%.6f", mode, threading.get_ident(), stamp)
    return stamp


def completed(mode: str, start: float) -> dict:
    end = time.perf_counter()
    logger.info("END mode=%s thread=%s monotonic=%.6f", mode, threading.get_ident(), end)
    return {"mode": mode, "started": start, "finished": end}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/blocking-async")
async def blocking_async():
    start = started("blocking-async")
    time.sleep(delay_seconds)  # Deliberately wrong, confined to this lab.
    return completed("blocking-async", start)


@app.get("/sync-threadpool")
def sync_threadpool():
    start = started("sync-threadpool")
    time.sleep(delay_seconds)  # FastAPI dispatches this def handler to a thread.
    return completed("sync-threadpool", start)


@app.get("/cooperative-async")
async def cooperative_async():
    start = started("cooperative-async")
    await asyncio.sleep(delay_seconds)
    return completed("cooperative-async", start)


async def measure(base_url: str, requests: int, delay: float) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=delay * requests + 15, trust_env=False) as client:
        for mode in ("blocking-async", "sync-threadpool", "cooperative-async"):
            run_start = time.perf_counter()

            async def work():
                response = await client.get(f"/{mode}")
                response.raise_for_status()
                return response.json()

            jobs = [asyncio.create_task(work()) for _ in range(requests)]
            try:
                # Probe while the work requests should still be in progress.
                await asyncio.sleep(min(delay / 4, 0.1))
                probe_start = time.perf_counter()
                probe = await client.get("/health")
                probe.raise_for_status()
                probe_ms = (time.perf_counter() - probe_start) * 1000
                rows = await asyncio.gather(*jobs)
            finally:
                for job in jobs:
                    if not job.done():
                        job.cancel()
                await asyncio.gather(*jobs, return_exceptions=True)
            origin = min(row["started"] for row in rows)
            print(json.dumps({
                "mode": mode, "requests": requests, "delay_seconds": delay,
                "client_wall_ms": round((time.perf_counter() - run_start) * 1000, 3),
                "health_ms": round(probe_ms, 3),
                "server_intervals_ms": [
                    {"start": round((row["started"] - origin) * 1000, 3),
                     "end": round((row["finished"] - origin) * 1000, 3)} for row in rows
                ],
            }), flush=True)


def main() -> None:
    global delay_seconds
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=2)
    parser.add_argument("--requests", type=int, default=3)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0.01 <= args.delay <= 10 or not 2 <= args.requests <= 10 or not 1024 <= args.port <= 65535:
        parser.error("delay must be 0.01..10, requests 2..10, port 1024..65535")
    if args.serve:
        delay_seconds = args.delay
        logging.basicConfig(level=logging.INFO)
        uvicorn.run(app, host="127.0.0.1", port=args.port, workers=1, log_level="info")
        return
    # Refuse an occupied port rather than accidentally measuring another server.
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    base_url = f"http://127.0.0.1:{args.port}"
    child = subprocess.Popen([
        sys.executable, str(Path(__file__).resolve()), "--serve", "--port", str(args.port),
        "--delay", str(args.delay), "--requests", str(args.requests),
    ])
    try:
        with httpx.Client(base_url=base_url, timeout=0.5, trust_env=False) as probe:
            deadline = time.monotonic() + 20
            while True:
                if child.poll() is not None:
                    raise RuntimeError("Lab server exited before becoming ready")
                try:
                    if probe.get("/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("Lab server did not become ready")
                time.sleep(0.1)
        asyncio.run(measure(base_url, args.requests, args.delay))
    finally:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


if __name__ == "__main__":
    main()
