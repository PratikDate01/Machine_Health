"""
Dataset Upload & Analysis Page — AI Machine Health Monitor.
Upload external CSV datasets, inspect schemas, auto-map columns, clean data, and export sanitized sets.
"""

import streamlit as st
import pandas as pd
from typing import Optional

from src.data_loader import load_csv
from src.data_cleaning import inspect_dataset, suggest_column_mapping, clean_dataset
from src.config import config
from dashboard.components.cards import render_metric_card, render_header_banner


def render():
    render_header_banner(
        page_title="Dataset Ingestion & Schema Diagnostics",
        page_description="Upload machine sensor CSV files, inspect data quality, execute automated sanitization, and prepare for ML training.",
        status_label="Data Ingestion"
    )

    # Ingestion Source Options
    st.markdown("<div class='section-header'>1. Ingest Dataset</div>", unsafe_allow_html=True)
    load_mode = st.radio("Choose Ingestion Method", ["Upload Local CSV File", "Load Pre-packaged Dataset"], horizontal=True)

    df_raw: Optional[pd.DataFrame] = None
    file_label = ""

    if load_mode == "Upload Local CSV File":
        uploaded_file = st.file_uploader("Upload Machine Sensor CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                df_raw = load_csv(uploaded_file)
                file_label = uploaded_file.name
                st.session_state["uploaded_df"] = df_raw
                st.session_state["uploaded_filename"] = file_label
            except Exception as e:
                st.error(f"Failed to parse CSV: {str(e)}")
                return
    else:
        sample_choice = st.selectbox(
            "Select Pre-packaged Dataset",
            [
                "sample_esp32_hardware_run.csv (ESP32 DevKit prototype baseline)",
                "nasa_cmapss_sample.csv (Turbofan Engine Degradation dataset)"
            ]
        )
        if st.button("Load Selected Dataset"):
            fname = sample_choice.split()[0]
            fpath = config.RAW_DATA_DIR / fname
            df_raw = load_csv(fpath)
            file_label = fname
            st.session_state["uploaded_df"] = df_raw
            st.session_state["uploaded_filename"] = file_label
            st.success(f"Loaded '{fname}' into memory session!")

    # Check if a dataset exists in session
    if df_raw is None:
        if "uploaded_df" in st.session_state and st.session_state["uploaded_df"] is not None:
            df_raw = st.session_state["uploaded_df"]
            file_label = st.session_state.get("uploaded_filename", "Current Session Data")
        else:
            st.info("Please upload a CSV file or select a pre-packaged dataset above to begin analysis.")
            return

    # 2. Schema Inspection & Health Check
    st.markdown(f"<div class='section-header'>2. Schema Inspection: {file_label}</div>", unsafe_allow_html=True)
    inspection = inspect_dataset(df_raw)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Rows", f"{inspection['row_count']:,}", "records", "Dataset length")
    with m2:
        render_metric_card("Total Columns", inspection['col_count'], "columns", "Variables identified")
    with m3:
        render_metric_card("Numeric Features", len(inspection['numeric_candidates']), "candidates", "Viable for ML models")
    with m4:
        total_missing = sum(c['null_count'] for c in inspection['columns'])
        render_metric_card("Total Missing Cells", f"{total_missing:,}", "cells", "Across all columns", status_color="#D97706" if total_missing > 0 else "#16A34A")

    # Column Details Table
    col_df = pd.DataFrame(inspection["columns"])
    st.dataframe(col_df, use_container_width=True, hide_index=True)

    # Raw Data Preview
    with st.expander("Preview Raw Dataset (First 10 Rows)", expanded=False):
        st.dataframe(df_raw.head(10), use_container_width=True)

    # 3. Column Mapping
    st.markdown("<div class='section-header'>3. Hardware Telemetry Column Mapping</div>", unsafe_allow_html=True)
    mapping = suggest_column_mapping(df_raw)
    st.caption("Automatic detection of standard machine monitoring parameters. Adjust manually if needed:")

    map_c1, map_c2, map_c3 = st.columns(3)
    all_cols_with_none = ["None"] + list(df_raw.columns)

    with map_c1:
        mapped_ext_temp = st.selectbox(
            "External Machine Temp (DS18B20)",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["external_temp_c"]) if mapping["external_temp_c"] in all_cols_with_none else 0
        )
        mapped_vib = st.selectbox(
            "Vibration Indicator",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["vibration_indicator_g"]) if mapping["vibration_indicator_g"] in all_cols_with_none else 0
        )

    with map_c2:
        mapped_imu_temp = st.selectbox(
            "IMU Silicon Temp",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["imu_temp_c"]) if mapping["imu_temp_c"] in all_cols_with_none else 0
        )
        mapped_ts = st.selectbox(
            "Timestamp / Cycle",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["timestamp"]) if mapping["timestamp"] in all_cols_with_none else 0
        )

    with map_c3:
        mapped_accel_x = st.selectbox(
            "Acceleration X",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["ax_g"]) if mapping["ax_g"] in all_cols_with_none else 0
        )
        mapped_gyro_x = st.selectbox(
            "Gyroscope X",
            all_cols_with_none,
            index=all_cols_with_none.index(mapping["gyro_x_dps"]) if mapping["gyro_x_dps"] in all_cols_with_none else 0
        )

    # 4. Data Cleaning Pipeline
    st.markdown("<div class='section-header'>4. Automated Cleaning & Sanitization</div>", unsafe_allow_html=True)
    cl_c1, cl_c2 = st.columns(2)

    with cl_c1:
        impute_strategy = st.selectbox(
            "Missing Value Handling Strategy",
            ["median", "mean", "drop", "ffill"],
            index=0,
            help="Median/mean imputation replaces missing cells with column summary. Drop removes corrupted rows."
        )
    with cl_c2:
        drop_dups = st.checkbox("Drop Exact Duplicate Rows", value=True)

    if st.button("Execute Data Cleaning Pipeline", type="primary"):
        candidate_features = inspection["numeric_candidates"]
        if not candidate_features:
            st.error("No numeric candidate features selected for cleaning.")
            return

        with st.spinner("Sanitizing dataset..."):
            cleaned_df, cleaning_log = clean_dataset(
                df_raw,
                feature_columns=candidate_features,
                timestamp_col=mapped_ts if mapped_ts != "None" else None,
                imputation_strategy=impute_strategy,
                drop_duplicates=drop_dups
            )

            st.session_state["cleaned_df"] = cleaned_df
            st.session_state["cleaning_log"] = cleaning_log
            st.success("Dataset successfully sanitized!")

    # Display Cleaning Log and Download
    if "cleaned_df" in st.session_state and "cleaning_log" in st.session_state:
        st.markdown("<div class='section-header'>Data Cleaning Changelog</div>", unsafe_allow_html=True)
        for entry in st.session_state["cleaning_log"]:
            st.markdown(f"- {entry}")

        cleaned_csv = st.session_state["cleaned_df"].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Cleaned CSV Dataset",
            data=cleaned_csv,
            file_name=f"cleaned_{file_label}",
            mime="text/csv",
            use_container_width=True
        )
