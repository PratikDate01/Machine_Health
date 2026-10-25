"""
Sensor Analytics Page — AI Machine Health Monitor.
Advanced descriptive statistics, multi-variable correlation, rolling smoothers, and normal vs anomalous comparisons.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd
import numpy as np

from src.data_loader import load_csv
from src.live_monitor import live_monitor
from src.database import get_latest_readings
from src.config import config
from dashboard.components.cards import render_header_banner
from dashboard.components.charts import (
    create_sensor_trend_chart,
    create_correlation_heatmap,
    create_normal_vs_anomaly_distribution
)


def render():
    render_header_banner(
        page_title="Sensor Analytics & Telemetry Diagnostics",
        page_description="Statistical distributions, rolling window smoothers, correlation matrices, and comparative defect analysis.",
        status_label="Analytics"
    )

    # 1. Select Analytics Data Source
    data_source_options = [
        "Current Live / Database Telemetry Buffer",
        "Pre-packaged ESP32 Baseline Run",
        "Pre-packaged NASA C-MAPSS Turbofan Run",
        "Custom Uploaded Dataset"
    ]
    source_choice = st.selectbox("Select Analytics Dataset", data_source_options)

    df: Optional[pd.DataFrame] = None

    if "Current Live" in source_choice:
        readings = live_monitor.get_buffered_readings()
        if not readings:
            readings = get_latest_readings(limit=300)
            readings = list(reversed(readings))
        if readings:
            df = pd.DataFrame(readings)
        else:
            st.info("No live or database telemetry recorded yet. Showing pre-packaged baseline run.")
            df = load_csv(config.RAW_DATA_DIR / "sample_esp32_hardware_run.csv")
    elif "ESP32 Baseline" in source_choice:
        df = load_csv(config.RAW_DATA_DIR / "sample_esp32_hardware_run.csv")
    elif "NASA C-MAPSS" in source_choice:
        df = load_csv(config.RAW_DATA_DIR / "nasa_cmapss_sample.csv")
    else:
        if "uploaded_df" in st.session_state and st.session_state["uploaded_df"] is not None:
            df = st.session_state["uploaded_df"]
        else:
            st.warning("No custom dataset uploaded in session. Please upload one via 'Dataset Upload & Analysis'.")
            return

    if df is None or df.empty:
        st.warning("Dataset contains no records.")
        return

    # Numeric Columns
    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not str(c).lower().endswith(("_id", "id"))]
    if not numeric_cols:
        st.error("No numeric features found to analyze.")
        return

    # Filter Controls
    st.markdown("<div class='section-header'>Data Filters & Signal Smoothing</div>", unsafe_allow_html=True)
    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])

    with fcol1:
        if len(df) > 10:
            sample_range = st.slider("Observation Range", 0, len(df), (0, min(500, len(df))))
            filtered_df = df.iloc[sample_range[0]:sample_range[1]].copy()
        else:
            filtered_df = df.copy()

    with fcol2:
        apply_rolling = st.checkbox("Apply Rolling Average", value=False)
        rolling_window = st.selectbox("Window Size", [3, 5, 10, 20], index=1) if apply_rolling else 5

    with fcol3:
        target_features = st.multiselect(
            "Select Sensors to Graph",
            options=numeric_cols,
            default=numeric_cols[:min(4, len(numeric_cols))]
        )

    # Compute Rolling Averages if Enabled
    plot_df = filtered_df.copy()
    if apply_rolling and target_features:
        for feat in target_features:
            plot_df[f"{feat}_rolling"] = plot_df[feat].rolling(window=rolling_window, min_periods=1).mean()
        display_y_cols = [f"{feat}_rolling" for feat in target_features]
        chart_title = f"Smoothed Sensor Trends (Rolling Window = {rolling_window})"
    else:
        display_y_cols = target_features
        chart_title = "Raw Sensor Telemetry Trends"

    # Multi-variable Trend Chart
    if display_y_cols:
        fig_trend = create_sensor_trend_chart(
            plot_df,
            y_columns=display_y_cols,
            title=chart_title
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # Statistical Overview Table
    st.markdown("<div class='section-header'>Descriptive Statistics Summary</div>", unsafe_allow_html=True)
    stats_df = filtered_df[target_features].describe().round(4).T
    st.dataframe(stats_df, use_container_width=True)

    # Correlation & Comparative Diagnostics
    st.markdown("<div class='section-header'>Correlation & Defect Comparisons</div>", unsafe_allow_html=True)
    c_tab1, c_tab2 = st.tabs(["Feature Correlation Heatmap", "Normal vs Anomalous Distribution"])

    with c_tab1:
        if len(numeric_cols) >= 2:
            fig_corr = create_correlation_heatmap(filtered_df, numeric_cols[:min(10, len(numeric_cols))])
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("At least two numeric features required for correlation matrix.")

    with c_tab2:
        # Check if an anomaly label column exists
        anomaly_cols = [c for c in filtered_df.columns if "anomaly" in c.lower() or "health" in c.lower() or "label" in c.lower()]
        if anomaly_cols and len(target_features) > 0:
            chosen_anom_col = anomaly_cols[0]
            chosen_feat = target_features[0]
            fig_comp = create_normal_vs_anomaly_distribution(filtered_df, feature=chosen_feat, label_col=chosen_anom_col)
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("No anomaly labels present in this dataset yet. Run the 'AI Anomaly Detection' tab to flag and compare normal vs anomalous distributions.")
