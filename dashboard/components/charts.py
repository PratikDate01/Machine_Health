"""
Plotly visualization builders styled for an industrial analytics aesthetic.
Features gap-break detection (no diagonal lines across disconnects),
missing-value isolation (no fake zeros), local timestamp formatting, and sensible axis scales.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


# Corporate styling palette
COLOR_PRIMARY = "#0284C7"    # Sky Blue
COLOR_TEAL = "#0D9488"       # Teal
COLOR_INDIGO = "#6366F1"     # Indigo
COLOR_AMBER = "#D97706"      # Amber
COLOR_RED = "#DC2626"        # Red (Anomalies)
COLOR_SLATE = "#64748B"      # Slate Gray
COLOR_GRID = "#F1F5F9"       # Very light gray gridline


def get_base_layout(title: str, x_title: str = "Local Time", y_title: str = "Value") -> Dict[str, Any]:
    """Generates standard layout dictionary for clean, responsive Plotly charts."""
    return dict(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=14, color="#1E293B", family="sans-serif")
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=20, t=45, b=40),
        hovermode="x unified",
        xaxis=dict(
            title=dict(text=x_title, font=dict(size=11, color="#64748B")),
            gridcolor=COLOR_GRID,
            linecolor="#E2E8F0",
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=11, color="#64748B")),
            gridcolor=COLOR_GRID,
            linecolor="#E2E8F0",
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#475569")
        )
    )


def sanitize_chart_dataframe(df: pd.DataFrame, max_gap_seconds: float = 5.0) -> pd.DataFrame:
    """
    Sorts chronologically, parses timestamps to local timezone, and inserts
    gap break records (None values) whenever the elapsed time between consecutive
    readings exceeds max_gap_seconds. This completely prevents long diagonal lines.
    """
    if df.empty:
        return df

    clean_df = df.copy()

    # Sort strictly by id or received_at to prevent backwards jumps from ESP32 reboots
    if "id" in clean_df.columns:
        clean_df = clean_df.sort_values(by="id", ascending=True)

    # Convert UTC timestamps to local timezone
    if "received_at" in clean_df.columns:
        parsed_dt = []
        for ts in clean_df["received_at"]:
            try:
                dt = datetime.fromisoformat(str(ts))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                parsed_dt.append(dt.astimezone())
            except Exception:
                parsed_dt.append(None)
        clean_df["local_time"] = parsed_dt

        # Remove rows without valid timestamps
        clean_df = clean_df.dropna(subset=["local_time"]).reset_index(drop=True)

        # Gap detection: insert None rows where gap > max_gap_seconds
        if len(clean_df) > 1:
            rows_with_breaks = []
            for i in range(len(clean_df)):
                rows_with_breaks.append(clean_df.iloc[i].to_dict())
                if i < len(clean_df) - 1:
                    t1 = clean_df.iloc[i]["local_time"]
                    t2 = clean_df.iloc[i + 1]["local_time"]
                    if (t2 - t1).total_seconds() > max_gap_seconds:
                        # Insert gap marker with NaN/None values
                        gap_row = {col: None for col in clean_df.columns}
                        gap_row["local_time"] = t1 + timedelta(seconds=1)
                        rows_with_breaks.append(gap_row)
            clean_df = pd.DataFrame(rows_with_breaks)

    return clean_df


def create_sensor_trend_chart(
    df: pd.DataFrame,
    y_columns: List[str],
    title: str,
    x_column: Optional[str] = None,
    anomaly_col: Optional[str] = "is_anomaly",
    y_unit: str = ""
) -> go.Figure:
    """
    Renders multi-line sensor trend chart with gap break support and anomaly highlights.
    Never plots fake zeros for missing/faulty sensor readings.
    """
    fig = go.Figure()

    if df.empty:
        fig.update_layout(get_base_layout(title, y_title=f"Measurement ({y_unit})" if y_unit else "Value"))
        fig.add_annotation(text="No telemetry recorded in selected window", showarrow=False, font=dict(color="#64748B", size=13))
        return fig

    # Sanitize dataframe with gap break insertion
    clean_df = sanitize_chart_dataframe(df)

    # Determine x values
    if "local_time" in clean_df.columns:
        x_vals = clean_df["local_time"]
        x_label = "Local Time"
    elif x_column and x_column in clean_df.columns:
        x_vals = clean_df[x_column]
        x_label = x_column
    else:
        x_vals = clean_df.index
        x_label = "Observation Index"

    palette = [COLOR_PRIMARY, COLOR_TEAL, COLOR_INDIGO, COLOR_AMBER, COLOR_SLATE]

    for idx, col in enumerate(y_columns):
        if col in clean_df.columns:
            color = palette[idx % len(palette)]
            clean_name = col.replace("_", " ").title()

            # Ensure numeric type, converting non-numeric or error flags (-999, etc.) to NaN
            y_series = pd.to_numeric(clean_df[col], errors='coerce')
            y_series = y_series.apply(lambda val: None if (val is None or (isinstance(val, (int, float)) and val <= -500)) else val)

            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_series,
                mode="lines",
                name=f"{clean_name} ({y_unit})" if y_unit else clean_name,
                line=dict(color=color, width=2),
                connectgaps=False,  # Essential: prevents long diagonal bridging across gaps
                hovertemplate=f"<b>{clean_name}</b>: %{{y:.2f}} {y_unit}<extra></extra>"
            ))

    # Overlay anomaly flags if present
    if anomaly_col and anomaly_col in clean_df.columns and len(y_columns) > 0:
        target_y = y_columns[0]
        anomaly_mask = clean_df[anomaly_col].astype(str).str.upper().str.contains("1|ANOMAL|-1")
        if anomaly_mask.any():
            fig.add_trace(go.Scatter(
                x=x_vals[anomaly_mask],
                y=clean_df[target_y][anomaly_mask],
                mode="markers",
                name="Anomaly Detected",
                marker=dict(color=COLOR_RED, size=8, symbol="circle", line=dict(color="#FFFFFF", width=1.5)),
                hovertemplate="<b>ANOMALY DETECTED</b><br>Value: %{y:.2f}<extra></extra>"
            ))

    layout = get_base_layout(title, x_title=x_label, y_title=f"Measurement ({y_unit})" if y_unit else "Value")
    fig.update_layout(layout)
    return fig


def create_correlation_heatmap(df: pd.DataFrame, features: List[str]) -> go.Figure:
    """Renders a correlation matrix heatmap for numeric features."""
    valid_features = [f for f in features if f in df.columns and pd.api.types.is_numeric_dtype(df[f])]
    if len(valid_features) < 2:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient numeric variables for correlation matrix", showarrow=False)
        return fig

    corr = df[valid_features].corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="Blues",
        title="Feature Correlation Matrix"
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(color="#1E293B", size=11)
    )
    return fig


def create_normal_vs_anomaly_distribution(
    df: pd.DataFrame,
    feature: str,
    label_col: str = "anomaly_label"
) -> go.Figure:
    """Compares distribution of a feature between Normal and Anomalous observations."""
    if feature not in df.columns or label_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Selected variable or label not found", showarrow=False)
        return fig

    fig = px.histogram(
        df,
        x=feature,
        color=label_col,
        barmode="overlay",
        marginal="box",
        color_discrete_map={"NORMAL": COLOR_PRIMARY, "ANOMALOUS": COLOR_RED, "0": COLOR_PRIMARY, "1": COLOR_RED},
        title=f"Distribution Comparison: {feature.replace('_', ' ').title()}"
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(title="Condition", orientation="h", y=1.05, x=1)
    )
    return fig
