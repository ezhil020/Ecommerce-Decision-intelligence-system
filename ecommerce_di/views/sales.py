"""
Page 2 — Sales Intelligence
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from analytics.sales import (
    get_sales_trend, get_category_performance, get_brand_performance,
    get_product_performance, get_period_comparison, get_day_of_week_analysis,
)
from views.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number, fmt_pct, fmt_pct,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state, alert_banner, render_inference_card,
)


def render(filters: dict):
    st.markdown("## Sales Intelligence")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Revenue, order and product performance analysis with AI inferences</p>',
        unsafe_allow_html=True,
    )

    # ── Controls ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        granularity = st.radio(
            "Time granularity",
            ["daily", "weekly", "monthly", "quarterly", "yearly"],
            index=2, horizontal=True,
            key="sales_gran",
        )
    with col2:
        sort_metric = st.selectbox(
            "Sort products by",
            ["revenue", "units_sold", "gross_profit", "orders"],
            key="sales_sort",
        )

    # ── Revenue & Order Trend ─────────────────────────────────────────────────
    section_header("Sales Trend", f"Aggregated by {granularity}")
    trend_df = get_sales_trend(granularity, filters)

    if trend_df.empty:
        empty_state("No sales data for the selected period / filters.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["Revenue & Discounts", "Orders", "Average Order Value", "Weekly Seasonality"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_df["period"], y=trend_df["revenue"],
                mode="lines+markers", name="Revenue",
                line=dict(color=COLORS["primary"], width=2.5),
                fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=trend_df["period"], y=trend_df["total_discount"],
                name="Discount", marker_color="rgba(245,158,11,0.4)",
                hovertemplate="Discount: ₹%{y:,.0f}<extra></extra>",
                yaxis="y2",
            ))
            fig.update_layout(
                yaxis2=dict(overlaying="y", side="right",
                            showgrid=False, tickfont=dict(size=10),
                            tickcolor=COLORS["warning"]),
            )
            chart_layout(fig, height=340)
            st.plotly_chart(fig, use_container_width=True)
            render_inference_card("sales_trend_revenue", "Revenue & Discount Dynamics")

        with tab2:
            fig2 = go.Figure(go.Bar(
                x=trend_df["period"], y=trend_df["orders"],
                marker_color=COLORS["info"],
                hovertemplate="<b>%{x}</b><br>Orders: %{y}<extra></extra>",
            ))
            chart_layout(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)
            render_inference_card("sales_trend_orders", "Order Volume Distribution")

        with tab3:
            fig3 = go.Figure(go.Scatter(
                x=trend_df["period"], y=trend_df["avg_order_value"],
                mode="lines+markers", line=dict(color=COLORS["success"], width=2.5),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                hovertemplate="AOV: ₹%{y:,.0f}<extra></extra>",
            ))
            chart_layout(fig3, height=300)
            st.plotly_chart(fig3, use_container_width=True)
            render_inference_card("sales_trend_aov", "Average Order Value Dynamics")

        with tab4:
            dow_df = get_day_of_week_analysis(filters)
            if not dow_df.empty:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    fig_dow1 = go.Figure(go.Bar(
                        x=dow_df["day_of_week"], y=dow_df["orders"],
                        marker=dict(color=COLORS["primary"]),
                        hovertemplate="<b>%{x}</b><br>Orders: %{y}<extra></extra>",
                    ))
                    chart_layout(fig_dow1, "Orders by Day of Week", height=280)
                    st.plotly_chart(fig_dow1, use_container_width=True)
                with col_d2:
                    fig_dow2 = go.Figure(go.Bar(
                        x=dow_df["day_of_week"], y=dow_df["avg_order_value"],
                        marker=dict(color=COLORS["success"]),
                        hovertemplate="<b>%{x}</b><br>AOV: ₹%{y:,.0f}<extra></extra>",
                    ))
                    chart_layout(fig_dow2, "Average Order Value by Day", height=280)
                    st.plotly_chart(fig_dow2, use_container_width=True)
            render_inference_card("sales_dow", "Day-of-Week Seasonality")

    st.markdown("---")

    # ── Category & Brand ───────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        section_header("Category Breakdown")
        cat_df = get_category_performance(filters)
        if cat_df.empty:
            empty_state("No data.")
        else:
            top_cat = cat_df.groupby("category").agg(
                revenue=("revenue","sum"),
                gross_profit=("gross_profit","sum"),
            ).reset_index().sort_values("revenue", ascending=True)

            fig4 = go.Figure()
            fig4.add_trace(go.Bar(y=top_cat["category"], x=top_cat["revenue"],
                                   orientation="h", name="Revenue",
                                   marker_color=COLORS["primary"]))
            fig4.add_trace(go.Bar(y=top_cat["category"], x=top_cat["gross_profit"],
                                   orientation="h", name="Gross Profit",
                                   marker_color=COLORS["success"]))
            fig4.update_layout(barmode="overlay", bargap=0.3)
            chart_layout(fig4, height=320)
            st.plotly_chart(fig4, use_container_width=True)

    with col_b:
        section_header("Top Brands by Revenue")
        brand_df = get_brand_performance(filters)
        if brand_df.empty:
            empty_state("No data.")
        else:
            top_brands = brand_df.head(12)
            fig5 = go.Figure(go.Bar(
                x=top_brands["revenue"], y=top_brands["brand"],
                orientation="h",
                marker=dict(color=top_brands["revenue"],
                            colorscale="Viridis",
                            showscale=False),
                hovertemplate="<b>%{y}</b><br>Revenue: ₹%{x:,.0f}<extra></extra>",
            ))
            fig5.update_layout(yaxis=dict(autorange="reversed"))
            chart_layout(fig5, height=320)
            st.plotly_chart(fig5, use_container_width=True)

    render_inference_card("sales_category_brand", "Category & Brand Concentration")


    st.markdown("---")

    # ── Product Table ──────────────────────────────────────────────────────────
    section_header("Product Performance", "Click column headers to sort")
    prod_df = get_product_performance(limit=100, sort_by=sort_metric, filters=filters)

    if prod_df.empty:
        empty_state("No product data for selected filters.")
    else:
        display_cols = {
            "product_name": "Product",
            "category": "Category",
            "brand": "Brand",
            "revenue": "Revenue (₹)",
            "units_sold": "Units Sold",
            "gross_profit": "Gross Profit (₹)",
            "profit_margin": "Margin %",
            "orders": "Orders",
            "total_discount": "Discount (₹)",
        }
        display_df = prod_df[[c for c in display_cols if c in prod_df.columns]].copy()
        display_df.columns = [display_cols[c] for c in display_df.columns]
        if "Margin %" in display_df.columns:
            display_df["Margin %"] = (display_df["Margin %"] * 100).round(1)
        for col in ["Revenue (₹)", "Gross Profit (₹)", "Discount (₹)"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].round(0).astype(int)

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

    st.markdown("---")

    # ── Period Comparison ──────────────────────────────────────────────────────
    section_header("Period Comparison", "Compare performance across quarters or custom date ranges")

    preset = st.selectbox(
        "Comparison Preset",
        ["Q3 2023 vs Q4 2023", "Q1 2023 vs Q2 2023", "H1 2023 vs H2 2023", "Custom Range"],
        index=0,
        key="pc_preset",
    )

    preset_map = {
        "Q3 2023 vs Q4 2023": ("2023-07-01", "2023-09-30", "2023-10-01", "2023-12-31"),
        "Q1 2023 vs Q2 2023": ("2023-01-01", "2023-03-31", "2023-04-01", "2023-06-30"),
        "H1 2023 vs H2 2023": ("2023-01-01", "2023-06-30", "2023-07-01", "2023-12-31"),
    }

    if preset in preset_map:
        p1s, p1e, p2s, p2e = preset_map[preset]
    else:
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            p1s = st.date_input("Period 1 Start", key="p1s", value=None, format="YYYY-MM-DD")
        with pc2:
            p1e = st.date_input("Period 1 End", key="p1e", value=None, format="YYYY-MM-DD")
        with pc3:
            p2s = st.date_input("Period 2 Start", key="p2s", value=None, format="YYYY-MM-DD")
        with pc4:
            p2e = st.date_input("Period 2 End", key="p2e", value=None, format="YYYY-MM-DD")

    if all([p1s, p1e, p2s, p2e]):
        comp = get_period_comparison(str(p1s), str(p1e), str(p2s), str(p2e))
        p1, p2, chg = comp["period1"], comp["period2"], comp["changes"]
        cols = st.columns(5)
        metrics = [
            ("Revenue", "revenue", fmt_currency),
            ("Orders",  "orders",  fmt_number),
            ("Units",   "units_sold", fmt_number),
            ("AOV",     "aov",     fmt_currency),
            ("Profit",  "gross_profit", fmt_currency),
        ]
        for col, (label, key, fmtr) in zip(cols, metrics):
            with col:
                delta = chg.get(key)
                delta_html = f'<span style="color:{"#10b981" if (delta or 0)>=0 else "#ef4444"};font-weight:600">{"↑" if (delta or 0)>=0 else "↓"} {abs((delta or 0)*100):.1f}%</span>' if delta is not None else ""
                kpi_card(
                    label,
                    fmtr(p2.get(key, 0)),
                    subtitle=f"vs {fmtr(p1.get(key, 0))}",
                    delta_html=delta_html,
                    icon="📊",
                )
