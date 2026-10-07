"""Điểm khởi chạy: ``uvicorn app.main:app --reload --port 8000``.

Nơi khai báo:
- lifespan (startup/shutdown): quản lý resource theo vòng đời ứng dụng.
- exception handler tập trung: chuẩn hóa body lỗi + validation 422.
- middleware: CORS (cho trình duyệt) + TimingLoggingMiddleware (log/thời gian).
- OpenAPI: FastAPI tự sinh schema từ router, Pydantic và OAuth2PasswordBearer dependency.
- async: chúng ta CHỈ dùng ``async def`` ở chỗ có I/O awaitable thật
  (xem services.notifier + POST /events/{id}/notify); handler dùng DB sync
  vẫn để ``def`` để FastAPI xử lý trong threadpool.
"""
import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import engine
from .middleware import TimingLoggingMiddleware
from .routers import api_router
from .config import settings
from .schemas import HealthOut
from .services.notifier import close_notifier_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evently")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown của ứng dụng (quản lý resource tập trung).

    - Startup: quét 1 lượt lifecycle + chạy task nền sweep mỗi 60s (asyncio,
      DB chạy trong threadpool) để tự động STARTED/COMPLETED theo giờ.
    - Shutdown: hủy sweep task, đóng notifier client, dispose engine.
    """
    from .services.lifecycle import lifecycle_loop, sweep_due_events

    logger.info("Lifespan startup: ứng dụng Evently bắt đầu khởi chạy.")
    try:
        # DB test (SQLite override) hoặc DB chưa sẵn: bỏ qua, sweep loop sẽ thử lại.
        await asyncio.to_thread(sweep_due_events)
    except Exception:  # noqa: BLE001
        logger.warning("startup sweep skipped (DB chưa sẵn sàng)")
    sweeper = asyncio.create_task(lifecycle_loop())
    try:
        yield
    finally:
        logger.info("Lifespan shutdown: đóng task nền, HTTP client và connection pool.")
        sweeper.cancel()
        # Chờ task nhận cancellation trước khi giải phóng tài nguyên dùng chung.
        with suppress(asyncio.CancelledError):
            await sweeper
        await close_notifier_client()
        engine.dispose()


app = FastAPI(
    title="Evently API",
    version="1.0.0",
    description=(
        "Event management API (FastAPI). Docs này được sinh tự động từ Pydantic "
        "models; bấm Authorize, nhập email ở username và mật khẩu để nhận JWT qua OAuth2 password flow."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Đăng nhập / refresh / logout"},
        {"name": "events", "description": "Sự kiện: tạo, dời lịch, chuyển trạng thái, notify"},
        {"name": "registrations", "description": "Đăng ký tham dự / hủy đăng ký"},
        {"name": "tickets", "description": "Vé sự kiện"},
        {"name": "checkins", "description": "Check-in tại cửa ra vào"},
        {"name": "realtime", "description": "Occupancy realtime qua WebSocket"},
        {"name": "staff", "description": "Sự kiện của staff"},
        {"name": "assignments", "description": "Gán staff vào sự kiện"},
        {"name": "system", "description": "Endpoint kiểm tra sức khỏe"},
    ],
    lifespan=lifespan,
)


# ---------------- Middleware ----------------------------------------------
# CORS: cho phép Frontend (React/Vite) gọi API. Trong phát triển cho phép
# mọi port localhost; production nên cố định origin qua FRONTEND_ORIGIN.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$" if settings.allow_localhost_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Next-Cursor", "X-Process-Time-Ms"],
)
# Middleware tự viết: log + đo thời gian từng request.
app.add_middleware(TimingLoggingMiddleware)


# ---------------- Exception handler tập trung ----------------------------
@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    """Chuẩn hóa MỌI lỗi HTTP thành body: {status, code, message}.

    Nếu module khác đã trả dạng {code,message} thì giữ
    nguyên; nếu không thì đóng gói lại để client xử lý thống nhất.
    """
    if isinstance(exc.detail, dict):
        detail = exc.detail
    else:
        detail = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": exc.status_code, **detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """Trả lời câu hỏi: "Model input sai kiểu thì lỗi sinh ở tầng nào?"

    Đáp án: Pydantic (tầng parsing/serialization) validate ngay lúc bind body
    -> ném RequestValidationError TRƯỚC khi endpoint được gọi. Handler này
    đóng gói lỗi đó về dạng chuẩn + kèm chi tiết từng field lỗi.
    """
    # Phase 1: model_validator đưa ValueError vào ctx.error — phải sanitize
    # trước khi json.dumps, nếu không handler 422 tự crash thành 500.
    details = jsonable_encoder(exc.errors(), custom_encoder={ValueError: str})
    return JSONResponse(
        status_code=422,
        content={
            "status": 422,
            "code": "VALIDATION_ERROR",
            "message": "Request payload is invalid",
            "details": details,
        },
    )


# ---------------- Routes ---------------------------------------------------
app.include_router(api_router)


@app.get("/health", tags=["system"], response_model=HealthOut)
def health():
    """Endpoint kiểm tra sức khỏe.

    Đây là ví dụ endpoint KHÔNG cần async: không có I/O, không có gì để await;
    viết ``async def`` ở đây chỉ vô ích và làm việc phân biệt async/sync mờ.
    """
    return {"status": "ok"}
