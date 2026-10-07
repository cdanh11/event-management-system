"""Bộ dữ liệu mẫu mở rộng, bổ sung an toàn bằng ``python -m app.seed``.

2 organizer, 5 staff, 100 attendee; 10 sự kiện mở đăng ký và 5 đã hoàn thành.
Chạy lại không nhân bản hoặc đặt lại dữ liệu người dùng đã thao tác.
Migration phải được chạy trước seed; seed không tự thay schema.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Checkin, Event, Registration, StaffEventAssignment, Ticket, User
from .security import hash_password

OPEN_TITLES = [
    "FastAPI REST API Workshop", "Python Async I/O Lab", "Pydantic Validation Clinic",
    "PostgreSQL Transaction Workshop", "WebSocket Realtime Meetup", "OAuth2 and JWT Lab",
    "Software Testing Bootcamp", "Docker Development Workshop", "OpenAPI Documentation Day",
    "Backend Architecture Forum",
]
PAST_TITLES = [
    "Python Foundation Seminar", "Database Design Lab", "Git Collaboration Workshop",
    "API Security Seminar", "Backend Engineering Day",
]
OPEN_COUNTS = [5, 8, 10, 12, 15, 18, 20, 25, 30, 35]


def run() -> None:
    with SessionLocal() as db:
        _seed(db)


def _seed(db: Session) -> None:
    """Một transaction cho toàn bộ fixture; giữ nguyên dữ liệu có sẵn.

    Email và cặp organizer/title nhận diện dataset. Nếu tài khoản đánh số
    đã có role khác, dừng thay vì tự đổi quyền hoặc mật khẩu của tài khoản đó.
    """
    now = datetime.now()
    users = {}
    password_hash = None
    for prefix, role, amount in [("organizer", "ORGANIZER", 2), ("staff", "STAFF", 5), ("user", "ATTENDEE", 100)]:
        for number in range(1, amount + 1):
            alias = f"{prefix}{number}"
            email = f"{alias}@demo.com"
            account = db.scalar(select(User).where(User.email == email))
            if account is not None and account.role != role:
                raise ValueError(f"Sample account {email} already has another role; no data changed")
            if account is None:
                # Chung mật khẩu mẫu, hash một lần để seed 107 user nhanh hơn.
                if password_hash is None:
                    password_hash = hash_password("123456")
                account = User(name=alias, email=email, role=role, avatar_url="", password_hash=password_hash)
                db.add(account)
            users[alias] = account
    db.flush()

    created_events = 0
    for completed, titles in [(False, OPEN_TITLES), (True, PAST_TITLES)]:
        for index, title in enumerate(titles, start=1):
            organizer = users[f"organizer{1 + (index - 1) % 2}"]
            # Nhận diện cả tên cũ để bỏ nhãn mẫu mà không tạo lại event/vé.
            legacy_title = "Backend Demo Day" if title == "Backend Engineering Day" else title
            existing = db.scalar(select(Event).where(
                Event.organizer_id == organizer.id,
                Event.title.in_([title, f"[Demo] {legacy_title}"]),
            ))
            if existing is not None:
                if existing.title != title:
                    existing.title = title
                continue  # Không mở lại event đã kết thúc/hủy hoặc khôi phục vé đã dùng.
            start = (now - timedelta(days=7 * index) if completed else now + timedelta(days=7 + index * 3)).replace(hour=9, minute=0, second=0, microsecond=0)
            count = 20 if completed else OPEN_COUNTS[index - 1]
            event = Event(organizer_id=organizer.id, title=title,
                          description="Dữ liệu mẫu cho đồ án FastAPI: API, xác thực, transaction và realtime.",
                          location="Phòng thực hành CNTT" if index % 2 else "Hội trường campus",
                          start_time=start, end_time=start + timedelta(hours=3), capacity=50 + index * 5,
                          registered_count=count, status="COMPLETED" if completed else "PUBLISHED",
                          category="Technology", banner_url="")
            db.add(event)
            db.flush()
            staff = users[f"staff{1 + (index - 1) % 5}"]
            second_staff = users[f"staff{1 + index % 5}"]
            for assigned in [staff, second_staff]:
                db.add(StaffEventAssignment(staff_id=assigned.id, event_id=event.id))
            for offset in range(count):
                # Past: đủ 100 attendee phân bố trên 5 event; open: user100 còn để đăng ký thử.
                number = (index - 1) * 20 + offset + 1 if completed else ((index - 1) * 7 + offset) % 90 + 1
                attendee = users[f"user{number}"]
                registered = (start - timedelta(days=2) if completed else now - timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)
                reg = Registration(event_id=event.id, attendee_id=attendee.id, registered_at=registered)
                db.add(reg)
                db.flush()
                code = f"EVT-{'PAST' if completed else 'OPEN'}-{index:02}-U{number:03}"
                used = completed and offset < 15
                ticket = Ticket(registration_id=reg.id, ticket_code=code, qr_value=code,
                                status="USED" if used else "VALID", issued_at=registered)
                db.add(ticket)
                db.flush()
                if used:
                    scanned = (start + timedelta(minutes=offset * 3)).astimezone(timezone.utc).replace(tzinfo=None)
                    db.add(Checkin(ticket_id=ticket.id, event_id=event.id, attendee_id=attendee.id,
                                   checked_in_by=staff.id, checked_in_at=scanned, status="SUCCESS"))
            created_events += 1
    db.commit()
    print(f"Sample dataset ready: 107 numbered accounts; {created_events} events added (target: 10 open, 5 completed). Existing data preserved.")


if __name__ == "__main__":
    run()
