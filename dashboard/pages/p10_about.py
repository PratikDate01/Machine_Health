"""
Project Information / About Page — AI Machine Health Monitor.
Details technical architecture, project objectives, and demonstration criteria.
"""

import streamlit as st
import pandas as pd
from dashboard.components.cards import render_header_banner


def render():
    render_header_banner(
        page_title="About AI Machine Health Monitor",
        page_description="B09 – FAIR-AI-09 | AI-Based Machine Health Monitoring and Anomaly Detection Using Machine Learning.",
        status_label="System Info"
    )

    # 1. Project Overview & Scope
    st.markdown("""
    ### Project Scope & Domain Architecture
    **System Title:** AI-Based Machine Health Monitoring and Anomaly Detection Using Machine Learning  
    **Domain:** Industrial IoT, Condition Monitoring & Predictive Maintenance  
    **Core Objective:** Detect unusual machine behavior and mechanical degradation from multi-variable sensor data using statistical data analysis, machine learning (Isolation Forest), and high-throughput real-time telemetry streaming.

    The application supports two unified operational modes:
    1. **Dataset Analysis Mode:** Ingests external machine sensor CSV datasets (such as NASA C-MAPSS and factory logs), cleans missing data, trains reproducible Isolation Forest anomaly models, and exports audit reports.
    2. **Live Hardware Telemetry Mode:** Receives real-time sensor packets from an ESP32 microcontroller over Wi-Fi, monitors physical motor health, visualizes 6-DOF motion and thermal parameters, and executes real-time anomaly inference.
    """)

    # 2. End-to-End System Architecture
    st.markdown("<div class='section-header'>End-to-End System Architecture</div>", unsafe_allow_html=True)
    st.markdown("""
    ```
    [ESP32 DevKit V1] 
         │
         ├── MPU6500 IMU ─────────── (I2C: GPIO 21/22) ─── [6-DOF Motion & Chip Temp]
         ├── DS18B20 Probe ───────── (1-Wire: GPIO 4) ──── [Machine External Temp]
         └── DC Motor (L298N) ────── (GPIO 26/27, ENA) ─── [Rotating Mechanical Load]
         │
         │ Wi-Fi HTTP POST (JSON Telemetry)
         ▼
    [FastAPI REST Gateway (Port 8000)]
         │
         ├── Pydantic Input Validation & Range Checking
         ├── Heartbeat & Device Presence Tracking
         │
         ▼
    [SQLite Persistence Layer (machine_health.db)]
         ├── sensor_readings (WAL mode, indexed lookups)
         ├── alerts (active / acknowledged / resolved / auto-resolved)
         └── model_registry (serialized artifacts)
         │
         ▼
    [Streamlit Industrial Analytics Dashboard (Port 8501)]
         ├── Overview Dashboard (Real-time KPIs, Motion Vector & Sensor Trends)
         ├── Live Machine Monitoring (Buffered Stream & Diagnostics)
         ├── AI Anomaly Detection (Isolation Forest Training & Evaluation)
         ├── Sensor Analytics (Rolling Windows, Correlation & Distributions)
         └── Engineering Reports & CSV Exports
    ```
    """)

    # 3. Project Guide Five-Week Schedule Alignment
    st.markdown("<div class='section-header'>Development Plan Alignment (B09 – FAIR-AI-09)</div>", unsafe_allow_html=True)

    plan_data = [
        {"Stage": "Week 1", "Focus": "Python, Pandas, NumPy, Statistics, and Data Modeling", "Deliverable": "Data loader and environment structure", "Status": "Completed"},
        {"Stage": "Week 2", "Focus": "Data cleaning, missing value imputation, and Plotly visualizations", "Deliverable": "Sanitized datasets & sensor graphs", "Status": "Completed"},
        {"Stage": "Week 3", "Focus": "Anomaly detection engineering and Isolation Forest pipeline", "Deliverable": "Functional Scikit-learn ML engine", "Status": "Completed"},
        {"Stage": "Week 4", "Focus": "Streamlit dashboard, real-time alerts, and CSV uploads", "Deliverable": "Interactive web application", "Status": "Completed"},
        {"Stage": "Week 5", "Focus": "Testing, UI refinement, hardware integration, and reporting", "Deliverable": "Passing test suite, firmware & documentation", "Status": "Completed"}
    ]
    st.dataframe(pd.DataFrame(plan_data), use_container_width=True, hide_index=True)

    # 4. Final Demonstration Checklist Verification
    st.markdown("<div class='section-header'>Demonstration Acceptance Checklist</div>", unsafe_allow_html=True)

    st.markdown("""
    - [x] **Machine-sensor dataset:** Pre-packaged ESP32 run and NASA C-MAPSS dataset included in `data/raw/`.
    - [x] **Data cleaning using Pandas:** Complete inspection, type coercion, deduplication, and missing-value imputation.
    - [x] **Sensor visualization:** High-contrast Plotly line charts, correlation matrices, and distribution histograms.
    - [x] **Machine-learning anomaly detection:** Working Scikit-learn Isolation Forest with configurable contamination.
    - [x] **Working Streamlit dashboard:** 10 responsive pages with modern industrial monitoring theme.
    - [x] **Anomaly results and interpretation:** Normal vs Anomaly labeling, continuous anomaly score, and top deviating feature explainability.
    - [x] **Project report and export:** Downloadable Markdown engineering summary, sensor history CSV, and alerts CSV.
    - [x] **Hardware demonstration integration:** Fast REST API, working sensor diagnostic sketch, and Wi-Fi transmitter sketch.
    """)
