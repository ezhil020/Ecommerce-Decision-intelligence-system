"""
Page 4 — Customer Intelligence
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from analytics.customers import (
    get_customer_overview, get_customer_revenue, get_customer_segmentation,
    get_geographic_analysis, get_demographic_analysis, get_membership_analysis,
    get_device_channel_analysis,
)
from views.ui_utils import (
    kpi_card, section_header, fmt_currency, fmt_number,
    chart_layout, COLORS, CATEGORY_COLORS, empty_state, render_inference_card,
)


def render(filters: dict):
    st.markdown("## Customer Intelligence")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Behavioral segmentation, channel preference and geographic analysis with AI inferences</p>',
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

    render_inference_card("customers_kpis", "Customer Base Foundation")

    st.markdown("---")


    # ── Segmentation ──────────────────────────────────────────────────────────
    section_header("Customer Behavioral Segmentation",
                   "Dynamic value-loyalty matrix: VIP Champions, High Spenders, Loyal Advocates, and Core Shoppers")
    seg_df = get_customer_segmentation()

    if seg_df.empty:
        empty_state("No customer data available.")
    else:
        seg_summary = (
            seg_df.groupby("segment")
            .agg(customers=("customer_id","count"),
                 total_revenue=("total_revenue","sum"),
                 avg_spend=("total_revenue","mean"),
                 avg_loyalty=("loyalty_points","mean"))
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
            chart_layout(fig, "Customer Share by Segment", height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = go.Figure(go.Bar(
                x=seg_summary["segment"],
                y=seg_summary["total_revenue"],
                marker=dict(color=CATEGORY_COLORS[:len(seg_summary)]),
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            fig2.update_xaxes(type="category")
            chart_layout(fig2, "Revenue Contribution by Segment", height=300)
            st.plotly_chart(fig2, use_container_width=True)

        display_seg = seg_summary.copy()
        display_seg["total_revenue"] = display_seg["total_revenue"].apply(lambda v: f"₹{v:,.0f}")
        display_seg["avg_spend"] = display_seg["avg_spend"].apply(lambda v: f"₹{v:,.0f}")
        display_seg["avg_loyalty"] = display_seg["avg_loyalty"].round(0).astype(int)
        st.dataframe(
            display_seg.rename(columns={
                "segment":"Segment","customers":"Customers",
                "total_revenue":"Total Revenue","avg_spend":"Avg Order Value",
                "avg_loyalty":"Avg Loyalty Pts",
            }),
            use_container_width=True, hide_index=True,
        )

        render_inference_card("customers_segmentation", "Behavioral Segmentation & Concentration")

    st.markdown("---")

    # ── Channel & Membership ──────────────────────────────────────────────────
    section_header("Device Channel & Membership Affinity",
                   "Shopping platform split (Mobile App vs Desktop) across loyalty tiers")
    dev_df = get_device_channel_analysis()

    if not dev_df.empty:
        col_c, col_d = st.columns(2)
        with col_c:
            dev_agg = dev_df.groupby("preferred_device").agg(
                revenue=("revenue", "sum"),
                customers=("customers", "sum"),
            ).reset_index()
            fig3 = go.Figure(go.Pie(
                labels=dev_agg["preferred_device"],
                values=dev_agg["revenue"],
                hole=0.5,
                marker=dict(colors=[COLORS["primary"], COLORS["secondary"]]),
                hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            chart_layout(fig3, "Revenue by Platform Channel", height=280)
            st.plotly_chart(fig3, use_container_width=True)

        with col_d:
            mem_df = get_membership_analysis()
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=mem_df["membership_label"],
                y=mem_df["revenue"],
                name="Revenue (₹)",
                marker_color=COLORS["secondary"],
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            fig4.update_xaxes(type="category")
            chart_layout(fig4, "Revenue by Membership Tier", height=280)
            st.plotly_chart(fig4, use_container_width=True)

        render_inference_card("customers_device_membership", "Mobile App Adoption & Membership Loyalty")

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
            fig5.update_xaxes(type="category")
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
        fig7.update_xaxes(type="category")
        chart_layout(fig7, "Top States by Revenue", height=340)
        st.plotly_chart(fig7, use_container_width=True)
        render_inference_card("customers_geo", "Geographic Demand Clusters")

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

