"""
E-Commerce Decision Intelligence System
Main Streamlit application entry point.
"""
import sys
import logging
from pathlib import Path

# ── Make sure the project root is on the path ─────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from database.connection import db_exists, get_connection
from data.loading import load_all
from config.settings import APP_TITLE, APP_ICON

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background: #080818 !important;
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0f0f2a 0%,#0a0a1e 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.15) !important;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

h1, h2, h3, h4 { color: #f1f5f9 !important; font-family: 'Inter', sans-serif !important; }

.stTabs [data-baseweb="tab-list"] {
    background: rgba(15,15,40,0.8) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
}

.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    padding: 6px 16px !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.2) !important;
    color: #a5b4fc !important;
}

.stButton > button {
    border-radius: 8px !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    background: rgba(99,102,241,0.12) !important;
    color: #a5b4fc !important;
    font-size: 0.83rem !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background: rgba(99,102,241,0.25) !important;
    border-color: rgba(99,102,241,0.5) !important;
    color: #c4b5fd !important;
    transform: translateY(-1px) !important;
}

.stProgress .st-bo {
    background-color: #6366f1 !important;
}

[data-testid="stMetricValue"] { color: #f1f5f9 !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.78rem !important; }

.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }

hr { border-color: rgba(99,102,241,0.15) !important; }

