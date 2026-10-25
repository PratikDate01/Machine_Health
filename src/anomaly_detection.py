"""
Isolation Forest Machine Learning Anomaly Detection Engine for AI Machine Health Monitor.
Provides model training, serialization, inference, evaluation, and explainability.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score

from src.config import config
from src.database import save_model_metadata, get_models_metadata
from src.feature_engineering import filter_usable_features, prepare_feature_matrix


class IsolationForestDetector:
    """
    Wrapper for Scikit-learn Isolation Forest model with metadata,
    standardized prediction output, feature stats, and explainability.
    """

    def __init__(
        self,
        model_name: str = "isolation_forest_v1",
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        self.model_name = model_name
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state

        self.model: Optional[IsolationForest] = None
        self.feature_names: List[str] = []
        self.feature_means: Dict[str, float] = {}
        self.feature_stds: Dict[str, float] = {}
        self.trained_at: Optional[str] = None
        self.n_samples: int = 0

    def fit(self, df: pd.DataFrame, features: List[str]) -> "IsolationForestDetector":
        """
        Fits the Isolation Forest on selected features.
        Computes baseline feature statistics for deviation explainability.
        """
        valid_features = filter_usable_features(df, features)
        if len(valid_features) == 0:
            raise ValueError("No valid numeric features found for training.")

        if len(df) < 15:
            raise ValueError(f"Insufficient training samples ({len(df)} rows). Need at least 15 observations.")

        X, self.feature_names = prepare_feature_matrix(df, valid_features)
        self.n_samples = len(X)

        # Baseline feature statistics for runtime explainability
        for idx, name in enumerate(self.feature_names):
            col_vals = X[:, idx]
            self.feature_means[name] = float(np.mean(col_vals))
            self.feature_stds[name] = float(np.std(col_vals)) if np.std(col_vals) > 1e-6 else 1.0

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.model.fit(X)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs anomaly inference on a DataFrame.
        Returns original dataframe with added columns:
        - anomaly_pred: 1 for Normal, -1 for Anomaly
        - anomaly_label: 'NORMAL' or 'ANOMALOUS'
        - anomaly_score: continuous score where higher = more anomalous (0.0 to 1.0 normalized)
        - top_deviating_feature: feature showing maximum absolute z-score deviation
        """
        if self.model is None or not self.feature_names:
            raise ValueError("Model is not fitted. Train or load a model first.")

        X, _ = prepare_feature_matrix(df, self.feature_names)

        # Scikit-learn: 1 = Normal, -1 = Anomaly
        preds = self.model.predict(X)

        # decision_function returns negative values for anomalies, positive for normal
        raw_scores = self.model.decision_function(X)

        # Normalize score into [0.0, 1.0] where higher = more anomalous
        # score = 0.5 - raw_score (rough baseline shift)
        min_s, max_s = raw_scores.min(), raw_scores.max()
        if max_s > min_s:
            norm_scores = 1.0 - (raw_scores - min_s) / (max_s - min_s)
        else:
            norm_scores = np.zeros_like(raw_scores)

        # Calculate deviation explanation for each sample
        top_features = []
        for i in range(len(X)):
            sample_deviations = {}
            for f_idx, f_name in enumerate(self.feature_names):
                f_val = X[i, f_idx]
                mean = self.feature_means.get(f_name, 0.0)
                std = self.feature_stds.get(f_name, 1.0)
                z_score = abs(f_val - mean) / std
                sample_deviations[f_name] = z_score

            top_feat = max(sample_deviations.items(), key=lambda item: item[1])[0]
            top_features.append(top_feat)

        result_df = df.copy()
        result_df["anomaly_pred"] = preds
        result_df["anomaly_label"] = np.where(preds == -1, "ANOMALOUS", "NORMAL")
        result_df["anomaly_score"] = np.round(norm_scores, 4)
        result_df["top_deviating_feature"] = top_features

        return result_df

    def predict_single(self, reading_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast single-reading inference for live telemetry incoming from ESP32.
        """
        if self.model is None or not self.feature_names:
            return {
                "is_available": False,
                "reason": "Model is not fitted or loaded."
            }

        # Check that required features are present
        row_vals = []
        deviations = {}
        for f in self.feature_names:
            val = reading_dict.get(f)
            if val is None or pd.isna(val):
                return {
                    "is_available": False,
                    "reason": f"Required model feature '{f}' is missing from reading."
                }
            val_f = float(val)
            row_vals.append(val_f)

            mean = self.feature_means.get(f, 0.0)
            std = self.feature_stds.get(f, 1.0)
            deviations[f] = abs(val_f - mean) / std

        X = np.array([row_vals])
        pred = int(self.model.predict(X)[0])  # 1 or -1
        raw_score = float(self.model.decision_function(X)[0])

        is_anomaly = (pred == -1)
        top_deviating = max(deviations.items(), key=lambda item: item[1])

        return {
            "is_available": True,
            "prediction": pred,
            "is_anomaly": is_anomaly,
            "label": "ANOMALOUS" if is_anomaly else "NORMAL",
            "decision_score": raw_score,
            "top_deviating_feature": top_deviating[0],
            "max_z_deviation": round(top_deviating[1], 2)
        }

    def save(self, filepath: Optional[Path] = None, notes: str = "") -> Path:
        """Serializes the detector to disk and registers in database."""
        if self.model is None:
            raise ValueError("Cannot save an unfitted model.")

        if filepath is None:
            config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            filepath = config.MODELS_DIR / f"{self.model_name}.joblib"

        state = {
            "model_name": self.model_name,
            "model": self.model,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "random_state": self.random_state,
            "feature_names": self.feature_names,
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "n_samples": self.n_samples
        }
        joblib.dump(state, filepath)

        # Register metadata in SQLite
        save_model_metadata(
            model_name=self.model_name,
            model_type="IsolationForest",
            contamination=self.contamination,
            features=self.feature_names,
            n_samples=self.n_samples,
            file_path=str(filepath),
            notes=notes
        )
        return filepath

    @classmethod
    def load(cls, filepath: Path) -> "IsolationForestDetector":
        """Loads a saved detector instance from disk."""
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")

        state = joblib.load(filepath)
        detector = cls(
            model_name=state.get("model_name", "loaded_model"),
            contamination=state.get("contamination", 0.05),
            n_estimators=state.get("n_estimators", 100),
            random_state=state.get("random_state", 42)
        )
        detector.model = state["model"]
        detector.feature_names = state["feature_names"]
        detector.feature_means = state.get("feature_means", {})
        detector.feature_stds = state.get("feature_stds", {})
        detector.n_samples = state.get("n_samples", 0)
        return detector


def evaluate_anomalies_if_ground_truth(
    df: pd.DataFrame,
    ground_truth_col: str,
    pred_col: str = "anomaly_label"
) -> Dict[str, Any]:
    """
    Evaluates anomaly detection against ground truth labels if available.
    Does NOT fabricate accuracy when ground truth is absent.
    """
    if ground_truth_col not in df.columns:
        return {"has_ground_truth": False}

    # Binarize ground truth: 1 for anomaly, 0 for normal
    gt_series = df[ground_truth_col].astype(str).str.upper()
    is_anomaly_gt = gt_series.apply(lambda x: 0 if x in ["NORMAL", "0", "OK", "HEALTHY"] else 1)

    # Predictions: 1 for anomaly, 0 for normal
    preds_series = df[pred_col].astype(str).str.upper()
    is_anomaly_pred = preds_series.apply(lambda x: 1 if "ANOMAL" in x or x == "-1" else 0)

    p = float(precision_score(is_anomaly_gt, is_anomaly_pred, zero_division=0))
    r = float(recall_score(is_anomaly_gt, is_anomaly_pred, zero_division=0))
    f1 = float(f1_score(is_anomaly_gt, is_anomaly_pred, zero_division=0))
    cm = confusion_matrix(is_anomaly_gt, is_anomaly_pred).tolist()

    return {
        "has_ground_truth": True,
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm,
        "total_true_anomalies": int(is_anomaly_gt.sum()),
        "total_predicted_anomalies": int(is_anomaly_pred.sum())
    }
