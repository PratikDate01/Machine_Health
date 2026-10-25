"""
Alert management, machine health classification, and threshold evaluation module.
Handles persistent alerts, deduplication, auto-resolution, and health scores for AI Machine Health Monitor.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from src.config import config
from src.database import upsert_alert, resolve_cleared_alerts, get_alerts, update_alert_status


def evaluate_threshold_rules(reading: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Evaluates configured demonstration threshold rules against a sensor reading.
    Returns:
    - triggered_alerts: list of rule violations with severity and observed values.
    - healthy_sensors: list of sensor names that are currently within normal limits.
    """
    alerts = []
    healthy_sensors = []
    device_id = reading.get("device_id", "esp32-machine-01")

    # 1. External Temperature (DS18B20)
    ext_temp = reading.get("external_temp_c")
    if ext_temp is not None:
        if ext_temp >= config.EXTERNAL_TEMP_CRIT_C:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "external_temp_c",
                "value": ext_temp,
                "rule": f"External Temp >= {config.EXTERNAL_TEMP_CRIT_C} °C (Critical Limit)",
                "severity": "CRITICAL"
            })
        elif ext_temp >= config.EXTERNAL_TEMP_WARN_C:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "external_temp_c",
                "value": ext_temp,
                "rule": f"External Temp >= {config.EXTERNAL_TEMP_WARN_C} °C (Warning Limit)",
                "severity": "WARNING"
            })
        else:
            healthy_sensors.append("external_temp_c")
    else:
        # Temperature probe is disconnected or unreadable
        alerts.append({
            "device_id": device_id,
            "source": "HARDWARE_STATUS",
            "sensor": "external_temp_c",
            "value": None,
            "rule": "External DS18B20 temperature probe disconnected or returning fault code.",
            "severity": "WARNING"
        })

    # 2. IMU Internal Temperature
    imu_temp = reading.get("imu_temp_c")
    if imu_temp is not None:
        if imu_temp >= config.IMU_TEMP_CRIT_C:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "imu_temp_c",
                "value": imu_temp,
                "rule": f"IMU Internal Temp >= {config.IMU_TEMP_CRIT_C} °C (Critical Limit)",
                "severity": "CRITICAL"
            })
        elif imu_temp >= config.IMU_TEMP_WARN_C:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "imu_temp_c",
                "value": imu_temp,
                "rule": f"IMU Internal Temp >= {config.IMU_TEMP_WARN_C} °C (Warning Limit)",
                "severity": "WARNING"
            })
        else:
            healthy_sensors.append("imu_temp_c")

    # 3. Vibration Indicator Magnitude
    vib = reading.get("vibration_indicator_g")
    if vib is not None:
        if vib >= config.VIBRATION_CRIT_G:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "vibration_indicator_g",
                "value": vib,
                "rule": f"Vibration Indicator >= {config.VIBRATION_CRIT_G} g (Critical Limit)",
                "severity": "CRITICAL"
            })
        elif vib >= config.VIBRATION_WARN_G:
            alerts.append({
                "device_id": device_id,
                "source": "THRESHOLD_RULE",
                "sensor": "vibration_indicator_g",
                "value": vib,
                "rule": f"Vibration Indicator >= {config.VIBRATION_WARN_G} g (Warning Limit)",
                "severity": "WARNING"
            })
        else:
            healthy_sensors.append("vibration_indicator_g")

    # 4. Sensor Disconnection or Hardware Error Status
    status_str = str(reading.get("status", "OK")).upper()
    if status_str not in ["OK", "NORMAL"]:
        alerts.append({
            "device_id": device_id,
            "source": "HARDWARE_STATUS",
            "sensor": "hardware_status",
            "value": None,
            "rule": f"Microcontroller reported abnormal state: {status_str}",
            "severity": "CRITICAL" if "ERROR" in status_str else "WARNING"
        })
    else:
        healthy_sensors.append("hardware_status")

    return alerts, healthy_sensors


