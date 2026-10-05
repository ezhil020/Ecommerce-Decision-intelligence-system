"""
Page 4 — Customer Intelligence
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from analytics.customers import (
    get_customer_overview, get_customer_revenue, get_customer_segmentation,
    get_geographic_analysis, get_demographic_analysis, get_membership_analysis,
)
from pages.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state,
)


def render(filters: dict):
    st.markdown("## Customer Intelligence")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Segmentation, demographics, loyalty and geographic analysis</p>',
        unsafe_allow_html=True,
    )

    # ── Overview KPIs ─────────────────────────────────────────────────────────
    overview = get_customer_overview()
    cols = st.columns(5)
    for col, (title, val, icon, accent) in zip(cols, [
        ("Total Customers", fmt_number(overview["total_customers"]), "👥", COLORS["primary"]),
        ("Avg Age",         f"{overview['avg_age']:.0f} yrs",       "🎂", COLORS["muted"]),
        ("Avg Loyalty Pts", fmt_number(overview["avg_loyalty_points"]), "⭐", COLORS["warning"]),
        ("States Covered",  str(int(overview["states_covered"] or 0)),  "🗺️", COLORS["info"]),
        ("Cities Covered",  str(int(overview["cities_covered"] or 0)),  "🏙️", COLORS["secondary"]),
    ]):
        with col:
            kpi_card(title, val, icon=icon, accent=accent)

    st.markdown("---")

    # ── Segmentation ──────────────────────────────────────────────────────────
    section_header("Customer Segmentation",
                   "Based on revenue contribution, order frequency and registration date")
    seg_df = get_customer_segmentation()

    if seg_df.empty:
        empty_state("No customer data available.")
    else:
        seg_summary = (
            seg_df.groupby("segment")
            .agg(customers=("customer_id","count"),
                 total_revenue=("total_revenue","sum"),
                 avg_orders=("order_count","mean"))
            .reset_index()
            .sort_values("total_revenue", ascending=False)
        )

        col_a, col_b = st.columns([1, 2])
        with col_a:
            fig = go.Figure(go.Pie(
                labels=seg_summary["segment"],
                values=seg_summary["customers"],
                hole=0.55,
                marker=dict(colors=CATEGORY_COLORS),
                hovertemplate="<b>%{label}</b><br>Customers: %{value}<br>%{percent}<extra></extra>",
            ))
            chart_layout(fig, "Customers by Segment", height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = go.Figure(go.Bar(
                x=seg_summary["segment"],
                y=seg_summary["total_revenue"],
                marker=dict(color=CATEGORY_COLORS[:len(seg_summary)]),
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            chart_layout(fig2, "Revenue by Segment", height=300)
            st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(
            seg_summary.round(2).rename(columns={
                "segment":"Segment","customers":"Customers",
                "total_revenue":"Revenue (₹)","avg_orders":"Avg Orders",
            }),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")

    # ── Membership ────────────────────────────────────────────────────────────
    section_header("Membership & Loyalty Analysis")
    mem_df = get_membership_analysis()

    if not mem_df.empty:
        col_c, col_d = st.columns(2)
        with col_c:
            fig3 = go.Figure(go.Bar(
                x=mem_df["membership_label"],
                y=mem_df["revenue"],
                marker_color=COLORS["secondary"],
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            chart_layout(fig3, "Revenue by Membership", height=280)
            st.plotly_chart(fig3, use_container_width=True)

        with col_d:
            fig4 = go.Figure(go.Bar(
                x=mem_df["membership_label"],
                y=mem_df["avg_loyalty_points"],
                marker_color=COLORS["warning"],
                hovertemplate="<b>%{x}</b><br>Avg Loyalty: %{y:.0f} pts<extra></extra>",
            ))
            chart_layout(fig4, "Avg Loyalty Points by Membership", height=280)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # ── Demographics ──────────────────────────────────────────────────────────
    col_e, col_f = st.columns(2)

    with col_e:
        section_header("Age Group Distribution")
        demo_df = get_demographic_analysis()
        if not demo_df.empty:
            age_rev = (demo_df.groupby("age_group")
                       .agg(revenue=("revenue","sum"), customers=("customers","sum"))
                       .reset_index().sort_values("age_group"))
            fig5 = go.Figure(go.Bar(
                x=age_rev["age_group"], y=age_rev["revenue"],
                marker_color=COLORS["info"],
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            chart_layout(fig5, height=270)
            st.plotly_chart(fig5, use_container_width=True)

    with col_f:
        section_header("Gender Distribution")
        if not demo_df.empty:
            gender_rev = (demo_df.groupby("gender")
                          .agg(revenue=("revenue","sum"), customers=("customers","sum"))
                          .reset_index())
            fig6 = go.Figure(go.Pie(
                labels=gender_rev["gender"],
                values=gender_rev["customers"],
                hole=0.5,
                marker=dict(colors=[COLORS["primary"], COLORS["success"], COLORS["warning"]]),
                hovertemplate="<b>%{label}</b><br>Customers: %{value}<extra></extra>",
            ))
            chart_layout(fig6, height=270)
            st.plotly_chart(fig6, use_container_width=True)

    st.markdown("---")

    # ── Geographic ────────────────────────────────────────────────────────────
    section_header("Geographic Intelligence", "Revenue and customers by state")
    geo_df = get_geographic_analysis()

    if not geo_df.empty:
        state_df = (geo_df.groupby("state")
                    .agg(revenue=("revenue","sum"),
                         customers=("customers","sum"),
                         orders=("orders","sum"))
                    .reset_index().sort_values("revenue", ascending=False))

        fig7 = go.Figure(go.Bar(
            x=state_df["state"].head(20),
            y=state_df["revenue"].head(20),
            marker=dict(color=state_df["revenue"].head(20),
                        colorscale="Viridis", showscale=True),
            hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
        ))
        chart_layout(fig7, "Top States by Revenue", height=340)
        st.plotly_chart(fig7, use_container_width=True)

        # Top customers table
        section_header("Top Customers by Revenue")
        top_cust = get_customer_revenue(top_n=20)
        if not top_cust.empty:
            st.dataframe(
                top_cust[["name","membership_label","state","city",
                           "order_count","total_revenue","avg_order_value"]].rename(columns={
                    "name":"Customer","membership_label":"Membership",
                    "state":"State","city":"City","order_count":"Orders",
                    "total_revenue":"Revenue (₹)","avg_order_value":"AOV (₹)",
                }).assign(**{
                    "Revenue (₹)": lambda d: d["Revenue (₹)"].round(0).astype(int),
                    "AOV (₹)": lambda d: d["AOV (₹)"].round(0).astype(int),
                }),
                use_container_width=True, hide_index=True,
            )
