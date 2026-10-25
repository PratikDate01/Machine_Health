"""
Validation and schema definition module using Pydantic.
Ensures rigorous payload verification for API requests, hardware telemetry, and CSV imports.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo
import numpy as np


class SensorReadingPayload(BaseModel):
    """
    Validated schema for incoming ESP32 telemetry via HTTP POST /api/readings.
    Matches the working hardware prototype fields.
    """
    device_id: str = Field(
        default="esp32-machine-01",
        min_length=2,
        max_length=64,
        description="Unique identifier of the physical device or machine"
    )
    timestamp_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="ESP32 internal millisecond uptime timestamp"
    )
    ax_g: Optional[float] = Field(
        default=None,
        ge=-16.0,
        le=16.0,
        description="Acceleration on X-axis in units of g"
    )
    ay_g: Optional[float] = Field(
        default=None,
        ge=-16.0,
        le=16.0,
        description="Acceleration on Y-axis in units of g"
    )
    az_g: Optional[float] = Field(
        default=None,
        ge=-16.0,
        le=16.0,
        description="Acceleration on Z-axis in units of g"
    )
    gyro_x_dps: Optional[float] = Field(
        default=None,
        ge=-2000.0,
        le=2000.0,
        description="Gyroscope rotation on X-axis in degrees per second"
    )
    gyro_y_dps: Optional[float] = Field(
        default=None,
        ge=-2000.0,
        le=2000.0,
        description="Gyroscope rotation on Y-axis in degrees per second"
    )
    gyro_z_dps: Optional[float] = Field(
        default=None,
        ge=-2000.0,
        le=2000.0,
        description="Gyroscope rotation on Z-axis in degrees per second"
    )
    imu_temp_c: Optional[float] = Field(
        default=None,
        ge=-40.0,
        le=90.0,
        description="Internal die temperature of the MPU6500 sensor in Celsius"
    )
    external_temp_c: Optional[float] = Field(
        default=None,
        ge=-55.0,
        le=125.0,
        description="External machine surface temperature measured by DS18B20 probe in Celsius"
    )
    vibration_indicator_g: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=32.0,
        description="Basic calculated vibration indicator magnitude in g (relative indicator, not calibrated RMS)"
    )
    status: Optional[str] = Field(
        default="OK",
        max_length=64,
        description="Hardware diagnostic status string reported by microcontroller"
    )

    @field_validator("external_temp_c")
    @classmethod
    def validate_external_temp(cls, v: Optional[float]) -> Optional[float]:
        # DS18B20 85C power-on reset value or -127 disconnected value
        if v is not None and (abs(v - 85.0) < 0.001 or abs(v - (-127.0)) < 0.001):
            # Sensor is returning fault code; mark as None to signify disconnected/unreadable probe
            return None
        return v


class AlertAcknowledgement(BaseModel):
    """Schema for acknowledging or resolving an alert."""
    status: str = Field(..., pattern="^(ACTIVE|ACKNOWLEDGED|RESOLVED)$")
    notes: Optional[str] = Field(default=None, max_length=500)


def sanitize_reading_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleanses and validates raw dictionary into schema-compliant fields.
    Replaces infinite or NaN values with None.
    """
    cleaned = {}
    for k, v in data.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, (float, np.floating)):
            if np.isnan(v) or np.isinf(v):
                cleaned[k] = None
            else:
                cleaned[k] = float(v)
        elif isinstance(v, (int, np.integer)):
            cleaned[k] = int(v)
        elif isinstance(v, str):
            cleaned[k] = v.strip()
        else:
            cleaned[k] = v
    return cleaned
