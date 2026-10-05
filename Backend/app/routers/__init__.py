"""Tổng hợp mọi router thành một ``api_router`` duy nhất.

Chia theo tài nguyên (auth, events, registrations, tickets, checkins, staff)
giúp mỗi file ngắn, dễ đọc, dễ nói vị trí code trong báo cáo.
"""
from fastapi import APIRouter

from ..schemas import ValidationErrorOut
from .auth import router as auth_router
from .checkins import router as checkins_router
from .events import router as events_router
from .realtime import router as realtime_router
from .registrations import router as registrations_router
from .staff import router as staff_router
from .tickets import router as tickets_router

api_router = APIRouter(
    responses={
        422: {
            "model": ValidationErrorOut,
            "description": "Request khong dung schema Pydantic.",
        }
    }
)
api_router.include_router(auth_router)
api_router.include_router(realtime_router)
api_router.include_router(events_router)
api_router.include_router(registrations_router)
api_router.include_router(tickets_router)
api_router.include_router(checkins_router)
api_router.include_router(staff_router)
