"""
Reporting and export module for AI Machine Health Monitor.
Generates structured analytical summaries and CSV export payloads.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

from src.database import get_latest_readings, get_alerts, get_readings_count


def generate_summary_report(
    analysis_name: str,
    target_info: str,
    selected_features: List[str],
    total_observations: int,
    anomaly_count: int,
    model_config: Dict[str, Any],
    stats_dict: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a professional Markdown & printable analytical summary report.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pct_anomalies = round((anomaly_count / total_observations * 100) if total_observations > 0 else 0, 2)

    report_lines = [
        f"# AI Machine Health Monitor — Analytical Summary",
        f"**Report Generated:** {now_str}",
        f"**Analysis Subject:** {analysis_name} ({target_info})",
        "",
        "## Executive Summary",
        f"- **Total Observations Analyzed:** {total_observations:,}",
        f"- **Detected Anomalous Observations:** {anomaly_count:,} ({pct_anomalies}%)",
        f"- **Normal Observations:** {total_observations - anomaly_count:,} ({100 - pct_anomalies:.2f}%)",
        f"- **Evaluation Model:** Isolation Forest (Unsupervised Tree-based Ensembles)",
        "",
        "## Feature Selection & Model Parameters",
        f"- **Active Model Features:** {', '.join(selected_features) if selected_features else 'None'}",
        f"- **Contamination Parameter:** {model_config.get('contamination', 'N/A')}",
        f"- **Number of Estimators:** {model_config.get('n_estimators', '100')}",
        f"- **Random State (Reproducibility):** {model_config.get('random_state', '42')}",
        "",
        "## Statistical Overview"
    ]

    if stats_dict:
        report_lines.append("| Feature | Mean | Std Dev | Min | Median | Max |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for feat in selected_features:
            f_stats = stats_dict.get(feat, {})
            mean_v = f_stats.get("mean", "N/A")
            std_v = f_stats.get("std", "N/A")
            min_v = f_stats.get("min", "N/A")
            med_v = f_stats.get("50%", "N/A")
            max_v = f_stats.get("max", "N/A")
            report_lines.append(f"| **{feat}** | {mean_v} | {std_v} | {min_v} | {med_v} | {max_v} |")
    else:
        report_lines.append("*Statistical distribution data not compiled for this run.*")

    report_lines.extend([
        "",
        "## Engineering Limitations & Disclaimers",
        "1. **Anomaly Detection vs. Failure Prediction:** This analytical pipeline employs unsupervised Isolation Forest anomaly detection to identify statistical outliers and deviation patterns. It does not predict an exact mechanical failure date, Remaining Useful Life (RUL), or wear rate unless explicitly paired with a validated physics-of-failure or degradation model.",
        "2. **Causal Attribution:** The model detects *that* an operating state deviates from normal operating baseline distributions; it does not automatically diagnose the underlying physical mechanical cause (e.g., stator winding short vs. bearing brinelling vs. mounting resonance).",
        "3. **Demonstration Thresholds:** Baseline rule-based limits are configured for demonstration purposes and do not substitute for manufacturer-certified machine operating standards (e.g. ISO 10816 / ISO 20816 vibration severity standards).",
        "",
        "---",
        "*AI Machine Health Monitor — Predictive Maintenance Telemetry Architecture.*"
    ])

    return "\n".join(report_lines)


def export_sensor_history_csv(limit: int = 2000) -> str:
    """Exports persisted SQLite sensor telemetry to CSV string."""
    readings = get_latest_readings(limit=limit)
    if not readings:
        return "id,device_id,received_at,external_temp_c,imu_temp_c,vibration_indicator_g,status\n"
    df = pd.DataFrame(readings)
    return df.to_csv(index=False)


def export_alerts_history_csv(limit: int = 1000) -> str:
    """Exports persisted SQLite alert events to CSV string."""
    alerts = get_alerts(limit=limit)
    if not alerts:
        return "id,created_at,device_or_dataset,alert_source,sensor_or_feature,observed_value,threshold_or_rule,severity,status\n"
    df = pd.DataFrame(alerts)
    return df.to_csv(index=False)
