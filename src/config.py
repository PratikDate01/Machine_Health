"""
Configuration module for AI Machine Health Monitor.
Loads settings from environment variables or .env file with production-ready defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    # Branding & App Info
    APP_NAME: str = "AI Machine Health Monitor"
    ORGANIZATION: str = "Industrial IoT Monitoring"
    VERSION: str = "1.0.0"

    # Filesystem Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DATA_DIR: Path = BASE_DIR / "data" / "processed"
    MODELS_DIR: Path = BASE_DIR / "models"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    DB_PATH: Path = BASE_DIR / os.getenv("DATABASE_PATH", "data/machine_health.db")

    # API Server Settings
    API_HOST: str = os.getenv("HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PORT", "8000"))
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "demo-secret-token-change-in-production")
    REQUIRE_DEVICE_AUTH: bool = os.getenv("REQUIRE_DEVICE_AUTH", "false").lower() in ("true", "1", "yes")

    # Live Monitoring Heartbeat Timeouts (in seconds)
    HEARTBEAT_TIMEOUT_SECONDS: float = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "10.0"))
    STALE_TIMEOUT_SECONDS: float = float(os.getenv("STALE_TIMEOUT_SECONDS", "5.0"))

    # Baseline Demonstration Thresholds (Notice: These are illustrative demo rules, not certified industrial safety limits)
    EXTERNAL_TEMP_WARN_C: float = float(os.getenv("EXTERNAL_TEMP_WARN_C", "45.0"))
    EXTERNAL_TEMP_CRIT_C: float = float(os.getenv("EXTERNAL_TEMP_CRIT_C", "60.0"))
    IMU_TEMP_WARN_C: float = float(os.getenv("IMU_TEMP_WARN_C", "50.0"))
    IMU_TEMP_CRIT_C: float = float(os.getenv("IMU_TEMP_CRIT_C", "65.0"))
    VIBRATION_WARN_G: float = float(os.getenv("VIBRATION_WARN_G", "0.25"))
    VIBRATION_CRIT_G: float = float(os.getenv("VIBRATION_CRIT_G", "0.60"))

    # Machine Learning Defaults
    DEFAULT_CONTAMINATION: float = float(os.getenv("DEFAULT_CONTAMINATION", "0.05"))
    RANDOM_STATE: int = int(os.getenv("RANDOM_STATE", "42"))

    # Email Alerts (Optional - Disabled by default)
    EMAIL_ENABLED: bool = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() in ("true", "1", "yes")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFICATION_RECIPIENT: str = os.getenv("NOTIFICATION_RECIPIENT", "")

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        for path in [self.DATA_DIR, self.RAW_DATA_DIR, self.PROCESSED_DATA_DIR, self.MODELS_DIR, self.REPORTS_DIR]:
            path.mkdir(parents=True, exist_ok=True)


config = Settings()
config.ensure_directories()
