"""Dịch vụ thông báo — minh chứng "async I/O đúng chỗ".

Đây là hàm được await trưng trong endpoints/bacground task:
- Công việc DUY NHẤT là network I/O (gửi email qua webhook/SMTP).
- Nếu cấu hình NOTIFY_WEBHOOK_URL, thật sự ``await`` một request HTTP
  (httpx.AsyncClient) — không block event loop.
- Nếu chưa cấu hình, mô phỏng độ trễ mạng bằng ``asyncio.sleep`` để demo:
  điểm mấu chốt là ``await`` giải phóng event loop cho request khác chạy.

Phân biệt với "queue thật": BackgroundTasks/await như thế này chỉ phù hợp
công việc NGẮN sau response. Tác vụ nặng/dài phải dùng queue (RabbitMQ,
Celery, Redis Streams...) — KHÔNG nhét vào BackgroundTasks.
"""
import asyncio
import logging

import httpx

from ..config import settings

logger = logging.getLogger("evently.notifier")


async def notify_attendees(event_title: str, attendee_emails: list[str]) -> int:
    """Gửi thông báo tới danh sách email người tham dự.

    Returns:
        Số email đã gửi (chính bằng độ dài danh sách đầu vào).
    """
    if settings.notify_webhook_url:
        # I/O THẬT: await phản hồi HTTP từ dịch vụ gửi email/webhook bên ngoài.
        payload = {"event": event_title, "recipients": attendee_emails}
        async with httpx.AsyncClient() as client:
            response = await client.post( # chờ server trả lời mà không chặn event loop, có thể xử lý việc khác
                settings.notify_webhook_url, json=payload, timeout=5.0
            )
            response.raise_for_status()
    else:
        # Mô phỏng độ trễ mạng (vd gửi SMTP). Chỉ để demo async I/O.
        await asyncio.sleep(0.05)

    logger.info("notified %d attendees about event '%s'", len(attendee_emails), event_title)
    return len(attendee_emails)