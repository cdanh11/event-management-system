"""Router: check-in — xác thực vé tại cửa ra vào.

- STAFF phải được gán vào event; ORGANIZER được check-in event của chính mình
  (tổ chức nhỏ không có staff riêng).
- Check-in chỉ mở khi event ở STARTED (tự động mở trước giờ bắt đầu 15 phút);
  ở ONGOING (đóng đăng ký, đang chuẩn bị) thì chưa được check-in.

Luồng kiểm tra (đúng thứ tự để báo lỗi rõ ràng từng trường hợp):
  1. Barcode/ticket_code có tồn tại?
  2. Xác định event thật từ vé, kiểm tra quyền trước khi khóa/trả trạng thái vé.
  3. Khóa event trước ticket; kiểm tra event được chọn và trạng thái vé/event.
  4. Lưu check-in và đổi trạng thái vé trong cùng transaction.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Checkin, Event, Registration, Ticket, User
from ..access import can_operate_event
from ..schemas import AUTH_RESPONSES, ERROR_400, ERROR_404, ERROR_409, CheckinIn, CheckinOut
from ..serializers import to_checkin

router = APIRouter(responses=AUTH_RESPONSES)


@router.post("/checkins", response_model=CheckinOut, status_code=201, tags=["checkins"], responses={400: ERROR_400, 404: ERROR_404, 409: ERROR_409})
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
    # Không tin event_id do client gửi: quyền phải kiểm tra trên event thật của vé.
    # Người không có quyền nhận cùng 403, bất kể vé VALID/USED/CANCELLED hay
    # event đã đóng. Vé không tồn tại vẫn trả 404; không tuyên bố chống dò mọi mã.
    event = db.get(Event, reg.event_id)
    if not can_operate_event(db, user, event):
        api_error(403, "FORBIDDEN", "You cannot check in this event")

    # Khóa event trước ticket để cùng thứ tự với hủy đăng ký/chuyển trạng thái.
    # Trade-off MVP: các check-in cùng event bị tuần tự hóa trong transaction
    # ngắn. Bỏ khóa này cần thiết kế lại race với đóng cửa, không chỉ khóa vé.
    event = db.scalar(
        select(Event).where(Event.id == reg.event_id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if payload.event_id is not None and payload.event_id != event.id:
        api_error(400, "WRONG_EVENT", "Ticket does not belong to the selected event")
    db.refresh(ticket, with_for_update=True)
    if ticket.status == "CANCELLED":
        api_error(400, "TICKET_CANCELLED", "Ticket cancelled")
    if ticket.status == "USED":
        api_error(409, "TICKET_ALREADY_USED", "Ticket already checked in")


    if event.status != "STARTED":
        api_error(400, "CHECKIN_CLOSED", "Check-in is only open while the event is STARTED")

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
