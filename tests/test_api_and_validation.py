"""
Unit and integration tests for FastAPI endpoints and Pydantic validation.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from src.validation import SensorReadingPayload

client = TestClient(app)


def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "AI Machine Health" in data["service"]


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_post_valid_telemetry_reading():
    payload = {
        "device_id": "esp32-machine-01",
        "timestamp_ms": 123456,
        "ax_g": 0.05,
        "ay_g": -0.02,
        "az_g": 0.98,
        "gyro_x_dps": 1.2,
        "gyro_y_dps": 0.5,
        "gyro_z_dps": -0.4,
        "imu_temp_c": 31.5,
        "external_temp_c": 29.8,
        "vibration_indicator_g": 0.035,
        "status": "OK"
    }
    response = client.post("/api/readings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == "esp32-machine-01"
    assert "reading_id" in data


def test_post_invalid_telemetry_payload():
    # Out of range temperature probe reading (> 125 C)
    invalid_payload = {
        "device_id": "esp32-machine-01",
        "external_temp_c": 500.0  # Invalid physics
    }
    response = client.post("/api/readings", json=invalid_payload)
    assert response.status_code == 422


def test_get_latest_reading_and_status():
    # Fetch status
    response = client.get("/api/status?device_id=esp32-machine-01")
    assert response.status_code == 200
    status_data = response.json()
    assert "connection_status" in status_data
    assert status_data["device_id"] == "esp32-machine-01"
