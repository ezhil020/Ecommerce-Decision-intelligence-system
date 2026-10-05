"""
Page 1 — Executive Overview Dashboard
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from analytics.sales import get_executive_kpis, get_sales_trend, get_category_performance
from analytics.inventory import get_inventory_risk
from analytics.payments import get_order_status_breakdown
from views.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number, fmt_pct,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state,
)


def render(filters: dict):
    st.markdown("## Executive Overview")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">High-level business performance at a glance</p>',
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    with st.spinner("Loading KPIs…"):
        kpis = get_executive_kpis(filters)

    rev = kpis.get("total_revenue", 0)
    gp = kpis.get("total_gross_profit", 0)
    margin_pct = (gp / rev * 100) if rev > 0 else 0
    disc = kpis.get("total_discount", 0)
    disc_pct = (disc / (rev + disc) * 100) if (rev + disc) > 0 else 0

    cols = st.columns(4)
    kpi_defs = [
        ("Total Net Revenue", fmt_currency(rev), "💰", COLORS["primary"], "Realized net order value"),
        ("Gross Profit",      fmt_currency(gp),  "📈", COLORS["success"], f"Overall margin: {margin_pct:.1f}%"),
        ("Total Orders",      fmt_number(kpis["total_orders"]), "📦", COLORS["info"], f"AOV: {fmt_currency(kpis['avg_order_value'])}"),
        ("Active Customers",  fmt_number(kpis["total_customers"]), "👥", COLORS["secondary"], "Distinct buyers across period"),
    ]
    for col, (title, val, icon, accent, sub) in zip(cols, kpi_defs):
        with col:
            kpi_card(title, val, subtitle=sub, icon=icon, accent=accent)

    cols2 = st.columns(4)
    kpi_defs2 = [
        ("Gross Margin",       f"{margin_pct:.1f}%", "🎯", COLORS["success"] if margin_pct > 25 else COLORS["warning"], "Profitability index"),
        ("Discount Erosion",   fmt_currency(disc),   "🏷️", COLORS["warning"], f"{disc_pct:.1f}% of gross GMV"),
        ("Return/Cancel Rate", fmt_pct(kpis["return_cancel_rate"]), "⚠️", COLORS["danger"], f"{int(kpis['returned_cancelled_orders'])} orders lost"),
        ("Stockout Risk",      f"{int(kpis['products_below_reorder'])} SKUs", "🔴", COLORS["danger"] if kpis['products_below_reorder'] > 0 else COLORS["success"], "Products below reorder level"),
    ]
    for col, (title, val, icon, accent, sub) in zip(cols2, kpi_defs2):
        with col:
            kpi_card(title, val, subtitle=sub, icon=icon, accent=accent)

    st.markdown("---")

    # ── Sales Trend ────────────────────────────────────────────────────────────
    col_l, col_r = st.columns([2, 1])

    with col_l:
        section_header("Revenue Trend", "Monthly revenue over time")
        trend_df = get_sales_trend("monthly", filters)
        if trend_df.empty:
            empty_state("No sales data available for selected filters.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_df["period"], y=trend_df["revenue"],
                mode="lines+markers",
                name="Revenue",
                line=dict(color=COLORS["primary"], width=2.5),
                marker=dict(size=5, color=COLORS["primary"]),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.08)",
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=trend_df["period"], y=trend_df["gross_profit"],
                mode="lines",
                name="Gross Profit",
                line=dict(color=COLORS["success"], width=2, dash="dot"),
                hovertemplate="<b>%{x}</b><br>Profit: ₹%{y:,.0f}<extra></extra>",
            ))
            chart_layout(fig, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        section_header("Order Status", "Breakdown by status")
        status_df = get_order_status_breakdown()
        if status_df.empty:
            empty_state("No data.")
        else:
            fig2 = go.Figure(go.Pie(
                labels=status_df["order_status"],
                values=status_df["orders"],
                hole=0.55,
                marker=dict(colors=CATEGORY_COLORS),
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate="<b>%{label}</b><br>Orders: %{value}<br>%{percent}<extra></extra>",
            ))
            chart_layout(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Category Performance ───────────────────────────────────────────────────
    section_header("Category Performance", "Revenue and profit by category")
    cat_df = get_category_performance(filters)
    if not cat_df.empty:
        top_cat = cat_df.groupby("category").agg(
            revenue=("revenue","sum"),
            gross_profit=("gross_profit","sum"),
            units_sold=("units_sold","sum"),
        ).reset_index().sort_values("revenue", ascending=False)

        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=top_cat["category"], y=top_cat["revenue"],
            name="Revenue", marker_color=COLORS["primary"],
            hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
        ))
        fig3.add_trace(go.Bar(
            x=top_cat["category"], y=top_cat["gross_profit"],
            name="Gross Profit", marker_color=COLORS["success"],
            hovertemplate="<b>%{x}</b><br>Profit: ₹%{y:,.0f}<extra></extra>",
        ))
        fig3.update_layout(barmode="group")
        chart_layout(fig3, height=320)
        st.plotly_chart(fig3, use_container_width=True)

    # ── Inventory Alerts ───────────────────────────────────────────────────────
    inv_df = get_inventory_risk()
    if not inv_df.empty:
        section_header("⚠️ Inventory Alerts", f"{len(inv_df)} products below reorder level")
        st.dataframe(
            inv_df[["product_name","category","brand","stock_quantity",
                    "reorder_level","stock_deficit","units_sold_30d"]].head(10),
            use_container_width=True,
            hide_index=True,
        )
