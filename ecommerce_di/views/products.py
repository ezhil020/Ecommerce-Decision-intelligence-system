"""
Page 3 — Product & Inventory Intelligence
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from analytics.sales import get_product_performance, get_profitability_analysis
from analytics.inventory import (
    get_inventory_risk, get_overstock_products, get_high_demand_low_stock,
    get_inventory_summary, get_rating_quality_analysis,
)
from views.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state, render_inference_card,
)


def render(filters: dict):
    st.markdown("## Product & Inventory Intelligence")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Stock levels, product performance and profitability with AI inferences</p>',
        unsafe_allow_html=True,
    )

    # ── Inventory Summary KPIs ─────────────────────────────────────────────────
    inv_sum = get_inventory_summary()
    cols = st.columns(5)
    cards = [
        ("Total Products",     fmt_number(inv_sum["total_products"]),         "🏪", COLORS["muted"]),
        ("Active Products",    fmt_number(inv_sum["active_products"]),         "✅", COLORS["success"]),
        ("Below Reorder",      str(int(inv_sum["below_reorder"] or 0)),        "🔴", COLORS["danger"]),
        ("Out of Stock",       str(int(inv_sum["out_of_stock"] or 0)),          "❌", COLORS["danger"]),
        ("Inventory Value",    fmt_currency(inv_sum["total_inventory_value"]), "💰", COLORS["primary"]),
    ]
    for col, (title, val, icon, accent) in zip(cols, cards):
        with col:
            kpi_card(title, val, icon=icon, accent=accent)

    render_inference_card("products_kpis", "Catalog Inventory Valuation")

    st.markdown("---")


    # ── Inventory Risk ─────────────────────────────────────────────────────────
    section_header("⚠️ Stock Risk — Below Reorder Level",
                   "Products that need immediate restocking attention")
    risk_df = get_inventory_risk()
    if risk_df.empty:
        st.success("✅ All active products are above their reorder levels.")
    else:
        # Risk severity: critical if stock < 50% of reorder level
        risk_df["risk_level"] = risk_df.apply(
            lambda r: "🔴 Critical" if r["stock_quantity"] < r["reorder_level"] * 0.5
            else "🟡 Warning",
            axis=1,
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(
                risk_df[["product_name","category","brand","stock_quantity",
                          "reorder_level","stock_deficit","units_sold_30d",
                          "units_sold_90d","risk_level"]].rename(columns={
                    "product_name":"Product","category":"Category","brand":"Brand",
                    "stock_quantity":"Stock","reorder_level":"Reorder Level",
                    "stock_deficit":"Deficit","units_sold_30d":"Sold (30d)",
                    "units_sold_90d":"Sold (90d)","risk_level":"Risk",
                }),
                use_container_width=True, hide_index=True, height=320,
            )
        with col2:
            fig = go.Figure(go.Bar(
                x=risk_df.head(10)["stock_deficit"],
                y=risk_df.head(10)["product_name"].str[:18],
                orientation="h",
                marker_color=COLORS["danger"],
                hovertemplate="Deficit: %{x}<extra></extra>",
            ))
            fig.update_layout(yaxis=dict(autorange="reversed"))
            chart_layout(fig, "Stock Deficit (Top 10)", height=320)
            st.plotly_chart(fig, use_container_width=True)

        render_inference_card("products_deficit", "Top Stock Deficit Bottlenecks")

    st.markdown("---")

    # ── High Demand / Low Stock ────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        section_header("🚨 High Demand / Low Stock",
                       "Products at stockout risk")
        hd_df = get_high_demand_low_stock()
        if hd_df.empty:
            empty_state("No high-demand low-stock products identified.")
        else:
            st.dataframe(
                hd_df[["product_name","category","brand","stock_quantity",
                        "units_sold_30d","days_of_stock"]].rename(columns={
                    "product_name":"Product","category":"Category","brand":"Brand",
                    "stock_quantity":"Current Stock","units_sold_30d":"Units/30d",
                    "days_of_stock":"Days Left",
                }).assign(**{"Days Left": lambda d: d["Days Left"].round(1) if "Days Left" in d else None}),
                use_container_width=True, hide_index=True, height=260,
            )

    with col_b:
        section_header("📦 Overstock Detection",
                       "High stock, low sales")
        os_df = get_overstock_products()
        if os_df.empty:
            empty_state("No overstock products detected.")
        else:
            st.dataframe(
                os_df[["product_name","category","brand","stock_quantity",
                        "reorder_level","units_sold_90d","inventory_value"]].rename(columns={
                    "product_name":"Product","category":"Category","brand":"Brand",
                    "stock_quantity":"Stock","reorder_level":"Reorder Level",
                    "units_sold_90d":"Sold (90d)","inventory_value":"Value (₹)",
                }),
                use_container_width=True, hide_index=True, height=260,
            )

    render_inference_card("products_high_demand_low_stock", "Stockout Risk Runway & Working Capital Exposure")

    st.markdown("---")

    # ── Profitability Analysis ─────────────────────────────────────────────────
    section_header("Profitability Analysis",
                   "Effective margin vs revenue — identify high-revenue/low-margin products")
    prof_df = get_profitability_analysis(filters)

    if not prof_df.empty:
        top_rev = prof_df.nlargest(40, "revenue")
        fig2 = px.scatter(
            top_rev,
            x="revenue", y="effective_margin",
            size="units_sold", color="category",
            hover_name="product_name",
            hover_data={"revenue": ":.0f", "effective_margin": ":.3f",
                        "units_sold": True, "total_discount": ":.0f"},
            color_discrete_sequence=CATEGORY_COLORS,
            labels={"revenue":"Revenue (₹)","effective_margin":"Effective Margin",
                    "category":"Category"},
        )
        fig2.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Revenue: ₹%{x:,.0f}<br>"
                "Margin: %{y:.1%}<br>"
                "Units Sold: %{marker.size}<extra></extra>"
            )
        )
        chart_layout(fig2, height=380)
        st.plotly_chart(fig2, use_container_width=True)

        # Table: top revenue, low margin products
        st.markdown("**⚠️ High Revenue / Low Margin Products** (review pricing strategy)")
        hl = prof_df[prof_df["revenue"] > prof_df["revenue"].quantile(0.6)].nsmallest(15, "effective_margin")
        if not hl.empty:
            st.dataframe(
                hl[["product_name","category","brand","revenue",
                    "gross_profit","effective_margin","total_discount"]].rename(columns={
                    "product_name":"Product","category":"Category","brand":"Brand",
                    "revenue":"Revenue","gross_profit":"Profit",
                    "effective_margin":"Margin","total_discount":"Discount",
                }),
                use_container_width=True, hide_index=True,
            )

    st.markdown("---")

    # ── Rating Quality & Return Analysis ───────────────────────────────────────
    section_header("⭐ Product Rating & Return Rate Correlation",
                   "Impact of customer ratings on return frequency and profit margins")
    rate_df = get_rating_quality_analysis()

    if not rate_df.empty:
        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            fig_r = go.Figure()
            fig_r.add_trace(go.Bar(
                x=rate_df["rating_tier"],
                y=rate_df["return_rate_pct"],
                name="Return Rate %",
                marker_color=COLORS["warning"],
                hovertemplate="<b>%{x}</b><br>Return Rate: %{y:.2f}%<extra></extra>",
            ))
            fig_r.add_trace(go.Scatter(
                x=rate_df["rating_tier"],
                y=rate_df["avg_margin_pct"],
                name="Avg Margin %",
                mode="lines+markers",
                marker=dict(size=8, color=COLORS["success"]),
                line=dict(width=2.5, color=COLORS["success"]),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
            ))
            fig_r.update_layout(
                yaxis=dict(title="Return Rate (%)"),
                yaxis2=dict(title="Avg Margin (%)", overlaying="y", side="right", showgrid=False),
                bargap=0.35,
            )
            fig_r.update_xaxes(type="category")
            chart_layout(fig_r, "Return Rate & Margin by Rating Tier", height=320)
            st.plotly_chart(fig_r, use_container_width=True)

        with col_r2:
            st.dataframe(
                rate_df.rename(columns={
                    "rating_tier": "Rating Tier",
                    "total_orders": "Orders",
                    "returned_orders": "Returns",
                    "return_rate_pct": "Return %",
                    "avg_margin_pct": "Margin %",
                    "total_revenue": "Revenue (₹)",
                }).assign(**{"Revenue (₹)": lambda d: d["Revenue (₹)"].apply(lambda v: f"₹{v:,.0f}")}),
                use_container_width=True,
                hide_index=True,
            )

        render_inference_card("products_rating_quality", "Product Satisfaction vs Sales & Returns")

