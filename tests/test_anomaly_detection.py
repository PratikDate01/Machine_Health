"""
Unit tests for Isolation Forest training, serialization, inference, and metrics.
"""

import pytest
import pandas as pd
import numpy as np

from src.anomaly_detection import IsolationForestDetector, evaluate_anomalies_if_ground_truth
from src.config import config


@pytest.fixture
def sample_training_data():
    np.random.seed(42)
    n = 100
    temp = np.random.normal(30.0, 1.5, n)
    vib = np.random.normal(0.05, 0.01, n)
    df = pd.DataFrame({"temperature": temp, "vibration": vib})
    return df


def test_isolation_forest_training_and_predict(sample_training_data):
    detector = IsolationForestDetector(model_name="test_model", contamination=0.1)
    detector.fit(sample_training_data, features=["temperature", "vibration"])

    assert detector.model is not None
    assert detector.feature_names == ["temperature", "vibration"]

    # Inference on same data
    res_df = detector.predict(sample_training_data)
    assert "anomaly_pred" in res_df.columns
    assert "anomaly_label" in res_df.columns
    assert "anomaly_score" in res_df.columns
    assert "top_deviating_feature" in res_df.columns

    # Verify predictions are mapped to 1 / -1 and NORMAL / ANOMALOUS
    assert set(res_df["anomaly_pred"].unique()).issubset({1, -1})
    assert set(res_df["anomaly_label"].unique()).issubset({"NORMAL", "ANOMALOUS"})


def test_isolation_forest_single_reading(sample_training_data):
    detector = IsolationForestDetector(model_name="single_test", contamination=0.05)
    detector.fit(sample_training_data, features=["temperature", "vibration"])

    # Normal reading
    normal_reading = {"temperature": 30.1, "vibration": 0.05}
    pred_normal = detector.predict_single(normal_reading)
    assert pred_normal["is_available"] is True
    assert pred_normal["prediction"] == 1
    assert pred_normal["is_anomaly"] is False

    # Extreme anomalous reading
    anomaly_reading = {"temperature": 85.0, "vibration": 1.50}
    pred_anomaly = detector.predict_single(anomaly_reading)
    assert pred_anomaly["is_available"] is True
    assert pred_anomaly["prediction"] == -1
    assert pred_anomaly["is_anomaly"] is True
    assert pred_anomaly["top_deviating_feature"] in ["temperature", "vibration"]


def test_isolation_forest_missing_features(sample_training_data):
    detector = IsolationForestDetector(model_name="missing_feat_test")
    detector.fit(sample_training_data, features=["temperature", "vibration"])

    incomplete_reading = {"temperature": 30.0}  # missing 'vibration'
    pred = detector.predict_single(incomplete_reading)
    assert pred["is_available"] is False
    assert "missing" in pred["reason"]


def test_isolation_forest_save_and_load(sample_training_data, tmp_path):
    detector = IsolationForestDetector(model_name="save_load_test", contamination=0.08)
    detector.fit(sample_training_data, features=["temperature", "vibration"])

    save_path = tmp_path / "test_detector.joblib"
    detector.save(filepath=save_path)
    assert save_path.exists()

    loaded = IsolationForestDetector.load(save_path)
    assert loaded.feature_names == ["temperature", "vibration"]
    assert loaded.contamination == 0.08

    # Predict with loaded model
    pred = loaded.predict_single({"temperature": 30.0, "vibration": 0.05})
    assert pred["is_available"] is True


def test_evaluate_anomalies_ground_truth():
    df = pd.DataFrame({
        "label": ["NORMAL", "NORMAL", "FAULT", "FAULT"],
        "anomaly_label": ["NORMAL", "NORMAL", "ANOMALOUS", "NORMAL"]
    })
    metrics = evaluate_anomalies_if_ground_truth(df, ground_truth_col="label")
    assert metrics["has_ground_truth"] is True
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 0.5
