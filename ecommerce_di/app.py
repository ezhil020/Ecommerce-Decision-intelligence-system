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

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: #0f111a !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}

[data-testid="block-container"] {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
}

h1, h2, h3, h4 { 
    font-family: 'Inter', sans-serif !important; 
    font-weight: 600 !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: rgba(20,20,30,0.4) !important;
    border-radius: 8px !important;
    padding: 2px !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    font-size: 0.9rem !important;
    padding: 8px 16px !important;
}

[data-testid="stMetricValue"] { font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; opacity: 0.8; }

.stDataFrame { border-radius: 8px !important; overflow: hidden !important; border: 1px solid rgba(255,255,255,0.1); }
hr { border-color: rgba(255,255,255,0.1) !important; }

/* Customizing scrollbar for cleaner look */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(100,100,100,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(100,100,100,0.8); }
</style>
""", unsafe_allow_html=True)


# ── Sidebar brand header ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 12px 0 16px; text-align:center; border-bottom: 1px solid rgba(99,102,241,0.2); margin-bottom:12px">
        <div style="font-size:2rem">📊</div>
        <div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-top:4px">Decision Intelligence</div>
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em">E-COMMERCE BI PLATFORM</div>
    </div>
    """, unsafe_allow_html=True)

    # Live Data Fingerprint Pill
    if db_exists():
        from analytics.inferences import get_current_data_fingerprint
        from database.connection import query_df
        data_hash = get_current_data_fingerprint()
        cnt_row = query_df("SELECT COUNT(*) AS n, COALESCE(SUM(total_amount), 0) AS rev FROM fact_orders").iloc[0]
        st.markdown(f"""
        <div style="
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 8px;
            padding: 8px 10px;
            margin-bottom: 14px;
            font-size: 0.73rem;
            color: #cbd5e1;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px;">
                <span style="font-weight: 600; color: #6ee7b7;">🟢 Warehouse Live</span>
                <span style="background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 4px; font-size: 0.65rem; color: #94a3b8;">v:{data_hash[:6]}</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.70rem;">
                Orders: <b style="color: #f1f5f9;">{int(cnt_row['n']):,}</b> &nbsp;|&nbsp; Rev: <b style="color: #f1f5f9;">₹{cnt_row['rev']/1e7:.2f}Cr</b>
            </div>
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
        label_visibility="collapsed"
    )

    st.markdown("---")
    
    # ── Filters ───────────────────────────────────────────────────────────────
    filters = {}
    with st.expander("🔍 Global Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From", value=None, format="YYYY-MM-DD")
        with col2:
            end_date   = st.date_input("To",   value=None, format="YYYY-MM-DD")

        if start_date:
            filters["start_date"] = str(start_date)
        if end_date:
            filters["end_date"] = str(end_date)

        # Dynamic filter options from DB (only if DB exists)
        if db_exists():
            from database.connection import query_df

            cats = query_df("SELECT DISTINCT category FROM dim_product ORDER BY category")["category"].dropna().tolist()
            sel_cats = st.multiselect("Category", cats)
            if sel_cats:
                filters["category"] = sel_cats

            states = query_df("SELECT DISTINCT state FROM dim_customer WHERE state IS NOT NULL ORDER BY state")["state"].dropna().tolist()
            sel_states = st.multiselect("State", states)
            if sel_states:
                filters["state"] = sel_states

            memberships = query_df("SELECT DISTINCT membership_label FROM dim_customer WHERE membership_label IS NOT NULL ORDER BY membership_label")["membership_label"].dropna().tolist()
            sel_mem = st.multiselect("Membership", memberships)
            if sel_mem:
                filters["membership"] = sel_mem

            pay_modes = query_df("SELECT DISTINCT payment_mode FROM fact_orders ORDER BY payment_mode")["payment_mode"].dropna().tolist()
            sel_pay = st.multiselect("Payment Mode", pay_modes)
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

    # ── Data Management Tabs ───────────────────────────────────────────────
    st.markdown("---")
    tab_entry, tab_csv, tab_inf = st.tabs([
        "⚡ Quick Record Entry",
        "📤 Upload / Append CSV Dataset",
        "🧠 AI Inferences Studio",
    ])

    # ─────────────── TAB 1: QUICK RECORD ENTRY ────────────────────────────────
    with tab_entry:
        st.markdown("### ➕ Instant Transaction Entry")
        st.markdown(
            '<p style="color:#94a3b8;font-size:0.83rem">'
            'Directly insert a new transaction to test live data updates. '
            'The system immediately writes to the dataset, updates fact tables, re-evaluates all metrics, '
            'and refreshes AI inferences across the entire dashboard.'
            '</p>',
            unsafe_allow_html=True,
        )

        from database.connection import query_df
        import pandas as pd
        from datetime import date

        # Fetch product and customer lists if DB exists
        prod_options = {}
        if db_exists():
            prods_df = query_df("SELECT product_id, product_name, category, selling_price FROM dim_product ORDER BY product_name LIMIT 100")
            for _, r in prods_df.iterrows():
                label = f"{r['product_name']} ({r['category']}) — ₹{r['selling_price']:,.0f}"
                prod_options[label] = {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "unit_price": float(r["selling_price"] or 0),
                }

        with st.form("manual_order_form", clear_on_submit=False):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                sel_prod_label = st.selectbox(
                    "Product",
                    list(prod_options.keys()) if prod_options else ["Standard Product"],
                    key="form_sel_product"
                )
                cust_id_input = st.text_input("Customer ID", value="CUST-0001", key="form_cust_id")
                order_date_input = st.date_input("Order Date", value=date.today(), key="form_order_date")
                payment_mode_input = st.selectbox(
                    "Payment Mode",
                    ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery"],
                    key="form_pay_mode"
                )

            with f_col2:
                qty_input = st.number_input("Quantity", min_value=1, max_value=50, value=2, key="form_qty")
                default_price = prod_options[sel_prod_label]["unit_price"] if prod_options and sel_prod_label in prod_options else 2500.0
                unit_price_input = st.number_input("Unit Price (₹)", min_value=1.0, value=default_price, step=100.0, key="form_unit_price")
                disc_input = st.number_input("Discount Amount (₹)", min_value=0.0, value=150.0, step=50.0, key="form_disc")
                order_status_input = st.selectbox(
                    "Order Status",
                    ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"],
                    key="form_order_status"
                )

            subtotal = qty_input * unit_price_input
            total_calc = max(0.0, subtotal - disc_input)
            st.info(f"💰 Calculated Order Total: **₹{total_calc:,.2f}** (Gross: ₹{subtotal:,.2f} - Discount: ₹{disc_input:,.2f})")

            submitted_entry = st.form_submit_button("⚡ Submit Transaction & Update Complete Dashboard", type="primary", use_container_width=True)

        if submitted_entry:
            try:
                import time
                new_order_id = f"ORD-LIVE-{int(time.time())}"
                new_pay_id = f"PAY-LIVE-{int(time.time())}"
                sel_info = prod_options.get(sel_prod_label, {"product_id": "P-999", "product_name": "Product"})

                # 1. Append to Orders.csv
                orders_path = files["Orders.csv"]
                existing_orders = pd.read_csv(orders_path, dtype=str) if orders_path.exists() else pd.DataFrame()
                new_order_data = {
                    "order_id": new_order_id,
                    "order_date": str(order_date_input),
                    "customer_id": cust_id_input.strip(),
                    "product_id": sel_info["product_id"],
                    "product_name": sel_info["product_name"],
                    "quantity": str(qty_input),
                    "unit_price": str(unit_price_input),
                    "discount_amount": str(disc_input),
                    "tax_amount": str(round(total_calc * 0.05, 2)),
                    "shipping_charge": "0",
                    "payment_mode": payment_mode_input,
                    "order_status": order_status_input,
                    "total_amount": str(round(total_calc, 2)),
                }
                order_row_mapped = {}
                for col in existing_orders.columns:
                    norm = col.strip().lower().replace(" (nos.)", "").replace(" ", "_")
                    order_row_mapped[col] = new_order_data.get(norm, "")

                updated_orders = pd.concat([existing_orders, pd.DataFrame([order_row_mapped])], ignore_index=True)
                updated_orders.to_csv(orders_path, index=False)

                # 2. Append to Payments.csv
                payments_path = files["Payments.csv"]
                existing_payments = pd.read_csv(payments_path, dtype=str) if payments_path.exists() else pd.DataFrame()
                new_pay_data = {
                    "payment_id": new_pay_id,
                    "order_id": new_order_id,
                    "payment_date": str(order_date_input),
                    "payment_mode": payment_mode_input,
                    "payment_status": "Success" if order_status_input in ["Delivered", "Shipped", "Processing"] else "Failed",
                    "transaction_fee": str(round(total_calc * 0.015, 2)),
                    "refund_amount": str(round(total_calc, 2)) if order_status_input == "Returned" else "0",
                    "refund_date": str(order_date_input) if order_status_input == "Returned" else "",
                }
                pay_row_mapped = {}
                for col in existing_payments.columns:
                    norm = col.strip().lower().replace(" ", "_")
                    pay_row_mapped[col] = new_pay_data.get(norm, "")

                updated_payments = pd.concat([existing_payments, pd.DataFrame([pay_row_mapped])], ignore_index=True)
                updated_payments.to_csv(payments_path, index=False)


                # 3. Rebuild star schema warehouse & refresh inferences
                with st.spinner("Rebuilding warehouse and updating all dashboard analytics & inferences…"):
                    summary = load_all()
                    st.success(
                        f"✅ **New Transaction {new_order_id} recorded successfully!** "
                        f"Warehouse updated to {summary['rows_loaded'].get('orders', 0):,} orders. "
                        f"All charts, metrics, and AI inferences are now refreshed."
                    )
                    st.rerun()

            except Exception as ex:
                st.error(f"Error inserting transaction: {ex}")
                logger.exception("Error inserting transaction")

    # ─────────────── TAB 2: UPLOAD CSV ────────────────────────────────────────
    with tab_csv:
        st.markdown("### 📤 Upload / Append CSV Dataset")
        col_up1, col_up2 = st.columns([1, 2])
        with col_up1:
            target_file_name = st.selectbox(
                "Target Dataset Table",
                ["Orders.csv", "Customers.csv", "Products.csv", "Payments.csv"],
                key="target_upload_table",
            )
            upload_mode = st.radio(
                "Import Mode",
                ["Append new rows to existing data", "Replace existing file completely"],
                key="upload_mode_choice",
            )
        with col_up2:
            uploaded_file = st.file_uploader(
                f"Upload new CSV for {target_file_name}",
                type=["csv"],
                key="csv_file_uploader",
            )

        if uploaded_file is not None:
            try:
                import pandas as pd
                new_df = pd.read_csv(uploaded_file, dtype=str)
                st.write(f"Preview of uploaded data ({len(new_df):,} rows, {len(new_df.columns)} columns):")
                st.dataframe(new_df.head(5), use_container_width=True)

                if st.button("💾 Save & Rebuild Warehouse", type="primary", key="save_rebuild_btn"):
                    target_path = files[target_file_name]
                    if upload_mode == "Append new rows to existing data" and target_path.exists():
                        existing_df = pd.read_csv(target_path, dtype=str)
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                        pk_col = {
                            "Orders.csv": "order_id",
                            "Customers.csv": "customer_id",
                            "Products.csv": "product_id",
                            "Payments.csv": "payment_id",
                        }.get(target_file_name)
                        if pk_col and pk_col in combined_df.columns:
                            combined_df = combined_df.drop_duplicates(subset=[pk_col], keep="last")
                        combined_df.to_csv(target_path, index=False)
                        st.success(f"Appended {len(new_df)} rows. Total rows now: {len(combined_df):,}.")
                    else:
                        new_df.to_csv(target_path, index=False)
                        st.success(f"Replaced {target_file_name} with {len(new_df):,} rows.")

                    # Trigger ETL
                    with st.spinner("Rebuilding Star Schema & updating all metrics & inferences…"):
                        summary = load_all()
                        st.success("✅ Warehouse successfully updated! All dashboards and AI tools are now in sync.")
                        st.rerun()

            except Exception as ex:
                st.error(f"Error reading uploaded file: {ex}")

    # ─────────────── TAB 3: INFERENCES STUDIO ──────────────────────────────────
    with tab_inf:
        st.markdown("### 🧠 AI Chart Inferences Management")
        st.markdown(
            '<p style="color:#94a3b8;font-size:0.83rem">'
            'Inferences are stored persistently in SQLite keyed to the dataset fingerprint. '
            'They do not consume LLM calls on regular dashboard visits. When data changes, '
            'they automatically synchronize with the new numbers.'
            '</p>',
            unsafe_allow_html=True,
        )

        from analytics.inferences import get_current_data_fingerprint, refresh_all_chart_inferences
        from database.connection import query_df

        current_hash = get_current_data_fingerprint()
        st.markdown(f"**Current Data Fingerprint:** `v-{current_hash}`")

        c_sync1, c_sync2 = st.columns([1, 2])
        with c_sync1:
            run_llm_batch = st.button("🤖 Batch Re-analyze with Ollama (Qwen2.5)", use_container_width=True)
        with c_sync2:
            run_fast_sync = st.button("⚡ Fast Analytical Inferences Re-sync", use_container_width=True)

        if run_llm_batch or run_fast_sync:
            prog = st.progress(0, text="Synchronizing chart inferences…")
            def _inf_cb(step, pct):
                prog.progress(pct / 100, text=step)

            use_llm_flag = True if run_llm_batch else False
            total_refreshed = refresh_all_chart_inferences(use_llm=use_llm_flag, progress_callback=_inf_cb)
            prog.progress(1.0, text="Complete!")
            st.success(f"✅ Successfully synchronized {total_refreshed} chart inferences for data hash {current_hash}!")
            st.rerun()

        # View stored inferences
        if db_exists():
            inf_df = query_df("""
                SELECT chart_key, title, impact_level, inference_text, key_takeaway, source, generated_at
                FROM chart_inferences
                WHERE data_hash = ?
                ORDER BY inference_id ASC
            """, [current_hash])

            if not inf_df.empty:
                st.markdown(f"#### Active Inferences ({len(inf_df)} items stored)")
                st.dataframe(
                    inf_df.rename(columns={
                        "chart_key": "Chart Key",
                        "title": "Visualization",
                        "impact_level": "Impact",
                        "inference_text": "Inference Summary",
                        "key_takeaway": "Action Recommendation",
                        "source": "Engine Source",
                        "generated_at": "Last Updated",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No inferences stored yet for current data fingerprint. Click 'Fast Analytical Inferences Re-sync' above.")



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
        from views.overview    import render; render(filters)
    elif page == "📈 Sales Intelligence":
        from views.sales       import render; render(filters)
    elif page == "📦 Products & Inventory":
        from views.products    import render; render(filters)
    elif page == "👥 Customer Intelligence":
        from views.customers   import render; render(filters)
    elif page == "💳 Payments & Operations":
        from views.payments    import render; render(filters)
    elif page == "🔬 Advanced Analytics":
        from views.analytics   import render; render(filters)
    elif page == "🤖 AI Assistant":
        from views.ai_assistant import render; render(filters)
