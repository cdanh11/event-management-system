"""Quyền đọc dữ liệu cá nhân: chủ vé, organizer sở hữu, staff được gán.

Kiểm tra role tại router chưa đủ: cần kiểm tra cả tài nguyên cụ thể để
organizer/staff của sự kiện khác không đọc được vé và đăng ký.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import api_error
from .models import Event, Registration, StaffEventAssignment, User


def require_registration_access(db: Session, user: User, reg: Registration) -> None:
    if user.role == "ATTENDEE" and reg.attendee_id == user.id:
        return
    event = db.get(Event, reg.event_id)
    if user.role == "ORGANIZER" and event.organizer_id == user.id:
        return
    if user.role == "STAFF" and db.scalar(
        select(StaffEventAssignment.id).where(
            StaffEventAssignment.event_id == reg.event_id,
            StaffEventAssignment.staff_id == user.id,
        )
    ):
        return
    api_error(403, "FORBIDDEN", "You cannot view this registration or ticket")
