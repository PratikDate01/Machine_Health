"""
Feature engineering and preprocessing module for AI Machine Health Monitor.
Guarantees clean feature selection and prevents identifier/timestamp leakage into ML models.
"""

from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


# Denylist of column substrings that must NEVER be passed as model features
IDENTIFIER_DENYLIST = [
    "id", "device_id", "unit_id", "timestamp", "time", "date",
    "received_at", "status", "ground_truth", "label", "condition", "target"
]


def filter_usable_features(
    df: pd.DataFrame,
    requested_features: Optional[List[str]] = None
) -> List[str]:
    """
    Selects valid numeric features and explicitly screens out identifiers,
    timestamps, and non-numeric columns.
    """
    if requested_features is not None:
        candidates = requested_features
    else:
        candidates = list(df.columns)

    usable = []
    for col in candidates:
        if col not in df.columns:
            continue

        col_lower = str(col).strip().lower()

        # Reject obvious ID or timestamp column names
        if any(bad_substr in col_lower for bad_substr in IDENTIFIER_DENYLIST):
            continue

        # Check numeric data type
        if pd.api.types.is_numeric_dtype(df[col]):
            # Reject zero-variance (constant) columns
            if df[col].nunique() > 1:
                usable.append(col)

    return usable


def prepare_feature_matrix(
    df: pd.DataFrame,
    features: List[str]
) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts a numpy array matrix strictly ordered by the features list.
    Ensures missing values are filled and values are float64.
    """
    if not features:
        raise ValueError("Cannot prepare feature matrix: no features specified.")

    missing_cols = [f for f in features if f not in df.columns]
    if missing_cols:
        raise ValueError(f"Required features missing from data: {missing_cols}")

    subset = df[features].copy()

    # Convert all columns to float
    for col in features:
        subset[col] = pd.to_numeric(subset[col], errors='coerce').fillna(0.0)

    return subset.values, features
