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
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator


class EventStatus(str, Enum):
    """Các trạng thái được công khai trong contract OpenAPI."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class NotifyMode(str, Enum):
    WEBHOOK = "webhook"
    SIMULATED = "simulated"


class ApiErrorOut(BaseModel):
    """Dạng lỗi nghiệp vụ thống nhất do exception handler trả về."""

    status: int
    code: str
    message: str


class ValidationErrorOut(ApiErrorOut):
    """Lỗi 422, bổ sung chi tiết field do Pydantic phát hiện."""

    details: list[dict[str, Any]]


# --- Swagger error contract dùng chung (Phase 1) ---------------------------
# Runtime đã trả body chuẩn {status, code, message} qua exception handler;
# khai báo ở đây để Swagger mô tả đúng error contract từng endpoint.
ERROR_401 = {"model": ApiErrorOut, "description": "Thiếu token hoặc token sai/hết hạn."}
ERROR_403 = {"model": ApiErrorOut, "description": "Sai role hoặc không sở hữu tài nguyên."}
ERROR_404 = {"model": ApiErrorOut, "description": "Tài nguyên không tồn tại."}
ERROR_409 = {"model": ApiErrorOut, "description": "Xung đột nghiệp vụ (trùng/full)."}
AUTH_RESPONSES = {401: ERROR_401, 403: ERROR_403}


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


class RegisterIn(BaseModel):
    """Body của POST /auth/register — tự mở tài khoản ATTENDEE.

    Role do server ấn định (ATTENDEE), client không được chọn role để
    tránh tự nâng quyền thành ORGANIZER/STAFF.
    """
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


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

    @model_validator(mode="after")
    def _check_time_order(self):
        """end_time phải sau start_time — lỗi Pydantic 422, không cần if/else ở endpoint."""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


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

    @model_validator(mode="after")
    def _check_time_order(self):
        """Khi gửi cả 2 mốc thời gian mà end <= start -> 422 ngay tại tầng bind body."""
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time")
        return self


class EventOut(EventIn):
    """Sự kiện đầy đủ trả về client (kế thừa mọi field của EventIn)."""
    id: str
    organizer_id: str
    registered_count: int
    status: EventStatus
    created_at: datetime


class NotifyOut(BaseModel):
    """Kết quả gửi thông báo (POST /events/{id}/notify - endpoint async)."""
    event_id: str
    emails_sent: int
    mode: NotifyMode


class TransitionIn(BaseModel):
    """Body của POST /events/{id}/transition: status đích."""
    status: EventStatus


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


class StaffAssignmentOut(BaseModel):
    """Một bản ghi gán staff vào event, kèm thông tin cơ bản của staff."""
    id: str
    event_id: str
    staff_id: str
    staff_name: str
    staff_email: str
    created_at: datetime