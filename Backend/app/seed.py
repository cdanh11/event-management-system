"""Seed dữ liệu demo. Chạy: ``python -m app.seed``.

Tạo database (nếu chưa có), thêm 6 tài khoản demo (mật khẩu: ``123456``),
6 sự kiện mẫu thuộc nhiều trạng thái, 2 assignment staff và 1 registration
+ticket sẵn (mã check-in ``AI-MEET-2026``).
"""
from datetime import datetime, timedelta

from .db import Base, SessionLocal, engine
from .models import Event, Registration, StaffEventAssignment, Ticket, User #tất cả tự đăng ký vào Base.metadata
from .security import hash_password


def run() -> None:
    """Tạo schema + dữ liệu demo nếu database chưa có user nào."""
    Base.metadata.create_all(engine)
    db = SessionLocal()

    if db.query(User).first() is not None:
        print("Database already seeded")
        db.close()
        return

    # --- 6 tài khoản theo 3 role -----------------------------------------
    users = [
        User(name="Minh Nguyen", email="attendee@demo.com", role="ATTENDEE",
             avatar_url="MN", password_hash=hash_password("123456")),
        User(name="Linh Tran", email="linh@demo.com", role="ATTENDEE",
             avatar_url="LT", password_hash=hash_password("123456")),
        User(name="Huy Pham", email="huy@demo.com", role="ATTENDEE",
             avatar_url="HP", password_hash=hash_password("123456")),
        User(name="An Le", email="staff@demo.com", role="STAFF",
             avatar_url="AL", password_hash=hash_password("123456")),
        User(name="Khanh Do", email="khanh.staff@demo.com", role="STAFF",
             avatar_url="KD", password_hash=hash_password("123456")),
        User(name="Evently Team", email="organizer@demo.com", role="ORGANIZER",
             avatar_url="ET", password_hash=hash_password("123456")),
    ]
    db.add_all(users)
    db.flush() # gửi câu lệnh SQL xuống DB (DB sinh ra id thật cho mỗi row), nhưng transaction chưa đóng — vẫn có thể rollback
    organizer = users[-1]

    # --- 6 sự kiện mẫu ở nhiều trạng thái ---------------------------------
    now = datetime.now()
    specs = [
        ("Vietnam Tech Conference 2026", "PUBLISHED", now + timedelta(days=30), 300, 184),
        ("Design Systems Workshop", "PUBLISHED", now + timedelta(days=15), 50, 47),
        ("Career Fair: Future Makers", "PUBLISHED", now + timedelta(days=22), 150, 150),
        ("AI Product Meetup", "ONGOING", now - timedelta(hours=1), 80, 63),
        ("Startup Pitch Night", "COMPLETED", now - timedelta(days=20), 100, 89),
        ("Community Design Day", "CANCELLED", now + timedelta(days=45), 60, 12),
    ]

    events = []
    for title, status, start, capacity, count in specs:
        events.append(
            Event(
                organizer_id=organizer.id,
                title=title,
                description=f"{title} for the Evently community.",
                location="Ho Chi Minh City",
                start_time=start,
                end_time=start + timedelta(hours=6),
                capacity=capacity,
                registered_count=count,
                status=status,
                category="Technology",
                banner_url="https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=1200&q=80",
            )
        )
    db.add_all(events)
    db.flush()

    # --- Gán staff cho 2 sự kiện + 1 registration kèm ticket sẵn ----------
    db.add_all(
        [
            StaffEventAssignment(staff_id=users[3].id, event_id=events[3].id),
            StaffEventAssignment(staff_id=users[4].id, event_id=events[0].id),
        ]
    )

    reg = Registration(event_id=events[3].id, attendee_id=users[0].id)
    db.add(reg)
    db.flush()
    db.add(Ticket(registration_id=reg.id, ticket_code="AI-MEET-2026", qr_value="AI-MEET-2026"))

    db.commit()
    print("Seeded Evently demo accounts and events")
    db.close()


if __name__ == "__main__":
    run()