"""Router: đăng ký (registration) — phần "Cancel" của vòng đời.

  - POST /events/{id}/register        -> đăng ký + cấp ticket
  - GET  /registrations/me            -> đăng ký của tôi
  - GET  /registrations/{id}          -> chi tiết đăng ký
  - POST /registrations/{id}/cancel   -> hủy đăng ký (Cancel)
  - GET  /registrations/{id}/ticket   -> vé của một đăng ký
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require
from ..errors import api_error
from ..models import Event, Registration, Ticket, User
from ..schemas import RegisterOut, RegistrationOut, TicketOut
from ..serializers import to_registration, to_ticket

router = APIRouter()


@router.post(
    "/events/{event_id}/register",
    response_model=RegisterOut,
    status_code=201,
    tags=["registrations"],
)
def register(
    event_id: str,
    user: User = Depends(require("ATTENDEE")),
    db: Session = Depends(get_db),
):
    """Đăng ký tham dự: tạo Registration + cấp Ticket, tăng registered_count.

    Dùng ``with_for_update`` để khoá dòng event ở DB (PostgreSQL) chống tình
    huống 2 request đăng ký đồng thời cùng vượt qua kiểm tra capacity.
    """
    try:
        # Khoá dòng event để kiểm tra capacity và cập nhật registered_count
        # thành một giao dịch nguyên tử.
        event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
        if event is None:
            api_error(404, "EVENT_NOT_FOUND", "Event not found")

        if event.status != "PUBLISHED":
            api_error(400, "REGISTRATION_CLOSED", "Registration is unavailable")

        existing = db.scalar(
            select(Registration).where(
                Registration.event_id == event_id, Registration.attendee_id == user.id
            )
        )
        if existing is not None:
            api_error(409, "ALREADY_REGISTERED", "Already registered")

        if event.registered_count >= event.capacity:
            api_error(409, "EVENT_FULL", "Event is full")

        # Tạo registration + ticket trong cùng 1 giao dịch.
        registration = Registration(event_id=event.id, attendee_id=user.id)
        db.add(registration)
        db.flush()  # flush để có registration.id trước khi tạo ticket

        code = f"EV-{registration.id.replace('-', '')[:8].upper()}"
        ticket = Ticket(registration_id=registration.id, ticket_code=code, qr_value=code)
        db.add(ticket)

        event.registered_count += 1
        db.commit()

        return {"registration": to_registration(registration), "ticket": to_ticket(ticket)}

    except IntegrityError:
        # Ràng buộc unique (event_id, attendee_id) được kích hoạt trong môi
        # trường cạnh tranh cao -> trả 409 thay vì 500.
        db.rollback()
        api_error(409, "ALREADY_REGISTERED", "Already registered")


@router.get("/registrations/me", response_model=list[RegistrationOut], tags=["registrations"])
def my_registrations(
    user: User = Depends(require("ATTENDEE")),
    db: Session = Depends(get_db),
):
    """Danh sách đăng ký của user hiện tại (mới nhất trước)."""
    rows = db.scalars(
        select(Registration)
        .where(Registration.attendee_id == user.id)
        .order_by(Registration.registered_at.desc())
    ).all()
    return [to_registration(r) for r in rows]


@router.get("/registrations/{registration_id}", response_model=RegistrationOut, tags=["registrations"])
def get_registration(
    registration_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Chi tiết đăng ký. ATTENDEE chỉ xem được đăng ký của chính mình."""
    reg = db.get(Registration, registration_id)
    if reg is None:
        api_error(404, "REGISTRATION_NOT_FOUND", "Registration not found")
    if user.role == "ATTENDEE" and reg.attendee_id != user.id:
        api_error(403, "FORBIDDEN", "Not your registration")
    return to_registration(reg)


@router.post(
    "/registrations/{registration_id}/cancel",
    response_model=RegistrationOut,
    tags=["registrations"],
)
def cancel_registration(
    registration_id: str,
    user: User = Depends(require("ATTENDEE")),
    db: Session = Depends(get_db),
):
    """Hủy đăng ký (Cancel step): hủy vé, trả lại 1 slot cho event.

    Nếu đã hủy rồi thì trả về nguyên trạng thái cũ thay vì báo lỗi (idempotent).
    """
    reg = db.scalar(
        select(Registration).where(Registration.id == registration_id).with_for_update()
    )
    if reg is None:
        api_error(404, "REGISTRATION_NOT_FOUND", "Registration not found")
    if reg.attendee_id != user.id:
        api_error(403, "FORBIDDEN", "Not your registration")

    if reg.status == "CANCELLED":
        return to_registration(reg)

    reg.status = "CANCELLED"

    ticket = db.scalar(select(Ticket).where(Ticket.registration_id == reg.id))
    if ticket is not None:
        ticket.status = "CANCELLED"

    event = db.scalar(select(Event).where(Event.id == reg.event_id).with_for_update())
    event.registered_count = max(0, event.registered_count - 1)

    db.commit()
    return to_registration(reg)


@router.get(
    "/registrations/{registration_id}/ticket",
    response_model=TicketOut,
    tags=["tickets"],
)
def ticket_for_registration(
    registration_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Lấy vé ứng với một đăng ký (người sở hữu hoặc staff/organizer)."""
    reg = db.get(Registration, registration_id)
    if reg is None:
        api_error(404, "REGISTRATION_NOT_FOUND", "Registration not found")
    if user.role == "ATTENDEE" and reg.attendee_id != user.id:
        api_error(403, "FORBIDDEN", "Not your registration")

    ticket = db.scalar(select(Ticket).where(Ticket.registration_id == registration_id))
    return to_ticket(ticket)