"""Middleware tự viết: log + đo thời gian xử lý request.

Mục đích minh chứng: FastAPI cho phép bọc thêm tầng xử lý trước/sau mọi
endpoint. Đây cũng là chỗ hợp lý để đo latency và gắn header ``X-Process-Time-Ms``
mà Frontend/test có thể đọc.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("evently.api")


class TimingLoggingMiddleware(BaseHTTPMiddleware):
    """Ghi log ``METHOD path -> status (ms)`` và gắn header thời gian xử lý."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()

        # call_next: chuyển request qua toàn bộ chuỗi còn lại (router, deps,
        # endpoint) và trả về response — đây là điểm await mà middleware chờ.
        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response