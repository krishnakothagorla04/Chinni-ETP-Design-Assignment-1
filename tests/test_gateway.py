import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.gateway.main import app
from fastapi.testclient import TestClient
import httpx

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Gateway UI" in response.text
    assert "POST /api/checkout" in response.text
    assert "Open /api/ping" in response.text


def test_ui_endpoint():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "Gateway UI" in response.text
    assert "HTML endpoint: <strong>/ui</strong>" in response.text


def test_get_arch():
    response = client.get("/api/arch")
    assert response.status_code == 200
    assert response.text == "nanoservices-k8s-keda"


def test_ping():
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_proxy_checkout_success():
    # Mock the httpx.AsyncClient used inside gateway
    mock_response = MagicMock()
    mock_response.json.return_value = {"order_id": 123, "total_cost": 20.0}
    mock_response.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)

    mock_async_client = MagicMock()
    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("services.gateway.main.httpx.AsyncClient", mock_async_client):
        payload = {"items": [{"item_id": "item-1", "quantity": 2}]}
        response = client.post("/api/checkout", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == 123
    assert data["total_cost"] == 20.0


def test_proxy_checkout_failure():
    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

    mock_async_client = MagicMock()
    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("services.gateway.main.httpx.AsyncClient", mock_async_client):
        payload = {"items": [{"item_id": "item-1", "quantity": 2}]}
        response = client.post("/api/checkout", json=payload)

    assert response.status_code == 503
    assert "Checkout service unavailable" in response.json()["detail"]