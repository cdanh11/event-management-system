"""Cấu hình tập trung của ứng dụng (settings).

Đọc giá trị từ biến môi trường (qua file .env nếu có) và cung cấp
một đối tượng ``settings`` dùng chung cho toàn bộ backend.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Nạp các biến từ file .env (nếu tồn tại) trước khi đọc settings.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # --- Database --------------------------------------------------------
    # URL kết nối PostgreSQL (SQLAlchemy + driver psycopg 3).
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://evently:evently@localhost:5433/evently",
    )

    # --- JWT / phiên đăng nhập ------------------------------------------
    # jwt_secret chỉ dùng cho môi trường phát triển; khi triển khai phải
    # đặt biến môi trường JWT_SECRET mới.
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-change-me")
    access_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    refresh_days: int = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))

    # --- CORS (Frontend) --------------------------------------------------
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    allow_localhost_origins: bool = os.getenv("ALLOW_LOCALHOST_ORIGINS", "true").lower() == "true"
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    # --- Thông báo (Notify) -----------------------------------------------
    # Nếu để trống, bộ gửi thông báo sẽ *mô phỏng* độ trễ mạng bằng
    # asyncio.sleep để minh hoạ async I/O. Nếu đặt URL webhook, backend sẽ
    # thật sự await một request HTTP (httpx.AsyncClient) tới dịch vụ đó.
    notify_webhook_url: str = os.getenv("NOTIFY_WEBHOOK_URL", "")
    # SMTP thật hoặc SMTP inbox local (vd Mailpit). Không có host thì giữ
    # webhook/simulated; credentials chỉ đọc từ env, không lưu vào source.
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "evently@localhost")
    smtp_starttls: bool = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
    smtp_ssl: bool = os.getenv("SMTP_SSL", "false").lower() == "true"


# Singleton: mọi module import ``settings`` từ đây đều dùng chung 1 cấu hình.
settings = Settings()
