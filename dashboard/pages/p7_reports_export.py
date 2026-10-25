"""
Reports & Export Page — AI Machine Health Monitor.
Generates comprehensive engineering reports and exports datasets, anomaly logs, and sensor telemetry.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from src.reporting import generate_summary_report, export_sensor_history_csv, export_alerts_history_csv
from src.live_monitor import live_monitor
from src.database import get_alerts, get_latest_readings
from dashboard.components.cards import render_header_banner


def render():
    render_header_banner(
        page_title="Engineering Reports & Telemetry Export",
        page_description="Export historical telemetry, anomaly audits, sanitized CSVs, and generate printable executive reports.",
        status_label="Reporting"
    )

    st.markdown("<div class='section-header'>1. Data Exports (CSV Formats)</div>", unsafe_allow_html=True)
    exp_c1, exp_c2, exp_c3 = st.columns(3)

    with exp_c1:
        st.subheader("Sensor History CSV")
        st.caption("Exports all persisted ESP32 and SQLite telemetry packets.")
        sensor_csv = export_sensor_history_csv(limit=5000)
        st.download_button(
            label="Download Sensor History",
            data=sensor_csv,
            file_name="sensor_telemetry_history.csv",
            mime="text/csv",
            use_container_width=True
        )

    with exp_c2:
        st.subheader("Alert Audit Log CSV")
        st.caption("Exports all triggered warning, critical, and ML anomaly records.")
        alerts_csv = export_alerts_history_csv(limit=2000)
        st.download_button(
            label="Download Alerts History",
            data=alerts_csv,
            file_name="alerts_audit_log.csv",
            mime="text/csv",
            use_container_width=True
        )

    with exp_c3:
        st.subheader("Current Anomaly Run CSV")
        st.caption("Exports the latest Isolation Forest anomaly scoring dataset.")
        if "anomaly_results_df" in st.session_state and st.session_state["anomaly_results_df"] is not None:
            anom_csv = st.session_state["anomaly_results_df"].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Anomaly Run",
                data=anom_csv,
                file_name="anomaly_scored_dataset.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("Train an Isolation Forest model first in 'AI Anomaly Detection' to export anomaly results.")

    # 2. Executive Analytical Summary Report Generator
    st.markdown("<div class='section-header'>2. Executive Summary Report Generator</div>", unsafe_allow_html=True)

    report_title = st.text_input("Analysis Project Title", value="Rotating Machinery Anomaly & Vibration Audit")
    target_machine = st.text_input("Machine / Asset Identifier", value="ESP32 Unit 01 — DC Motor Testbed")

    # Check if a model result is available in session
    if "anomaly_results_df" in st.session_state and "fitted_detector" in st.session_state:
        res_df = st.session_state["anomaly_results_df"]
        detector = st.session_state["fitted_detector"]
        total_obs = len(res_df)
        total_anom = int((res_df["anomaly_label"] == "ANOMALOUS").sum())
        features = detector.feature_names
        cfg = {
            "contamination": detector.contamination,
            "n_estimators": detector.n_estimators,
            "random_state": detector.random_state
        }
        stats_dict = res_df[features].describe().to_dict()
    else:
        # Generate baseline report using buffered readings
        readings = live_monitor.get_buffered_readings(limit=100)
        if readings:
            df_buf = pd.DataFrame(readings)
            total_obs = len(df_buf)
            total_anom = int(df_buf.get("is_anomaly", pd.Series([0]*len(df_buf))).sum())
            features = ["external_temp_c", "imu_temp_c", "vibration_indicator_g"]
            cfg = {"contamination": 0.05, "n_estimators": 100, "random_state": 42}
            stats_dict = df_buf[features].describe().to_dict() if all(f in df_buf.columns for f in features) else None
        else:
            total_obs = 600
            total_anom = 65
            features = ["external_temp_c", "imu_temp_c", "vibration_indicator_g", "ax_g", "ay_g"]
            cfg = {"contamination": 0.05, "n_estimators": 100, "random_state": 42}
            stats_dict = None

    if st.button("Generate Analytical Summary Report", type="primary"):
        report_md = generate_summary_report(
            analysis_name=report_title,
            target_info=target_machine,
            selected_features=features,
            total_observations=total_obs,
            anomaly_count=total_anom,
            model_config=cfg,
            stats_dict=stats_dict
        )
        st.session_state["generated_report_md"] = report_md

    # Display Generated Report
    if "generated_report_md" in st.session_state:
        st.markdown("<div class='section-header'>Report Document Preview</div>", unsafe_allow_html=True)
        report_text = st.session_state["generated_report_md"]

        st.markdown(report_text)

        st.download_button(
            label="Download Markdown Summary Report (.md)",
            data=report_text,
            file_name=f"Machine_Health_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
