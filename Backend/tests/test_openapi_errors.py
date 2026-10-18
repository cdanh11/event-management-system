"""Check actual error responses against the public OpenAPI contract."""
from app.routers import events
from app.services.notifier import NotificationError
from tests.test_final_review import booking, event_payload


def test_observed_errors_are_documented_with_the_runtime_schema(client, auth_headers, monkeypatch):
    spec = client.get("/openapi.json").json()

    def check(method, path, template, status, **kwargs):
        response = client.request(method, path, **kwargs)
        assert response.status_code == status, response.text
        documented = spec["paths"][template][method.lower()]["responses"]
        assert str(status) in documented, (method, template, status)
        schema = documented[str(status)]["content"]["application/json"]["schema"]
        model = "ValidationErrorOut" if status == 422 else "ApiErrorOut"
        assert schema["$ref"] == f"#/components/schemas/{model}"
        body = response.json()
        assert body["status"] == status
        assert isinstance(body["code"], str) and isinstance(body["message"], str)
        if status == 422:
            assert isinstance(body["details"], list) and body["details"]

    check("GET", "/auth/me", "/auth/me", 401)
    check("POST", "/auth/login", "/auth/login", 401,
          json={"email": "missing@example.com", "password": "wrong"})
    check("POST", "/auth/refresh", "/auth/refresh", 401)
    check("POST", "/ws/ticket", "/ws/ticket", 401)
    check("GET", "/staff/events", "/staff/events", 401)
    check("GET", "/events?cursor=bad-cursor", "/events", 400)
    check("GET", "/events/missing", "/events/{event_id}", 404)

    org, att, event_id, registration = booking(client, auth_headers)
    check("GET", "/organizer/dashboard", "/organizer/dashboard", 403, headers=att)
    check("POST", "/events", "/events", 422, headers=org,
          json={**event_payload(), "capacity": -1})
    check("POST", "/auth/register", "/auth/register", 409,
          json={"name": "Already exists", "email": "att@demo.com", "password": "123456"})
    check("DELETE", f"/events/{event_id}", "/events/{event_id}", 400, headers=org)
    second_attendee = auth_headers(email="second@example.com")
    assert client.post(f"/events/{event_id}/register", headers=second_attendee).status_code == 201
    check("PATCH", f"/events/{event_id}", "/events/{event_id}", 409,
          headers=org, json={"capacity": 1})
    check("POST", f"/events/{event_id}/register", "/events/{event_id}/register", 409, headers=att)
    check("GET", "/registrations/missing", "/registrations/{registration_id}", 404, headers=att)
    check("GET", "/tickets/missing", "/tickets/{ticket_id}", 404, headers=att)
    check("POST", "/checkins", "/checkins", 404, headers=org, json={"ticket_code": "MISSING"})
    check("POST", "/checkins", "/checkins", 400, headers=org,
          json={"ticket_code": registration["ticket"]["ticket_code"]})

    async def unavailable(*_args, **_kwargs):
        raise NotificationError("Controlled transport failure")

    monkeypatch.setattr(events, "notify_attendees", unavailable)
    check("POST", f"/events/{event_id}/notify", "/events/{event_id}/notify", 502, headers=org)

    # Every operation protected by OAuth2 documents authentication failure.
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if operation.get("security"):
                assert "401" in operation["responses"], (method, path)
