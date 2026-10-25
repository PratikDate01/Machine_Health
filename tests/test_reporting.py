"""
Unit tests for summary report generation and CSV exports.
"""

from src.reporting import generate_summary_report, export_sensor_history_csv, export_alerts_history_csv


def test_generate_summary_report():
    report = generate_summary_report(
        analysis_name="Turbofan Engine Run",
        target_info="Unit 01",
        selected_features=["sensor_2", "sensor_3"],
        total_observations=200,
        anomaly_count=10,
        model_config={"contamination": 0.05, "n_estimators": 100, "random_state": 42},
        stats_dict={
            "sensor_2": {"mean": 642.5, "std": 1.2, "min": 640.0, "50%": 642.3, "max": 646.0},
            "sensor_3": {"mean": 1588.0, "std": 2.5, "min": 1582.0, "50%": 1587.5, "max": 1595.0}
        }
    )
    assert "AI Machine Health Monitor" in report
    assert "Turbofan Engine Run" in report
    assert "sensor_2" in report
    assert "Engineering Limitations & Disclaimers" in report


def test_export_csv_functions():
    sensor_csv = export_sensor_history_csv(limit=10)
    assert isinstance(sensor_csv, str)
    assert "external_temp_c" in sensor_csv

    alerts_csv = export_alerts_history_csv(limit=10)
    assert isinstance(alerts_csv, str)
    assert "severity" in alerts_csv
