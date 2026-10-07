"""Router realtime: snapshot REST + kênh WebSocket occupancy.

- GET  /events/{event_id}/occupancy : snapshot cho dashboard (ORGANIZER).
- POST /ws/ticket                   : cấp ticket WS một lần (mọi role đã login, qua header).
- WS   /ws/events/{event_id}        : stream occupancy theo room event.

Ticket sống 30s, dùng 1 lần — JWT không bao giờ đi trên query string
(tránh dính log proxy, referer, history). Dữ liệu occupancy (số ghế/số vé)
vốn đã public qua GET /events nên mọi role đã đăng nhập đều subscribe được;
mã đóng: 4401 ticket sai/hết hạn/đã dùng, 4404 event không tồn tại.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require
from ..errors import api_error
from ..models import Event, User
from ..realtime import WS_TICKET_TTL_SECONDS, manager, mint_ws_ticket, occupancy_payload, redeem_ws_ticket
from ..schemas import AUTH_RESPONSES, ERROR_404, OccupancyOut, WsTicketOut

router = APIRouter()


def _ws_snapshot(websocket: WebSocket, event_id: str, db: Session = Depends(get_db)) -> dict:
    """Dependency sync: handshake DB chạy trong threadpool, trả dữ liệu thuần.

    Kết thúc transaction ngay sau snapshot để WebSocket không giữ connection
    PostgreSQL suốt thời gian người dùng mở màn hình live.
    """
    try:
        user_id = redeem_ws_ticket(websocket.query_params.get("ticket"))
        if not user_id or db.get(User, user_id) is None:
            return {"close_code": 4401}
        event = db.get(Event, event_id)
        if event is None:
            return {"close_code": 4404}
        return {**occupancy_payload(event), "type": "snapshot"}
    finally:
        db.rollback()


@router.get(
    "/events/{event_id}/occupancy",
    response_model=OccupancyOut,
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
    response_model=WsTicketOut,
    tags=["realtime"],
)
def create_ws_ticket(user: User = Depends(current_user)):
    """Cấp ticket WS một lần cho user đã đăng nhập (gọi qua header Authorization)."""
    return {"ticket": mint_ws_ticket(user.id), "expires_in": WS_TICKET_TTL_SECONDS}


@router.websocket("/ws/events/{event_id}")
async def event_occupancy_ws(
    websocket: WebSocket,
    event_id: str,
    snapshot: dict = Depends(_ws_snapshot),
):
    """Kênh realtime occupancy của một event (auth bằng ticket một lần)."""
    if "close_code" in snapshot:
        await websocket.close(code=snapshot["close_code"])
        return

    await manager.connect(event_id, websocket)
    try:
        # Snapshot đầu để client vẽ ngay, không phải chờ có biến động.
        await websocket.send_json(snapshot)
        while True:
            # Nhận heartbeat; server không echo và không thực hiện DB I/O tại đây.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(event_id, websocket)
