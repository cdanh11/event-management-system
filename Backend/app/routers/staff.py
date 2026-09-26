"""Router: staff — sự kiện được gán, dashboard organizer, gán staff."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Checkin, Event, Registration, StaffEventAssignment, User
from ..schemas import AssignmentIn, EventOut, StaffAssignmentOut, UserOut
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


@router.get("/organizer/dashboard", tags=["organizer"])
def organizer_dashboard(
    user: User = Depends(require("ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Thống kê nhanh cho organizer: sự kiện, tổng đăng ký còn hiệu lực, tổng check-in."""
    events = db.scalars(
        select(Event).where(Event.organizer_id == user.id).order_by(Event.start_time)
    ).all()
    event_ids = [e.id for e in events]

    registrations = (
        []
        if not event_ids
        else db.scalars(select(Registration).where(Registration.event_id.in_(event_ids))).all()
    )
    checkins = (
        []
        if not event_ids
        else db.scalars(select(Checkin).where(Checkin.event_id.in_(event_ids))).all()
    )

    return {
        "events": [to_event(e) for e in events],
        "total_registrations": len([r for r in registrations if r.status == "REGISTERED"]),
        "total_checkins": len(checkins),
    }


@router.post("/events/{event_id}/staff", status_code=201, tags=["assignments"])
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