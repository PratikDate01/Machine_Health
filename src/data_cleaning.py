"""
Data cleaning and validation module for AI Machine Health Monitor.
Performs robust inspection, type coercion, missing value handling, and column mapping.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np


# Common sensor aliases for auto-mapping
COLUMN_ALIASES = {
    "external_temp_c": ["external_temp_c", "ext_temp", "temperature", "temp", "temp_c", "motor_temp", "s2", "sensor2"],
    "imu_temp_c": ["imu_temp_c", "internal_temp", "board_temp", "mpu_temp", "chip_temp"],
    "vibration_indicator_g": ["vibration_indicator_g", "vibration", "vib", "vib_g", "vib_indicator", "vibration_g"],
    "ax_g": ["ax_g", "accel_x", "ax", "acc_x", "acceleration_x"],
    "ay_g": ["ay_g", "accel_y", "ay", "acc_y", "acceleration_y"],
    "az_g": ["az_g", "accel_z", "az", "acc_z", "acceleration_z"],
    "gyro_x_dps": ["gyro_x_dps", "gx", "gyro_x", "rot_x"],
    "gyro_y_dps": ["gyro_y_dps", "gy", "gyro_y", "rot_y"],
    "gyro_z_dps": ["gyro_z_dps", "gz", "gyro_z", "rot_z"],
    "timestamp": ["timestamp", "time", "datetime", "date", "time_ms", "timestamp_ms", "cycle", "cycles"]
}


def inspect_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes an uploaded DataFrame and returns structured metadata,
    including missing counts, data types, and potential candidate columns.
    """
    total_rows = len(df)
    total_cols = len(df.columns)

    column_info = []
    numeric_candidates = []
    timestamp_candidates = []

    for col in df.columns:
        col_str = str(col)
        dtype = str(df[col].dtype)
        null_count = int(df[col].isnull().sum())
        null_pct = round((null_count / total_rows * 100) if total_rows > 0 else 0, 2)
        n_unique = int(df[col].nunique())

        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        is_candidate_feature = False

        # Exclude constant columns or ID columns from being auto-selected features
        if is_numeric and n_unique > 1 and not col_str.lower().endswith(("_id", "id")):
            numeric_candidates.append(col_str)
            is_candidate_feature = True

        # Check for potential timestamp column
        col_lower = col_str.lower()
        if any(ts_alias in col_lower for ts_alias in ["time", "date", "cycle", "timestamp"]):
            timestamp_candidates.append(col_str)

        column_info.append({
            "column": col_str,
            "dtype": dtype,
            "null_count": null_count,
            "null_percent": null_pct,
            "n_unique": n_unique,
            "is_numeric": is_numeric,
            "is_candidate_feature": is_candidate_feature
        })

    summary_stats = df.describe().round(4).to_dict() if len(numeric_candidates) > 0 else {}

    return {
        "row_count": total_rows,
        "col_count": total_cols,
        "columns": column_info,
        "numeric_candidates": numeric_candidates,
        "timestamp_candidates": timestamp_candidates,
        "summary_statistics": summary_stats
    }


def suggest_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Automatically detects best-match columns for standard hardware telemetry parameters.
    """
    mapping = {}
    lower_cols = {str(c).strip().lower(): str(c) for c in df.columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        matched = None
        for alias in aliases:
            if alias.lower() in lower_cols:
                matched = lower_cols[alias.lower()]
                break
        mapping[canonical] = matched

    return mapping


def clean_dataset(
    df: pd.DataFrame,
    feature_columns: List[str],
    timestamp_col: Optional[str] = None,
    imputation_strategy: str = "median",
    drop_duplicates: bool = True
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Cleans the dataset safely and transparently:
    - Verifies feature columns exist.
    - Drops duplicates if requested.
    - Coerces feature columns to float, turning invalid characters to NaN.
    - Imputes or drops NaNs with explicit changelog.
    - Does NOT invent synthetic measurements.
    """
    cleaning_log = []
    clean_df = df.copy()

    initial_rows = len(clean_df)

    # 1. Deduplication
    if drop_duplicates:
        clean_df = clean_df.drop_duplicates()
        dups_removed = initial_rows - len(clean_df)
        if dups_removed > 0:
            cleaning_log.append(f"Removed {dups_removed} exact duplicate row(s).")

    # 2. Verify selected features
    valid_features = [col for col in feature_columns if col in clean_df.columns]
    if not valid_features:
        raise ValueError("No valid numeric feature columns were found in the dataset.")

    # 3. Numeric Coercion
    for col in valid_features:
        non_num_count = clean_df[col].apply(lambda x: not (isinstance(x, (int, float, np.number)) or str(x).replace(".", "", 1).replace("-", "", 1).isdigit())).sum()
        clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
        coerced_nan = clean_df[col].isnull().sum()
        if non_num_count > 0:
            cleaning_log.append(f"Column '{col}': coerced non-numeric values to NaN ({coerced_nan} total NaN cells).")

    # 4. Handle Missing Values
    null_count_before = clean_df[valid_features].isnull().sum().sum()
    if null_count_before > 0:
        if imputation_strategy == "drop":
            rows_before = len(clean_df)
            clean_df = clean_df.dropna(subset=valid_features)
            rows_dropped = rows_before - len(clean_df)
            cleaning_log.append(f"Dropped {rows_dropped} row(s) containing missing values across selected features.")
        elif imputation_strategy == "median":
            for col in valid_features:
                med_val = clean_df[col].median()
                if pd.isna(med_val):
                    med_val = 0.0
                clean_df[col] = clean_df[col].fillna(med_val)
            cleaning_log.append(f"Imputed missing feature values using column median.")
        elif imputation_strategy == "mean":
            for col in valid_features:
                mean_val = clean_df[col].mean()
                if pd.isna(mean_val):
                    mean_val = 0.0
                clean_df[col] = clean_df[col].fillna(mean_val)
            cleaning_log.append(f"Imputed missing feature values using column mean.")
        elif imputation_strategy == "ffill":
            clean_df[valid_features] = clean_df[valid_features].ffill().bfill().fillna(0.0)
            cleaning_log.append("Imputed missing feature values using forward-fill / backward-fill.")

    # 5. Timestamp validation
    if timestamp_col and timestamp_col in clean_df.columns:
        # Check if it parses as datetime or numeric uptime
        if not pd.api.types.is_numeric_dtype(clean_df[timestamp_col]):
            try:
                clean_df["parsed_timestamp"] = pd.to_datetime(clean_df[timestamp_col], errors='coerce')
                cleaning_log.append(f"Parsed timestamp column '{timestamp_col}' to standard datetime.")
            except Exception:
                cleaning_log.append(f"Could not parse '{timestamp_col}' to datetime; kept in raw form.")

    final_rows = len(clean_df)
    cleaning_log.append(f"Data cleaning finalized: {final_rows} observations retained across {len(valid_features)} features.")

    return clean_df, cleaning_log
