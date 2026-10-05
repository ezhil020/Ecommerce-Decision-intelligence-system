"""
Page 5 — Payments & Operations
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from analytics.payments import (
    get_payment_overview, get_payment_method_analysis,
    get_refund_analysis, get_refund_trend, get_order_status_breakdown,
)
from pages.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number, fmt_pct,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state,
)


def render(filters: dict):
    st.markdown("## Payments & Operations")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Payment success, failure, refunds and operational status</p>',
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    pov = get_payment_overview()
    total = pov["total_payments"] or 1
    fail_rate = pov["failed"] / total

    cols = st.columns(5)
    for col, (title, val, icon, accent) in zip(cols, [
        ("Total Payments",  fmt_number(pov["total_payments"]),  "💳", COLORS["primary"]),
        ("Successful",      fmt_number(pov["successful"]),      "✅", COLORS["success"]),
        ("Failed",          fmt_number(pov["failed"]),          "❌", COLORS["danger"]),
        ("Failure Rate",    fmt_pct(fail_rate),                 "⚠️", COLORS["warning"]),
        ("Total Refunds",   fmt_currency(pov["total_refunds"]), "↩️", COLORS["danger"]),
    ]):
        with col:
            kpi_card(title, val, icon=icon, accent=accent)

    st.markdown("---")

    # ── Payment Method Analysis ────────────────────────────────────────────────
    section_header("Payment Method Performance",
                   "Success/failure rates and volumes by payment method")
    method_df = get_payment_method_analysis()

    if method_df.empty:
        empty_state("No payment data available.")
    else:
        col_a, col_b = st.columns(2)

        with col_a:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=method_df["payment_mode"], y=method_df["successful"],
                name="Successful", marker_color=COLORS["success"],
                hovertemplate="<b>%{x}</b><br>Successful: %{y}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=method_df["payment_mode"], y=method_df["failed"],
                name="Failed", marker_color=COLORS["danger"],
                hovertemplate="<b>%{x}</b><br>Failed: %{y}<extra></extra>",
            ))
            fig.update_layout(barmode="stack")
            chart_layout(fig, "Payments by Method", height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = go.Figure(go.Bar(
                x=method_df["payment_mode"],
                y=method_df["failure_rate_pct"],
                marker=dict(
                    color=method_df["failure_rate_pct"],
                    colorscale=[[0,"#10b981"],[0.5,"#f59e0b"],[1,"#ef4444"]],
                    showscale=True,
                    colorbar=dict(title="Failure %", len=0.8),
                ),
                hovertemplate="<b>%{x}</b><br>Failure Rate: %{y:.1f}%<extra></extra>",
            ))
            chart_layout(fig2, "Failure Rate by Method (%)", height=300)
            st.plotly_chart(fig2, use_container_width=True)

        # Transaction fees table
        st.dataframe(
            method_df[["payment_mode","total_payments","successful","failed",
                        "failure_rate_pct","total_fees","total_volume"]].rename(columns={
                "payment_mode":"Method","total_payments":"Payments",
                "successful":"Success","failed":"Failed",
                "failure_rate_pct":"Failure %","total_fees":"Fees (₹)",
                "total_volume":"Volume (₹)",
            }).assign(**{
                "Fees (₹)": lambda d: d["Fees (₹)"].round(0),
                "Volume (₹)": lambda d: d["Volume (₹)"].round(0),
            }),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")

    # ── Refund Analysis ────────────────────────────────────────────────────────
    col_c, col_d = st.columns(2)

    with col_c:
        section_header("Refund by Category")
        ref_df = get_refund_analysis()
        if ref_df.empty:
            empty_state("No refund data.")
        else:
            cat_ref = (ref_df.groupby("category")
                       .agg(total_refund=("total_refund","sum"),
                            refund_count=("refund_count","sum"))
                       .reset_index().sort_values("total_refund", ascending=True))
            fig3 = go.Figure(go.Bar(
                x=cat_ref["total_refund"], y=cat_ref["category"],
                orientation="h",
                marker_color=COLORS["danger"],
                hovertemplate="<b>%{y}</b><br>Refund: ₹%{x:,.0f}<extra></extra>",
            ))
            chart_layout(fig3, height=300)
            st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        section_header("Refund Trend")
        trend_df = get_refund_trend("monthly")
        if trend_df.empty:
            empty_state("No refund trend data.")
        else:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=trend_df["period"], y=trend_df["refund_amount"],
                marker_color="rgba(239,68,68,0.6)",
                name="Refund Amount",
                hovertemplate="<b>%{x}</b><br>Refund: ₹%{y:,.0f}<extra></extra>",
            ))
            fig4.add_trace(go.Scatter(
                x=trend_df["period"], y=trend_df["refund_count"],
                mode="lines+markers", name="Refund Count",
                line=dict(color=COLORS["warning"], width=2),
                yaxis="y2",
                hovertemplate="Count: %{y}<extra></extra>",
            ))
            fig4.update_layout(
                yaxis2=dict(overlaying="y", side="right",
                            showgrid=False, tickfont=dict(size=10)),
            )
            chart_layout(fig4, height=300)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # ── Order Status ───────────────────────────────────────────────────────────
    section_header("Order Status Breakdown", "Operational view of all orders")
    status_df = get_order_status_breakdown()

    if not status_df.empty:
        col_e, col_f = st.columns([1, 2])
        with col_e:
            fig5 = go.Figure(go.Pie(
                labels=status_df["order_status"],
                values=status_df["orders"],
                hole=0.5,
                marker=dict(colors=CATEGORY_COLORS),
                hovertemplate="<b>%{label}</b><br>%{value} orders (%{percent})<extra></extra>",
            ))
            chart_layout(fig5, height=280)
            st.plotly_chart(fig5, use_container_width=True)

        with col_f:
            st.dataframe(
                status_df.rename(columns={
                    "order_status":"Status","orders":"Orders",
                    "revenue":"Revenue (₹)","units":"Units",
                }).assign(**{"Revenue (₹)": lambda d: d["Revenue (₹)"].round(0).astype(int)}),
                use_container_width=True, hide_index=True, height=280,
            )
