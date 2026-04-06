import pytest
from services.pricing.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_price_single_item():
    response = client.get("/price?item_id=item-1&quantity=1")
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "item-1"
    assert data["quantity"] == 1
    assert data["total_price"] == 10.0


def test_get_price_bulk_discount():
    response = client.get("/price?item_id=item-1&quantity=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_price"] == 90.0  # 10 * 10 * 0.9


def test_get_price_no_discount():
    response = client.get("/price?item_id=item-1&quantity=9")
    assert response.status_code == 200
    data = response.json()
    assert data["total_price"] == 90.0  # 9 * 10