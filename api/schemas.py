"""
Pydantic API request/response schemas for the FastAPI telemetry gateway.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Re-export validated SensorReadingPayload from src.validation for consistency
from src.validation import SensorReadingPayload, AlertAcknowledgement


class APIResponse(BaseModel):
    """Generic API response envelope."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class TelemetryIngestResponse(BaseModel):
    """Response returned upon successful sensor reading ingestion."""
    success: bool
    reading_id: int
    device_id: str
    ml_evaluated: bool
    is_anomaly: bool
    status: str


class DeviceStatusResponse(BaseModel):
    """Hardware heartbeat and connection status response."""
    device_id: str
    connection_status: str  # 'ONLINE', 'STALE', 'OFFLINE'
    seconds_since_last_seen: Optional[float]
    detail: str
    latest_reading: Optional[Dict[str, Any]]