.stSpinner { color: #6366f1 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(15,15,40,0.5); }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.7); }
</style>
""", unsafe_allow_html=True)


# ── Sidebar brand header ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 12px 0 20px; text-align:center; border-bottom: 1px solid rgba(99,102,241,0.2); margin-bottom:16px">
        <div style="font-size:2rem">📊</div>
        <div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-top:4px">Decision Intelligence</div>
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em">E-COMMERCE BI PLATFORM</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    page = st.radio(
        "Navigation",
        options=[
            "🏠 Executive Overview",
            "📈 Sales Intelligence",
            "📦 Products & Inventory",
            "👥 Customer Intelligence",
            "💳 Payments & Operations",
            "🔬 Advanced Analytics",
            "🤖 AI Assistant",
            "⚙️ Data Management",
        ],
        label_visibility="collapsed",
        key="nav_page",
    )

    st.markdown("---")
    st.markdown('<p style="color:#64748b;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.07em">Global Filters</p>', unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    filters = {}

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=None, format="YYYY-MM-DD", key="f_start")
    with col2:
        end_date   = st.date_input("To",   value=None, format="YYYY-MM-DD", key="f_end")

    if start_date:
        filters["start_date"] = str(start_date)
    if end_date:
        filters["end_date"] = str(end_date)

    # Dynamic filter options from DB (only if DB exists)
    if db_exists():
        from database.connection import query_df

        cats = query_df("SELECT DISTINCT category FROM dim_product ORDER BY category")["category"].dropna().tolist()
        sel_cats = st.multiselect("Category", cats, key="f_cat")
        if sel_cats:
            filters["category"] = sel_cats

        states = query_df("SELECT DISTINCT state FROM dim_customer WHERE state IS NOT NULL ORDER BY state")["state"].dropna().tolist()
        sel_states = st.multiselect("State", states, key="f_state")
        if sel_states:
            filters["state"] = sel_states

        memberships = query_df("SELECT DISTINCT membership_label FROM dim_customer WHERE membership_label IS NOT NULL ORDER BY membership_label")["membership_label"].dropna().tolist()
        sel_mem = st.multiselect("Membership", memberships, key="f_mem")
        if sel_mem:
            filters["membership"] = sel_mem

        pay_modes = query_df("SELECT DISTINCT payment_mode FROM fact_orders ORDER BY payment_mode")["payment_mode"].dropna().tolist()
        sel_pay = st.multiselect("Payment Mode", pay_modes, key="f_pay")
        if sel_pay:
            filters["payment_mode"] = sel_pay

    st.markdown("---")
    st.markdown(
        '<div style="color:#374151;font-size:0.68rem;text-align:center">'
        'v1.0 • E-Commerce DI System</div>',
        unsafe_allow_html=True
    )


# ── Database setup check ───────────────────────────────────────────────────────
def _data_management_page():
    st.markdown("## ⚙️ Data Management")
    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-12px">Import and manage your e-commerce dataset</p>',
        unsafe_allow_html=True,
    )

    from config.settings import CUSTOMERS_CSV, ORDERS_CSV, PRODUCTS_CSV, PAYMENTS_CSV

    # Check file existence
    files = {
        "Customers.csv": CUSTOMERS_CSV,
        "Orders.csv":    ORDERS_CSV,
        "Products.csv":  PRODUCTS_CSV,
        "Payments.csv":  PAYMENTS_CSV,
    }

    st.markdown("### Dataset Files")
    all_found = True
    for name, path in files.items():
        found = path.exists()
        if not found:
            all_found = False
        status = "✅" if found else "❌"
        st.markdown(
            f'<div style="padding:8px 12px;margin:4px 0;background:rgba(15,15,40,0.7);'
            f'border:1px solid rgba(99,102,241,0.15);border-radius:8px;font-size:0.85rem">'
            f'{status} <code>{name}</code> — <span style="color:#64748b">{path}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if not all_found:
        st.error(
            "Some dataset files are missing. "
            "Please ensure the `project_ecom_dataset/` folder is in the correct location."
        )
        return

    # Load button
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        load_btn = st.button(
            "🔄 Load / Reload Data",
            use_container_width=True,
            type="primary",
        )

    with col_info:
        if db_exists():
            from database.connection import query_df
            counts = {}
            for tbl in ["dim_customer","dim_product","fact_orders","fact_payments"]:
                counts[tbl] = query_df(f"SELECT COUNT(*) AS n FROM {tbl}").iloc[0]["n"]
            st.info(
                f"✅ Database loaded — "
                f"Customers: {counts['dim_customer']:,} | "
                f"Products: {counts['dim_product']:,} | "
                f"Orders: {counts['fact_orders']:,} | "
                f"Payments: {counts['fact_payments']:,}"
            )
        else:
            st.warning("⚠️ Database not yet loaded. Click 'Load / Reload Data' to start.")

    if load_btn:
        progress_bar = st.progress(0, text="Starting…")
        status_text  = st.empty()

        def _cb(step: str, pct: int):
            progress_bar.progress(pct / 100, text=step)
            status_text.markdown(f'<p style="color:#94a3b8;font-size:0.82rem">{step}</p>',
                                  unsafe_allow_html=True)

        try:
            summary = load_all(progress_callback=_cb)
            progress_bar.progress(1.0, text="Complete!")
            status_text.empty()

            st.success(
                f"✅ Data loaded successfully! "
                f"Customers: {summary['rows_loaded'].get('customers',0):,} | "
                f"Products: {summary['rows_loaded'].get('products',0):,} | "
                f"Orders: {summary['rows_loaded'].get('orders',0):,} | "
                f"Payments: {summary['rows_loaded'].get('payments',0):,}"
            )

            if summary["issues"]:
                with st.expander(f"⚠️ Data Quality Issues ({len(summary['issues'])} found)"):
                    for issue in summary["issues"]:
                        st.markdown(
                            f"- **{issue.get('table','?')} / {issue.get('issue','?')}**: "
                            f"{issue.get('count',0)} records"
                        )

            st.rerun()

        except FileNotFoundError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Data loading failed: {exc}")
            logger.exception("Data loading error")

    # Quality log
    if db_exists():
        from database.connection import query_df
        dql = query_df("SELECT * FROM data_quality_log ORDER BY log_id DESC LIMIT 50")
        if not dql.empty:
            with st.expander("📋 Data Quality Log"):
                st.dataframe(dql, use_container_width=True, hide_index=True)


# ── Route to pages ─────────────────────────────────────────────────────────────
if page == "⚙️ Data Management":
    _data_management_page()

elif not db_exists():
    st.warning(
        "⚠️ **No data loaded yet.** "
        "Go to **⚙️ Data Management** in the sidebar to import your dataset."
    )
    st.markdown("---")
    _data_management_page()

else:
    # Import pages lazily (only when DB exists)
    if page == "🏠 Executive Overview":
        from pages.overview    import render; render(filters)
    elif page == "📈 Sales Intelligence":
        from pages.sales       import render; render(filters)
    elif page == "📦 Products & Inventory":
        from pages.products    import render; render(filters)
    elif page == "👥 Customer Intelligence":
        from pages.customers   import render; render(filters)
    elif page == "💳 Payments & Operations":
        from pages.payments    import render; render(filters)
    elif page == "🔬 Advanced Analytics":
        from pages.analytics   import render; render(filters)
    elif page == "🤖 AI Assistant":
        from pages.ai_assistant import render; render(filters)
