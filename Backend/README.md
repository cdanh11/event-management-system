# Evently FastAPI backend

1. Create PostgreSQL database `evently` and copy `.env.example` to `.env` (or export its values).
2. `python -m venv .venv`, activate it, then `pip install -r requirements.txt`.
3. Apply schema with `alembic upgrade head` (or `python -m app.seed` for a seeded local demo).
4. Run `uvicorn app.main:app --reload --port 8000`.

Swagger is available at `http://localhost:8000/docs`. Seeded demo password is `123456`.
