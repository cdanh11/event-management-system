"""Router: staff — sự kiện được gán, dashboard organizer, gán staff."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Checkin, Event, Registration, StaffEventAssignment, User
from ..schemas import AssignmentIn, EventOut
from ..serializers import to_event

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