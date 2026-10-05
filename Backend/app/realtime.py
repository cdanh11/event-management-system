"""Realtime occupancy qua WebSocket — Phase 0.

Màn hình Admin xem "Vé còn lại" tự nhảy số khi có đăng ký/hủy,
không cần reload. Mỗi event là một room `event_id`.

Giới hạn Phase 0 (ghi rõ để báo cáo trung thực):
- Broadcast trong tiến trình (in-memory). Chạy nhiều worker/instance
  thì client ở instance khác không nhận được tin — cần Redis pub/sub
  ở phase sau (đúng câu hỏi Tầng 3 C2.3).
"""

import asyncio
import secrets
import time

from fastapi import WebSocket

# --- WS ticket handshake (trả lời góp ý bảo mật hội đồng) -------------------
# JWT không đi trên query string (dính log proxy, referer, history).
# Client lấy ticket một lần qua REST có header Authorization, ticket sống
# 30s, dùng 1 lần duy nhất rồi bị thu hồi.
WS_TICKET_TTL_SECONDS = 30

_tickets: dict[str, tuple[str, float]] = {}  # ticket -> (user_id, expires_at)


def mint_ws_ticket(user_id: str) -> str:
    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = (user_id, time.monotonic() + WS_TICKET_TTL_SECONDS)
    return ticket


def redeem_ws_ticket(ticket: str | None) -> str | None:
    """Đổi ticket lấy user_id; ticket sai/hết hạn/đã dùng -> None."""
    if not ticket:
        return None
    found = _tickets.pop(ticket, None)
    if found is None:
        return None
    user_id, expires_at = found
    if time.monotonic() > expires_at:
        return None
    return user_id


def occupancy_payload(event) -> dict:
    """Snapshot occupancy chuẩn cho cả REST và WS."""
    capacity = event.capacity
    registered = event.registered_count
    return {
        "type": "occupancy",
        "event_id": event.id,
        "capacity": capacity,
        "registered_count": registered,
        "remaining": max(0, capacity - registered),
        "status": event.status,
    }


class ConnectionManager:
    """Quản lý kết nối WS theo room `event_id`."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, event_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(event_id, set()).add(websocket)

    async def disconnect(self, event_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(event_id)
            if room and websocket in room:
                room.remove(websocket)
            if room is not None and not room:
                del self._rooms[event_id]

    async def broadcast_occupancy(self, event_id: str, message: dict) -> None:
        """Gửi occupancy tới mọi client đang xem event. Kẻ chết thì bỏ qua."""
        async with self._lock:
            targets = list(self._rooms.get(event_id, set()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(event_id, ws)

    def room_size(self, event_id: str) -> int:
        return len(self._rooms.get(event_id, set()))


# Singleton dùng chung toàn app (Phase 0: single-process).
manager = ConnectionManager()
