import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.checkout.main import app
from fastapi.testclient import TestClient
import httpx

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_checkout_success():
    # Mock inventory response
    inv_mock = MagicMock()
    inv_mock.status_code = 200
    inv_mock.json.return_value = {"available": 10}

    # Mock pricing response
    price_mock = MagicMock()
    price_mock.status_code = 200
    price_mock.json.return_value = {"total_price": 20.0}

    # Create a mock async client that supports async context manager
    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(side_effect=[inv_mock, price_mock])

    mock_async_client = MagicMock()
    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("services.checkout.main.httpx.AsyncClient", mock_async_client), \
         patch("services.checkout.main._save_order_to_db", return_value=1):
        payload = {"items": [{"item_id": "item-1", "quantity": 2}]}
        response = client.post("/api/checkout", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_cost"] == 20.0
    assert data["order_id"] == 1
    assert len(data["items"]) == 1


def test_checkout_insufficient_stock():
    # Mock inventory response - not enough stock
    inv_mock = MagicMock()
    inv_mock.status_code = 200
    inv_mock.json.return_value = {"available": 1}  # Only 1 available, requesting 2

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=inv_mock)

    mock_async_client = MagicMock()
    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("services.checkout.main.httpx.AsyncClient", mock_async_client):
        payload = {"items": [{"item_id": "item-1", "quantity": 2}]}
        response = client.post("/api/checkout", json=payload)

    assert response.status_code == 409
    assert "Not enough stock" in response.json()["detail"]


def test_checkout_inventory_unavailable():
    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(side_effect=httpx.RequestError("Timeout"))

    mock_async_client = MagicMock()
    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("services.checkout.main.httpx.AsyncClient", mock_async_client):
        payload = {"items": [{"item_id": "item-1", "quantity": 1}]}
        response = client.post("/api/checkout", json=payload)

    assert response.status_code == 503
    assert "Inventory service unavailable" in response.json()["detail"]


def test_checkout_no_items():
    payload = {"items": []}
    response = client.post("/api/checkout", json=payload)
    assert response.status_code == 400
    assert "No items provided" in response.json()["detail"]