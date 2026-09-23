"""Các model ORM (SQLAlchemy 2.0, cú pháp ``Mapped``/``mapped_column``).

7 bảng chính của hệ thống Evently:
  users, events, registrations, tickets, checkins,
  staff_event_assignments, refresh_tokens.

Quy ước:
- Mọi bảng dùng khóa chính UUID dạng chuỗi 36 ký tự, sinh bởi ``uid()``.
- Cột ``status`` dùng chuỗi ngắn; các giá trị hợp lệ được ghi trong comment.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid() -> str:
    """Sinh khóa chính UUID (chuỗi 36 ký tự)."""
    return str(uuid4())


class User(Base):
    """Người dùng. role quyết định quyền truy cập:
    ORGANIZER (tạo/quản lý sự kiện), STAFF (check-in), ATTENDEE (đăng ký).
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), index=True)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Event(Base):
    """Sự kiện. status theo máy trạng thái:
    DRAFT -> PUBLISHED -> ONGOING -> COMPLETED; bất kỳ bước nào cũng có thể CANCELLED.
    """

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(300))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column(Integer)
    registered_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    category: Mapped[str] = mapped_column(String(80))
    banner_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StaffEventAssignment(Base):
    """Gán nhân viên (STAFF) vào sự kiện để được phép check-in tại sự kiện đó."""

    __tablename__ = "staff_event_assignments"
    __table_args__ = (
        # Một staff chỉ được gán vào một event một lần.
        UniqueConstraint("staff_id", "event_id", name="uq_staff_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    staff_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Registration(Base):
    """Đăng ký tham dự của một ATTENDEE vào một sự kiện.

    status: REGISTERED hoặc CANCELLED. Ràng buộc unique (event, attendee)
    đảm bảo một người chỉ đăng ký một sự kiện một lần.
    """

    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "attendee_id", name="uq_event_attendee"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    attendee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(16), default="REGISTERED")


class Ticket(Base):
    """Vé cấp cho mỗi Registration; dùng để check-in.

    status: VALID -> USED (sau check-in) hoặc CANCELLED (khi hủy đăng ký).
    """

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    registration_id: Mapped[str] = mapped_column(
        ForeignKey("registrations.id"), unique=True, index=True
    )
    ticket_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    qr_value: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="VALID")
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Checkin(Base):
    """Lịch sử check-in: một vé chỉ được check-in đúng một lần (unique ticket_id)."""

    __tablename__ = "checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id"), unique=True, index=True
    )
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    attendee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    checked_in_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(16), default="SUCCESS")


class RefreshToken(Base):
    """Refresh token (chỉ lưu hash). Bị vô hiệu khi revoked_at có giá trị."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)