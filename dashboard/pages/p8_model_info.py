"""
Model Information Page — AI Machine Health Monitor.
Explains the Isolation Forest algorithm, lists model registry entries, and manages saved model artifacts.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd

from src.database import get_models_metadata
from src.anomaly_detection import IsolationForestDetector
from src.live_monitor import live_monitor
from dashboard.components.cards import render_header_banner


def render():
    render_header_banner(
        page_title="Machine Learning Model Registry & Architecture",
        page_description="Inspect registered Isolation Forest models, hyperparameter configurations, and algorithmic principles.",
        status_label="Model Registry"
    )

    # 1. Registered Models in SQLite
    st.markdown("<div class='section-header'>1. Persistent Model Registry</div>", unsafe_allow_html=True)
    models = get_models_metadata()

    active_detector = live_monitor.get_active_model()
    active_name = active_detector.model_name if active_detector else "None"

    st.write(f"Currently active live scoring model: **{active_name}**")

    if models:
        for m in models:
            is_active = (m["model_name"] == active_name)
            card_border = "#0284C7" if is_active else "#E2E8F0"
            badge = '<span style="background: #0284C7; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">ACTIVE IN LIVE GATEWAY</span>' if is_active else ''

            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid {card_border}; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; font-size: 1.05rem; color: #0F172A;">{m['model_name']} {badge}</div>
                    <div style="font-size: 0.8rem; color: #64748B;">Trained: {m['trained_at'][:19].replace('T', ' ')} UTC</div>
                </div>
                <div style="margin-top: 8px; font-size: 0.85rem; color: #334155;">
                    <b>Algorithm:</b> {m['model_type']} | <b>Contamination:</b> {m['contamination']} | <b>Training Samples:</b> {m['n_samples']:,}<br/>
                    <b>Input Features:</b> <code>{', '.join(m['features'])}</code><br/>
                    <b>Artifact Location:</b> <code>{m['file_path']}</code><br/>
                    <b>Notes:</b> {m.get('notes', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Option to load this model as active
            col_act1, col_act2 = st.columns([1, 4])
            with col_act1:
                if st.button(f"Activate '{m['model_name']}'", key=f"btn_act_{m['id']}"):
                    try:
                        loaded_det = IsolationForestDetector.load(Path(m["file_path"]))
                        live_monitor.set_active_model(loaded_det)
                        st.success(f"Model '{m['model_name']}' successfully activated for live hardware scoring!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load model: {str(e)}")
    else:
        st.info("No models registered in database yet. Train a model in the 'AI Anomaly Detection' tab and click 'Save Model to Registry'.")

    # 2. Technical Architecture & Algorithmic Principles
    st.markdown("<div class='section-header'>2. Isolation Forest Algorithmic Principles</div>", unsafe_allow_html=True)

    st.markdown("""
    ### Why Isolation Forest for Industrial Machine Telemetry?
    Traditional anomaly detection often models normal data points and identifies points that do not conform. **Isolation Forest** (Liu et al., 2008) inverts this paradigm by explicitly isolating anomalies:

    1. **Random Recursive Partitioning:**
       - An ensemble of Isolation Trees (*iTrees*) is constructed by randomly selecting a feature and then randomly selecting a split value between the minimum and maximum values of that feature.
    2. **Fewer Splits for Anomalies:**
       - In rotating machinery telemetry, abnormal conditions (such as high thermal spikes or bearing vibration bursts) are structurally isolated in feature space compared to dense clusters of nominal operating states.
       - Consequently, anomalies require significantly fewer tree splits (shorter path lengths from the root) to be isolated.
    3. **Unsupervised Advantage:**
       - Industrial machines spend 99%+ of their operating life in normal states. True mechanical failure runs are rare, expensive, and dangerous to induce. Isolation Forest operates entirely unsupervised without requiring balanced defect labels.

    ### Key Hyperparameters
    - **`contamination`:** The estimated proportion of anomalous observations in the training baseline. In this application, it defaults to `0.05` (5%) and is fully user-configurable.
    - **`n_estimators`:** The number of isolation trees in the ensemble (standard default is `100`). Higher values increase score stability with minimal computational penalty.
    - **`random_state`:** Fixes the pseudo-random seed to guarantee reproducibility across repeated analysis runs.

    ### Engineering Disclaimers & Model Scope
    > **Crucial Engineering Reality:**  
    > Anomaly detection answers the question: *"Does this sensor observation deviate statistically from established normal baselines?"*  
    > It does **NOT** by itself diagnose the exact physical root cause (e.g. stator winding insulation breakdown vs. rotor shaft eccentricity) nor does it predict the exact Remaining Useful Life (RUL) date. Causal diagnosis requires physics-of-failure modeling, acoustic spectral decomposition, and domain-expert validation.
    """)
