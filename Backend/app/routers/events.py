"""Router: sự kiện — đọc, tạo, dời lịch (Reschedule), chuyển trạng thái, thông báo.

Vòng đời sự kiện trọn vẹn phục vụ yêu cầu "Create–Reschedule–Complete–Notify":
  - Create:     POST  /events
  - Reschedule: PATCH /events/{id}      (đổi start/end time và thông tin khác)
  - Complete:   POST  /events/{id}/transition -> COMPLETED (kích hoạt Notify)
  - Notify:     POST  /events/{id}/notify       (endpoint async gửi thông báo)
"""
from datetime import datetime
from dataclasses import dataclass
import httpx

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import bearer, get_authenticated_user, require
from ..errors import api_error
from ..models import Event, Registration, User
from ..schemas import (
    AUTH_RESPONSES,
    ERROR_404,
    ERROR_409,
    EventIn,
    EventOut,
    EventStatus,
    EventUpdateIn,
    NotifyOut,
    TransitionIn,
)
from ..realtime import manager, occupancy_payload
from ..serializers import to_event
from ..services.notifier import NotificationError, notification_mode, notify_attendees, notify_in_background

router = APIRouter()

# Máy trạng thái hợp lệ: trạng thái hiện tại -> tập các trạng thái được chuyển tới.
# PUBLISHED (public/mở đăng ký) -> ONGOING (đóng đăng ký, organizer chuẩn bị)
#   -> STARTED (mở check-in, tự động trước giờ bắt đầu 15 phút) -> COMPLETED
#   (tự động khi hết giờ). Hủy được ở DRAFT/PUBLISHED/ONGOING.
# Organizer có mọi quyền ở mọi trạng thái nên được phép nhảy cóc tiến
# (vd PUBLISHED -> STARTED để mở check-in sớm).
VALID_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"PUBLISHED", "CANCELLED"},
    "PUBLISHED": {"ONGOING", "STARTED", "CANCELLED"},
    "ONGOING": {"STARTED", "CANCELLED"},
    "STARTED": {"COMPLETED"},
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


@dataclass(frozen=True)
class NotificationTarget:
    """Chuẩn bị quyền/dữ liệu bằng dependency sync trước khi gửi thông báo."""

    event_id: str
    event_title: str
    attendee_emails: list[str]


def _notification_target(
    event_id: str,
    credentials: str | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> NotificationTarget:
    """Xác thực và đọc DB trong sync dependency, trước event loop async."""
    user = get_authenticated_user(credentials, db)
    if user.role != "ORGANIZER":
        api_error(403, "FORBIDDEN", "Insufficient permission")

    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    return NotificationTarget(
        event_id=event.id,
        event_title=event.title,
        attendee_emails=_registered_emails(db, event.id),
    )


@router.get("/events", response_model=list[EventOut], tags=["events"])
def list_events(
    status: EventStatus | None = None,
    q: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None),
    response: Response = None,  # type: ignore[assignment]  # FastAPI inject Response
    db: Session = Depends(get_db),
):
    """Danh sách sự kiện: lọc status, tìm title, phân trang offset hoặc cursor.

    - Mặc định offset (giữ tương thích FE Phase 1).
    - Phase 2 cursor (keyset theo ``(start_time, id)``): truyền ``cursor=<id event
      cuối trang trước>``, server trả trang tiếp theo + header ``X-Next-Cursor``
      (rỗng khi hết). Cursor và offset không dùng chung.
    """
    if cursor is not None and offset != 0:
        api_error(400, "CURSOR_OFFSET_CONFLICT", "Use either cursor or offset, not both")

    stmt = select(Event)
    if status:
        stmt = stmt.where(Event.status == status)
    if q:
        stmt = stmt.where(Event.title.ilike(f"%{q}%"))

    if cursor is not None:
        anchor = db.get(Event, cursor)
        if anchor is None:
            api_error(404, "CURSOR_NOT_FOUND", "Cursor event not found")
        stmt = stmt.where(
            (Event.start_time > anchor.start_time)
            | ((Event.start_time == anchor.start_time) & (Event.id > anchor.id))
        )
        stmt = stmt.order_by(Event.start_time, Event.id).limit(limit)
    else:
        stmt = stmt.order_by(Event.start_time, Event.id).offset(offset).limit(limit)

    rows = db.scalars(stmt).all()
    if response is not None:
        response.headers["X-Next-Cursor"] = rows[-1].id if len(rows) == limit else ""
    return [to_event(e) for e in rows]


