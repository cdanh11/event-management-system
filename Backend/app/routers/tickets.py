"""Router: vé (ticket) — xem thông tin vé và mã để check-in."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..access import require_registration_access
from ..deps import current_user
from ..errors import api_error
from ..models import Registration, Ticket, User
from ..schemas import TicketOut
from ..serializers import to_ticket

router = APIRouter()


@router.get("/tickets/{ticket_id}", response_model=TicketOut, tags=["tickets"])
def get_ticket(
    ticket_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Chi tiết một vé. ATTENDEE chỉ xem được vé của chính mình."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        api_error(404, "TICKET_NOT_FOUND", "Ticket not found")

    reg = db.get(Registration, ticket.registration_id)
    require_registration_access(db, user, reg)

    return to_ticket(ticket)
