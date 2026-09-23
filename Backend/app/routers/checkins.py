"""Router: check-in — xác thực vé tại cửa ra vào (chỉ STAFF được gán vào event).

Luồng kiểm tra (đúng thứ tự để báo lỗi rõ ràng từng trường hợp):
  1. Barcode/ticket_code có tồn tại?
  2. Vé đã hủy chưa? Đã dùng chưa?
  3. Sự kiện có đang ONGOING không?
  4. Staff có được gán vào sự kiện này không?
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from ..schemas import CheckinIn, CheckinOut
from ..serializers import to_checkin

router = APIRouter()


@router.post("/checkins", response_model=CheckinOut, status_code=201, tags=["checkins"])
def checkin(
    payload: CheckinIn,
    user: User = Depends(require("STAFF")),
    db: Session = Depends(get_db),
):
    """Check-in một vé. Trả 201 và lưu bản ghi checkin nếu hợp lệ."""
    code = payload.ticket_code.strip().upper()
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_code == code).with_for_update())

    if ticket is None:
        api_error(404, "INVALID_TICKET", "Invalid ticket")
    if ticket.status == "CANCELLED":
        api_error(400, "TICKET_CANCELLED", "Ticket cancelled")
    if ticket.status == "USED":
        api_error(409, "TICKET_ALREADY_USED", "Ticket already checked in")

    reg = db.get(Registration, ticket.registration_id)
    event = db.get(Event, reg.event_id)

    if event.status != "ONGOING":
        api_error(400, "CHECKIN_CLOSED", "Check-in is only available for ongoing events")

    assigned = db.scalar(
        select(StaffEventAssignment).where(
            StaffEventAssignment.staff_id == user.id,
            StaffEventAssignment.event_id == event.id,
        )
    )
    if assigned is None:
        api_error(403, "FORBIDDEN", "You are not assigned to this event")

    checkin_record = Checkin(
        ticket_id=ticket.id,
        event_id=event.id,
        attendee_id=reg.attendee_id,
        checked_in_by=user.id,
    )
    ticket.status = "USED"  # vé chỉ dùng được một lần
    db.add(checkin_record)
    db.commit()
    db.refresh(checkin_record)
    return to_checkin(checkin_record)