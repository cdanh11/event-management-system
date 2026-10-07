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
from typing import Any, Literal
import re

from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator, model_validator

from .models import as_local_naive


class EventStatus(str, Enum):
    """Các trạng thái được công khai trong contract OpenAPI."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"  # public: mở đăng ký
    ONGOING = "ONGOING"  # đóng đăng ký, organizer chuẩn bị; staff chưa check-in
    STARTED = "STARTED"  # mở check-in (tự động trước giờ bắt đầu 15 phút)
    COMPLETED = "COMPLETED"  # tự động khi hết giờ
    CANCELLED = "CANCELLED"


class NotifyMode(str, Enum):
    SMTP = "smtp"
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


def login_email(identifier: str) -> str:
    """Username đánh số trỏ tới email duy nhất; không xác thực theo tên hiển thị.

    Giữ miền email của tài khoản seed cũ để các liên kết và vé vẫn hợp lệ.
    """
    identifier = identifier.strip().lower()
    return f"{identifier}@demo.com" if re.fullmatch(r"(?:user|staff|organizer)[1-9][0-9]*", identifier) else identifier


class LoginIn(BaseModel):
    """Nhận username hoặc email; giữ key email để tương thích client hiện có."""
    email: EmailStr = Field(validation_alias=AliasChoices("email", "username"))
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def accept_username(cls, value):
        return login_email(value) if isinstance(value, str) else value


class RegisterIn(BaseModel):
    """Body của POST /auth/register — tự mở tài khoản ATTENDEE.

    Role do server ấn định (ATTENDEE), client không được chọn role để
    tránh tự nâng quyền thành ORGANIZER/STAFF.
    """
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


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
    location: str = Field(min_length=1, max_length=300)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0)
    category: str = Field(min_length=1, max_length=80)
    banner_image: str = Field(default="", max_length=500)

    @field_validator("title", "description", "location", "category", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_event_time(cls, value: datetime) -> datetime:
        # Cột DB là DateTime không timezone: chuẩn hóa trước cả validation và lưu.
        return as_local_naive(value)

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
    location: str | None = Field(default=None, min_length=1, max_length=300)
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    banner_image: str | None = Field(default=None, max_length=500)

    @field_validator("title", "description", "location", "category", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_event_time(cls, value: datetime | None) -> datetime | None:
        return as_local_naive(value) if value is not None else None

    @model_validator(mode="after")
    def _check_time_order(self):
        """Khi gửi cả 2 mốc thời gian mà end <= start -> 422 ngay tại tầng bind body."""
        # PATCH cho phép bỏ qua field; không cho null vì cột DB là NOT NULL.
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Updated fields cannot be null")
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


class EventPageOut(BaseModel):
    """Trang sự kiện organizer; total là số kết quả sau bộ lọc, không phải số hàng trang."""
    items: list[EventOut]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool


class OrganizerDashboardOut(BaseModel):
    events: list[EventOut]
    total_registrations: int = Field(ge=0)
    total_checkins: int = Field(ge=0)


class OccupancyOut(BaseModel):
    type: Literal["occupancy"] = "occupancy"
    event_id: str
    capacity: int = Field(gt=0)
    registered_count: int = Field(ge=0)
    remaining: int = Field(ge=0)
    status: EventStatus


class WsTicketOut(BaseModel):
    ticket: str
    expires_in: int = Field(gt=0)


class HealthOut(BaseModel):
    """Liveness của tiến trình; không khẳng định database đang sẵn sàng."""
    status: Literal["ok"]


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
    event_id: str | None = None  # Client Door gửi event đang chọn; Swagger cũ vẫn tương thích.


class CheckinOut(BaseModel):
    """Kết quả check-in."""
    id: str
    ticket_id: str
    event_id: str
    attendee_id: str
    checked_in_by: str
    checked_in_at: datetime
    status: str


class CheckinHistoryOut(BaseModel):
    """Một dòng lịch sử check-in cho staff/organizer (thông tin public)."""
    id: str
    ticket_code: str
    attendee_name: str
    checked_in_at: datetime


class StaffCreateIn(BaseModel):
    """Body của POST /users/staff — organizer tạo tài khoản STAFF."""
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


# ----------------------------- Assignments -------------------------------
class AssignmentIn(BaseModel):
    """Body của POST /events/{id}/staff: staff_id người được gán."""

    staff_id: str


class AssignmentOut(BaseModel):
    event_id: str
    staff_id: str


class StaffAssignmentOut(BaseModel):
    """Một bản ghi gán staff vào event, kèm thông tin cơ bản của staff."""
    id: str
    event_id: str
    staff_id: str
    staff_name: str
    staff_email: str
    created_at: datetime
