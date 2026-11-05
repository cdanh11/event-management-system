from fastapi.testclient import TestClient
from lab_app import app, CapacityPolicy, get_policy


PAYLOAD = {
    "title": "FastAPI Workshop",
    "start_time": "2030-01-15T09:00:00+07:00",
    "end_time": "2030-01-15T11:00:00+07:00",
    "capacity": 20,
}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_valid_event_and_response_filter():
    with TestClient(app) as client:
        response = client.post("/events", json=PAYLOAD)
        assert response.status_code == 201
        assert response.json()["capacity"] == 20
        assert "id" in response.json()
        assert "internal_note" not in response.json()


def test_negative_capacity():
    with TestClient(app) as client:
        data = {**PAYLOAD, "capacity": -1}
        response = client.post("/events", json=data)
        assert response.status_code == 422
        assert any(e["loc"] == ["body", "capacity"]
                   for e in response.json()["detail"])


def test_missing_title():
    with TestClient(app) as client:
        data = {k: v for k, v in PAYLOAD.items() if k != "title"}
        assert client.post("/events", json=data).status_code == 422


def test_end_before_start():
    with TestClient(app) as client:
        data = {**PAYLOAD, "end_time": "2030-01-15T08:00:00+07:00"}
        response = client.post("/events", json=data)
        assert response.status_code == 422
        assert any(e["type"] == "value_error"
                   for e in response.json()["detail"])


def test_policy_dependency_override():
    try:
        with TestClient(app) as client:
            assert client.post("/events", json=PAYLOAD).status_code == 201
            app.dependency_overrides[get_policy] = (
                lambda: CapacityPolicy(max_capacity=10)
            )
            response = client.post("/events", json=PAYLOAD)
            assert response.status_code == 400
            assert response.json()["detail"] == "CAPACITY_POLICY_LIMIT"
            app.dependency_overrides[get_policy] = (
                lambda: CapacityPolicy(max_capacity=100)
            )
            assert client.post("/events", json=PAYLOAD).status_code == 201
    finally:
        app.dependency_overrides.clear()
