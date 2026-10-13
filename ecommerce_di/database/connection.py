"""
Database connection and schema management using SQLite.
Star-schema design: dim_customer, dim_product, dim_date, fact_orders, fact_payments.
"""
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


# ── Connection ─────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_cursor():
    """Context-manager that yields a cursor and auto-commits / rolls back."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("DB error: %s", exc)
        raise
    finally:
        conn.close()


def query_df(sql: str, params=None):
    """Execute a SELECT and return a pandas DataFrame."""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params or [])
        return df
    finally:
        conn.close()


# ── Schema ─────────────────────────────────────────────────────────────────

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     INTEGER PRIMARY KEY,   -- YYYYMMDD int key
    full_date   TEXT NOT NULL,
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    month_name  TEXT,
    week        INTEGER,
    day         INTEGER,
    day_of_week TEXT
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id         TEXT PRIMARY KEY,
    name                TEXT,
    gender              TEXT,
    age                 INTEGER,
    date_of_birth       TEXT,
    email               TEXT,
    phone               TEXT,
    city                TEXT,
    state               TEXT,
    country             TEXT,
    pincode             TEXT,
    registration_date   TEXT,
    registration_date_id INTEGER REFERENCES dim_date(date_id),
    membership_label    TEXT,
    loyalty_points      REAL,
    preferred_device    TEXT
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT,
    category        TEXT,
    sub_category    TEXT,
    brand           TEXT,
    sku             TEXT,
    cost_price      REAL,
    selling_price   REAL,
    profit_margin   REAL,
    discount_pct    REAL,
    stock_quantity  INTEGER,
    reorder_level   INTEGER,
    product_rating  REAL,
    launch_date     TEXT,
    launch_date_id  INTEGER REFERENCES dim_date(date_id),
    product_status  TEXT
);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id        TEXT PRIMARY KEY,
    order_date      TEXT,
    order_date_id   INTEGER REFERENCES dim_date(date_id),
    customer_id     TEXT REFERENCES dim_customer(customer_id),
    product_id      TEXT REFERENCES dim_product(product_id),
    product_name    TEXT,
    quantity        INTEGER,
    unit_price      REAL,
    discount_amount REAL,
    tax_amount      REAL,
    shipping_charge REAL,
    payment_mode    TEXT,
    order_status    TEXT,
    total_amount    REAL,
    -- derived
    gross_revenue   REAL,   -- unit_price * quantity
    net_revenue     REAL,   -- total_amount
    gross_profit    REAL    -- (selling_price - cost_price) * quantity
);

CREATE TABLE IF NOT EXISTS fact_payments (
    payment_id      TEXT PRIMARY KEY,
    order_id        TEXT REFERENCES fact_orders(order_id),
    payment_date    TEXT,
    payment_date_id INTEGER REFERENCES dim_date(date_id),
    payment_mode    TEXT,
    payment_status  TEXT,
    transaction_fee REAL,
    refund_amount   REAL,
    refund_date     TEXT
);

-- ── Data quality log ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_quality_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_time    TEXT,
    table_name  TEXT,
    issue_type  TEXT,
    description TEXT,
    row_count   INTEGER
);

-- ── Recommendations ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    rec_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at    TEXT,
    rec_type        TEXT,   -- inventory / product / payment / customer
    entity          TEXT,
    reason          TEXT,
    suggested_action TEXT,
    status          TEXT DEFAULT 'New',  -- New/Reviewed/Accepted/Rejected/Implemented
    action_date     TEXT,
    outcome         TEXT
);

-- ── AI conversation log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_interaction_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT,
    user_query  TEXT,
    tools_used  TEXT,
    response_summary TEXT
);

-- ── Chart Inferences (Persistent LLM Insights per Visualization) ───────────
CREATE TABLE IF NOT EXISTS chart_inferences (
    inference_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_key       TEXT NOT NULL,
    data_hash       TEXT NOT NULL,
    title           TEXT NOT NULL,
    inference_text  TEXT NOT NULL,
    key_takeaway    TEXT,
    impact_level    TEXT DEFAULT 'info',  -- positive, warning, danger, info
    generated_at    TEXT,
    source          TEXT DEFAULT 'llm'    -- baseline, llm, rule_engine
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chart_data_hash ON chart_inferences(chart_key, data_hash);
"""


def create_schema():
    """Create all tables if they don't exist."""
    conn = get_connection()
    try:
        conn.executescript(DDL)
        conn.commit()
        logger.info("Database schema ensured.")
    finally:
        conn.close()


def db_exists() -> bool:
    """Return True if the database has been populated (fact_orders has rows)."""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_orders")
            return cur.fetchone()[0] > 0
    except Exception:
        return False
