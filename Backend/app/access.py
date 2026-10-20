"""Quyền tài nguyên: sự kiện, đăng ký/vé và check-in.

Kiểm tra role tại router chưa đủ: cần kiểm tra cả tài nguyên cụ thể để
organizer/staff của sự kiện khác không đọc được vé và đăng ký.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import api_error
from .models import Event, Registration, StaffEventAssignment, User


def can_operate_event(db: Session, user: User | None, event: Event) -> bool:
    """Chủ sự kiện hoặc STAFF đã được phân công mới có quyền nghiệp vụ."""
    if user is None:
        return False
    if user.role == "ORGANIZER":
        return event.organizer_id == user.id
    if user.role == "STAFF":
        return db.scalar(select(StaffEventAssignment.id).where(
            StaffEventAssignment.event_id == event.id,
            StaffEventAssignment.staff_id == user.id,
        )) is not None
    return False


def can_view_event(db: Session, user: User | None, event: Event) -> bool:
    """DRAFT là riêng tư; các trạng thái còn lại được xem công khai."""
    return event.status != "DRAFT" or can_operate_event(db, user, event)


def require_registration_access(db: Session, user: User, reg: Registration) -> None:
    if user.role == "ATTENDEE" and reg.attendee_id == user.id:
        return
    event = db.get(Event, reg.event_id)
    if can_operate_event(db, user, event):
        return
    api_error(403, "FORBIDDEN", "You cannot view this registration or ticket")
