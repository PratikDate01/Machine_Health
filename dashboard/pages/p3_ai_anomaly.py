"""
AI Anomaly Detection Page — AI Machine Health Monitor.
Isolation Forest training pipeline, parameter configuration, interactive evaluation, and model deployment.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.anomaly_detection import IsolationForestDetector, evaluate_anomalies_if_ground_truth
from src.feature_engineering import filter_usable_features
from src.data_loader import load_csv
from src.config import config
from src.live_monitor import live_monitor
from dashboard.components.cards import render_metric_card, render_header_banner
from dashboard.components.charts import create_sensor_trend_chart, create_normal_vs_anomaly_distribution


def render():
    render_header_banner(
        page_title="AI Machine Learning Anomaly Detection",
        page_description="Unsupervised Isolation Forest training pipeline, multivariate pattern analysis, and real-time model deployment.",
        status_label="Isolation Forest"
    )

    # 1. Dataset Selection
    st.markdown("<div class='section-header'>1. Select Training Data Source</div>", unsafe_allow_html=True)

    data_source_options = [
        "Pre-packaged ESP32 Hardware Run (Realistic baseline with bearing & thermal anomalies)",
        "Pre-packaged NASA C-MAPSS Turbofan Run (Run-to-failure degradation)",
        "Custom Uploaded Dataset (From Session Cache)"
    ]

    selected_source = st.selectbox("Data Source", data_source_options)

    df: Optional[pd.DataFrame] = None
    source_name = ""

    if "ESP32" in selected_source:
        source_path = config.RAW_DATA_DIR / "sample_esp32_hardware_run.csv"
        df = load_csv(source_path)
        source_name = "ESP32 Hardware Run Baseline"
    elif "NASA" in selected_source:
        source_path = config.RAW_DATA_DIR / "nasa_cmapss_sample.csv"
        df = load_csv(source_path)
        source_name = "NASA C-MAPSS FD001 Turbofan Dataset"
    else:
        if "uploaded_df" in st.session_state and st.session_state["uploaded_df"] is not None:
            df = st.session_state["uploaded_df"].copy()
            source_name = st.session_state.get("uploaded_filename", "Custom Upload")
        else:
            st.warning("No custom dataset found in session. Please upload a CSV first in the 'Dataset Upload & Analysis' tab or select a pre-packaged dataset.")
            return

    st.write(f"Loaded **{len(df):,}** observations from **{source_name}**.")

    # 2. Feature Selection & Model Parameters
    st.markdown("<div class='section-header'>2. Feature Selection & Hyperparameters</div>", unsafe_allow_html=True)

    usable_cols = filter_usable_features(df)
    if not usable_cols:
        st.error("No valid numeric features found in the chosen dataset.")
        return

    col_cfg1, col_cfg2 = st.columns([2, 1])

    with col_cfg1:
        # Default suggested features
        default_features = [c for c in usable_cols if any(k in c.lower() for k in ["temp", "vib", "accel", "gyro", "sensor"])][:5]
        if not default_features:
            default_features = usable_cols[:4]

        selected_features = st.multiselect(
            "Select Numeric Sensor Features for Anomaly Detection",
            options=usable_cols,
            default=default_features,
            help="Select continuous numeric sensor variables. Identifiers and timestamps are automatically excluded."
        )

    with col_cfg2:
        contamination = st.slider(
            "Expected Contamination Factor",
            min_value=0.01,
            max_value=0.20,
            value=config.DEFAULT_CONTAMINATION,
            step=0.01,
            help="Proportion of anomalies expected in the dataset. Default: 0.05 (5%)."
        )
        n_estimators = st.selectbox("Number of Trees (n_estimators)", [50, 100, 150, 200], index=1)
        model_name_input = st.text_input("Model Identifier", value=f"iso_forest_{source_name.lower().split()[0]}")

    if not selected_features:
        st.warning("Please select at least one numeric feature to train the model.")
        return

    # 3. Train Model
    st.markdown("<div class='section-header'>3. Model Training & Anomaly Evaluation</div>", unsafe_allow_html=True)

    if st.button("Fit Isolation Forest & Detect Anomalies", type="primary", use_container_width=True):
        with st.spinner("Training Isolation Forest ensemble and evaluating isolation paths..."):
            try:
                detector = IsolationForestDetector(
                    model_name=model_name_input,
                    contamination=contamination,
                    n_estimators=n_estimators,
                    random_state=config.RANDOM_STATE
                )
                detector.fit(df, selected_features)
                pred_df = detector.predict(df)

                # Store in session state
                st.session_state["fitted_detector"] = detector
                st.session_state["anomaly_results_df"] = pred_df
                st.session_state["last_trained_features"] = selected_features
                st.session_state["last_model_name"] = model_name_input

                st.success("Model trained successfully!")
            except Exception as e:
                st.error(f"Training failed: {str(e)}")
                return

    # Display Results if Available
    if "anomaly_results_df" in st.session_state and "fitted_detector" in st.session_state:
        res_df = st.session_state["anomaly_results_df"]
        detector: IsolationForestDetector = st.session_state["fitted_detector"]

        total_obs = len(res_df)
        total_anom = int((res_df["anomaly_label"] == "ANOMALOUS").sum())
        anom_rate = round(total_anom / total_obs * 100, 2) if total_obs > 0 else 0

        # Summary KPIs
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_metric_card("Total Analyzed", f"{total_obs:,}", "samples", "Input dataset size")
        with k2:
            render_metric_card("Detected Anomalies", f"{total_anom:,}", "samples", f"{anom_rate}% contamination rate", status_color="#DC2626")
        with k3:
            render_metric_card("Normal Samples", f"{total_obs - total_anom:,}", "samples", f"{100 - anom_rate:.1f}% normal operation", status_color="#16A34A")
        with k4:
            render_metric_card("Active Features", len(detector.feature_names), "features", f"{', '.join(detector.feature_names[:2])}...")

        # Visualizations
        st.markdown("<div class='section-header'>Anomaly Visualizations</div>", unsafe_allow_html=True)
        res_tab1, res_tab2, res_tab3 = st.tabs(["Scatter Plot (Feature Space)", "Timeline Trend", "Score Distribution"])

        with res_tab1:
            if len(detector.feature_names) >= 2:
                feat_x = detector.feature_names[0]
                feat_y = detector.feature_names[1]
                fig_scatter = px.scatter(
                    res_df,
                    x=feat_x,
                    y=feat_y,
                    color="anomaly_label",
                    color_discrete_map={"NORMAL": "#0284C7", "ANOMALOUS": "#DC2626"},
                    title=f"Feature Space Anomaly Distribution ({feat_x} vs {feat_y})",
                    hover_data=["top_deviating_feature", "anomaly_score"]
                )
                fig_scatter.update_layout(
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    margin=dict(l=40, r=20, t=50, b=40)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Select at least 2 features to view a 2D feature space scatter plot.")

        with res_tab2:
            fig_trend = create_sensor_trend_chart(
                res_df,
                y_columns=[detector.feature_names[0]],
                title=f"Anomaly Highlight on Primary Feature ({detector.feature_names[0]})",
                anomaly_col="anomaly_label"
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with res_tab3:
            fig_scores = px.histogram(
                res_df,
                x="anomaly_score",
                color="anomaly_label",
                barmode="overlay",
                color_discrete_map={"NORMAL": "#0284C7", "ANOMALOUS": "#DC2626"},
                title="Anomaly Score Distribution (Higher Score = More Isolated / Anomalous)"
            )
            fig_scores.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
            st.plotly_chart(fig_scores, use_container_width=True)

        # Ground Truth Evaluation (if column exists)
        gt_cols = [c for c in res_df.columns if any(k in c.lower() for k in ["ground_truth", "health_state", "target_label"])]
        if gt_cols:
            st.markdown("<div class='section-header'>Evaluation Against Ground Truth Labels</div>", unsafe_allow_html=True)
            eval_metrics = evaluate_anomalies_if_ground_truth(res_df, ground_truth_col=gt_cols[0])
            if eval_metrics["has_ground_truth"]:
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    render_metric_card("Precision", f"{eval_metrics['precision']:.3f}", "", "True Positives / Predicted Positives")
                with ec2:
                    render_metric_card("Recall", f"{eval_metrics['recall']:.3f}", "", "True Positives / Actual Anomalies")
                with ec3:
                    render_metric_card("F1-Score", f"{eval_metrics['f1_score']:.3f}", "", "Harmonic Mean of Precision & Recall")
        else:
            st.markdown("""
            <div class="info-callout">
                <b>Evaluation Notice:</b> Ground truth defect labels are not present in this dataset. As per predictive maintenance best practices, unsupervised anomaly detection precision and accuracy are not fabricated. Review detected anomalies by inspecting their deviation scores and feature contributions below.
            </div>
            """, unsafe_allow_html=True)

        # Model Save & Deployment Actions
        st.markdown("<div class='section-header'>Model Registry & Live Deployment</div>", unsafe_allow_html=True)
        act_col1, act_col2 = st.columns(2)

        with act_col1:
            if st.button("Save Model to Registry", use_container_width=True):
                save_path = detector.save(notes=f"Trained on {source_name} with features: {detector.feature_names}")
                st.success(f"Model saved to `{save_path}` and registered in SQLite database!")

        with act_col2:
            if st.button("Deploy as Active Live Telemetry Model", use_container_width=True):
                live_monitor.set_active_model(detector)
                st.success(f"Model '{detector.model_name}' is now actively scoring live ESP32 hardware telemetry!")
