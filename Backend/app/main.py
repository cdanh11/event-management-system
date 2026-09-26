"""Points vào chạy: ``uvicorn app.main:app --reload --port 8000``.

Nơi khai báo:
- lifespan (startup/shutdown): quản lý resource theo vòng đời ứng dụng.
- exception handler tập trung: chuẩn hóa body lỗi + validation 422.
- middleware: CORS (cho trình duyệt) + TimingLoggingMiddleware (log/thời gian).
- OpenAPI: gắn security scheme JWT để Swagger hiện nút "Authorize".
- async: chúng ta CHỈ dùng ``async def`` ở chỗ có I/O awaitable thật
  (xem services.notifier + POST /events/{id}/notify); handler dùng DB sync
  vẫn để ``def`` để FastAPI xử lý trong threadpool.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from .db import engine
from .middleware import TimingLoggingMiddleware
from .routers import api_router
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evently")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown của ứng dụng (quản lý resource tập trung).

    - Startup: nơi hợp lý để mở kết nối model/load model phục vụ app.
    - Shutdown: giải phóng connection pool của database (engine.dispose).
    """
    logger.info("Lifespan startup: ứng dụng Evently bắt đầu khởi chạy.")
    yield
    logger.info("Lifespan shutdown: đóng connection pool database.")
    engine.dispose() #dọn dẹp db


app = FastAPI(
    title="Evently API",
    version="1.0.0",
    description=(
        "Event management API (FastAPI). Docs này được sinh tự động từ Pydantic "
        "models; bấm Authorize và dán access token (Bearer) để gọi các endpoint có khóa."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Đăng nhập / refresh / logout"},
        {"name": "events", "description": "Sự kiện: tạo, dời lịch, chuyển trạng thái, notify"},
        {"name": "registrations", "description": "Đăng ký tham dự / hủy đăng ký"},
        {"name": "tickets", "description": "Vé sự kiện"},
        {"name": "checkins", "description": "Check-in tại cửa ra vào"},
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
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Middleware tự viết: log + đo thời gian từng request.
app.add_middleware(TimingLoggingMiddleware)


# ---------------- Exception handler tập trung ----------------------------
@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    """Chuẩn hóa MỌI lỗi HTTP thành body: {status, code, message}.

    Nếu code khác module (vd OURBEAT...) đã sẵn dạng {code,message} thì giữ
    nguyên; nếu không thì đóng gói lại để client xử lý thống nhất.
    """
    if isinstance(exc.detail, dict):
        detail = exc.detail
    else:
        detail = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"status": exc.status_code, **detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """Trả lời câu hỏi: "Model input sai kiểu thì lỗi sinh ở tầng nào?"

    Đáp án: Pydantic (tầng parsing/serialization) validate ngay lúc bind body
    -> ném RequestValidationError TRƯỚC khi endpoint được gọi. Handler này
    đóng gói lỗi đó về dạng chuẩn + kèm chi tiết từng field lỗi.
    """
    return JSONResponse(
        status_code=422,
        content={
            "status": 422,
            "code": "VALIDATION_ERROR",
            "message": "Request payload is invalid",
            "details": exc.errors(),
        },
    )


# ---------------- OpenAPI: gắn security scheme JWT ------------------------
def custom_openapi():
    """Bổ sung security scheme "HTTP Bearer" vào schema OpenAPI.

    Mặc định FastAPI không tự khai báo security từ HTTPBearer dependency;
    phần này làm cho Swagger (docs) hiện nút Authorize và mô tả đúng auth."""
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "HTTPBearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    schema["security"] = [{"HTTPBearer": []}] # Áp dụng scheme đó làm security mặc định cho toàn bộ API

    app.openapi_schema = schema # Lưu lại vào cache để lần gọi sau không build lại
    return schema


app.openapi = custom_openapi


# ---------------- Routes ---------------------------------------------------
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health():
    """Endpoint kiểm tra sức khỏe.

    Đây là ví dụ endpoint KHÔNG cần async: không có I/O, không có gì để await;
    viết ``async def`` ở đây chỉ vô ích và làm việc phân biệt async/sync mờ.
    """
    return {"status": "ok"}