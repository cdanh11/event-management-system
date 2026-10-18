"""Dữ liệu bảo vệ: 20 sự kiện, 30 attendee, 5 staff, 2 organizer.

Chạy ``python -m app.seed`` sau Alembic. Chỉ bổ sung sự kiện/tài khoản còn
thiếu; không xóa dữ liệu, đổi mật khẩu hay đặt lại vé đã được sử dụng.
Vé/đăng ký/check-in là bản ghi thật, không gọi dịch vụ gửi mail khi seed.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, assert_schema_ready
from .models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from .security import hash_password
from .timeutils import EVENT_TIMEZONE

ATTENDEE_COUNT = 30
ACCOUNT_PASSWORD = "123456"


@dataclass(frozen=True)
class EventFixture:
    title: str
    status: str
    day: int
    capacity: int
    attendees: tuple[int, ...] = ()
    used: int = 0
    cancelled: tuple[int, ...] = ()
    image: str = "workshop"


def event_fixtures() -> tuple[EventFixture, ...]:
    """Các tình huống cố định; ngày tương đối để seed dùng được ở máy khác.

    Các buổi sắp tới cách ngày seed ít nhất 30 ngày. Buổi STARTED được
    organizer mở check-in sớm, đúng transition API cho phép; không dùng
    tình huống này để chứng minh scheduler đã tự mở theo đồng hồ.
    """
    titles = (
        "FastAPI REST API Workshop", "Python Async I/O Lab", "Pydantic Validation Clinic",
        "PostgreSQL Transaction Workshop", "WebSocket Realtime Meetup", "OAuth2 and JWT Lab",
        "Software Testing Bootcamp", "Docker Development Workshop", "OpenAPI Documentation Day",
        "Backend Architecture Roundtable",
    )
    counts = (0, 3, 5, 7, 8, 10, 12, 14, 16, 3)
    capacities = (40, 40, 45, 50, 35, 40, 50, 60, 60, 3)
    images = ("coding", "workspace", "workshop", "infrastructure", "conference")
    fixtures = []
    for index, title in enumerate(titles):
        # user1 và user2 còn chỗ cho thao tác đăng ký mới. Buổi cuối đã đầy.
        attendees = tuple(3 + (index * 2 + offset) % 28 for offset in range(counts[index]))
        fixtures.append(EventFixture(
            title, "PUBLISHED", 30 + index * 2, capacities[index], attendees,
            cancelled=(2,) if index in (0, 2, 5) else (), image=images[index % 5],
        ))
    for index, title in enumerate((
        "Python Foundation Seminar", "Database Design Lab", "Git Collaboration Workshop",
        "API Security Seminar", "Backend Engineering Day",
    )):
        attendees = tuple(1 + (index * 3 + offset) % 26 for offset in range(15))
        fixtures.append(EventFixture(
            title, "COMPLETED", -7 * (index + 1), 40, attendees,
            used=12, cancelled=(29, 30), image=images[index],
        ))
    fixtures.extend((
        EventFixture("API Integration Planning", "DRAFT", 55, 30, image="workspace"),
        EventFixture("Cloud Infrastructure Planning", "DRAFT", 57, 35, image="infrastructure"),
        EventFixture("Observability Practice Session", "ONGOING", 35, 30, (8, 9, 10, 11, 12)),
        EventFixture("Check-in Operations Lab", "STARTED", 36, 20, (1, 2, 3, 4, 5, 6),
                     used=2, cancelled=(7,), image="conference"),
        EventFixture("Distributed Systems Reading Group", "CANCELLED", 38, 25,
                     cancelled=(1, 2, 3), image="coding"),
    ))
    return tuple(fixtures)


def _seed(db: Session) -> dict[str, int]:
    """Bổ sung trong transaction do caller quản lý; không commit giữa chừng."""
    now = datetime.now(EVENT_TIMEZONE)
    audit_now = now.astimezone(timezone.utc).replace(tzinfo=None)
    account_created_at = audit_now - timedelta(days=90)
    users: dict[str, User] = {}
    password_hash = None
    for prefix, role, amount in (("organizer", "ORGANIZER", 2), ("staff", "STAFF", 5),
                                 ("user", "ATTENDEE", ATTENDEE_COUNT)):
        for number in range(1, amount + 1):
            alias = f"{prefix}{number}"
            email = f"{alias}@demo.com"
            account = db.scalar(select(User).where(User.email == email))
            if account is not None and account.role != role:
                raise ValueError(f"Account {email} has another role; transaction must be rolled back")
            if account is None:
                if password_hash is None:
                    password_hash = hash_password(ACCOUNT_PASSWORD)
                account = User(name=alias, email=email, role=role, avatar_url="",
                               password_hash=password_hash, created_at=account_created_at,
                               updated_at=account_created_at)
                db.add(account)
            users[alias] = account
    db.flush()

    created = 0
    for index, fixture in enumerate(event_fixtures()):
        # Hai organizer đều có sự kiện nháp và đã hoàn thành; buổi check-in
        # dành cho organizer1 + staff1/staff2 để thao tác dễ nhớ.
        owner = users[f"organizer{1 if fixture.status == 'STARTED' else 1 + index % 2}"]
        existing = db.scalar(select(Event).where(
            Event.organizer_id == owner.id,
            Event.title.in_((fixture.title, f"[Demo] {fixture.title}")),
        ))
        if existing is not None:
            if existing.title.startswith("[Demo]"):
                existing.title = fixture.title
            continue
        start = (now + timedelta(days=fixture.day)).replace(hour=9, minute=0, second=0, microsecond=0)
        description = {
            "PUBLISHED": "Buổi thực hành công nghệ backend, mở đăng ký tham dự và cấp vé QR.",
            "COMPLETED": "Buổi học đã kết thúc; giữ lịch sử đăng ký, vé và check-in để đối chiếu.",
            "DRAFT": "Kế hoạch đang soạn, organizer có thể sửa, công bố hoặc xóa bản nháp.",
            "ONGOING": "Đã đóng đăng ký để chuẩn bị; organizer có thể mở check-in khi sẵn sàng.",
            "STARTED": "Organizer đã mở check-in sớm để thực hành kiểm vé; không phải scheduler tự mở.",
            "CANCELLED": "Buổi học đã hủy; các đăng ký được hủy trước khi đóng sự kiện.",
        }[fixture.status]
        event = Event(
            organizer_id=owner.id, title=fixture.title, description=description,
            location="Phòng thực hành CNTT" if index % 2 == 0 else "Hội trường campus",
            start_time=start, end_time=start + timedelta(hours=3), capacity=fixture.capacity,
            registered_count=len(fixture.attendees), status=fixture.status,
            category="Technology", banner_url=f"/images/events/{fixture.image}.webp",
            created_at=min((start - timedelta(days=5)).astimezone(timezone.utc).replace(tzinfo=None),
                           audit_now - timedelta(days=3)),
        )
        db.add(event)
        db.flush()
        staff_number = 1 if fixture.status == "STARTED" else 1 + index % 5
        staff = users[f"staff{staff_number}"]
        for number in (staff_number, 1 + staff_number % 5):
            db.add(StaffEventAssignment(staff_id=users[f"staff{number}"].id, event_id=event.id,
                                        created_at=event.created_at))

        # Sự kiện đã qua có đăng ký trước giờ bắt đầu; sự kiện tương lai
        # có vé cấp trước hiện tại. Audit/token vẫn lưu UTC-naive theo schema.
        issued = (start - timedelta(days=2)).astimezone(timezone.utc).replace(tzinfo=None)
        registered_at = min(issued, audit_now - timedelta(days=1))
        for offset, number in enumerate((*fixture.attendees, *fixture.cancelled)):
            cancelled = number in fixture.cancelled
            used = not cancelled and offset < fixture.used
            attendee = users[f"user{number}"]
            registration = Registration(
                event_id=event.id, attendee_id=attendee.id, registered_at=registered_at,
                status="CANCELLED" if cancelled else "REGISTERED",
            )
            db.add(registration)
            db.flush()
            code = f"EV-{registration.id.replace('-', '')[:24].upper()}"
            ticket = Ticket(
                registration_id=registration.id, ticket_code=code, qr_value=code,
                status="CANCELLED" if cancelled else "USED" if used else "VALID",
                issued_at=registered_at,
            )
            db.add(ticket)
            db.flush()
            if used:
                scanned_at = (
                    (start + timedelta(minutes=5 + offset * 3)).astimezone(timezone.utc).replace(tzinfo=None)
                    if fixture.status == "COMPLETED"
                    else audit_now - timedelta(minutes=10 - offset)
                )
                db.add(Checkin(
                    ticket_id=ticket.id, event_id=event.id, attendee_id=attendee.id,
                    checked_in_by=staff.id, checked_in_at=scanned_at, status="SUCCESS",
                ))
        created += 1
    db.flush()
    return {"accounts": 2 + 5 + ATTENDEE_COUNT, "events_added": created}


def run() -> None:
    assert_schema_ready()
    with SessionLocal.begin() as db:
        result = _seed(db)
    print(f"Dataset ready: {result['accounts']} numbered accounts; "
          f"{result['events_added']} events added (target: 20). Existing data preserved.")


if __name__ == "__main__":
    run()
