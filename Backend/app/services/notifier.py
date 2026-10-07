"""Dịch vụ thông báo — minh chứng "async I/O đúng chỗ".

Các hàm được await trong endpoint hoặc BackgroundTasks:
- Webhook dùng httpx async; SMTP sync chạy trong thread qua asyncio.to_thread.
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
import smtplib
import ssl
from email.message import EmailMessage
from io import BytesIO

import httpx

from ..config import settings

logger = logging.getLogger("evently.notifier")


class NotificationError(Exception):
    """Lỗi transport đã chuẩn hóa; không làm rollback vé đã được cấp."""


def notification_mode() -> str:
    return "smtp" if settings.smtp_host else "webhook" if settings.notify_webhook_url else "simulated"


def _send_smtp(payload: dict) -> None:
    """I/O blocking: chỉ gọi từ to_thread, không gọi trực tiếp trên event loop.

    Mỗi recipient có thư riêng. Gửi vé kèm PNG QR chứa đúng mã backend cấp.
    Connection có timeout; thư lỗi không được ghi là đã gửi thành công.
    """
    recipients = [payload["to"]] if payload.get("type") == "ticket" else payload["recipients"]
    if not recipients:
        return
    try:
        client_type = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
        options = {"context": ssl.create_default_context()} if settings.smtp_ssl else {}
        with client_type(settings.smtp_host, settings.smtp_port, timeout=5, **options) as smtp:
            if settings.smtp_starttls and not settings.smtp_ssl:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            title = payload["event"].replace("\r", " ").replace("\n", " ")
            for recipient in recipients:
                message = EmailMessage()
                message["From"] = settings.smtp_from
                message["To"] = recipient
                if payload.get("type") == "ticket":
                    message["Subject"] = f"Evently ticket: {title}"
                    message.set_content(f"Registration confirmed for {title}.\nTicket code: {payload['ticket_code']}\nShow the attached QR at check-in.\n")
                    import qrcode

                    png = BytesIO()
                    qrcode.make(payload["qr_value"]).save(png, format="PNG")
                    message.add_attachment(png.getvalue(), maintype="image", subtype="png", filename="ticket-qr.png")
                else:
                    message["Subject"] = f"Evently: {title} ({payload['subject']})"
                    message.set_content(f"Event: {title}\nNotification: {payload['subject']}\nPlease check the event page for current details.\n")
                refused = smtp.send_message(message)
                if refused:
                    raise NotificationError("SMTP rejected a recipient")
    except (smtplib.SMTPException, OSError) as exc:
        raise NotificationError("SMTP delivery failed") from exc


async def _deliver(payload: dict) -> None:
    if settings.smtp_host:
        await asyncio.to_thread(_send_smtp, payload)
    else:
        await _post_webhook(payload)

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
        # Không có transport: mô phỏng I/O, không gửi email thật.
        await asyncio.sleep(0.05)
        return
    # I/O THẬT: await phản hồi HTTP của dịch vụ gửi email/webhook bên ngoài.
    response = await _client().post(settings.notify_webhook_url, json=payload)
    response.raise_for_status()


async def notify_attendees(
    event_title: str, attendee_emails: list[str], subject: str = "update"
) -> int:
    """Gửi thông báo tới danh sách email người tham dự.

    ``subject`` phân biệt mail hoàn thành / mail hủy (vd "cancelled").
    Returns:
        Số người nhận đã xử lý; simulated không khẳng định đã giao email.
    """
    await _deliver(
        {"event": event_title, "recipients": attendee_emails, "subject": subject}
    )

    logger.info(
        "notified %d attendees about event '%s' (%s)",
        len(attendee_emails), event_title, subject,
    )
    return len(attendee_emails)


async def send_ticket_email(
    to_email: str, event_title: str, ticket_code: str, qr_value: str
) -> str:
    """Gửi vé/QR cho 1 attendee sau khi đăng ký — chạy nền sau commit.

    Chỉ nhận kiểu nguyên thủy (str), KHÔNG nhận ORM: BackgroundTasks chạy
    sau khi response được gửi, lúc đó Session đã đóng, chạm ORM sẽ lỗi
    DetachedInstanceError. Ưu tiên SMTP, tiếp đến webhook; không cấu hình
    transport thì chỉ mô phỏng. SMTP chạy trong thread để tránh chặn event loop.
    """
    try:
        await _deliver({
            "type": "ticket", "to": to_email, "event": event_title,
            "ticket_code": ticket_code, "qr_value": qr_value,
        })
    except (httpx.HTTPError, NotificationError):
        # Vé đã commit trước response: lỗi transport không được làm mất vé.
        logger.exception("ticket notification failed for event '%s'", event_title)
        return ""

    logger.info("ticket notification completed (%s)", notification_mode())
    return ticket_code


async def notify_in_background(event_title: str, emails: list[str], subject: str) -> None:
    """Task sau commit: ghi nhận lỗi gửi, không giả định rollback được response."""
    try:
        await notify_attendees(event_title, emails, subject)
    except (httpx.HTTPError, NotificationError):
        logger.exception("background notification failed for event '%s'", event_title)
