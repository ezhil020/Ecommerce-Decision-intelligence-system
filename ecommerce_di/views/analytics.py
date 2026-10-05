"""
Page 6 — Advanced Analytics (Forecasting + Anomaly Detection)
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from analytics.anomalies import get_all_anomalies
from forecasting.forecasting import forecast_revenue, forecast_orders
from analytics.sales import get_sales_trend
from config.settings import FORECAST_PERIODS
from views.ui_utils import (
    section_header, fmt_currency, fmt_number,
    chart_layout, COLORS, empty_state, alert_banner,
)


def render(filters: dict):
    st.markdown("## Advanced Analytics")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Forecasting, anomaly detection and trend analysis</p>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📈 Forecasting", "🔍 Anomaly Detection"])

    # ─────────────── FORECASTING ────────────────────────────────────────────────
    with tab1:
        col_ctrl1, col_ctrl2 = st.columns([2, 1])
        with col_ctrl1:
            metric = st.radio("Forecast metric", ["Revenue", "Order Volume"],
                              horizontal=True, key="fc_metric")
        with col_ctrl2:
            periods = st.slider("Months to forecast", 3, 24,
                                FORECAST_PERIODS, key="fc_periods")

        alert_banner(
            "⚠️ Forecasts are statistical estimates based on historical patterns. "
            "They are not guaranteed outcomes and should inform, not replace, business judgement.",
            "info"
        )

        with st.spinner("Computing forecast…"):
            if metric == "Revenue":
                result = forecast_revenue(periods)
            else:
                result = forecast_orders(periods)

        if "error" in result and result["error"]:
            st.error(result["error"])
        else:
            hist_df  = result["historical"]
            fcast_df = result["forecast"]
            method   = result.get("method","")

            st.caption(f"Method: **{method}**")

            # Value column
            val_col = "revenue" if metric == "Revenue" else "orders"
            if val_col not in hist_df.columns and len(hist_df.columns) >= 2:
                val_col = hist_df.columns[1]

            fcast_val = "forecast"

            fig = go.Figure()

            # Historical line
            fig.add_trace(go.Scatter(
                x=hist_df["period"], y=hist_df[val_col],
                mode="lines+markers", name="Historical",
                line=dict(color=COLORS["primary"], width=2.5),
                marker=dict(size=5),
                hovertemplate="<b>%{x}</b><br>Actual: %{y:,.0f}<extra></extra>",
            ))

            # Confidence interval
            if "upper" in fcast_df.columns and "lower" in fcast_df.columns:
                fig.add_trace(go.Scatter(
                    x=list(fcast_df["period"]) + list(fcast_df["period"][::-1]),
                    y=list(fcast_df["upper"]) + list(fcast_df["lower"][::-1]),
                    fill="toself",
                    fillcolor="rgba(139,92,246,0.12)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="95% CI",
                    hoverinfo="skip",
                ))

            # Forecast line
            fig.add_trace(go.Scatter(
                x=fcast_df["period"], y=fcast_df[fcast_val],
                mode="lines+markers", name="Forecast (estimate)",
                line=dict(color=COLORS["secondary"], width=2.5, dash="dash"),
                marker=dict(size=6, symbol="diamond"),
                hovertemplate="<b>%{x}</b><br>Forecast: %{y:,.0f}<extra></extra>",
            ))

            chart_layout(fig, f"{metric} Forecast — Next {periods} Months", height=420)
            st.plotly_chart(fig, use_container_width=True)

            # Forecast table
            section_header("Forecast Values")
            disp = fcast_df[["period", fcast_val]].copy()
            disp.columns = ["Month", f"Forecast {metric}"]
            if metric == "Revenue":
                disp[f"Forecast {metric}"] = disp[f"Forecast {metric}"].apply(
                    lambda v: f"₹{v:,.0f}"
                )
            else:
                disp[f"Forecast {metric}"] = disp[f"Forecast {metric}"].apply(
                    lambda v: f"{int(v):,}"
                )
            st.dataframe(disp, use_container_width=True, hide_index=True)

    # ─────────────── ANOMALY DETECTION ──────────────────────────────────────────
    with tab2:
        section_header("Anomaly Detection",
                       f"Statistical outliers (Z-score threshold ≥ 2.5σ)")

        with st.spinner("Detecting anomalies…"):
            anom_df = get_all_anomalies()

        if anom_df.empty:
            st.success("✅ No statistically significant anomalies detected in the dataset.")
        else:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Anomalies Detected", len(anom_df))
            with col2:
                spikes = len(anom_df[anom_df["direction"] == "spike"])
                st.metric("Spikes (↑)", spikes)
            with col3:
                drops = len(anom_df[anom_df["direction"] == "drop"])
                st.metric("Drops (↓)", drops)

            # Chart per metric
            for metric_name in anom_df["metric"].unique():
                section_header(f"Anomalies in: {metric_name.replace('_',' ').title()}")
                mdf = anom_df[anom_df["metric"] == metric_name]

                # Get full trend for context
                if "revenue" in metric_name:
                    trend_df = get_sales_trend("monthly")
                    val_col = "revenue"
                    trend_df = trend_df[["period", val_col]]
                else:
                    trend_df = None

                fig2 = go.Figure()

                if trend_df is not None and not trend_df.empty:
                    fig2.add_trace(go.Scatter(
                        x=trend_df["period"], y=trend_df[val_col],
                        mode="lines", name="Trend",
                        line=dict(color="rgba(148,163,184,0.5)", width=1.5),
                    ))

                # Anomaly markers
                spike_df = mdf[mdf["direction"] == "spike"]
                drop_df  = mdf[mdf["direction"] == "drop"]

                if not spike_df.empty:
                    fig2.add_trace(go.Scatter(
                        x=spike_df["period"], y=spike_df[metric_name] if metric_name in spike_df else [0]*len(spike_df),
                        mode="markers", name="Spike",
                        marker=dict(color=COLORS["warning"], size=14, symbol="triangle-up"),
                        hovertemplate="<b>%{x}</b><br>Spike detected<br>Magnitude: %{customdata:.1f}σ<extra></extra>",
                        customdata=spike_df["magnitude"],
                    ))
                if not drop_df.empty:
                    fig2.add_trace(go.Scatter(
                        x=drop_df["period"], y=drop_df[metric_name] if metric_name in drop_df else [0]*len(drop_df),
                        mode="markers", name="Drop",
                        marker=dict(color=COLORS["danger"], size=14, symbol="triangle-down"),
                        hovertemplate="<b>%{x}</b><br>Drop detected<br>Magnitude: %{customdata:.1f}σ<extra></extra>",
                        customdata=drop_df["magnitude"],
                    ))

                chart_layout(fig2, height=280)
                st.plotly_chart(fig2, use_container_width=True)

            # Full anomaly table
            section_header("All Detected Anomalies")
            st.dataframe(
                anom_df[["period","metric","direction","magnitude","zscore"]].rename(columns={
                    "period":"Period","metric":"Metric","direction":"Direction",
                    "magnitude":"Magnitude (σ)","zscore":"Z-Score",
                }),
                use_container_width=True, hide_index=True,
            )
