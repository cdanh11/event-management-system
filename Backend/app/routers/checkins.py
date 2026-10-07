"""Router: check-in — xác thực vé tại cửa ra vào.

- STAFF phải được gán vào event; ORGANIZER được check-in event của chính mình
  (tổ chức nhỏ không có staff riêng).
- Check-in chỉ mở khi event ở STARTED (tự động mở trước giờ bắt đầu 15 phút);
  ở ONGOING (đóng đăng ký, đang chuẩn bị) thì chưa được check-in.

Luồng kiểm tra (đúng thứ tự để báo lỗi rõ ràng từng trường hợp):
  1. Barcode/ticket_code có tồn tại?
  2. Vé đã hủy chưa? Đã dùng chưa?
  3. Sự kiện có đang STARTED không?
  4. Người check-in có quyền không (staff được gán / organizer sở hữu)?
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
    user: User = Depends(require("STAFF", "ORGANIZER")),
    db: Session = Depends(get_db),
):
    """Check-in một vé. Trả 201 và lưu bản ghi checkin nếu hợp lệ."""
    code = payload.ticket_code.strip().upper()
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_code == code))

    if ticket is None:
        api_error(404, "INVALID_TICKET", "Invalid ticket")
    reg = db.get(Registration, ticket.registration_id)
    # Khóa event trước ticket để cùng thứ tự với hủy đăng ký/chuyển trạng thái.
    event = db.scalar(select(Event).where(Event.id == reg.event_id).with_for_update())
    if payload.event_id is not None and payload.event_id != event.id:
        api_error(400, "WRONG_EVENT", "Ticket does not belong to the selected event")
    db.refresh(ticket, with_for_update=True)
    if ticket.status == "CANCELLED":
        api_error(400, "TICKET_CANCELLED", "Ticket cancelled")
    if ticket.status == "USED":
        api_error(409, "TICKET_ALREADY_USED", "Ticket already checked in")


    if event.status != "STARTED":
        api_error(400, "CHECKIN_CLOSED", "Check-in is only open while the event is STARTED")

    if user.role == "ORGANIZER":
        if event.organizer_id != user.id:
            api_error(403, "FORBIDDEN", "You do not own this event")
    else:
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
