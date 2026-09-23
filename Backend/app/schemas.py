"""Pydantic v2: schema request/response cho API.

Nguyên tắc:
- ``*In`` = model nhận từ client (request). FastAPI dựa vào đây để *validate*
  tự động (sai kiểu/thiếu field -> 422... do Pydantic sinh ra, chưa chạy tới
  endpoint).
- ``*Out`` = model trả về client (response), thường được khai báo trong
  parameter ``response_model`` để OpenAPI mô tả đúng và filter dữ liệu thừa.
"""
from __future__ import annotations  # cho phép kiểu tham chiếu tới model "phía sau"

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ------------------------------- Auth ------------------------------------
class UserOut(BaseModel):
    """Thông tin người dùng trả về cho client."""
    id: str
    name: str
    email: EmailStr
    role: str
    avatar: str


class LoginIn(BaseModel):
    """Body của POST /auth/login."""
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    """Kết quả đăng nhập / refresh: access token + user."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ------------------------------- Events ----------------------------------
class EventIn(BaseModel):
    """Dữ liệu tạo sự kiện. Field ràng buộc để Pydantic validate từ đầu."""
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0)
    category: str
    banner_image: str


class EventUpdateIn(BaseModel):
    """Dữ liệu cập nhật sự kiện (PATCH - mọi field đều tùy chọn).

    Đây là endpoint dùng cho bước "Reschedule": đổi start_time/end_time
    cùng các thông tin khác của sự kiện.
    """
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)
    category: str | None = None
    banner_image: str | None = None


class EventOut(EventIn):
    """Sự kiện đầy đủ trả về client (kế thừa mọi field của EventIn)."""
    id: str
    organizer_id: str
    registered_count: int
    status: str
    created_at: datetime


class NotifyOut(BaseModel):
    """Kết quả gửi thông báo (POST /events/{id}/notify - endpoint async)."""
    event_id: str
    emails_sent: int
    mode: str  # "webhook" nếu gửi thật, "simulated" nếu demo


class TransitionIn(BaseModel):
    """Body của POST /events/{id}/transition: status đích."""
    status: str


# ---------------------------- Registrations ------------------------------
class RegistrationOut(BaseModel):
    """Một bản ghi đăng ký tham dự."""
    id: str
    event_id: str
    attendee_id: str
    registered_at: datetime
    status: str


class RegisterOut(BaseModel):
    """Kết quả đăng ký: registration + ticket được cấp."""
    registration: RegistrationOut
    ticket: TicketOut  # noqa: F821 - định nghĩa phía dưới file này


# ------------------------------- Tickets ---------------------------------
class TicketOut(BaseModel):
    """Một vé (ticket) với mã check-in và QR value."""
    id: str
    registration_id: str
    ticket_code: str
    qr_value: str
    status: str
    issued_at: datetime


# ------------------------------ Checkins ---------------------------------
class CheckinIn(BaseModel):
    """Body của POST /checkins: mã vé để xác thực."""

    ticket_code: str


class CheckinOut(BaseModel):
    """Kết quả check-in."""
    id: str
    ticket_id: str
    event_id: str
    attendee_id: str
    checked_in_by: str
    checked_in_at: datetime
    status: str


# ----------------------------- Assignments -------------------------------
class AssignmentIn(BaseModel):
    """Body của POST /events/{id}/staff: staff_id người được gán."""

    staff_id: str