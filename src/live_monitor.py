"""
Live hardware monitoring manager for AI Machine Health Monitor.
Tracks ESP32 telemetry, calculates connection heartbeat states, and runs live inference.
Bridges SQLite storage and multi-process dashboard synchronization.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
import threading

from src.config import config
from src.database import (
    insert_sensor_reading,
    get_latest_sensor_reading,
    get_readings_window,
    get_latest_readings,
    get_device_status
)
from src.anomaly_detection import IsolationForestDetector
from src.alerts import process_reading_alerts, compute_machine_health_status


def parse_timestamp_safe(ts_str: Optional[str]) -> Optional[datetime]:
    """Safely parses ISO timestamp into a timezone-aware UTC datetime."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(str(ts_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def format_uptime_human(timestamp_ms: Optional[int]) -> str:
    """Formats microcontroller uptime in milliseconds to human readable (e.g., 5m 24s)."""
    if timestamp_ms is None or timestamp_ms < 0:
        return "N/A"
    total_seconds = timestamp_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


class LiveMonitorManager:
    """
    Thread-safe live monitoring state manager.
    Coordinates real-time incoming packets from FastAPI with SQLite and Streamlit.
    """

    def __init__(self, buffer_size: int = 300):
        self.buffer_size = buffer_size
        self._buffer: deque = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._active_detector: Optional[IsolationForestDetector] = None

    def set_active_model(self, detector: Optional[IsolationForestDetector]) -> None:
        """Sets or unloads the active Isolation Forest model for real-time inference."""
        with self._lock:
            self._active_detector = detector

    def get_active_model(self) -> Optional[IsolationForestDetector]:
        with self._lock:
            return self._active_detector

    def ingest_reading(self, reading_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives, validates, infers anomalies, checks thresholds, and saves telemetry.
        Called by FastAPI POST /api/readings.
        """
        now_dt = datetime.now(timezone.utc)
        reading = dict(reading_data)
        reading["received_at"] = now_dt.isoformat()

        # Run Live ML inference if a model is loaded and compatible
        ml_result = None
        with self._lock:
            detector = self._active_detector

        if detector:
            ml_result = detector.predict_single(reading)
            if ml_result.get("is_available"):
                reading["is_anomaly"] = 1 if ml_result["is_anomaly"] else 0
                reading["anomaly_score"] = float(ml_result["decision_score"])
            else:
                reading["is_anomaly"] = 0
                reading["anomaly_score"] = 0.0
        else:
            reading["is_anomaly"] = 0
            reading["anomaly_score"] = 0.0

        # Persist to database
        reading_id = insert_sensor_reading(reading)
        reading["id"] = reading_id

        # Evaluate threshold rules & generate alerts (with deduplication)
        process_reading_alerts(reading, ml_result)

        # Update in-memory ring buffer
        with self._lock:
            self._buffer.append(reading)

        return {
            "success": True,
            "reading_id": reading_id,
            "ml_evaluated": ml_result.get("is_available", False) if ml_result else False,
            "is_anomaly": reading["is_anomaly"] == 1
        }

    def get_latest_reading(self, device_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Returns the single most recent sensor reading.
        Directly checks SQLite for the latest record across processes,
        ensuring Streamlit always has real-time telemetry from FastAPI.
        """
        # Always verify against persistent SQLite storage
        db_reading = get_latest_sensor_reading(device_id)

        with self._lock:
            if self._buffer:
                buf_reading = self._buffer[-1]
                if db_reading is None:
                    return buf_reading
                # Compare IDs if available
                if buf_reading.get("id", 0) > db_reading.get("id", 0):
                    return buf_reading

        return db_reading

    def get_window_readings(
        self,
        minutes: int = 5,
        max_points: int = 1200,
        device_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches chronological readings for the specified rolling time window directly from SQLite.
        Guarantees instant, gap-free, accurate data for live charts.
        """
        return get_readings_window(minutes=minutes, max_points=max_points, device_id=device_id)

    def get_buffered_readings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fallback helper: returns latest readings in chronological order."""
        return self.get_window_readings(minutes=15, max_points=limit)

    def get_connection_status(self, device_id: str = "esp32-machine-01") -> Tuple[str, Optional[float], str]:
        """
        Calculates heartbeat connection status from the freshest packet:
        - LIVE: packet received within STALE_TIMEOUT_SECONDS (<= 5s)
        - STALE: packet received between STALE_TIMEOUT_SECONDS and HEARTBEAT_TIMEOUT_SECONDS (5s - 15s)
        - OFFLINE: no packet received for over HEARTBEAT_TIMEOUT_SECONDS (> 15s)
        """
        latest = self.get_latest_reading(device_id)
        if not latest or not latest.get("received_at"):
            return "OFFLINE", None, "No data has ever been received from the device."

        last_dt = parse_timestamp_safe(latest.get("received_at"))
        if not last_dt:
            return "OFFLINE", None, "Unable to parse timestamp."

        now_dt = datetime.now(timezone.utc)
        seconds_ago = max(0.0, (now_dt - last_dt).total_seconds())

        if seconds_ago <= config.STALE_TIMEOUT_SECONDS:
            return "LIVE", round(seconds_ago, 1), f"Device actively transmitting ({seconds_ago:.1f}s ago)"
        elif seconds_ago <= config.HEARTBEAT_TIMEOUT_SECONDS:
            return "STALE", round(seconds_ago, 1), f"Telemetry delay detected ({seconds_ago:.1f}s ago)"
        else:
            return "OFFLINE", round(seconds_ago, 1), f"Device disconnected / telemetry lost ({seconds_ago:.1f}s ago)"

    def get_sensor_availability(self, reading: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Separates physical sensor hardware availability from network link state.
        Returns explicit status for each connected physical sensor.
        """
        if not reading:
            return {
                "ds18b20": {"connected": False, "label": "NO DATA", "value": None},
                "imu": {"connected": False, "label": "NO DATA", "value": None},
                "bus_status": "NO SIGNAL",
                "uptime": "N/A"
            }

        ext_temp = reading.get("external_temp_c")
        imu_temp = reading.get("imu_temp_c")
        status_raw = str(reading.get("status", "OK")).upper()

        ds18b20_ok = ext_temp is not None and "DS18B20" not in status_raw
        imu_ok = imu_temp is not None and "IMU" not in status_raw

        return {
            "ds18b20": {
                "connected": ds18b20_ok,
                "label": f"CONNECTED ({ext_temp:.2f} °C)" if ds18b20_ok else "FAULT / DISCONNECTED",
                "value": ext_temp
            },
            "imu": {
                "connected": imu_ok,
                "label": f"ONLINE ({imu_temp:.2f} °C)" if imu_ok else "FAULT / OFFLINE",
                "value": imu_temp
            },
            "bus_status": status_raw,
            "uptime": format_uptime_human(reading.get("timestamp_ms"))
        }


# Global live monitor manager instance
live_monitor = LiveMonitorManager()
