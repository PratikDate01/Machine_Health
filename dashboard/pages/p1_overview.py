"""
Overview Dashboard Page — AI Machine Health Monitor.
Real-time IoT overview featuring automatic fragment-based refresh (1–2s),
live hardware heartbeat, separate sensor availability, and rolling sensor trends.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

from src.live_monitor import live_monitor, parse_timestamp_safe
from src.database import get_alerts, get_active_alerts_count
from src.alerts import compute_machine_health_status
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
    # User controls for auto-refresh and time window
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])
    with ctrl_col1:
        auto_refresh_enabled = st.toggle("⚡ Real-Time Live Sync (2s)", value=True, help="Enables automatic 2-second background refresh via Streamlit fragments.")
    with ctrl_col2:
        selected_window = st.selectbox("Rolling Trend Window", ["1 minute", "5 minutes", "15 minutes", "60 minutes"], index=1)
        window_minutes = int(selected_window.split()[0])
    with ctrl_col3:
        if st.button("🔄 Force Manual Refresh", use_container_width=True):
            st.rerun()

    # Define the real-time auto-updating fragment
    if auto_refresh_enabled:
        @st.fragment(run_every="2s")
        def render_live_overview_fragment():
            _render_overview_content(window_minutes=window_minutes)
        render_live_overview_fragment()
    else:
        _render_overview_content(window_minutes=window_minutes)


def _render_overview_content(window_minutes: int = 5):
    """Core view renderer for Overview metrics and charts."""
    # 1. Fetch live connection and freshest reading directly from SQLite
    conn_status, secs_ago, conn_detail = live_monitor.get_connection_status("esp32-machine-01")
    latest_reading = live_monitor.get_latest_reading("esp32-machine-01")
    sensors_info = live_monitor.get_sensor_availability(latest_reading)

    # 2. Determine machine health status & indicative score
    is_anomaly = bool(latest_reading.get("is_anomaly")) if latest_reading else False
    health_status, status_reason, health_score, deductions = compute_machine_health_status(
        latest_reading,
        device_status=conn_status,
        is_ml_anomaly=is_anomaly
    )

    # Formatted timestamps
    local_ts = format_timestamp_local(latest_reading.get("received_at") if latest_reading else None)
    uptime_str = sensors_info["uptime"]

    # 3. Header Banner (Dark Navy Surface with Live Pulse Badge)
    render_header_banner(
        page_title="Machine Operational Overview",
        page_description="Real-time predictive telemetry, sensor trends, and anomaly indicators.",
        status_label=conn_status,
        last_updated=f"{local_ts} ({secs_ago:.1f}s ago)" if secs_ago is not None else "No Telemetry",
        uptime_str=uptime_str
    )

    # 4. Sensor Availability Diagnostics Strip
    render_sensor_availability_strip(
        ds18b20_label=sensors_info["ds18b20"]["label"],
        imu_label=sensors_info["imu"]["label"],
        bus_status=sensors_info["bus_status"],
        ds18b20_ok=sensors_info["ds18b20"]["connected"],
        imu_ok=sensors_info["imu"]["connected"]
    )

    # 5. Primary KPI Metrics (Row 1)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ext_temp = latest_reading.get('external_temp_c') if latest_reading else None
        render_metric_card(
            title="External Temp (DS18B20)",
            value=f"{ext_temp:.2f}" if ext_temp is not None else "FAULT",
            unit="°C" if ext_temp is not None else "",
            footer=f"Warn: >{config.EXTERNAL_TEMP_WARN_C}°C | Crit: >{config.EXTERNAL_TEMP_CRIT_C}°C",
            status_color="#DC2626" if ext_temp is None or (ext_temp >= config.EXTERNAL_TEMP_CRIT_C) else ("#D97706" if ext_temp >= config.EXTERNAL_TEMP_WARN_C else None)
        )

    with col2:
        imu_temp = latest_reading.get('imu_temp_c') if latest_reading else None
        render_metric_card(
            title="IMU Internal Temp",
            value=f"{imu_temp:.2f}" if imu_temp is not None else "FAULT",
            unit="°C" if imu_temp is not None else "",
            footer="MPU6500 silicon die temperature",
            status_color="#DC2626" if imu_temp is not None and imu_temp >= config.IMU_TEMP_CRIT_C else ("#D97706" if imu_temp is not None and imu_temp >= config.IMU_TEMP_WARN_C else None)
        )

    with col3:
        vib = latest_reading.get('vibration_indicator_g') if latest_reading else None
        render_metric_card(
            title="Vibration Indicator",
            value=f"{vib:.4f}" if vib is not None else "—",
            unit="g" if vib is not None else "",
            footer=f"Warn: >{config.VIBRATION_WARN_G}g | Crit: >{config.VIBRATION_CRIT_G}g (Indicative)",
            status_color="#DC2626" if vib is not None and vib >= config.VIBRATION_CRIT_G else ("#D97706" if vib is not None and vib >= config.VIBRATION_WARN_G else None)
        )

    with col4:
        score_color = "#16A34A" if health_score >= 80 else ("#D97706" if health_score >= 50 else "#DC2626")
        render_metric_card(
            title="Indicative Health Score",
            value=f"{health_score}" if conn_status != "OFFLINE" else "OFFLINE",
            unit="/ 100" if conn_status != "OFFLINE" else "",
            footer="Transparent heuristic index",
            status_color=score_color
        )

    # 6. Secondary KPI Metrics (Row 2)
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        render_metric_card(
            title="Link State",
            value=conn_status,
            unit="",
            footer=f"Last packet {secs_ago:.1f}s ago" if secs_ago is not None else "No data received",
            status_color="#16A34A" if conn_status == "LIVE" else ("#D97706" if conn_status == "STALE" else "#64748B")
        )

    with col6:
        active_model = live_monitor.get_active_model()
        render_metric_card(
            title="Active ML Model",
            value=active_model.model_name if active_model else "Baseline Ready",
            unit="",
            footer="Isolation Forest Engine"
        )

    with col7:
        active_alerts_count = get_active_alerts_count("esp32-machine-01")
        render_metric_card(
            title="Current Active Alerts",
            value=active_alerts_count,
            unit="active",
            footer="Requires investigation",
            status_color="#DC2626" if active_alerts_count > 0 else "#16A34A"
        )

    with col8:
        render_metric_card(
            title="Microcontroller Uptime",
            value=uptime_str,
            unit="",
            footer=f"Packet local time: {local_ts}"
        )

    # 7. Real-Time 6-DOF Motion Vector Summary
    ax = latest_reading.get("ax_g") if latest_reading else None
    ay = latest_reading.get("ay_g") if latest_reading else None
    az = latest_reading.get("az_g") if latest_reading else None
    gx = latest_reading.get("gyro_x_dps") if latest_reading else None
    gy = latest_reading.get("gyro_y_dps") if latest_reading else None
    gz = latest_reading.get("gyro_z_dps") if latest_reading else None

    st.markdown("<div class='section-header'>Real-Time 6-DOF Motion Telemetry</div>", unsafe_allow_html=True)
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1:
        render_metric_card("Accel X", f"{ax:+.3f}" if ax is not None else "N/A", "g", "Lateral axis")
    with m_col2:
        render_metric_card("Accel Y", f"{ay:+.3f}" if ay is not None else "N/A", "g", "Longitudinal axis")
    with m_col3:
        render_metric_card("Accel Z", f"{az:+.3f}" if az is not None else "N/A", "g", "Vertical / 1g baseline")
    with m_col4:
        render_metric_card("Gyro X", f"{gx:+.1f}" if gx is not None else "N/A", "dps", "Roll velocity")
    with m_col5:
        render_metric_card("Gyro Y", f"{gy:+.1f}" if gy is not None else "N/A", "dps", "Pitch velocity")
    with m_col6:
        render_metric_card("Gyro Z", f"{gz:+.1f}" if gz is not None else "N/A", "dps", "Yaw velocity")

    # 8. Motor Hardware Subsystem Card
    render_motor_status_card(is_live=(conn_status == "LIVE"), vibration_val=vib)

    # Health Condition & Score Deductions Callout
    deductions_txt = " • ".join(deductions)
    st.markdown(f"""
    <div class="info-callout">
        <b>Condition Assessment:</b> {status_reason}<br/>
        <span style="font-size: 0.8rem; color: #64748B;">
            <b>Health Score Breakdown:</b> Base (100) | {deductions_txt}.  
            <i>Note: Heuristic composite score for demonstration. Uncalibrated vibration indicators are relative magnitudes, not certified industrial ISO 10816 measurements.</i>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 9. Rolling Sensor Trends (Direct SQLite Window Query)
    st.markdown(f"<div class='section-header'>Real-Time Sensor Trends ({window_minutes}-Minute Window)</div>", unsafe_allow_html=True)
    readings = live_monitor.get_window_readings(minutes=window_minutes, max_points=1200, device_id="esp32-machine-01")

    if readings:
        df_trends = pd.DataFrame(readings)

        tab1, tab2, tab3 = st.tabs(["Thermal & Vibration", "3-Axis Acceleration", "3-Axis Gyroscope"])

        with tab1:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_temp = create_sensor_trend_chart(
                    df_trends,
                    y_columns=["external_temp_c", "imu_temp_c"],
                    title=f"External vs IMU Temperature ({window_minutes}m)",
                    y_unit="°C"
                )
                st.plotly_chart(fig_temp, use_container_width=True, key=f"fig_temp_{window_minutes}")
            with col_t2:
                fig_vib = create_sensor_trend_chart(
                    df_trends,
                    y_columns=["vibration_indicator_g"],
                    title=f"Calculated Vibration Indicator ({window_minutes}m)",
                    y_unit="g"
                )
                st.plotly_chart(fig_vib, use_container_width=True, key=f"fig_vib_{window_minutes}")

        with tab2:
            fig_accel = create_sensor_trend_chart(
                df_trends,
                y_columns=["ax_g", "ay_g", "az_g"],
                title=f"Tri-Axial Acceleration ({window_minutes}m)",
                y_unit="g"
            )
            st.plotly_chart(fig_accel, use_container_width=True, key=f"fig_acc_{window_minutes}")

        with tab3:
            fig_gyro = create_sensor_trend_chart(
                df_trends,
                y_columns=["gyro_x_dps", "gyro_y_dps", "gyro_z_dps"],
                title=f"Tri-Axial Gyroscope Velocity ({window_minutes}m)",
                y_unit="dps"
            )
            st.plotly_chart(fig_gyro, use_container_width=True, key=f"fig_gyr_{window_minutes}")

    else:
        st.info("No sensor telemetry recorded in the selected window. Connect ESP32 to Wi-Fi sending HTTP POST to `/api/readings`.")

    # 10. Current Active Alerts Table (With Deduplication Occurrences & Timestamps)
    st.markdown("<div class='section-header'>Current Active Machine Alerts</div>", unsafe_allow_html=True)
    active_alerts = get_alerts(status_filter="ACTIVE", limit=10)

    if active_alerts:
        alerts_df = pd.DataFrame(active_alerts)
        alerts_df["first_seen"] = alerts_df["created_at"].apply(format_timestamp_local)
        if "last_seen_at" in alerts_df.columns:
            alerts_df["last_seen"] = alerts_df["last_seen_at"].apply(format_timestamp_local)
        else:
            alerts_df["last_seen"] = alerts_df["first_seen"]
        
        display_cols = ["id", "first_seen", "last_seen", "occurrence_count", "alert_source", "sensor_or_feature", "observed_value", "threshold_or_rule", "severity", "status"]
        valid_cols = [c for c in display_cols if c in alerts_df.columns]
        st.dataframe(alerts_df[valid_cols], use_container_width=True, hide_index=True)
    else:
        st.success("All sensor parameters are currently within normal baseline thresholds. No active warnings.")
