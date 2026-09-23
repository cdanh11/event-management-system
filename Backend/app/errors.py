"""Helper ném lỗi HTTP tập trung.

Mọi lỗi nghiệp vụ của hệ thống đều dùng ``api_error`` để trả về body chuẩn:
    {"status": 404, "code": "EVENT_NOT_FOUND", "message": "Event not found"}
Exception handler ở app/main.py sẽ chuẩn hóa lần cuối trước khi gửi tới client.
"""
from fastapi import HTTPException


def api_error(status: int, code: str, message: str) -> None:
    """Ném HTTPException với body {code, message}.

    Hàm luôn raise nên không bao giờ trả về; type return ``None`` chỉ để
    nói rõ "không trả giá trị".
    """
    raise HTTPException(status, detail={"code": code, "message": message})