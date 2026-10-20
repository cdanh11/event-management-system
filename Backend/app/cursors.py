"""Versioned keyset cursor independent of whether the anchor event still exists.

This token is pagination metadata, not an authentication credential. Validation
rejects malformed tokens; filters/permissions remain enforced by the endpoint.
"""
import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from .timeutils import event_utc


def encode_event_cursor(start_time: datetime, event_id: str) -> str:
    payload = json.dumps({"v": 1, "time": event_utc(start_time).isoformat(), "id": event_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_event_cursor(value: str) -> tuple[datetime, str]:
    try:
        payload = json.loads(base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True))
        if (not isinstance(payload, dict) or set(payload) != {"v", "time", "id"}
                or type(payload["v"]) is not int or payload["v"] != 1
                or not isinstance(payload["time"], str) or not isinstance(payload["id"], str)):
            raise ValueError("Unsupported cursor")
        stamp = datetime.fromisoformat(payload["time"])
        if stamp.tzinfo is None:
            raise ValueError("Cursor requires a timezone")
        return event_utc(stamp), str(UUID(payload["id"]))
    except (ValueError, TypeError, KeyError, binascii.Error) as exc:
        raise ValueError("Invalid event cursor") from exc
