"""Tự động chuyển trạng thái event theo thời gian (không cần scheduler ngoài).

Quy tắc (wall-clock địa phương, khớp giờ event do organizer nhập):
- PUBLISHED/ONGOING và đã tới (start_time - 15 phút) -> STARTED (mở check-in).
- STARTED và đã qua end_time -> COMPLETED.

Chạy trong lifespan bằng asyncio task lặp mỗi 60 giây (DB sync chạy trong
threadpool qua asyncio.to_thread để không chặn event loop), mỗi lần flip xong
broadcast occupancy để mọi client WS cập nhật trạng thái realtime.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from ..db import SessionLocal
from ..models import Event, as_local_naive, localnow
from ..realtime import manager, occupancy_payload

logger = logging.getLogger("evently.lifecycle")

CHECKIN_OPENS_BEFORE_START = timedelta(minutes=15)
SWEEP_INTERVAL_SECONDS = 60


def _now() -> datetime:
    return localnow()


def _naive(value: datetime) -> datetime:
    return as_local_naive(value)


def sweep_due_events(session_factory=SessionLocal) -> list[dict]:
    """Quét 1 lượt, flip các event tới hạn, trả về occupancy payloads để broadcast.

    Hàm sync thuần (dễ test trực tiếp bằng session SQLite); lifespan gọi qua
    to_thread với SessionLocal mặc định.
    """
    db = session_factory()
    try:
        now = _now()
        flipped: list[dict] = []

        # Khóa event giống các endpoint nghiệp vụ, tránh ghi đè transition thủ công.
        due_events = db.scalars(
            select(Event).where(
                Event.status.in_(["PUBLISHED", "ONGOING", "STARTED"]),
                Event.start_time <= now + CHECKIN_OPENS_BEFORE_START,
            ).with_for_update()
        ).all()
        for event in due_events:
            # Sau downtime, sự kiện đã hết giờ phải COMPLETED ngay trong một sweep.
            # Không truy vấn lần hai trên dữ liệu chưa flush (autoflush=False).
            target = "COMPLETED" if event.end_time <= now else "STARTED"
            if event.status != target:
                event.status = target
                flipped.append(event)

        db.commit()
        payloads = []
        for event in flipped:
            db.refresh(event)
            payloads.append(occupancy_payload(event))
            logger.info("auto-transition event %s -> %s", event.id, event.status)
        return payloads
    finally:
        db.close()


async def lifecycle_loop() -> None:
    """Vòng lặp nền của lifespan: sweep mỗi 60s + broadcast từng event flip."""
    while True:
        try:
            for payload in await asyncio.to_thread(sweep_due_events):
                await manager.broadcast_occupancy(payload["event_id"], payload)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - sweep không được làm chết lifespan
            logger.exception("lifecycle sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
