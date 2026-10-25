"""
Data loader module for AI Machine Health Monitor.
Loads external CSV files, sample datasets (ESP32 prototype & NASA C-MAPSS), and generates baseline datasets.
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import pandas as pd
import numpy as np

from src.config import config


def load_csv(file_or_path: Any) -> pd.DataFrame:
    """
    Safely reads a CSV file from a file path or UploadedFile buffer.
    Handles different encodings and delimiter detection.
    """
    try:
        df = pd.read_csv(file_or_path)
    except UnicodeDecodeError:
        if hasattr(file_or_path, 'seek'):
            file_or_path.seek(0)
        df = pd.read_csv(file_or_path, encoding='latin1')
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")

    if df.empty:
        raise ValueError("Uploaded CSV file contains no data (empty file).")

    return df


def ensure_sample_datasets() -> None:
    """
    Generates and saves the baseline demonstration datasets in data/raw/
    if they do not already exist.
    """
    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    esp32_sample_path = config.RAW_DATA_DIR / "sample_esp32_hardware_run.csv"
    cmapss_sample_path = config.RAW_DATA_DIR / "nasa_cmapss_sample.csv"

    # 1. ESP32 Prototype Telemetry Dataset
    if not esp32_sample_path.exists():
        np.random.seed(config.RANDOM_STATE)
        n_samples = 600  # 10 minutes at 1 reading/sec

        time_ms = [i * 1000 for i in range(n_samples)]

        # Baseline normal running conditions
        # Acceleration around gravity (z ~ 1g)
        ax = np.random.normal(0.04, 0.03, n_samples)
        ay = np.random.normal(-0.02, 0.03, n_samples)
        az = np.random.normal(0.98, 0.04, n_samples)

        # Gyroscope rotational speed near resting / slight motor vibration
        gx = np.random.normal(1.2, 0.8, n_samples)
        gy = np.random.normal(0.4, 0.8, n_samples)
        gz = np.random.normal(-0.5, 0.8, n_samples)

        # DS18B20 external temperature starts at ~29.5C with gradual ambient motor heating
        base_ext_temp = 29.5 + (np.arange(n_samples) / n_samples) * 3.5
        ext_temp = base_ext_temp + np.random.normal(0, 0.15, n_samples)

        # IMU internal die temperature sits ~2C above external
        imu_temp = ext_temp + 1.8 + np.random.normal(0, 0.2, n_samples)

        # Vibration indicator: basic vector magnitude variance or residual
        vibration = np.abs(np.random.normal(0.04, 0.02, n_samples))

        # Ground truth status label for evaluation
        ground_truth = ["NORMAL"] * n_samples

        # Inject controlled anomalies to demonstrate predictive maintenance
        # Anomaly 1: Mechanical vibration burst (simulated bearing friction/misalignment at t = 200..230)
        ax[200:230] += np.random.uniform(0.3, 0.8, 30)
        ay[200:230] += np.random.uniform(-0.5, 0.6, 30)
        vibration[200:230] += np.random.uniform(0.28, 0.55, 30)
        for i in range(200, 230):
            ground_truth[i] = "ANOMALY_VIBRATION"

        # Anomaly 2: Thermal overheating event (t = 450..485)
        ext_temp[450:485] += np.linspace(8.0, 18.0, 35)
        imu_temp[450:485] += np.linspace(9.0, 21.0, 35)
        for i in range(450, 485):
            ground_truth[i] = "ANOMALY_THERMAL"

        esp32_df = pd.DataFrame({
            "time_ms": time_ms,
            "ax_g": np.round(ax, 4),
            "ay_g": np.round(ay, 4),
            "az_g": np.round(az, 4),
            "gyro_x_dps": np.round(gx, 2),
            "gyro_y_dps": np.round(gy, 2),
            "gyro_z_dps": np.round(gz, 2),
            "imu_temp_c": np.round(imu_temp, 2),
            "external_temp_c": np.round(ext_temp, 2),
            "vibration_indicator_g": np.round(vibration, 4),
            "status": ["OK" if g == "NORMAL" else "SIMULATED_FAULT" for g in ground_truth],
            "ground_truth_label": ground_truth
        })
        esp32_df.to_csv(esp32_sample_path, index=False)

    # 2. NASA C-MAPSS Turbofan Engine Sample (FD001 style)
    if not cmapss_sample_path.exists():
        np.random.seed(config.RANDOM_STATE)
        n_cycles = 250
        unit_id = [1] * n_cycles
        cycles = list(range(1, n_cycles + 1))

        # C-MAPSS sensor trends: degrade over engine operational cycles
        # Sensor 2 (Total Temperature at LPC outlet) rises as wear increases
        s2 = 642.0 + 0.05 * np.array(cycles) + np.random.normal(0, 0.2, n_cycles)
        # Sensor 3 (Total Temperature at HPC outlet)
        s3 = 1585.0 + 0.08 * np.array(cycles) + np.random.normal(0, 0.4, n_cycles)
        # Sensor 4 (Physical Core Speed)
        s4 = 1400.0 - 0.04 * np.array(cycles) + np.random.normal(0, 0.3, n_cycles)
        # Sensor 7 (High-Pressure Compressor static pressure)
        s7 = 553.0 - 0.03 * np.array(cycles) + np.random.normal(0, 0.15, n_cycles)
        # Sensor 11 (Vibration / Static pressure ratio)
        s11 = 47.0 + 0.02 * np.array(cycles) + np.random.normal(0, 0.1, n_cycles)

        # Failure / Anomaly onset in final 40 cycles
        condition = ["HEALTHY" if c < 210 else "DEGRADED_ANOMALY" for c in cycles]

        cmapss_df = pd.DataFrame({
            "unit_id": unit_id,
            "cycle": cycles,
            "setting_1": np.round(np.random.normal(0.001, 0.002, n_cycles), 4),
            "setting_2": np.round(np.random.normal(0.0002, 0.0001, n_cycles), 4),
            "sensor_2_T24": np.round(s2, 2),
            "sensor_3_T30": np.round(s3, 2),
            "sensor_4_Nf": np.round(s4, 2),
            "sensor_7_Ps30": np.round(s7, 2),
            "sensor_11_phi": np.round(s11, 2),
            "health_state": condition
        })
        cmapss_df.to_csv(cmapss_sample_path, index=False)


# Initialize sample datasets
ensure_sample_datasets()