@router.get("/events/{event_id}", response_model=EventOut, tags=["events"])
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Chi tiết một sự kiện."""
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    return to_event(event)


@router.post(
    "/events",
    response_model=EventOut,
    status_code=201,
    tags=["events"],
    responses={**AUTH_RESPONSES},
)
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


@router.patch(
    "/events/{event_id}",
    response_model=EventOut,
    tags=["events"],
    responses={**AUTH_RESPONSES, 404: ERROR_404},
)
def reschedule_event(
    event_id: str,
    payload: EventUpdateIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Dời lịch / cập nhật sự kiện (PATCH). Chỉ ORGANIZER sở hữu sự kiện.

    Chỉ cập nhật các field được gửi lên (exclude_unset); nếu đổi thời gian
    thì bắt buộc hợp lệ: start < end và start ở tương lai.
    """
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")
    if event.status not in {"DRAFT", "PUBLISHED"}:
        api_error(400, "EVENT_NOT_EDITABLE", "Only DRAFT or PUBLISHED events can be edited")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("capacity", event.capacity) < event.registered_count:
        api_error(409, "CAPACITY_TOO_SMALL", "Capacity cannot be below the registered count")
    if "banner_image" in updates:
        updates["banner_url"] = updates.pop("banner_image")

    new_start = updates.get("start_time", event.start_time)
    new_end = updates.get("end_time", event.end_time)
    _validate_event_time(new_start, new_end)

    for field, value in updates.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    # PATCH cũng đổi dữ liệu occupancy (capacity): phát snapshot sau commit,
    # giống đăng ký/hủy/chuyển trạng thái, tránh dashboard giữ sức chứa cũ.
    background_tasks.add_task(manager.broadcast_occupancy, event.id, occupancy_payload(event))
    return to_event(event)


@router.delete(
    "/events/{event_id}",
    status_code=204,
    tags=["events"],
    responses={**AUTH_RESPONSES, 404: ERROR_404},
)
def delete_event(
    event_id: str,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Xóa sự kiện (Phase 1): chỉ ORGANIZER sở hữu và chỉ khi còn DRAFT.

    Event đã PUBLISHED/ONGOING có thể đã có registration/ticket nên không
    cho xóa cứng — dùng transition sang CANCELLED thay thế (soft-delete).
    """
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")
    if event.status != "DRAFT":
        api_error(400, "EVENT_NOT_DELETABLE", "Only DRAFT events can be deleted")

    # DRAFT vẫn có thể đã gán staff: xóa assignment trước để không vi phạm FK.
    from sqlalchemy import delete
    from ..models import StaffEventAssignment

    db.execute(delete(StaffEventAssignment).where(StaffEventAssignment.event_id == event.id))
    db.delete(event)
    db.commit()
    return None


@router.post(
    "/events/{event_id}/transition",
    response_model=EventOut,
    tags=["events"],
    responses={**AUTH_RESPONSES, 404: ERROR_404},
)
def transition_event(
    event_id: str,
    payload: TransitionIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Chuyển trạng thái sự kiện theo máy trạng thái VALID_TRANSITIONS.

    Khi sang COMPLETED hoặc CANCELLED, lên lịch background task gửi thông báo
    (mail demo) cho attendee còn đăng ký. BackgroundTasks chỉ dành cho việc
    NGẮN sau response — không phải queue thật.
    """
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    if payload.status not in VALID_TRANSITIONS.get(event.status, set()):
        api_error(400, "INVALID_TRANSITION", "This event transition is not allowed")

    # Read emails trước khi commit để background task chỉ cần gửi, không truy DB.
    notify_statuses = {"COMPLETED", "CANCELLED"}
    emails = _registered_emails(db, event.id) if payload.status in notify_statuses else []

    event.status = payload.status
    db.commit()
    db.refresh(event)

    # Mọi client WS đang xem event đều nhận status mới realtime —
    # fix lỗi attendee kẹt ở trạng thái cũ khi organizer đổi trạng thái.
    background_tasks.add_task(
        manager.broadcast_occupancy, event.id, occupancy_payload(event)
    )

    if payload.status in notify_statuses and emails:
        # Đăng ký background task: FastAPI gọi async notify_attendees sau khi
        # response đã được gửi đi -> client không phải đợi việc gửi email.
        subject = "cancelled" if payload.status == "CANCELLED" else "completed"
        background_tasks.add_task(notify_in_background, event.title, emails, subject)

    return to_event(event)


@router.post(
    "/events/{event_id}/notify",
    response_model=NotifyOut,
    tags=["events"],
    responses={**AUTH_RESPONSES, 404: ERROR_404},
)
async def notify_event_now(
    target: NotificationTarget = Depends(_notification_target),
):
    """Gửi thông báo NGAY LẬP TỨC tới attendee — endpoint **async đúng chỗ**.

    Tại sao endpoint này nên là async:
      - Dependency sync ``_notification_target`` đã xác thực, kiểm tra quyền
        và đọc DB trước khi handler này chạy.
      - Toàn bộ công việc của handler là network I/O (gửi email/webhook) — có
        awaitable operation thật sự.
      - ``await notify_attendees(...)`` chờ HTTP async hoặc SMTP trong thread;
        trong lúc chờ, event loop vẫn phục vụ các request khác.

    So với transition->COMPLETED ở trên: endpoint đó dùng background task vì
    không muốn bắt client đợi; endpoint này chủ động chờ (organizer muốn gửi
    và chờ kết quả) — đây chính là "async đúng chỗ".
    """
    # ĐIỂM MẤU CHỐT: đây là await I/O thật, không block event loop.
    try:
        sent = await notify_attendees(target.event_title, target.attendee_emails)
    except (httpx.HTTPError, NotificationError):
        api_error(502, "NOTIFICATION_FAILED", "Notification service is unavailable")

    mode = notification_mode()
    return NotifyOut(event_id=target.event_id, emails_sent=sent, mode=mode)
