"""
Metric card and indicator components for the Streamlit dashboard.
"""

from typing import Optional, Any
import streamlit as st
from dashboard.styles import get_status_badge_html


def render_metric_card(
    title: str,
    value: Any,
    unit: str = "",
    footer: str = "",
    status_color: Optional[str] = None
) -> None:
    """Renders a styled metric KPI card with clean contrast."""
    val_str = "—" if value is None else str(value)
    color_style = f"style='color: {status_color};'" if status_color else ""

    card_html = f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value" {color_style}>
            {val_str}<span class="metric-unit">{unit}</span>
        </div>
        <div class="metric-footer">{footer}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_header_banner(
    page_title: str,
    page_description: str,
    status_label: Optional[str] = None,
    last_updated: Optional[str] = None,
    uptime_str: Optional[str] = None
) -> None:
    """Renders the dark navy branding banner with live status, latency, and uptime."""
    badge_html = get_status_badge_html(status_label) if status_label else '<span class="header-meta-pill">Industrial AI</span>'
    
    meta_pills = []
    if last_updated:
        meta_pills.append(f'<span class="header-meta-pill">🕒 Last Sync: {last_updated}</span>')
    if uptime_str:
        meta_pills.append(f'<span class="header-meta-pill">⚡ Node Uptime: {uptime_str}</span>')
    meta_html = " ".join(meta_pills)

    html = f"""
    <div class="brand-header-box">
        <div>
            <h1 class="brand-title">{page_title}</h1>
            <p class="brand-subtitle">{page_description}</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            {meta_html}
            {badge_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_sensor_availability_strip(
    ds18b20_label: str,
    imu_label: str,
    bus_status: str,
    ds18b20_ok: bool = True,
    imu_ok: bool = True
) -> None:
    """Renders a dedicated hardware sensor diagnostics strip."""
    ds_color = "#16A34A" if ds18b20_ok else "#DC2626"
    imu_color = "#16A34A" if imu_ok else "#DC2626"
    bus_color = "#16A34A" if bus_status.upper() == "OK" else "#D97706"

    html = f"""
    <div class="sensor-strip">
        <div>
            <span style="color: #64748B; font-weight: 600;">DS18B20 Ext Temp Probe:</span>
            <span style="color: {ds_color}; font-weight: 700; margin-left: 6px;">{ds18b20_label}</span>
        </div>
        <div>
            <span style="color: #64748B; font-weight: 600;">MPU6500 6-DOF IMU:</span>
            <span style="color: {imu_color}; font-weight: 700; margin-left: 6px;">{imu_label}</span>
        </div>
        <div>
            <span style="color: #64748B; font-weight: 600;">ESP32 Diagnostic Bus:</span>
            <span style="color: {bus_color}; font-weight: 700; margin-left: 6px;">{bus_status}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_motor_status_card(
    is_live: bool = True,
    vibration_val: Optional[float] = None
) -> None:
    """
    Renders an accurate, transparent motor status & hardware specification component.
    Accurately represents hardware capabilities:
    - Motor driver: L298N
    - Channel: Motor A (OUT1 / OUT2)
    - Logic inputs: IN1 (GPIO 26), IN2 (GPIO 27)
    - Hardware enable: Physical ENA 5V jumper installed (100% fixed speed)
    - Software limitations: No remote PWM speed or remote actuation allowed
    """
    status_text = "AUTONOMOUS FIRMWARE CYCLE (DEMO)" if is_live else "IDLE / NODE OFFLINE"
    status_bg = "#DCFCE7" if is_live else "#F1F5F9"
    status_fg = "#166534" if is_live else "#475569"

    vib_str = f"{vibration_val:.4f} g" if vibration_val is not None else "Sensor unavailable"

    html = f"""
    <div class="motor-info-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <div>
                <span style="font-weight: 700; font-size: 1.05rem; color: #0B192C;">⚙️ Motor Subsystem & Driver Status</span>
                <span style="margin-left: 10px; background: {status_bg}; color: {status_fg}; padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">
                    {status_text}
                </span>
            </div>
            <div style="font-size: 0.8rem; color: #64748B;">
                Mode: <b>Local Microcontroller Automation</b>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; font-size: 0.84rem; color: #334155;">
            <div style="background: #F8FAFC; padding: 10px 14px; border-radius: 6px; border: 1px solid #E2E8F0;">
                <div style="color: #64748B; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Motor Driver Module</div>
                <div style="font-weight: 700; color: #0F172A; margin-top: 2px;">L298N Dual H-Bridge</div>
                <div style="color: #64748B; font-size: 0.75rem;">Channel A (OUT1 / OUT2)</div>
            </div>
            <div style="background: #F8FAFC; padding: 10px 14px; border-radius: 6px; border: 1px solid #E2E8F0;">
                <div style="color: #64748B; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Control Logic Pins</div>
                <div style="font-weight: 700; color: #0F172A; margin-top: 2px;">IN1: GPIO 26 | IN2: GPIO 27</div>
                <div style="color: #64748B; font-size: 0.75rem;">Digital Direction Switching</div>
            </div>
            <div style="background: #F8FAFC; padding: 10px 14px; border-radius: 6px; border: 1px solid #E2E8F0;">
                <div style="color: #64748B; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Enable / Speed Control</div>
                <div style="font-weight: 700; color: #0F172A; margin-top: 2px;">ENA Jumper Installed</div>
                <div style="color: #D97706; font-size: 0.75rem;">Fixed full speed (No PWM wired)</div>
            </div>
            <div style="background: #F8FAFC; padding: 10px 14px; border-radius: 6px; border: 1px solid #E2E8F0;">
                <div style="color: #64748B; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Current Load Vibration</div>
                <div style="font-weight: 700; color: #0284C7; margin-top: 2px;">{vib_str}</div>
                <div style="color: #64748B; font-size: 0.75rem;">Indicative dynamic magnitude</div>
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 0.78rem; color: #64748B; line-height: 1.4;">
            ℹ️ <b>Operational Clarification:</b> The physical ESP32 firmware executes an autonomous local demonstration sequence (Forward 2s → Stop 2s → Reverse 2s → Stop 2s). Remote web/API start, stop, or reverse actuation is <b>intentionally disabled</b> because the current hardware wiring lacks feedback encoders, emergency limit switches, and secure hardware interlocks.
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
