import pytest
from services.inventory.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_stock_available():
    response = client.get("/stock?item_id=item-1")
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "item-1"
    assert data["available"] == 100


def test_get_stock_out_of_stock():
    response = client.get("/stock?item_id=item-2")
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "item-2"
    assert data["available"] == 0


def test_get_stock_not_found():
    response = client.get("/stock?item_id=item-999")
    assert response.status_code == 404
    assert "Item not found" in response.json()["detail"]