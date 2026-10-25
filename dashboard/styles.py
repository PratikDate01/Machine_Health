"""
UI/UX Design and CSS tokens for AI Machine Health Monitor.
High-contrast industrial aesthetic with professional dark navy navigation headers,
clean analytical surfaces, animated real-time status pulses, and hardware diagnostic styling.
"""

CUSTOM_CSS = """
<style>
    /* Main Background & Clean Industrial Typography */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Live Telemetry Animated Pulse */
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.7); }
        70% { box-shadow: 0 0 0 8px rgba(22, 163, 74, 0); }
        100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
    }
    @keyframes pulse-amber {
        0% { box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.7); }
        70% { box-shadow: 0 0 0 8px rgba(217, 119, 6, 0); }
        100% { box-shadow: 0 0 0 0 rgba(217, 119, 6, 0); }
    }
    .live-dot {
        width: 10px;
        height: 10px;
        background-color: #16A34A;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        vertical-align: middle;
        animation: pulse-green 1.6s infinite;
    }
    .stale-dot {
        width: 10px;
        height: 10px;
        background-color: #D97706;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        vertical-align: middle;
        animation: pulse-amber 1.6s infinite;
    }
    .offline-dot {
        width: 10px;
        height: 10px;
        background-color: #64748B;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* Top Navy Header Branding Box */
    .brand-header-box {
        background: linear-gradient(135deg, #0B192C 0%, #1E3E62 60%, #000000 100%);
        border: 1px solid #1E3E62;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 20px;
        color: #FFFFFF;
        box-shadow: 0 4px 12px -2px rgba(11, 25, 44, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .brand-title {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: #FFFFFF;
    }
    .brand-subtitle {
        font-size: 0.88rem;
        color: #94A3B8;
        margin: 4px 0 0 0;
        font-weight: 400;
    }
    .header-meta-pill {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #F1F5F9;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.80rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
    }

    /* Professional Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 12px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        box-shadow: 0 4px 10px 0 rgba(0, 0, 0, 0.08);
        border-color: #CBD5E1;
    }
    .metric-title {
        font-size: 0.80rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .metric-unit {
        font-size: 0.95rem;
        font-weight: 500;
        color: #64748B;
        margin-left: 4px;
    }
    .metric-footer {
        font-size: 0.75rem;
        color: #94A3B8;
        margin-top: 6px;
    }

    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.03em;
        text-align: center;
    }
    .status-live, .status-normal {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }
    .status-stale, .status-warning {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
    }
    .status-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
    }
    .status-offline {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }
    .status-insufficient {
        background-color: #E0F2FE;
        color: #075985;
        border: 1px solid #BAE6FD;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }

    /* Section Subheaders */
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0B192C;
        margin-top: 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 6px;
    }

    /* Sensor Availability Strip */
    .sensor-strip {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 0.85rem;
    }

    /* Clean Informational Callout */
    .info-callout {
        background-color: #F8FAFC;
        border-left: 4px solid #0284C7;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        font-size: 0.88rem;
        color: #334155;
        margin: 12px 0;
    }

    /* Motor Status Box */
    .motor-info-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 14px 0;
    }
    .motor-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
"""


def get_status_badge_html(status: str) -> str:
    """Generates an accessible, stylized HTML badge with live pulse indicators."""
    status_clean = str(status).strip().upper()
    if status_clean in ["LIVE", "ONLINE", "NORMAL"]:
        cls = "status-live"
        dot = '<span class="live-dot"></span>'
    elif status_clean in ["STALE", "WARNING"]:
        cls = "status-stale"
        dot = '<span class="stale-dot"></span>'
    elif status_clean == "CRITICAL":
        cls = "status-critical"
        dot = '<span style="color: #991B1B; font-weight: bold; margin-right: 5px;">✖</span>'
    elif status_clean == "OFFLINE":
        cls = "status-offline"
        dot = '<span class="offline-dot"></span>'
    else:
        cls = "status-insufficient"
        dot = '<span style="color: #075985; font-weight: bold; margin-right: 5px;">◌</span>'

    return f'<span class="status-badge {cls}">{dot}{status_clean}</span>'
