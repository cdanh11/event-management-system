"""Hàm chuyển ORM -> dict theo đúng schema API.

Tên cột trong DB (vd ``banner_url``, ``avatar_url``) khác tên field API
(vd ``banner_image``, ``avatar``). Tập trung mọi mapping ở đây để endpoint
chỉ cần gọi ``to_event(e)``... thay vì tự viết dict ở từng router.
"""
from .models import Checkin, Event, Registration, Ticket, User


def to_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar_url,
    }


def to_event(event: Event) -> dict:
    return {
        "id": event.id,
        "organizer_id": event.organizer_id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "capacity": event.capacity,
        "registered_count": event.registered_count,
        "status": event.status,
        "category": event.category,
        "banner_image": event.banner_url,
        "created_at": event.created_at,
    }


def to_registration(reg: Registration) -> dict:
    return {
        "id": reg.id,
        "event_id": reg.event_id,
        "attendee_id": reg.attendee_id,
        "registered_at": reg.registered_at,
        "status": reg.status,
    }


def to_ticket(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "registration_id": ticket.registration_id,
        "ticket_code": ticket.ticket_code,
        "qr_value": ticket.qr_value,
        "status": ticket.status,
        "issued_at": ticket.issued_at,
    }


def to_checkin(checkin: Checkin) -> dict:
    return {
        "id": checkin.id,
        "ticket_id": checkin.ticket_id,
        "event_id": checkin.event_id,
        "attendee_id": checkin.attendee_id,
        "checked_in_by": checkin.checked_in_by,
        "checked_in_at": checkin.checked_in_at,
        "status": checkin.status,
    }