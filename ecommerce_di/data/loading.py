"""
Data loading pipeline: reads CSVs, cleans them, enriches with derived columns,
and loads into the SQLite database.
"""
import logging
from datetime import datetime

import pandas as pd

from config.settings import (
    CUSTOMERS_CSV, ORDERS_CSV, PRODUCTS_CSV, PAYMENTS_CSV
)
from data.cleaning import (
    clean_customers, clean_products, clean_orders, clean_payments,
    build_dim_date, date_to_id,
)
from database.connection import get_connection, create_schema, db_cursor

logger = logging.getLogger(__name__)


def load_all(progress_callback=None) -> dict:
    """
    Full ETL pipeline. Returns a summary dict with row counts and issues.
    progress_callback(step: str, pct: int) → called to update a progress bar.
    """
    summary = {
        "run_time": datetime.now().isoformat(),
        "rows_loaded": {},
        "issues": [],
    }

    def _progress(step, pct):
        if progress_callback:
            progress_callback(step, pct)
        logger.info("[%d%%] %s", pct, step)

    _progress("Creating schema…", 0)
    create_schema()

    # ── Load raw CSVs ─────────────────────────────────────────────────────
    _progress("Reading CSVs…", 5)
    try:
        raw_customers = pd.read_csv(CUSTOMERS_CSV, dtype=str)
        raw_orders    = pd.read_csv(ORDERS_CSV,    dtype=str)
        raw_products  = pd.read_csv(PRODUCTS_CSV,  dtype=str)
        raw_payments  = pd.read_csv(PAYMENTS_CSV,  dtype=str)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Dataset file not found: {exc.filename}\n"
            "Please ensure the CSV files are in the project_ecom_dataset directory."
        )

    # ── Clean ─────────────────────────────────────────────────────────────
    _progress("Cleaning customers…", 10)
    customers, c_issues = clean_customers(raw_customers)
    summary["issues"].extend(c_issues)

    _progress("Cleaning products…", 20)
    products, p_issues = clean_products(raw_products)
    summary["issues"].extend(p_issues)

    _progress("Cleaning orders…", 30)
    valid_customers = set(customers["customer_id"].dropna())
    valid_products  = set(products["product_id"].dropna())
    orders, o_issues = clean_orders(raw_orders, valid_customers, valid_products)
    summary["issues"].extend(o_issues)

    _progress("Cleaning payments…", 40)
    valid_orders = set(orders["order_id"].dropna())
    payments, pay_issues = clean_payments(raw_payments, valid_orders)
    summary["issues"].extend(pay_issues)

    # ── Enrich orders with product cost (for gross_profit) ────────────────
    _progress("Enriching data…", 50)
    prod_cost = products[["product_id", "cost_price", "selling_price"]].copy()
    orders = orders.merge(prod_cost, on="product_id", how="left")
    orders["gross_profit"] = (
        (orders["selling_price"] - orders["cost_price"]) * orders["quantity"]
    )
    # Drop temp columns not needed in fact table
    orders = orders.drop(columns=["cost_price", "selling_price"], errors="ignore")

    # ── Build dim_date ─────────────────────────────────────────────────────
    _progress("Building date dimension…", 55)
    all_dates = (
        list(customers["registration_date"].dropna()) +
        list(customers["date_of_birth"].dropna()) +
        list(products["launch_date"].dropna()) +
        list(orders["order_date"].dropna()) +
        list(payments["payment_date"].dropna()) +
        list(payments["refund_date"].dropna())
    )
    dim_date = build_dim_date(all_dates)

    # Add date_id foreign keys
    def _add_date_id(df, date_col, id_col):
        df[id_col] = df[date_col].apply(date_to_id)
        return df

    customers = _add_date_id(customers, "registration_date", "registration_date_id")
    products  = _add_date_id(products,  "launch_date",        "launch_date_id")
    orders    = _add_date_id(orders,    "order_date",         "order_date_id")
    payments  = _add_date_id(payments,  "payment_date",       "payment_date_id")

    # ── Write to DB ────────────────────────────────────────────────────────
    _progress("Writing to database…", 60)
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ai_interaction_log")
        conn.execute("DELETE FROM recommendations")
        conn.execute("DELETE FROM data_quality_log")
        conn.execute("DELETE FROM fact_payments")
        conn.execute("DELETE FROM fact_orders")
        conn.execute("DELETE FROM dim_product")
        conn.execute("DELETE FROM dim_customer")
        conn.execute("DELETE FROM dim_date")
        conn.commit()

        _progress("Loading dim_date…", 65)
        dim_date.to_sql("dim_date", conn, if_exists="append", index=False)

        _progress("Loading dim_customer…", 70)
        _df_to_sql(customers, "dim_customer", conn,
                   columns=["customer_id","name","gender","age","date_of_birth",
                             "email","phone","city","state","country","pincode",
                             "registration_date","registration_date_id",
                             "membership_label","loyalty_points","preferred_device"])

        _progress("Loading dim_product…", 75)
        _df_to_sql(products, "dim_product", conn,
                   columns=["product_id","product_name","category","sub_category",
                             "brand","sku","cost_price","selling_price","profit_margin",
                             "discount_pct","stock_quantity","reorder_level",
                             "product_rating","launch_date","launch_date_id","product_status"])

        _progress("Loading fact_orders…", 82)
        _df_to_sql(orders, "fact_orders", conn,
                   columns=["order_id","order_date","order_date_id","customer_id",
                             "product_id","product_name","quantity","unit_price",
                             "discount_amount","tax_amount","shipping_charge",
                             "payment_mode","order_status","total_amount",
                             "gross_revenue","net_revenue","gross_profit"])

        _progress("Loading fact_payments…", 90)
        _df_to_sql(payments, "fact_payments", conn,
                   columns=["payment_id","order_id","payment_date","payment_date_id",
                             "payment_mode","payment_status","transaction_fee",
                             "refund_amount","refund_date"])

        # ── Write data quality log ─────────────────────────────────────────
        if summary["issues"]:
            now_str = datetime.now().isoformat()
            rows = [(now_str, i.get("table",""), i.get("issue",""),
                     str(i), i.get("count", 0))
                    for i in summary["issues"]]
            conn.executemany(
                "INSERT INTO data_quality_log(run_time,table_name,issue_type,description,row_count) "
                "VALUES(?,?,?,?,?)", rows)
            conn.commit()

        summary["rows_loaded"] = {
            "customers": len(customers),
            "products":  len(products),
            "orders":    len(orders),
            "payments":  len(payments),
            "dates":     len(dim_date),
        }

    finally:
        conn.close()

    _progress("Synchronizing AI chart inferences for new data…", 95)
    try:
        from analytics.inferences import refresh_all_chart_inferences
        inf_count = refresh_all_chart_inferences()
        summary["inferences_refreshed"] = inf_count
    except Exception as e:
        logger.warning("Could not auto-refresh inferences during load: %s", e)

    _progress("Done!", 100)
    logger.info("ETL complete: %s", summary["rows_loaded"])
    return summary



def _df_to_sql(df: pd.DataFrame, table: str, conn, columns: list):
    """Write only the specified columns to the table, ignoring extras."""
    cols_present = [c for c in columns if c in df.columns]
    df[cols_present].to_sql(table, conn, if_exists="append", index=False)
