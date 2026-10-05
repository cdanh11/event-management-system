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

# Client dùng chung (connection pooling): mở một lần, tái dùng socket/TLS
# cho mọi lần gửi thay vì new Client mỗi lần. Đóng ở lifespan shutdown.
_shared_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(timeout=5.0)
    return _shared_client


async def close_notifier_client() -> None:
    """Đóng shared client khi app shutdown (gọi từ lifespan)."""
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


async def _post_webhook(payload: dict) -> None:
    if not settings.notify_webhook_url:
        # Mô phỏng độ trễ mạng (vd gửi SMTP). Chỉ để demo async I/O.
        await asyncio.sleep(0.05)
        return
    # I/O THẬT: await phản hồi HTTP của dịch vụ gửi email/webhook bên ngoài.
    response = await _client().post(settings.notify_webhook_url, json=payload)
    response.raise_for_status()


async def notify_attendees(event_title: str, attendee_emails: list[str]) -> int:
    """Gửi thông báo tới danh sách email người tham dự.

    Returns:
        Số email đã gửi (chính bằng độ dài danh sách đầu vào).
    """
    await _post_webhook({"event": event_title, "recipients": attendee_emails})

    logger.info("notified %d attendees about event '%s'", len(attendee_emails), event_title)
    return len(attendee_emails)


async def send_ticket_email(
    to_email: str, event_title: str, ticket_code: str, qr_value: str
) -> str:
    """Gửi vé/QR cho 1 attendee sau khi đăng ký — chạy nền (Phase 2).

    Chỉ nhận kiểu nguyên thủy (str), KHÔNG nhận ORM: BackgroundTasks chạy
    sau khi response được gửi, lúc đó Session đã đóng, chạm ORM sẽ lỗi
    DetachedInstanceError. Webhook thật nếu có NOTIFY_WEBHOOK_URL,
    ngược lại mô phỏng I/O (không cần SMTP thật).
    """
    await _post_webhook({
        "type": "ticket",
        "to": to_email,
        "event": event_title,
        "ticket_code": ticket_code,
        "qr_value": qr_value,
    })

    logger.info("sent ticket %s to %s for event '%s'", ticket_code, to_email, event_title)
    return ticket_code