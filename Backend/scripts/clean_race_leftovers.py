"""Dọn dữ liệu sót từ các lần chạy concurrency test (thứ tự FK)."""
import sqlalchemy as sa
from sqlalchemy import text

e = sa.create_engine("postgresql+psycopg://evently:evently@localhost:5433/evently")
with e.begin() as c:
    ev = [r[0] for r in c.execute(text("SELECT id FROM events WHERE title = 'Race'")).all()]
    for eid in ev:
        rids = [r[0] for r in c.execute(
            text("SELECT id FROM registrations WHERE event_id = :eid"), {"eid": eid}).all()]
        for rid in rids:
            c.execute(text("DELETE FROM tickets WHERE registration_id = :rid"), {"rid": rid})
            c.execute(text("DELETE FROM registrations WHERE id = :rid"), {"rid": rid})
        c.execute(text("DELETE FROM events WHERE id = :eid"), {"eid": eid})
    emails = ["org@demo.com"] + [f"att{i}@demo.com" for i in range(5)]
    uids = [r[0] for r in c.execute(
        text("SELECT id FROM users WHERE email = ANY(:emails)"), {"emails": emails}).all()]
    for uid in uids:
        c.execute(text("DELETE FROM refresh_tokens WHERE user_id = :uid"), {"uid": uid})
        c.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
    print("events removed:", len(ev), "| users removed:", len(uids))
