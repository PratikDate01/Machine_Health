"""
Sidebar navigation and status indicator component.
Directly synchronizes with SQLite to display live node telemetry across processes.
"""

import streamlit as st
from src.live_monitor import live_monitor
from src.database import get_readings_count, get_active_alerts_count
from dashboard.styles import get_status_badge_html


PAGES = [
    "1. Overview Dashboard",
    "2. Live Machine Monitoring",
    "3. AI Anomaly Detection",
    "4. Sensor Analytics",
    "5. Dataset Upload & Analysis",
    "6. Anomaly & Alert History",
    "7. Reports & Export",
    "8. Model Information",
    "9. Hardware & Connection Status",
    "10. Project Information / About"
]


def render_sidebar() -> str:
    """
    Renders the persistent sidebar with brand logo, navigation options,
    and a live hardware status widget directly synchronized with SQLite.
    """
    with st.sidebar:
        # Neutral Project Branding
        st.markdown("""
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 16px;">
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; color: #0284C7; font-weight: 700;">
                Industrial IoT Platform
            </div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #0B192C; margin-top: 2px;">
                AI Machine Health Monitor
            </div>
            <div style="font-size: 0.78rem; color: #64748B;">
                Predictive Maintenance & Telemetry
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation Selector
        st.markdown("<div style='font-size: 0.8rem; font-weight: 600; color: #475569; text-transform: uppercase; margin-bottom: 6px;'>Navigation</div>", unsafe_allow_html=True)
        selected_page = st.radio(
            "Navigation",
            PAGES,
            label_visibility="collapsed"
        )

        st.markdown("<hr style='margin: 16px 0; border-color: #E2E8F0;'/>", unsafe_allow_html=True)

        # Live Hardware Heartbeat Widget (Queried fresh from SQLite)
        conn_status, secs_ago, detail = live_monitor.get_connection_status("esp32-machine-01")
        total_readings = get_readings_count()
        active_alerts = get_active_alerts_count("esp32-machine-01")

        st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: #475569; text-transform: uppercase;'>Hardware Node Link</div>", unsafe_allow_html=True)

        if conn_status == "LIVE":
            status_indicator = '<span class="status-badge status-live"><span class="live-dot"></span>LIVE</span>'
        elif conn_status == "STALE":
            status_indicator = '<span class="status-badge status-stale"><span class="stale-dot"></span>STALE</span>'
        else:
            status_indicator = '<span class="status-badge status-offline"><span class="offline-dot"></span>OFFLINE</span>'

        st.markdown(f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-top: 8px; font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #64748B; font-weight: 500;">Link State:</span>
                <span>{status_indicator}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #64748B;">Last Packet:</span>
                <span style="color: #0F172A; font-weight: 600;">{f"{secs_ago:.1f}s ago" if secs_ago is not None else "No signal"}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #64748B;">Total Readings:</span>
                <span style="color: #0F172A; font-weight: 600;">{total_readings:,}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #64748B;">Active Alerts:</span>
                <span style="color: {'#DC2626' if active_alerts > 0 else '#16A34A'}; font-weight: 700;">{active_alerts}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding-top: 4px; border-top: 1px dashed #E2E8F0;">
                <span style="color: #64748B;">Motor Load:</span>
                <span style="color: #0284C7; font-weight: 600;">L298N (Auto-Cycle)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Footer notes
        st.markdown("""
        <div style="margin-top: 24px; font-size: 0.72rem; color: #94A3B8; text-align: center;">
            AI Machine Health Monitor &copy; 2026<br/>
            Industrial IoT Predictive Maintenance System
        </div>
        """, unsafe_allow_html=True)

        return selected_page
