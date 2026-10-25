"""
FastAPI Telemetry Gateway for AI Machine Health Monitor.
Receives sensor readings from ESP32 via Wi-Fi HTTP POST, serves live status, and persists readings.
"""

from fastapi import FastAPI, HTTPException, Request, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

from src.config import config
from src.live_monitor import live_monitor
from src.database import get_alerts, update_alert_status, get_latest_readings
from api.schemas import (
    SensorReadingPayload,
    TelemetryIngestResponse,
    DeviceStatusResponse,
    APIResponse,
    AlertAcknowledgement
)

app = FastAPI(
    title="AI Machine Health Telemetry API",
    description="High-performance HTTP REST ingestion gateway for ESP32 and industrial sensor telemetry.",
    version="1.0.0"
)

# Enable CORS for local Streamlit and web client dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_device_token(x_device_token: Optional[str] = Header(None)) -> bool:
    """Optional security verification for device access."""
    if not config.REQUIRE_DEVICE_AUTH:
        return True
    if not x_device_token or x_device_token != config.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Device-Token header."
        )
    return True


@app.get("/", tags=["Health"])
async def root():
    """Root health check returning server branding and status."""
    return {
        "service": "AI Machine Health Telemetry Gateway",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "ingest_reading": "POST /api/readings",
            "device_status": "GET /api/status",
            "latest_reading": "GET /api/readings/latest",
            "active_alerts": "GET /api/alerts"
        }
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Standard liveness probe."""
    return {"status": "ok", "app": config.APP_NAME}


@app.post(
    "/api/readings",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Telemetry"]
)
async def ingest_sensor_reading(
    payload: SensorReadingPayload,
    request: Request,
    authorized: bool = Depends(verify_device_token)
):
    """
    Receives real-time sensor measurements from ESP32 over Wi-Fi.
    Validates payload, executes threshold and ML anomaly checks, and persists to SQLite.
    """
    # Extract client IP for device monitoring
    client_ip = request.client.host if request.client else "unknown"

    data_dict = payload.model_dump()
    data_dict["ip_address"] = client_ip

    result = live_monitor.ingest_reading(data_dict)

    return TelemetryIngestResponse(
        success=True,
        reading_id=result["reading_id"],
        device_id=payload.device_id,
        ml_evaluated=result["ml_evaluated"],
        is_anomaly=result["is_anomaly"],
        status="PROCESSED"
    )


@app.get("/api/readings/latest", tags=["Telemetry"])
async def get_latest_reading(device_id: Optional[str] = None):
    """Returns the most recent single sensor reading received."""
    latest = live_monitor.get_latest_reading()
    if not latest:
        raise HTTPException(status_code=404, detail="No telemetry readings recorded yet.")
    return latest


@app.get("/api/readings/history", tags=["Telemetry"])
async def get_readings_history(limit: int = 50):
    """Returns recent sensor readings history."""
    clamped_limit = max(1, min(limit, 500))
    readings = get_latest_readings(limit=clamped_limit)
    return {"count": len(readings), "readings": readings}


@app.get("/api/status", response_model=DeviceStatusResponse, tags=["Hardware"])
async def get_hardware_status(device_id: str = "esp32-machine-01"):
    """
    Returns connection and heartbeat status for a device:
    - ONLINE: Active transmission received in last 5s.
    - STALE: Telemetry delayed between 5s and 10s.
    - OFFLINE: No communication for > 10s.
    """
    conn_status, secs_ago, detail = live_monitor.get_connection_status(device_id)
    latest = live_monitor.get_latest_reading()

    return DeviceStatusResponse(
        device_id=device_id,
        connection_status=conn_status,
        seconds_since_last_seen=secs_ago,
        detail=detail,
        latest_reading=latest
    )


@app.get("/api/alerts", tags=["Alerts"])
async def get_active_alerts(status_filter: str = "ACTIVE", limit: int = 50):
    """Retrieves machine health alerts filtered by status."""
    alerts = get_alerts(status_filter=status_filter, limit=limit)
    return {"count": len(alerts), "alerts": alerts}


@app.post("/api/alerts/{alert_id}/acknowledge", response_model=APIResponse, tags=["Alerts"])
async def acknowledge_alert(alert_id: int, ack: AlertAcknowledgement):
    """Updates an alert status (ACKNOWLEDGED or RESOLVED) with optional notes."""
    updated = update_alert_status(alert_id, ack.status, ack.notes)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Alert #{alert_id} not found.")
    return APIResponse(
        success=True,
        message=f"Alert #{alert_id} marked as {ack.status}."
    )
