"""
Anomaly and Alert History Page — AI Machine Health Monitor.
Persistent audit trail separating current active alerts, acknowledged/resolved alerts,
and historical events with operator resolution workflows.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

from src.database import get_alerts, update_alert_status, get_active_alerts_count
from src.live_monitor import parse_timestamp_safe
from src.config import config
from dashboard.components.cards import render_metric_card, render_header_banner


def format_timestamp_local(ts_str: Optional[str]) -> str:
    """Formats an ISO UTC timestamp string into local time in Asia/Kolkata timezone."""
    if not ts_str:
        return "—"
    dt = parse_timestamp_safe(ts_str)
    if not dt:
        return "—"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def render():
    render_header_banner(
        page_title="Anomaly & Alert Management Audit Trail",
        page_description="Persistent SQLite record of machine anomalies, threshold violations, operator acknowledgements, and resolutions.",
        status_label="Alert Audit"
    )

    # 1. Summary Metrics
    total_active = get_active_alerts_count()
    total_ack = len(get_alerts(status_filter="ACKNOWLEDGED", limit=500))
    total_res = len(get_alerts(status_filter="RESOLVED", limit=500))
    total_all = len(get_alerts(status_filter="ALL", limit=1000))

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card("Current Active Alerts", total_active, "unresolved", "Immediate operator attention", status_color="#DC2626" if total_active > 0 else "#16A34A")
    with k2:
        render_metric_card("Acknowledged", total_ack, "in review", "Under investigation", status_color="#D97706")
    with k3:
        render_metric_card("Resolved / Normalized", total_res, "closed", "Normal operations restored", status_color="#16A34A")
    with k4:
        render_metric_card("Total Audit Events", total_all, "records", "Stored in SQLite")

    # 2. Distinct Tabs for Alert Categories
    st.markdown("<div class='section-header'>Alert Lifecycle Records</div>", unsafe_allow_html=True)
    tab_active, tab_ack, tab_all = st.tabs([
        f"🚨 Current Active Alerts ({total_active})",
        f"⏳ Acknowledged & Under Review ({total_ack})",
        f"📜 Complete Historical Audit Log ({total_all})"
    ])

    with tab_active:
        active_list = get_alerts(status_filter="ACTIVE", limit=100)
        if active_list:
            df_act = pd.DataFrame(active_list)
            df_act["created_local"] = df_act["created_at"].apply(format_timestamp_local)
            df_act["last_seen_local"] = df_act["last_seen_at"].apply(format_timestamp_local) if "last_seen_at" in df_act.columns else df_act["created_local"]
            cols = ["id", "created_local", "last_seen_local", "occurrence_count", "alert_source", "sensor_or_feature", "observed_value", "threshold_or_rule", "severity"]
            valid_cols = [c for c in cols if c in df_act.columns]
            st.dataframe(df_act[valid_cols], use_container_width=True, hide_index=True)

            # Operator Action Form
            st.markdown("<div class='section-header'>Operator Action / Alert Resolution</div>", unsafe_allow_html=True)
            act_c1, act_c2, act_c3 = st.columns([1, 1.5, 2])

            with act_c1:
                active_ids = [a["id"] for a in active_list]
                selected_alert_id = st.selectbox("Select Alert #", active_ids, key="sel_act_alert")

            with act_c2:
                new_status = st.selectbox("Action to Apply", ["ACKNOWLEDGED", "RESOLVED"], key="sel_act_status")

            with act_c3:
                operator_notes = st.text_input("Operator Maintenance Notes", placeholder="e.g. Motor mount tightened; vibration nominal.", key="inp_act_notes")

            if st.button("Apply Status Update", type="primary"):
                ok = update_alert_status(selected_alert_id, new_status, operator_notes)
                if ok:
                    st.success(f"Alert #{selected_alert_id} marked as {new_status}!")
                    st.rerun()
                else:
                    st.error("Failed to update alert.")
        else:
            st.success("No active unresolved alerts! All machine parameters are within normal baseline thresholds.")

    with tab_ack:
        ack_list = get_alerts(status_filter="ACKNOWLEDGED", limit=100)
        if ack_list:
            df_ack = pd.DataFrame(ack_list)
            df_ack["created_local"] = df_ack["created_at"].apply(format_timestamp_local)
            df_ack["last_seen_local"] = df_ack["last_seen_at"].apply(format_timestamp_local) if "last_seen_at" in df_ack.columns else df_ack["created_local"]
            cols = ["id", "created_local", "last_seen_local", "occurrence_count", "alert_source", "sensor_or_feature", "observed_value", "threshold_or_rule", "severity", "resolution_notes"]
            valid_cols = [c for c in cols if c in df_ack.columns]
            st.dataframe(df_ack[valid_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No alerts are currently in acknowledged/under review status.")

    with tab_all:
        all_list = get_alerts(status_filter="ALL", limit=250)
        if all_list:
            df_all = pd.DataFrame(all_list)
            df_all["created_local"] = df_all["created_at"].apply(format_timestamp_local)
            df_all["last_seen_local"] = df_all["last_seen_at"].apply(format_timestamp_local) if "last_seen_at" in df_all.columns else df_all["created_local"]
            cols = ["id", "created_local", "last_seen_local", "occurrence_count", "alert_source", "sensor_or_feature", "observed_value", "threshold_or_rule", "severity", "status", "resolution_notes"]
            valid_cols = [c for c in cols if c in df_all.columns]
            st.dataframe(df_all[valid_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No alert records stored in SQLite.")

    # Threshold Policy Disclaimer
    st.markdown(f"""
    <div class="info-callout">
        <b>Active Baseline Threshold Rules:</b><br/>
        - <b>External Surface Temp (DS18B20):</b> Warning: &ge; {config.EXTERNAL_TEMP_WARN_C} °C | Critical: &ge; {config.EXTERNAL_TEMP_CRIT_C} °C<br/>
        - <b>IMU Silicon Die Temp (MPU6500):</b> Warning: &ge; {config.IMU_TEMP_WARN_C} °C | Critical: &ge; {config.IMU_TEMP_CRIT_C} °C<br/>
        - <b>Vibration Indicator Magnitude:</b> Warning: &ge; {config.VIBRATION_WARN_G} g | Critical: &ge; {config.VIBRATION_CRIT_G} g<br/>
        <i>Demonstration limits: Prototyping baseline rules. Always refer to machine OEM specifications.</i>
    </div>
    """, unsafe_allow_html=True)
