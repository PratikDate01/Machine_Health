"""
Unit tests for dataset inspection, column mapping, and data cleaning.
"""

import pytest
import pandas as pd
import numpy as np

from src.data_cleaning import inspect_dataset, suggest_column_mapping, clean_dataset
from src.data_loader import load_csv, ensure_sample_datasets
from src.config import config


def test_inspect_dataset():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "temperature": [25.5, 26.0, np.nan, 28.1],
        "vibration": [0.02, 0.05, 0.03, 0.04],
        "status": ["OK", "OK", "WARN", "OK"]
    })
    info = inspect_dataset(df)
    assert info["row_count"] == 4
    assert info["col_count"] == 4
    # "id" should be excluded from candidate numeric features
    assert "id" not in info["numeric_candidates"]
    assert "temperature" in info["numeric_candidates"]
    assert "vibration" in info["numeric_candidates"]


def test_suggest_column_mapping():
    df = pd.DataFrame({
        "time_ms": [100, 200],
        "temp": [30.1, 30.2],
        "vib_g": [0.02, 0.03],
        "accel_x": [0.01, 0.02]
    })
    mapping = suggest_column_mapping(df)
    assert mapping["external_temp_c"] == "temp"
    assert mapping["vibration_indicator_g"] == "vib_g"
    assert mapping["ax_g"] == "accel_x"


def test_clean_dataset_median_imputation():
    df = pd.DataFrame({
        "temp": [20.0, 30.0, np.nan, 40.0],
        "vib": [0.1, 0.2, 0.3, "invalid_str"]
    })
    clean_df, log = clean_dataset(df, feature_columns=["temp", "vib"], imputation_strategy="median")
    assert len(clean_df) == 4
    assert clean_df["temp"].isnull().sum() == 0
    assert clean_df["vib"].isnull().sum() == 0
    assert clean_df["temp"].iloc[2] == 30.0  # Median of 20, 30, 40


def test_clean_dataset_drop_imputation():
    df = pd.DataFrame({
        "temp": [20.0, 30.0, np.nan, 40.0],
        "vib": [0.1, 0.2, 0.3, 0.4]
    })
    clean_df, log = clean_dataset(df, feature_columns=["temp", "vib"], imputation_strategy="drop")
    assert len(clean_df) == 3


def test_clean_dataset_empty_features_error():
    df = pd.DataFrame({"temp": [20.0, 30.0]})
    with pytest.raises(ValueError):
        clean_dataset(df, feature_columns=["non_existent_column"])


def test_sample_datasets_generation():
    ensure_sample_datasets()
    esp32_path = config.RAW_DATA_DIR / "sample_esp32_hardware_run.csv"
    cmapss_path = config.RAW_DATA_DIR / "nasa_cmapss_sample.csv"

    assert esp32_path.exists()
    assert cmapss_path.exists()

    esp32_df = load_csv(esp32_path)
    assert len(esp32_df) == 600
    assert "external_temp_c" in esp32_df.columns
    assert "vibration_indicator_g" in esp32_df.columns
