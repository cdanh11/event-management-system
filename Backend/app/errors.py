"""Helper ném lỗi HTTP tập trung.

Mọi lỗi nghiệp vụ của hệ thống đều dùng ``api_error`` để trả về body chuẩn:
    {"status": 404, "code": "EVENT_NOT_FOUND", "message": "Event not found"}
Exception handler ở app/main.py sẽ chuẩn hóa lần cuối trước khi gửi tới client.
"""
from fastapi import HTTPException
from typing import NoReturn


def api_error(status: int, code: str, message: str) -> NoReturn:
    """Ném HTTPException với body {code, message}.

    NoReturn giúp người đọc/type checker biết nhánh này luôn kết thúc bằng lỗi.
    """
    raise HTTPException(status, detail={"code": code, "message": message})
