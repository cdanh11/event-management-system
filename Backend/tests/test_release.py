"""Kiểm tra contract và tích hợp trước khi đóng source MVP.

SMTP chỉ kết nối inbox localhost của fixture, không gửi tới người thật.
"""
import socketserver
import threading
from contextlib import contextmanager
from dataclasses import replace
from email import policy
from email.parser import BytesParser

from app.services import notifier
from tests.test_final_review import booking, event_payload


def test_oauth2_form_uses_same_identity_and_cannot_request_a_role(client, make_user):
    make_user("Reader", "reader@demo.com", "ATTENDEE")
    response = client.post("/auth/token", data={"username": "reader@demo.com", "password": "123456", "grant_type": "password", "scope": "ORGANIZER"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.cookies.get("evently_refresh")
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["role"] == "ATTENDEE"
    assert client.post("/events", headers=headers, json=event_payload()).status_code == 403
    assert client.post("/auth/token", data={"username": "reader@demo.com", "password": "wrong", "grant_type": "password"}).status_code == 401
    assert client.post("/auth/token", data={"username": "reader@demo.com", "password": "123456", "grant_type": "client_credentials"}).status_code == 422


def test_patch_capacity_reaches_connected_dashboard(client, auth_headers):
    org, _, event_id, _ = booking(client, auth_headers)
    ticket = client.post("/ws/ticket", headers=org).json()["ticket"]
    with client.websocket_connect(f"/ws/events/{event_id}?ticket={ticket}") as ws:
        assert ws.receive_json()["capacity"] == 5
        response = client.patch(f"/events/{event_id}", headers=org, json={"capacity": 9})
        assert response.status_code == 200
        frame = ws.receive_json()
        assert (frame["capacity"], frame["registered_count"], frame["remaining"]) == (9, 1, 8)
        assert client.get(f"/events/{event_id}/occupancy", headers=org).json() == frame


def test_organizer_pagination_is_scoped_sorted_and_filtered_in_db(client, auth_headers):
    owner = auth_headers(role="ORGANIZER", email="owner@demo.com")
    other = auth_headers(role="ORGANIZER", email="other@demo.com")
    attendee = auth_headers(email="reader@demo.com")
    ids = []
    for name, status in [("Draft", None), ("Published", "PUBLISHED"), ("Open", "STARTED")]:
        payload = {**event_payload(), "title": name}
        event_id = client.post("/events", headers=owner, json=payload).json()["id"]
        ids.append(event_id)
        if status:
            client.post(f"/events/{event_id}/transition", headers=owner, json={"status": "PUBLISHED"})
            if status == "STARTED":
                client.post(f"/events/{event_id}/transition", headers=owner, json={"status": status})
    client.post("/events", headers=other, json=event_payload())
    pages = [client.get(f"/organizer/events?limit=1&offset={offset}", headers=owner).json() for offset in range(3)]
    assert [page["items"][0]["id"] for page in pages] == [ids[2], ids[1], ids[0]]
    assert all(page["total"] == 3 for page in pages)
    assert [page["has_more"] for page in pages] == [True, True, False]
    assert client.get("/organizer/events?status=DRAFT&q=Draft", headers=owner).json()["total"] == 1
    assert client.get("/organizer/events?offset=99", headers=owner).json()["items"] == []
    assert client.get("/organizer/events?limit=0", headers=owner).status_code == 422
    assert client.get("/organizer/events?sort=unknown", headers=owner).status_code == 422
    assert client.get("/organizer/events", headers=attendee).status_code == 403


def test_new_endpoints_have_typed_openapi_contract(client):
    spec = client.get("/openapi.json").json()
    flow = spec["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]
    assert flow["tokenUrl"] == "auth/token"
    for path, method, name in [
        ("/organizer/events", "get", "EventPageOut"),
        ("/organizer/dashboard", "get", "OrganizerDashboardOut"),
        ("/events/{event_id}/occupancy", "get", "OccupancyOut"),
        ("/ws/ticket", "post", "WsTicketOut"),
        ("/health", "get", "HealthOut"),
    ]:
        assert spec["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/" + name)


@contextmanager
def smtp_inbox():
    """SMTP test ở port tạm, chỉ loopback; không gửi ra dịch vụ bên ngoài."""
    messages = []

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.wfile.write(b"220 localhost ready\r\n")
            while command := self.rfile.readline():
                verb = command.split()[0].upper()
                if verb in (b"EHLO", b"HELO"):
                    self.wfile.write(b"250 localhost\r\n")
                elif verb == b"DATA":
                    self.wfile.write(b"354 End with dot\r\n")
                    content = []
                    while (line := self.rfile.readline()) and line != b".\r\n":
                        content.append(line[1:] if line.startswith(b"..") else line)
                    messages.append(BytesParser(policy=policy.default).parsebytes(b"".join(content)))
                    self.wfile.write(b"250 accepted\r\n")
                elif verb == b"QUIT":
                    self.wfile.write(b"221 bye\r\n")
                    break
                else:
                    self.wfile.write(b"250 ok\r\n")

    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], messages
        finally:
            server.shutdown()
            thread.join(timeout=2)


def test_registration_background_task_delivers_smtp_ticket_and_png(client, auth_headers, monkeypatch):
    with smtp_inbox() as (port, messages):
        monkeypatch.setattr(notifier, "settings", replace(notifier.settings, smtp_host="127.0.0.1", smtp_port=port, smtp_starttls=False, smtp_ssl=False, smtp_username="", smtp_from="demo@evently.local"))
        org, _, event_id, result = booking(client, auth_headers)
        assert len(messages) == 1
        message = messages[0]
        assert message["To"] == "att@demo.com"
        assert result["ticket"]["ticket_code"] in message.get_body(preferencelist=("plain",)).get_content()
        attachment = list(message.iter_attachments())[0]
        assert attachment.get_content_type() == "image/png"
        assert attachment.get_payload(decode=True).startswith(b"\x89PNG\r\n\x1a\n")
        response = client.post(f"/events/{event_id}/notify", headers=org)
        assert response.json()["mode"] == "smtp"
        assert response.json()["emails_sent"] == 1
        assert len(messages) == 2


def test_delivery_failure_preserves_booking_and_explicit_notify_returns_502(client, auth_headers, monkeypatch):
    def unavailable(_payload):
        raise notifier.NotificationError("test transport unavailable")

    monkeypatch.setattr(notifier, "settings", replace(notifier.settings, smtp_host="localhost"))
    monkeypatch.setattr(notifier, "_send_smtp", unavailable)
    org, att, event_id, result = booking(client, auth_headers)
    assert client.get(f"/tickets/{result['ticket']['id']}", headers=att).json()["status"] == "VALID"
    assert client.get(f"/events/{event_id}").json()["registered_count"] == 1
    assert client.post(f"/events/{event_id}/notify", headers=org).status_code == 502
