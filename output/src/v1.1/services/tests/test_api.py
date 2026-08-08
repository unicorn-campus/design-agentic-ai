from fastapi.testclient import TestClient

from services.api.main import create_app


def test_health_and_openapi() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok", "version": "1.1.0"}
        assert "/api/v1/recommendations" in client.get("/openapi.json").json()["paths"]


def test_recommendation_returns_exactly_three_cards() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/recommendations", json={"member_id": "member-1", "region_label": "강남역"})
    assert response.status_code == 200
    assert response.json()["card_count"] == 3
    assert len(response.json()["cards"]) == 3


def test_validation_error_does_not_echo_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/recommendations", json={"member_id": "", "region_label": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert "input" not in response.text


def test_sse_has_complete_event() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/recommendations/stream", json={"member_id": "member-1", "region_label": "강남역"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.count("event: recommendation") == 3
    assert "event: complete" in response.text


def test_subscription_requires_approval_and_is_idempotent() -> None:
    payload = {"member_id": "member-1", "approved": False, "idempotency_key": "subscription-0001"}
    with TestClient(create_app()) as client:
        denied = client.post("/api/v1/subscriptions", json=payload)
        payload["approved"] = True
        first = client.post("/api/v1/subscriptions", json=payload)
        second = client.post("/api/v1/subscriptions", json=payload)
    assert denied.status_code == 409
    assert denied.json()["code"] == "approval_required"
    assert first.json() == second.json()
