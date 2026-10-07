"""Router: staff — sự kiện được gán, dashboard organizer, gán staff."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from typing import Literal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import Query

from ..db import get_db
from ..deps import current_user, require
from ..errors import api_error
from ..models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from ..schemas import (
    AssignmentIn,
    AssignmentOut,
    CheckinHistoryOut,
    EventOut,
    EventPageOut,
    EventStatus,
    OrganizerDashboardOut,
    StaffAssignmentOut,
    StaffCreateIn,
    UserOut,
)
from ..security import hash_password
from ..serializers import to_event, to_staff_assignment, to_user

router = APIRouter()


@router.get("/staff/events", response_model=list[EventOut], tags=["staff"])
def staff_events(
    user: User = Depends(require("STAFF")),
    db: Session = Depends(get_db),
):
    """Danh sách sự kiện mà staff hiện tại được gán làm việc."""
    rows = db.scalars(
        select(Event)
        .join(StaffEventAssignment, StaffEventAssignment.event_id == Event.id)
        .where(StaffEventAssignment.staff_id == user.id)
    ).all()
    return [to_event(e) for e in rows]


@router.get("/organizer/dashboard", response_model=OrganizerDashboardOut, tags=["organizer"])
def organizer_dashboard(
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Thống kê nhanh cho organizer: sự kiện, tổng đăng ký còn hiệu lực, tổng check-in.

    Đếm bằng SQL func.count() — O(1) bộ nhớ, không kéo toàn bộ ORM về RAM.
    """
    events = db.scalars(
        select(Event).where(Event.organizer_id == user.id).order_by(Event.start_time)
    ).all()
    # Subquery để DB lọc tài nguyên sở hữu, không truyền một danh sách ID lớn.
    event_ids = select(Event.id).where(Event.organizer_id == user.id)

    total_registrations = (
        db.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.event_id.in_(event_ids), Registration.status == "REGISTERED")
        )
        or 0
    )
    total_checkins = (
        db.scalar(
            select(func.count())
            .select_from(Checkin)
            .where(Checkin.event_id.in_(event_ids))
        )
        or 0
    )

    return {
        "events": [to_event(e) for e in events],
        "total_registrations": total_registrations,
        "total_checkins": total_checkins,
    }


@router.get("/organizer/events", response_model=EventPageOut, tags=["organizer"])
def organizer_events(
    status: EventStatus | None = None,
    q: str | None = Query(default=None, max_length=200),
    sort: Literal["soonest", "popular"] = "soonest",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Phân trang thật cho Events: lọc/sort/COUNT/LIMIT đều tại DB.

    Mặc định đang check-in → sắp diễn ra → terminal mới nhất → draft.
    ID là tie-breaker để hai event cùng giờ không đổi vị trí tùy lần truy vấn.
    """
    filters = [Event.organizer_id == user.id]
    if status is not None:
        filters.append(Event.status == status)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        filters.append(Event.title.ilike(needle) | Event.location.ilike(needle) | Event.category.ilike(needle))
    total = db.scalar(select(func.count()).select_from(Event).where(*filters)) or 0
    rank = case((Event.status == "STARTED", 0), (Event.status.in_(["PUBLISHED", "ONGOING"]), 1), (Event.status == "DRAFT", 3), else_=2)
    terminal = Event.status.in_(["COMPLETED", "CANCELLED"])
    order = [rank, case((terminal, Event.start_time)).desc(), case((~terminal, Event.start_time)), Event.id]
    if sort == "popular":
        order = [Event.registered_count.desc(), *order]
    rows = db.scalars(select(Event).where(*filters).order_by(*order).offset(offset).limit(limit)).all()
    return {"items": [to_event(row) for row in rows], "total": total, "limit": limit, "offset": offset, "has_more": offset + len(rows) < total}


@router.post("/events/{event_id}/staff", response_model=AssignmentOut, status_code=201, tags=["assignments"])
def assign_staff(
    event_id: str,
    payload: AssignmentIn,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Gán một STAFF vào sự kiện (chỉ organizer sở hữu sự kiện)."""
    event = db.get(Event, event_id)
    staff = db.get(User, payload.staff_id)

    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")
    if staff is None or staff.role != "STAFF":
        api_error(400, "INVALID_STAFF", "User must be staff")

    db.add(StaffEventAssignment(event_id=event.id, staff_id=staff.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(409, "ALREADY_ASSIGNED", "Staff is already assigned")

    return {"event_id": event.id, "staff_id": staff.id}


@router.get("/users", response_model=list[UserOut], tags=["staff"])
def list_users(
    role: str | None = None,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Danh sách user, lọc theo role. Dùng để organizer tìm staff gán vào event."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)

    users = db.scalars(stmt.order_by(User.name)).all()
    return [to_user(u) for u in users] # convert từng User → dict


@router.get("/events/{event_id}/staff", response_model=list[StaffAssignmentOut], tags=["assignments"])
def list_event_staff(
    event_id: str,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Danh sách staff đã được gán vào event (chỉ organizer sở hữu event)."""
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if event.organizer_id != user.id:
        api_error(403, "FORBIDDEN", "You do not own this event")

    rows = db.scalars(select(StaffEventAssignment).where(StaffEventAssignment.event_id == event_id)).all()
    return [to_staff_assignment(a, db.get(User, a.staff_id)) for a in rows]


def _can_view_event(user: User, event: Event, db: Session) -> bool:
    """Staff được gán hoặc organizer sở hữu mới được xem lịch sử check-in."""
    if user.role == "ORGANIZER" and event.organizer_id == user.id:
        return True
    if user.role == "STAFF":
        return (
            db.scalar(
                select(StaffEventAssignment).where(
                    StaffEventAssignment.staff_id == user.id,
                    StaffEventAssignment.event_id == event.id,
                )
            )
            is not None
        )
    return False


@router.get(
    "/events/{event_id}/checkins",
    response_model=list[CheckinHistoryOut],
    tags=["checkins"],
)
def event_checkin_history(
    event_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Lịch sử check-in mới nhất của event (thông tin public: tên, mã vé, giờ).

    Dùng cho màn hình làm việc của staff và organizer — realtime bằng cách
    poll endpoint này kết hợp WS occupancy.
    """
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    if not _can_view_event(user, event, db):
        api_error(403, "FORBIDDEN", "You cannot view this event")

    rows = db.scalars(
        select(Checkin)
        .where(Checkin.event_id == event_id)
        .order_by(Checkin.checked_in_at.desc())
        .limit(limit)
    ).all()
    history = []
    for record in rows:
        ticket = db.get(Ticket, record.ticket_id)
        attendee = db.get(User, record.attendee_id)
        history.append({
            "id": record.id,
            "ticket_code": ticket.ticket_code if ticket else "?",
            "attendee_name": attendee.name if attendee else "?",
            "checked_in_at": record.checked_in_at,
        })
    return history


@router.post("/users/staff", response_model=UserOut, status_code=201, tags=["staff"])
def create_staff(
    payload: StaffCreateIn,
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Organizer tạo tài khoản STAFF (tổ chức nhỏ tự lo nhân sự)."""
    staff = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        role="STAFF",
        avatar_url="",
        password_hash=hash_password(payload.password),
    )
    db.add(staff)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(409, "EMAIL_TAKEN", "Email is already registered")
    db.refresh(staff)
    return to_user(staff)
