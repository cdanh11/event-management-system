"""Router: sự kiện — đọc, tạo, dời lịch (Reschedule), chuyển trạng thái, thông báo.

Vòng đời sự kiện trọn vẹn phục vụ yêu cầu "Create–Reschedule–Complete–Notify":
  - Create:     POST  /events
  - Reschedule: PATCH /events/{id}      (đổi start/end time và thông tin khác)
  - Complete:   POST  /events/{id}/transition -> COMPLETED (kích hoạt Notify)
  - Notify:     POST  /events/{id}/notify       (endpoint async gửi thông báo)
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Event, Registration, User
from ..schemas import EventIn, EventOut, EventUpdateIn, NotifyOut, TransitionIn
from ..serializers import to_event
from ..services.notifier import notify_attendees

router = APIRouter()

# Máy trạng thái hợp lệ: trạng thái hiện tại -> tập các trạng thái được chuyển tới.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"PUBLISHED", "CANCELLED"},
    "PUBLISHED": {"ONGOING", "CANCELLED"},
    "ONGOING": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


def _validate_event_time(start: datetime, end: datetime) -> None:
    """Kiểm tra thời gian sự kiện: bắt đầu phải ở tương lai và trước thời điểm kết thúc.

    Hỗ trợ cả datetime có hoặc không có timezone: nếu ``start`` là naive thì
    ``now`` cũng dùng naive (datetime.now()), tránh lỗi so trộn "naive/aware".
    """
    now = datetime.now() if start.tzinfo is None else datetime.now(start.tzinfo)
    if start >= end or start <= now:
        api_error(
            400,
            "INVALID_EVENT_TIME",
            "Start time must be in the future and before end time",
        )


def _registered_emails(db: Session, event_id: str) -> list[str]:
    """Email của các attendee còn đăng ký hiệu lực cho sự kiện (để Notify)."""
    emails = db.scalars(
        select(User.email)
        .join(Registration, Registration.attendee_id == User.id)
        .where(Registration.event_id == event_id, Registration.status == "REGISTERED")
    ).all()
    return list(emails)


@router.get("/events", response_model=list[EventOut], tags=["events"])
def list_events(
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    """Danh sách sự kiện, có thể lọc theo status và tìm theo title (không dấu)."""
    stmt = select(Event)
    if status:
        stmt = stmt.where(Event.status == status)
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))
    return [to_event(e) for e in db.scalars(stmt.order_by(Event.start_time)).all()]


@router.get("/events/{event_id}", response_model=EventOut, tags=["events"])
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Chi tiết một sự kiện."""
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    return to_event(event)


@router.post("/events", response_model=EventOut, status_code=201, tags=["events"])
def create_event(
    payload: EventIn,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Tạo sự kiện mới (chỉ ORGANIZER). Status khởi tạo là DRAFT."""
    _validate_event_time(payload.start_time, payload.end_time)

    values = payload.model_dump()
    values["banner_url"] = values.pop("banner_image")  # đổi tên cột DB

    event = Event(organizer_id=user.id, **values)
    db.add(event)
    db.commit()
    db.refresh(event)
    return to_event(event)


@router.patch("/events/{event_id}", response_model=EventOut, tags=["events"])
def reschedule_event(
    event_id: str,
    payload: EventUpdateIn,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Dời lịch / cập nhật sự kiện (PATCH). Chỉ ORGANIZER sở hữu sự kiện.

    Chỉ cập nhật các field được gửi lên (exclude_unset); nếu đổi thời gian
    thì bắt buộc hợp lệ: start < end và start ở tương lai.
    """
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    updates = payload.model_dump(exclude_unset=True)
    if "banner_image" in updates:
        updates["banner_url"] = updates.pop("banner_image")

    new_start = updates.get("start_time", event.start_time)
    new_end = updates.get("end_time", event.end_time)
    _validate_event_time(new_start, new_end)

    for field, value in updates.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return to_event(event)


@router.post("/events/{event_id}/transition", response_model=EventOut, tags=["events"])
def transition_event(
    event_id: str,
    payload: TransitionIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Chuyển trạng thái sự kiện theo máy trạng thái VALID_TRANSITIONS.

    Khi sang COMPLETED, lên lịch background task gửi thông báo cho attendee.
    BackgroundTasks chỉ dành cho việc NGẮN sau response — không phải queue thật.
    """
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    if payload.status not in VALID_TRANSITIONS.get(event.status, set()):
        api_error(400, "INVALID_TRANSITION", "This event transition is not allowed")

    # Read emails trước khi commit để background task chỉ cần gửi, không truy DB.
    emails = _registered_emails(db, event.id) if payload.status == "COMPLETED" else []

    event.status = payload.status
    db.commit()
    db.refresh(event)

    if payload.status == "COMPLETED" and emails:
        # Đăng ký background task: FastAPI gọi async notify_attendees sau khi
        # response đã được gửi đi -> client không phải đợi việc gửi email.
        background_tasks.add_task(notify_attendees, event.title, emails)

    return to_event(event)


@router.post("/events/{event_id}/notify", response_model=NotifyOut, tags=["events"])
async def notify_event_now(
    event_id: str,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Gửi thông báo NGAY LẬP TỨC tới attendee — endpoint **async đúng chỗ**.

    Tại sao endpoint này nên là async:
      - Toàn bộ công việc còn lại sau khi đọc DB là một phép network I/O
        (gửi email/webhook) — có awaitable operation thật sự.
      - ``await notify_attendees(...)`` chờ phản hồi HTTP của dịch vụ gửi
        thông báo; trong lúc chờ, event loop vẫn phục vụ các request khác.

    So với transition->COMPLETED ở trên: endpoint đó dùng background task vì
    không muốn bắt client đợi; endpoint này chủ động chờ (organizer muốn gửi
    và chờ kết quả) — đây chính là "async đúng chỗ".
    """
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    emails = _registered_emails(db, event.id)

    # ĐIỂM MẤU CHỐT: đây là await I/O thật, không block event loop.
    sent = await notify_attendees(event.title, emails)

    mode = "webhook" if settings.notify_webhook_url else "simulated"
    return NotifyOut(event_id=event.id, emails_sent=sent, mode=mode)