def process_reading_alerts(
    reading: Dict[str, Any],
    ml_result: Optional[Dict[str, Any]] = None
) -> List[int]:
    """
    Evaluates rules and ML results, deduplicates alerts, updates existing active alerts,
    auto-resolves cleared conditions, and optionally triggers notifications.
    """
    device_id = reading.get("device_id", "esp32-machine-01")
    saved_alert_ids = []

    # Evaluate rules
    raw_alerts, healthy_sensors = evaluate_threshold_rules(reading)

    # Auto-resolve conditions that have normalized
    if healthy_sensors:
        resolve_cleared_alerts(device_id, healthy_sensors)

    # Add ML anomaly alert if flagged
    if ml_result and ml_result.get("is_anomaly"):
        top_feat = ml_result.get("top_deviating_feature", "multivariate_sensor_pattern")
        max_dev = ml_result.get("max_z_deviation", 0.0)
        raw_alerts.append({
            "device_id": device_id,
            "source": "ISOLATION_FOREST",
            "sensor": top_feat,
            "value": reading.get(top_feat),
            "rule": f"Multivariate outlier pattern detected (Primary deviation: {top_feat}, z-score ~ {max_dev})",
            "severity": "WARNING"
        })

    for alert in raw_alerts:
        alert_id, is_new = upsert_alert(
            device_or_dataset=alert["device_id"],
            alert_source=alert["source"],
            sensor_or_feature=alert["sensor"],
            observed_value=alert["value"],
            threshold_or_rule=alert["rule"],
            severity=alert["severity"]
        )
        saved_alert_ids.append(alert_id)

        # Trigger optional email dispatch only on newly created alerts
        if is_new and config.EMAIL_ENABLED:
            send_email_notification(alert)

    return saved_alert_ids


def compute_machine_health_status(
    latest_reading: Optional[Dict[str, Any]],
    device_status: Optional[str] = "LIVE",
    is_ml_anomaly: bool = False
) -> Tuple[str, str, int, List[str]]:
    """
    Determines overall machine health category and an indicative health score (0-100).
    Categories:
    - NORMAL: Operating within normal baseline parameters.
    - WARNING: Warning threshold reached, non-critical sensor fault, or ML anomaly.
    - CRITICAL: Critical thermal or vibration threshold exceeded.
    - OFFLINE: Device connection lost / telemetry stopped.
    - INSUFFICIENT DATA: No readings received yet.

    Returns (status_label, explanation_text, health_score, deduction_details).
    """
    if not latest_reading:
        return "INSUFFICIENT DATA", "No sensor readings have been loaded or received yet.", 0, ["No data recorded."]

    if device_status == "OFFLINE":
        return "OFFLINE", "Microcontroller telemetry connection lost. Awaiting heartbeat.", 0, ["Device is offline (-100)."]

    score = 100
    deductions = []

    # Evaluate live threshold rules on the current reading
    threshold_alerts, _ = evaluate_threshold_rules(latest_reading)

    crit_alerts = [a for a in threshold_alerts if a["severity"] == "CRITICAL"]
    warn_alerts = [a for a in threshold_alerts if a["severity"] == "WARNING"]

    # Check for hardware probe availability
    ext_temp = latest_reading.get("external_temp_c")
    imu_temp = latest_reading.get("imu_temp_c")

    if ext_temp is None:
        score -= 20
        deductions.append("External DS18B20 temperature probe unavailable or disconnected (-20)")

    if imu_temp is None:
        score -= 20
        deductions.append("MPU6500 IMU telemetry unavailable (-20)")

    if crit_alerts:
        score -= 40 * len(crit_alerts)
        for ca in crit_alerts:
            deductions.append(f"Critical violation: {ca['rule']} (-40)")

    if warn_alerts:
        for wa in warn_alerts:
            if wa["sensor"] != "external_temp_c" or ext_temp is not None:
                score -= 15
                deductions.append(f"Warning condition: {wa['rule']} (-15)")

    if is_ml_anomaly:
        score -= 20
        deductions.append("Isolation Forest detected an unusual multivariate operating pattern (-20)")

    score = max(0, min(100, score))

    if crit_alerts:
        return "CRITICAL", "Critical limit violated: " + "; ".join(a["rule"] for a in crit_alerts), score, deductions

    if warn_alerts or is_ml_anomaly or ext_temp is None:
        reasons = deductions if deductions else ["Operating with non-critical warning conditions."]
        return "WARNING", " | ".join(reasons[:2]), score, deductions

    return "NORMAL", "All sensor parameters are operating within baseline demonstration limits.", 100, ["Operating nominally (No deductions)."]


def send_email_notification(alert: Dict[str, Any]) -> bool:
    """
    Dispatches alert via SMTP when enabled in environment configuration.
    Fails safely without breaking core telemetry loop.
    """
    if not config.EMAIL_ENABLED or not config.SMTP_SERVER or not config.NOTIFICATION_RECIPIENT:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{alert.get('severity', 'WARNING')}] Machine Alert - {alert.get('sensor', 'Sensor')}"
        msg["From"] = config.SMTP_USER
        msg["To"] = config.NOTIFICATION_RECIPIENT

        body = f"""
AI Machine Health Monitor — Machine Alert
-----------------------------------------
Severity: {alert.get('severity')}
Device: {alert.get('device_id')}
Sensor/Feature: {alert.get('sensor')}
Observed Value: {alert.get('value')}
Trigger Condition: {alert.get('rule')}
Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=5) as server:
            server.starttls()
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[Alert System Warning] Failed to send email alert: {e}")
        return False
