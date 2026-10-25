"""
Main Application Entry Point — AI Machine Health Monitor.
Launches the Streamlit web dashboard with multi-page navigation and industrial monitoring interface.
"""

import streamlit as st

# Configure Streamlit page settings
st.set_page_config(
    page_title="AI Machine Health Monitor",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply corporate light styling tokens
from dashboard.styles import CUSTOM_CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Import sidebar and page views
from dashboard.components.sidebar import render_sidebar
from dashboard.pages import (
    p1_overview,
    p2_live_monitoring,
    p3_ai_anomaly,
    p4_sensor_analytics,
    p5_dataset_analysis,
    p6_alert_history,
    p7_reports_export,
    p8_model_info,
    p9_hardware_status,
    p10_about
)

# Render Sidebar and receive active selection
selected_page = render_sidebar()

# Page Routing
if selected_page == "1. Overview Dashboard":
    p1_overview.render()
elif selected_page == "2. Live Machine Monitoring":
    p2_live_monitoring.render()
elif selected_page == "3. AI Anomaly Detection":
    p3_ai_anomaly.render()
elif selected_page == "4. Sensor Analytics":
    p4_sensor_analytics.render()
elif selected_page == "5. Dataset Upload & Analysis":
    p5_dataset_analysis.render()
elif selected_page == "6. Anomaly & Alert History":
    p6_alert_history.render()
elif selected_page == "7. Reports & Export":
    p7_reports_export.render()
elif selected_page == "8. Model Information":
    p8_model_info.render()
elif selected_page == "9. Hardware & Connection Status":
    p9_hardware_status.render()
elif selected_page == "10. Project Information / About":
    p10_about.render()
else:
    p1_overview.render()
