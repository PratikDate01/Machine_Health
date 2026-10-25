"""
Live Machine Monitoring Page — AI Machine Health Monitor.
Real-time streaming telemetry gateway view powered by Streamlit @st.fragment auto-refresh.
High-frequency SQLite polling, gap-break charting, and separate hardware sensor diagnostics.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import numpy as np

from src.live_monitor import live_monitor, parse_timestamp_safe
from src.database import get_latest_sensor_reading, get_active_alerts_count
from src.config import config
from dashboard.components.cards import (
    render_metric_card,
    render_header_banner,
    render_sensor_availability_strip,
    render_motor_status_card
)
from dashboard.components.charts import create_sensor_trend_chart


def format_timestamp_local(ts_str: Optional[str]) -> str:
    """Formats an ISO UTC timestamp string into local time (HH:MM:SS) in Asia/Kolkata timezone."""
    if not ts_str:
        return "—"
    dt = parse_timestamp_safe(ts_str)
    if not dt:
        return "—"
    return dt.astimezone().strftime("%H:%M:%S")


def render():
    # Live Control Bar
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])
    with ctrl_col1:
        auto_refresh_enabled = st.toggle("⚡ Real-Time Streaming Sync (1.5s)", value=True, help="Automatically refreshes live telemetry plots every 1.5 seconds.")
    with ctrl_col2:
        window_selection = st.selectbox("Historical Trend Window", ["1 minute", "5 minutes", "15 minutes", "60 minutes"], index=1)
        window_minutes = int(window_selection.split()[0])
    with ctrl_col3:
        if st.button("🔄 Manual Snapshot", use_container_width=True):
            st.rerun()

    if auto_refresh_enabled:
        @st.fragment(run_every="2s")
        def render_live_monitoring_fragment():
            _render_live_monitoring_content(window_minutes=window_minutes)
        render_live_monitoring_fragment()
    else:
        _render_live_monitoring_content(window_minutes=window_minutes)


def _render_live_monitoring_content(window_minutes: int = 5):
    """Inner fragment view for high-frequency live monitoring."""
    # 1. Fetch live connection and freshest reading directly from SQLite
    conn_status, secs_ago, conn_detail = live_monitor.get_connection_status("esp32-machine-01")
    latest = live_monitor.get_latest_reading("esp32-machine-01")
    sensors_info = live_monitor.get_sensor_availability(latest)

    local_ts = format_timestamp_local(latest.get("received_at") if latest else None)
    uptime_str = sensors_info["uptime"]

    # 2. Header Banner
    render_header_banner(
        page_title="Live Hardware Telemetry Gateway",
        page_description="ESP32 Wi-Fi streaming receiver, real-time bus diagnostics, and live buffer monitoring.",
        status_label=conn_status,
        last_updated=f"{local_ts} ({secs_ago:.1f}s ago)" if secs_ago is not None else "No Telemetry",
        uptime_str=uptime_str
    )

    # 3. Sensor Availability Diagnostics Strip
    render_sensor_availability_strip(
        ds18b20_label=sensors_info["ds18b20"]["label"],
        imu_label=sensors_info["imu"]["label"],
        bus_status=sensors_info["bus_status"],
        ds18b20_ok=sensors_info["ds18b20"]["connected"],
        imu_ok=sensors_info["imu"]["connected"]
    )

    # 4. Telemetry Link Status Cards
    st.markdown("<div class='section-header'>Hardware Node Link Status</div>", unsafe_allow_html=True)
    sc1, sc2, sc3, sc4 = st.columns(4)

    with sc1:
        render_metric_card(
            title="Link Status",
            value=conn_status,
            unit="",
            footer=conn_detail,
            status_color="#16A34A" if conn_status == "LIVE" else ("#D97706" if conn_status == "STALE" else "#64748B")
        )
    with sc2:
        render_metric_card(
            title="Last Packet Latency",
            value=f"{secs_ago:.1f}" if secs_ago is not None else "N/A",
            unit="s ago",
            footer="Heartbeat timeout: 10s"
        )
    with sc3:
        status_val = latest.get("status", "NO_SIGNAL") if latest else "NO_SIGNAL"
        render_metric_card(
            title="Sensor Bus Diagnosis",
            value=status_val,
            unit="",
            footer="Microcontroller bus status",
            status_color="#16A34A" if status_val == "OK" else "#DC2626"
        )
    with sc4:
        is_anom = latest.get("is_anomaly", 0) == 1 if latest else False
        render_metric_card(
            title="Live ML Anomaly Flag",
            value="ANOMALY" if is_anom else "NORMAL",
            unit="",
            footer=f"Score: {latest.get('anomaly_score', 0.0):.2f}" if latest else "No inference",
            status_color="#DC2626" if is_anom else "#16A34A"
        )

    # 5. Live Physical Telemetry Readings (Individual Sensor Values)
    st.markdown("<div class='section-header'>Current Live Sensor Telemetry (Raw Measurements)</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    ext_temp = latest.get("external_temp_c") if latest else None
    imu_temp = latest.get("imu_temp_c") if latest else None
    vib_val = latest.get("vibration_indicator_g") if latest else None
    ip_addr = latest.get("ip_address", "Unknown") if latest else "N/A"

    with c1:
        render_metric_card(
            title="External DS18B20 Temp",
            value=f"{ext_temp:.2f}" if ext_temp is not None else "FAULT / DISCONNECTED",
            unit="°C" if ext_temp is not None else "",
            footer="Machine surface probe (GPIO 4)",
            status_color="#DC2626" if ext_temp is None else None
        )
    with c2:
        render_metric_card(
            title="MPU6500 Die Temp",
            value=f"{imu_temp:.2f}" if imu_temp is not None else "FAULT / OFFLINE",
            unit="°C" if imu_temp is not None else "",
            footer="Internal silicon junction (I2C)",
            status_color="#DC2626" if imu_temp is None else None
        )
    with c3:
        render_metric_card(
            title="Vibration Indicator",
            value=f"{vib_val:.4f}" if vib_val is not None else "UNAVAILABLE",
            unit="g" if vib_val is not None else "",
            footer="Euclidean residual from 1g (Indicative)",
            status_color="#DC2626" if vib_val is None else None
        )
    with c4:
        render_metric_card(
            title="Transmitter IP Address",
            value=ip_addr,
            unit="",
            footer="ESP32 local network client IP"
        )

    # 6. Motor Subsystem Hardware Card
    render_motor_status_card(is_live=(conn_status == "LIVE"), vibration_val=vib_val)

    # 7. Live Streaming Telemetry Plots
    st.markdown(f"<div class='section-header'>Streaming Telemetry Graphs ({window_minutes}-Minute Window)</div>", unsafe_allow_html=True)
    readings = live_monitor.get_window_readings(minutes=window_minutes, max_points=1200, device_id="esp32-machine-01")

    if readings:
        df_buf = pd.DataFrame(readings)

        # Plot 1: Temperatures & Vibration
        p1, p2 = st.columns(2)
        with p1:
            fig_temp = create_sensor_trend_chart(
                df_buf,
                y_columns=["external_temp_c", "imu_temp_c"],
                title=f"Real-Time Thermal Monitoring ({window_minutes}m)",
                y_unit="°C"
            )
            st.plotly_chart(fig_temp, use_container_width=True, key=f"live_p_temp_{window_minutes}")

        with p2:
            fig_vib = create_sensor_trend_chart(
                df_buf,
                y_columns=["vibration_indicator_g"],
                title=f"Dynamic Vibration Indicator ({window_minutes}m)",
                y_unit="g"
            )
            st.plotly_chart(fig_vib, use_container_width=True, key=f"live_p_vib_{window_minutes}")

        # Plot 2: Motion 6-DOF
        p3, p4 = st.columns(2)
        with p3:
            fig_acc = create_sensor_trend_chart(
                df_buf,
                y_columns=["ax_g", "ay_g", "az_g"],
                title=f"Tri-Axial Accelerometer ({window_minutes}m)",
                y_unit="g"
            )
            st.plotly_chart(fig_acc, use_container_width=True, key=f"live_p_acc_{window_minutes}")
        with p4:
            fig_gyr = create_sensor_trend_chart(
                df_buf,
                y_columns=["gyro_x_dps", "gyro_y_dps", "gyro_z_dps"],
                title=f"Tri-Axial Gyroscope Velocity ({window_minutes}m)",
                y_unit="dps"
            )
            st.plotly_chart(fig_gyr, use_container_width=True, key=f"live_p_gyr_{window_minutes}")

        # Recent Telemetry Table
        st.markdown("<div class='section-header'>Recent Packets (Last 15 Observations)</div>", unsafe_allow_html=True)
        recent_15 = df_buf.tail(15).iloc[::-1].copy()
        recent_15["local_time"] = recent_15["received_at"].apply(format_timestamp_local)
        cols_to_show = ["id", "local_time", "external_temp_c", "imu_temp_c", "vibration_indicator_g", "ax_g", "ay_g", "az_g", "status", "is_anomaly"]
        valid_cols = [c for c in cols_to_show if c in recent_15.columns]
        st.dataframe(recent_15[valid_cols], use_container_width=True, hide_index=True)

    else:
        st.warning("No live packets recorded in the selected window. Connect the ESP32 to Wi-Fi sending HTTP POST to `/api/readings`.")
