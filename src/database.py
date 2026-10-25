"""
SQLite database persistence layer for AI Machine Health Monitor.
Provides persistent storage for sensor telemetry, anomalies, alerts, and model metadata.
Features WAL concurrency mode, indexed lookups, and time-window queries.
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.config import config


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with WAL mode and row factory."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    """Initializes the database schema with appropriate tables and indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Sensor Readings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                timestamp_ms INTEGER,
                ax_g REAL,
                ay_g REAL,
                az_g REAL,
                gyro_x_dps REAL,
                gyro_y_dps REAL,
                gyro_z_dps REAL,
                imu_temp_c REAL,
                external_temp_c REAL,
                vibration_indicator_g REAL,
                status TEXT,
                is_anomaly INTEGER DEFAULT 0,
                anomaly_score REAL DEFAULT 0.0
            );
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_device_time ON sensor_readings(device_id, received_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_received_at ON sensor_readings(received_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_id_asc ON sensor_readings(id ASC);")

        # 2. Alerts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT,
                device_or_dataset TEXT NOT NULL,
                alert_source TEXT NOT NULL,  -- 'THRESHOLD_RULE', 'ISOLATION_FOREST', 'HARDWARE_STATUS'
                sensor_or_feature TEXT NOT NULL,
                observed_value REAL,
                threshold_or_rule TEXT NOT NULL,
                severity TEXT NOT NULL,      -- 'INFO', 'WARNING', 'CRITICAL'
                status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'AUTO_RESOLVED'
                occurrence_count INTEGER DEFAULT 1,
                resolution_notes TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_device_sensor ON alerts(device_or_dataset, sensor_or_feature, status);")

        # Safe schema migration for existing databases
        cursor.execute("PRAGMA table_info(alerts)")
        existing_alert_cols = [row["name"] for row in cursor.fetchall()]
        if "occurrence_count" not in existing_alert_cols:
            cursor.execute("ALTER TABLE alerts ADD COLUMN occurrence_count INTEGER DEFAULT 1;")
        if "last_seen_at" not in existing_alert_cols:
            cursor.execute("ALTER TABLE alerts ADD COLUMN last_seen_at TEXT;")

        # 3. Model Registry Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT UNIQUE NOT NULL,
                model_type TEXT NOT NULL,
                trained_at TEXT NOT NULL,
                contamination REAL NOT NULL,
                features_json TEXT NOT NULL,
                n_samples INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                notes TEXT
            );
        """)

        # 4. Dataset Metadata Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dataset_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                col_count INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                features_json TEXT,
                notes TEXT
            );
        """)

        # 5. Device Status / Heartbeat Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL,
                ip_address TEXT,
                status TEXT NOT NULL, -- 'ONLINE', 'STALE', 'OFFLINE'
                last_payload_json TEXT
            );
        """)

        conn.commit()


# Initialize database upon import
init_db()


def insert_sensor_reading(data: Dict[str, Any]) -> int:
    """Inserts a validated sensor reading and updates device heartbeat."""
    now_iso = datetime.now(timezone.utc).isoformat()
    received_at = data.get("received_at", now_iso)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_readings (
                device_id, received_at, timestamp_ms,
                ax_g, ay_g, az_g,
                gyro_x_dps, gyro_y_dps, gyro_z_dps,
                imu_temp_c, external_temp_c,
                vibration_indicator_g, status,
                is_anomaly, anomaly_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("device_id", "esp32-machine-01"),
            received_at,
            data.get("timestamp_ms"),
            data.get("ax_g"),
            data.get("ay_g"),
            data.get("az_g"),
            data.get("gyro_x_dps"),
            data.get("gyro_y_dps"),
            data.get("gyro_z_dps"),
            data.get("imu_temp_c"),
            data.get("external_temp_c"),
            data.get("vibration_indicator_g"),
            data.get("status", "OK"),
            1 if data.get("is_anomaly") else 0,
            data.get("anomaly_score", 0.0)
        ))
        reading_id = cursor.lastrowid

        # Upsert device status
        cursor.execute("""
            INSERT INTO device_status (device_id, last_seen, ip_address, status, last_payload_json)
            VALUES (?, ?, ?, 'ONLINE', ?)
            ON CONFLICT(device_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                ip_address = COALESCE(excluded.ip_address, device_status.ip_address),
                status = 'ONLINE',
                last_payload_json = excluded.last_payload_json;
        """, (
            data.get("device_id", "esp32-machine-01"),
            now_iso,
            data.get("ip_address", "unknown"),
            json.dumps(data)
        ))

        conn.commit()
        return reading_id


def get_latest_sensor_reading(device_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Directly fetches the single newest reading from SQLite."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if device_id:
            cursor.execute("SELECT * FROM sensor_readings WHERE device_id = ? ORDER BY id DESC LIMIT 1", (device_id,))
        else:
            cursor.execute("SELECT * FROM sensor_readings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def get_latest_readings(device_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves the latest sensor readings ordered from newest to oldest."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if device_id:
            cursor.execute("""
                SELECT * FROM sensor_readings
                WHERE device_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (device_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM sensor_readings
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_readings_window(
    minutes: int = 5,
    max_points: int = 1200,
    device_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetches chronologically sorted (ORDER BY id ASC) sensor readings
    spanning the last N minutes or the most recent max_points.
    Guarantees true real-time charting without missing readings.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

        if device_id:
            cursor.execute("""
                SELECT * FROM sensor_readings
                WHERE device_id = ? AND received_at >= ?
                ORDER BY id ASC
                LIMIT ?
            """, (device_id, cutoff_iso, max_points))
            rows = cursor.fetchall()
            if not rows:
                # If no records in the exact time window, fetch the latest max_points chronologically
                cursor.execute("""
                    SELECT * FROM (
                        SELECT * FROM sensor_readings
                        WHERE device_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                    ) ORDER BY id ASC
                """, (device_id, min(max_points, 100)))
                rows = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT * FROM sensor_readings
                WHERE received_at >= ?
                ORDER BY id ASC
                LIMIT ?
            """, (cutoff_iso, max_points))
            rows = cursor.fetchall()
            if not rows:
                cursor.execute("""
                    SELECT * FROM (
                        SELECT * FROM sensor_readings
                        ORDER BY id DESC
                        LIMIT ?
                    ) ORDER BY id ASC
                """, (min(max_points, 100),))
                rows = cursor.fetchall()

        return [dict(row) for row in rows]


def get_readings_count() -> int:
    """Returns the total number of sensor readings stored in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        return cursor.fetchone()[0]


def get_device_status(device_id: str = "esp32-machine-01") -> Optional[Dict[str, Any]]:
    """Fetches the current known status and last_seen timestamp for a device."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_status WHERE device_id = ?", (device_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def upsert_alert(
    device_or_dataset: str,
    alert_source: str,
    sensor_or_feature: str,
    observed_value: Optional[float],
    threshold_or_rule: str,
    severity: str = "WARNING"
) -> Tuple[int, bool]:
    """
    Inserts a new alert or updates an existing ACTIVE alert for the same sensor/condition.
    Prevents repeated identical alert records from spamming the database.
    Returns (alert_id, is_new_alert).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if an active alert already exists for this exact device, source, and sensor
        cursor.execute("""
            SELECT id, occurrence_count FROM alerts
            WHERE device_or_dataset = ? AND sensor_or_feature = ? AND status = 'ACTIVE'
            ORDER BY id DESC LIMIT 1
        """, (device_or_dataset, sensor_or_feature))
        existing = cursor.fetchone()

        if existing:
            alert_id = existing["id"]
            count = (existing["occurrence_count"] or 1) + 1
            cursor.execute("""
                UPDATE alerts
                SET last_seen_at = ?, observed_value = ?, threshold_or_rule = ?,
                    severity = ?, occurrence_count = ?
                WHERE id = ?
            """, (now_iso, observed_value, threshold_or_rule, severity, count, alert_id))
            conn.commit()
            return alert_id, False
        else:
            cursor.execute("""
                INSERT INTO alerts (
                    created_at, last_seen_at, device_or_dataset, alert_source,
                    sensor_or_feature, observed_value, threshold_or_rule,
                    severity, status, occurrence_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 1)
            """, (
                now_iso,
                now_iso,
                device_or_dataset,
                alert_source,
                sensor_or_feature,
                observed_value,
                threshold_or_rule,
                severity
            ))
            alert_id = cursor.lastrowid
            conn.commit()
            return alert_id, True


def insert_alert(
    device_or_dataset: str,
    alert_source: str,
    sensor_or_feature: str,
    observed_value: Optional[float],
    threshold_or_rule: str,
    severity: str = "WARNING"
) -> int:
    """Legacy helper: routes to upsert_alert for deduplicated persistence."""
    alert_id, _ = upsert_alert(
        device_or_dataset=device_or_dataset,
        alert_source=alert_source,
        sensor_or_feature=sensor_or_feature,
        observed_value=observed_value,
        threshold_or_rule=threshold_or_rule,
        severity=severity
    )
    return alert_id


def resolve_cleared_alerts(
    device_id: str,
    healthy_sensors: List[str]
) -> int:
    """
    Auto-resolves ACTIVE alerts for sensors that have returned to normal operating limits.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    if not healthy_sensors:
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in healthy_sensors)
        query = f"""
            UPDATE alerts
            SET status = 'RESOLVED',
                resolution_notes = 'Auto-resolved: Sensor telemetry returned to normal operating limits.'
            WHERE device_or_dataset = ? AND sensor_or_feature IN ({placeholders}) AND status = 'ACTIVE'
        """
        cursor.execute(query, [device_id] + healthy_sensors)
        resolved_count = cursor.rowcount
        conn.commit()
        return resolved_count


def get_alerts(
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieves alerts with optional status and severity filtering."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List[Any] = []

        if status_filter and status_filter.upper() != "ALL":
            query += " AND status = ?"
            params.append(status_filter.upper())

        if severity_filter and severity_filter.upper() != "ALL":
            query += " AND severity = ?"
            params.append(severity_filter.upper())

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_active_alerts_count(device_id: Optional[str] = None) -> int:
    """Returns the count of truly currently ACTIVE alerts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if device_id:
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE' AND device_or_dataset = ?", (device_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE'")
        return cursor.fetchone()[0]


def update_alert_status(alert_id: int, new_status: str, notes: Optional[str] = None) -> bool:
    """Updates the status of an alert (ACKNOWLEDGED or RESOLVED)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alerts
            SET status = ?, resolution_notes = COALESCE(?, resolution_notes)
            WHERE id = ?
        """, (new_status.upper(), notes, alert_id))
        conn.commit()
        return cursor.rowcount > 0


def save_model_metadata(
    model_name: str,
    model_type: str,
    contamination: float,
    features: List[str],
    n_samples: int,
    file_path: str,
    notes: str = ""
) -> int:
    """Saves metadata for a trained machine learning model."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_registry (
                model_name, model_type, trained_at, contamination,
                features_json, n_samples, file_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_name) DO UPDATE SET
                model_type = excluded.model_type,
                trained_at = excluded.trained_at,
                contamination = excluded.contamination,
                features_json = excluded.features_json,
                n_samples = excluded.n_samples,
                file_path = excluded.file_path,
                notes = excluded.notes;
        """, (
            model_name,
            model_type,
            now_iso,
            contamination,
            json.dumps(features),
            n_samples,
            str(file_path),
            notes
        ))
        model_id = cursor.lastrowid
        conn.commit()
        return model_id


def get_models_metadata() -> List[Dict[str, Any]]:
    """Retrieves all registered models."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_registry ORDER BY id DESC")
        rows = cursor.fetchall()
        models = []
        for row in rows:
            m = dict(row)
            m["features"] = json.loads(m["features_json"])
            models.append(m)
        return models


def clear_sensor_history() -> int:
    """Safely cleans sensor readings history (for maintenance or reset)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_readings")
        deleted = cursor.rowcount
        conn.commit()
        return deleted
