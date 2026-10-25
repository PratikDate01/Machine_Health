"""
Unit tests for SQLite persistence, alert triggering, alert deduplication,
time window queries, and real-time machine status evaluation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.database import (
    insert_sensor_reading,
    get_latest_readings,
    get_latest_sensor_reading,
    get_readings_window,
    upsert_alert,
    insert_alert,
    resolve_cleared_alerts,
    get_alerts,
    update_alert_status,
    get_active_alerts_count
)
from src.alerts import evaluate_threshold_rules, compute_machine_health_status
from src.live_monitor import live_monitor


def test_database_insert_and_retrieve():
    reading = {
        "device_id": "test-device-db",
        "ax_g": 0.01,
        "ay_g": -0.01,
        "az_g": 1.0,
        "external_temp_c": 32.0,
        "imu_temp_c": 33.5,
        "vibration_indicator_g": 0.04,
        "status": "OK"
    }
    r_id = insert_sensor_reading(reading)
    assert r_id > 0

    readings = get_latest_readings(device_id="test-device-db", limit=5)
    assert len(readings) >= 1
    assert readings[0]["external_temp_c"] == 32.0

    latest_single = get_latest_sensor_reading("test-device-db")
    assert latest_single is not None
    assert latest_single["id"] == r_id


def test_evaluate_threshold_rules_normal():
    reading = {
        "device_id": "machine-1",
        "external_temp_c": 30.0,
        "imu_temp_c": 32.0,
        "vibration_indicator_g": 0.05,
        "status": "OK"
    }
    alerts, healthy = evaluate_threshold_rules(reading)
    assert len(alerts) == 0
    assert "external_temp_c" in healthy
    assert "vibration_indicator_g" in healthy


def test_evaluate_threshold_rules_critical():
    reading = {
        "device_id": "machine-1",
        "external_temp_c": 65.0,  # Exceeds CRITICAL threshold (60 C)
        "imu_temp_c": 40.0,
        "vibration_indicator_g": 0.75,  # Exceeds CRITICAL threshold (0.60 g)
        "status": "OK"
    }
    alerts, healthy = evaluate_threshold_rules(reading)
    assert len(alerts) >= 2
    severities = [a["severity"] for a in alerts]
    assert "CRITICAL" in severities


def test_compute_machine_health_status_disconnected():
    status, reason, score, deductions = compute_machine_health_status(None, device_status="OFFLINE")
    assert status == "INSUFFICIENT DATA"
    assert score == 0


def test_alert_lifecycle_in_database():
    alert_id = insert_alert(
        device_or_dataset="esp32-test-unique",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="external_temp_c",
        observed_value=48.5,
        threshold_or_rule="Temp >= 45 C",
        severity="WARNING"
    )
    assert alert_id > 0

    alerts = get_alerts(status_filter="ACTIVE", limit=10)
    found = [a for a in alerts if a["id"] == alert_id]
    assert len(found) == 1
    assert found[0]["status"] == "ACTIVE"

    ok = update_alert_status(alert_id, "ACKNOWLEDGED", notes="Inspecting coolant line")
    assert ok is True

    alerts_ack = get_alerts(status_filter="ACKNOWLEDGED", limit=10)
    found_ack = [a for a in alerts_ack if a["id"] == alert_id]
    assert len(found_ack) == 1
    assert found_ack[0]["resolution_notes"] == "Inspecting coolant line"


def test_alert_deduplication():
    # Ensure any previous active test alert for esp32-dedup is cleared
    resolve_cleared_alerts("esp32-dedup", ["vibration_indicator_g"])

    # Insert first alert for vibration on device test-dedup
    aid1, is_new1 = upsert_alert(
        device_or_dataset="esp32-dedup",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="vibration_indicator_g",
        observed_value=0.28,
        threshold_or_rule="Vibration >= 0.25g",
        severity="WARNING"
    )
    assert is_new1 is True

    # Insert a second alert for the same active condition
    aid2, is_new2 = upsert_alert(
        device_or_dataset="esp32-dedup",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="vibration_indicator_g",
        observed_value=0.31,
        threshold_or_rule="Vibration >= 0.25g",
        severity="WARNING"
    )
    # Should update the existing active alert without creating a duplicate row
    assert is_new2 is False
    assert aid1 == aid2


def test_auto_resolve_cleared_alerts():
    aid, _ = upsert_alert(
        device_or_dataset="esp32-autores",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="vibration_indicator_g",
        observed_value=0.29,
        threshold_or_rule="Vibration >= 0.25g",
        severity="WARNING"
    )
    # Now simulate vibration returning to normal
    resolved = resolve_cleared_alerts("esp32-autores", ["vibration_indicator_g"])
    assert resolved >= 1

    active_count = get_active_alerts_count("esp32-autores")
    assert active_count == 0


def test_readings_window_ordering():
    # Insert 3 sequential readings
    now = datetime.now(timezone.utc)
    for i in range(3):
        ts = (now + timedelta(seconds=i)).isoformat()
        insert_sensor_reading({
            "device_id": "esp32-window-test",
            "received_at": ts,
            "external_temp_c": 30.0 + i,
            "imu_temp_c": 32.0,
            "vibration_indicator_g": 0.05,
            "status": "OK"
        })

    window = get_readings_window(minutes=5, device_id="esp32-window-test")
    assert len(window) >= 3
    # Check chronological ordering
    ids = [r["id"] for r in window]
    assert ids == sorted(ids)


def test_sensor_availability_separation():
    # Reading where DS18B20 is disconnected (None) but device is streaming (OK)
    reading = {
        "device_id": "esp32-test-sens",
        "external_temp_c": None,
        "imu_temp_c": 32.5,
        "vibration_indicator_g": 0.05,
        "status": "DS18B20_FAULT"
    }
    diag = live_monitor.get_sensor_availability(reading)
    assert diag["ds18b20"]["connected"] is False
    assert "FAULT" in diag["ds18b20"]["label"]
    assert diag["imu"]["connected"] is True
    assert "ONLINE" in diag["imu"]["label"]


def test_alert_deduplication_occurrence_and_timestamps():
    resolve_cleared_alerts("esp32-ts-dedup", ["imu_temp_c"])
    
    # 1st occurrence
    aid1, is_new1 = upsert_alert(
        device_or_dataset="esp32-ts-dedup",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="imu_temp_c",
        observed_value=55.0,
        threshold_or_rule="IMU Temp >= 50C",
        severity="WARNING"
    )
    assert is_new1 is True

    # 2nd occurrence
    aid2, is_new2 = upsert_alert(
        device_or_dataset="esp32-ts-dedup",
        alert_source="THRESHOLD_RULE",
        sensor_or_feature="imu_temp_c",
        observed_value=57.5,
        threshold_or_rule="IMU Temp >= 50C",
        severity="WARNING"
    )
    assert is_new2 is False
    assert aid1 == aid2

    alerts = get_alerts(status_filter="ACTIVE", limit=10)
    found = [a for a in alerts if a["id"] == aid1]
    assert len(found) == 1
    assert found[0]["occurrence_count"] >= 2
    assert found[0]["last_seen_at"] is not None
    assert found[0]["observed_value"] == 57.5


def test_full_sensor_disconnection():
    # Both sensors disconnected
    reading = {
        "device_id": "esp32-dead-sensors",
        "external_temp_c": None,
        "imu_temp_c": None,
        "vibration_indicator_g": None,
        "status": "IMU_UNAVAILABLE+DS18B20_FAULT"
    }
    diag = live_monitor.get_sensor_availability(reading)
    assert diag["ds18b20"]["connected"] is False
    assert diag["imu"]["connected"] is False
    assert "FAULT" in diag["ds18b20"]["label"]
    assert "FAULT" in diag["imu"]["label"]
