"""Router realtime: snapshot REST + kênh WebSocket occupancy.

- GET  /events/{event_id}/occupancy : snapshot cho dashboard (ORGANIZER).
- POST /ws/ticket                   : cấp ticket WS một lần (ORGANIZER, qua header).
- WS   /ws/events/{event_id}        : stream occupancy, auth bằng `?ticket=`.

Ticket sống 30s, dùng 1 lần — JWT không bao giờ đi trên query string
(tránh dính log proxy, referer, history). Mã đóng: 4401 ticket sai/hết hạn/đã
dùng, 4403 sai role, 4404 event không tồn tại.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..errors import api_error
from ..models import Event, User
from ..realtime import WS_TICKET_TTL_SECONDS, manager, mint_ws_ticket, occupancy_payload, redeem_ws_ticket
from ..schemas import AUTH_RESPONSES, ERROR_404

router = APIRouter()


@router.get(
    "/events/{event_id}/occupancy",
    tags=["realtime"],
    dependencies=[Depends(require("ORGANIZER"))],
    responses={**AUTH_RESPONSES, 404: ERROR_404},
)
def event_occupancy(event_id: str, db: Session = Depends(get_db)):
    """Snapshot occupancy cho dashboard Admin (cần ORGANIZER)."""
    event = db.get(Event, event_id)
    if event is None:
        api_error(404, "EVENT_NOT_FOUND", "Event not found")
    return occupancy_payload(event)


@router.post(
    "/ws/ticket",
    tags=["realtime"],
    dependencies=[Depends(require("ORGANIZER"))],
)
def create_ws_ticket(user: User = Depends(require("ORGANIZER"))):
    """Cấp ticket WS một lần cho ORGANIZER (gọi qua header Authorization)."""
    return {"ticket": mint_ws_ticket(user.id), "expires_in": WS_TICKET_TTL_SECONDS}


@router.websocket("/ws/events/{event_id}")
async def event_occupancy_ws(
    websocket: WebSocket,
    event_id: str,
    db: Session = Depends(get_db),
):
    """Kênh realtime occupancy của một event (auth bằng ticket một lần)."""
    user_id = redeem_ws_ticket(websocket.query_params.get("ticket"))
    user = db.get(User, user_id) if user_id else None
    if user is None:
        await websocket.close(code=4401)
        return
    if user.role != "ORGANIZER":
        await websocket.close(code=4403)
        return

    event = db.get(Event, event_id)
    if event is None:
        await websocket.close(code=4404)
        return

    await manager.connect(event_id, websocket)
    try:
        # Snapshot đầu để client vẽ ngay, không phải chờ có biến động.
        await websocket.send_json({"type": "snapshot", **occupancy_payload(event)})
        while True:
            # Giữ kết nối sống; client gửi ping/text bất kỳ đều được echo nhẹ.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(event_id, websocket)
