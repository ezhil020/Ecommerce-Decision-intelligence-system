"""
Sales analytics functions — reusable by dashboard and AI agent.
"""
import pandas as pd
from database.connection import query_df


# ── Helpers ──────────────────────────────────────────────────────────────────

def _date_filter(start: str | None, end: str | None, alias: str = "o") -> tuple[str, list]:
    """Return (WHERE clause fragment, params) for a date range."""
    clauses, params = [], []
    if start:
        clauses.append(f"{alias}.order_date >= ?")
        params.append(start)
    if end:
        clauses.append(f"{alias}.order_date <= ?")
        params.append(end)
    return (" AND ".join(clauses), params)


def _build_where(filters: dict | None) -> tuple[str, list]:
    """
    Build WHERE clause from a dict of optional filter keys.
    Keys: start_date, end_date, category, sub_category, brand, product_id,
          state, city, membership, payment_mode, order_status.
    """
    filters = filters or {}
    clauses, params = [], []

    if filters.get("start_date"):
        clauses.append("o.order_date >= ?")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        clauses.append("o.order_date <= ?")
        params.append(filters["end_date"])
    if filters.get("category"):
        placeholders = ",".join("?" * len(filters["category"]))
        clauses.append(f"p.category IN ({placeholders})")
        params.extend(filters["category"])
    if filters.get("sub_category"):
        placeholders = ",".join("?" * len(filters["sub_category"]))
        clauses.append(f"p.sub_category IN ({placeholders})")
        params.extend(filters["sub_category"])
    if filters.get("brand"):
        placeholders = ",".join("?" * len(filters["brand"]))
        clauses.append(f"p.brand IN ({placeholders})")
        params.extend(filters["brand"])
    if filters.get("state"):
        placeholders = ",".join("?" * len(filters["state"]))
        clauses.append(f"c.state IN ({placeholders})")
        params.extend(filters["state"])
    if filters.get("city"):
        placeholders = ",".join("?" * len(filters["city"]))
        clauses.append(f"c.city IN ({placeholders})")
        params.extend(filters["city"])
    if filters.get("membership"):
        placeholders = ",".join("?" * len(filters["membership"]))
        clauses.append(f"c.membership_label IN ({placeholders})")
        params.extend(filters["membership"])
    if filters.get("payment_mode"):
        placeholders = ",".join("?" * len(filters["payment_mode"]))
        clauses.append(f"o.payment_mode IN ({placeholders})")
        params.extend(filters["payment_mode"])
    if filters.get("order_status"):
        placeholders = ",".join("?" * len(filters["order_status"]))
        clauses.append(f"o.order_status IN ({placeholders})")
        params.extend(filters["order_status"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# ── Executive KPIs ─────────────────────────────────────────────────────────

def get_executive_kpis(filters: dict | None = None) -> dict:
    where, params = _build_where(filters)
    sql = f"""
        SELECT
            COALESCE(SUM(o.total_amount), 0)                          AS total_revenue,
            COUNT(DISTINCT o.order_id)                                 AS total_orders,
            COUNT(DISTINCT o.customer_id)                              AS total_customers,
            COALESCE(SUM(o.quantity), 0)                               AS total_units_sold,
            COALESCE(AVG(o.total_amount), 0)                           AS avg_order_value,
            COALESCE(SUM(o.discount_amount), 0)                        AS total_discount,
            COALESCE(SUM(o.gross_profit), 0)                           AS total_gross_profit,
            COALESCE(SUM(o.tax_amount), 0)                             AS total_tax,
            COALESCE(SUM(o.shipping_charge), 0)                        AS total_shipping,
            COUNT(CASE WHEN o.order_status IN ('Returned','Cancelled') THEN 1 END) AS returned_cancelled_orders
        FROM fact_orders o
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        LEFT JOIN dim_product  p ON o.product_id  = p.product_id
        {where}
    """
    row = query_df(sql, params).iloc[0].to_dict()

    # Refund total (needs payments join)
    ref_where = where.replace("o.order_date", "fp.payment_date").replace(
        "c.state", "c.state").replace("c.city", "c.city")
    # Simpler: get refunds separately without all filters for now
    ref_sql = f"""
        SELECT COALESCE(SUM(fp.refund_amount),0) AS total_refund
        FROM fact_payments fp
        JOIN fact_orders o ON fp.order_id = o.order_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        LEFT JOIN dim_product  p ON o.product_id  = p.product_id
        {where}
    """
    row["total_refund"] = query_df(ref_sql, params).iloc[0]["total_refund"]

    # Return/cancel rate
    if row["total_orders"] > 0:
        row["return_cancel_rate"] = row["returned_cancelled_orders"] / row["total_orders"]
    else:
        row["return_cancel_rate"] = 0.0

    # Products below reorder
    low_sql = """
        SELECT COUNT(*) AS below_reorder
        FROM dim_product
        WHERE stock_quantity < reorder_level AND product_status = 'Active'
    """
    row["products_below_reorder"] = query_df(low_sql).iloc[0]["below_reorder"]
    row["total_products"] = query_df("SELECT COUNT(*) AS n FROM dim_product").iloc[0]["n"]

    return row


# ── Sales trend ─────────────────────────────────────────────────────────────

def get_sales_trend(granularity: str = "monthly",
                    filters: dict | None = None) -> pd.DataFrame:
    """
    granularity: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
    """
    where, params = _build_where(filters)

    group_map = {
        "daily":     ("d.full_date", "d.full_date"),
        "weekly":    ("d.year || '-W' || printf('%02d', d.week)",
                      "d.year || '-W' || printf('%02d', d.week)"),
        "monthly":   ("d.year || '-' || printf('%02d', d.month)",
                      "d.year || '-' || printf('%02d', d.month)"),
        "quarterly": ("d.year || '-Q' || d.quarter",
                      "d.year || '-Q' || d.quarter"),
        "yearly":    ("CAST(d.year AS TEXT)", "CAST(d.year AS TEXT)"),
    }
    label_expr, group_expr = group_map.get(granularity, group_map["monthly"])

    sql = f"""
        SELECT
            {label_expr}  AS period,
            SUM(o.total_amount)   AS revenue,
            COUNT(o.order_id)     AS orders,
            SUM(o.quantity)       AS units_sold,
            AVG(o.total_amount)   AS avg_order_value,
            SUM(o.gross_profit)   AS gross_profit,
            SUM(o.discount_amount) AS total_discount
        FROM fact_orders o
        JOIN dim_date d ON o.order_date_id = d.date_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        LEFT JOIN dim_product  p ON o.product_id  = p.product_id
        {where}
        GROUP BY {group_expr}
        ORDER BY {group_expr}
    """
    return query_df(sql, params)


# ── Category performance ─────────────────────────────────────────────────────

def get_category_performance(filters: dict | None = None) -> pd.DataFrame:
    where, params = _build_where(filters)
    sql = f"""
        SELECT
            p.category,
            p.sub_category,
            COUNT(DISTINCT p.brand)       AS brand_count,
            COUNT(DISTINCT p.product_id)  AS product_count,
            SUM(o.total_amount)           AS revenue,
            SUM(o.quantity)               AS units_sold,
            SUM(o.gross_profit)           AS gross_profit,
            AVG(p.profit_margin)          AS avg_margin,
            SUM(o.discount_amount)        AS total_discount
        FROM fact_orders o
        JOIN dim_product p ON o.product_id = p.product_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        {where}
        GROUP BY p.category, p.sub_category
        ORDER BY revenue DESC
    """
    return query_df(sql, params)


def get_brand_performance(filters: dict | None = None) -> pd.DataFrame:
    where, params = _build_where(filters)
    sql = f"""
        SELECT
            p.brand,
            p.category,
            SUM(o.total_amount)  AS revenue,
            SUM(o.quantity)      AS units_sold,
            SUM(o.gross_profit)  AS gross_profit,
            AVG(p.profit_margin) AS avg_margin,
            COUNT(o.order_id)    AS orders
        FROM fact_orders o
        JOIN dim_product p ON o.product_id = p.product_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        {where}
        GROUP BY p.brand, p.category
        ORDER BY revenue DESC
    """
    return query_df(sql, params)


# ── Product performance ──────────────────────────────────────────────────────

def get_product_performance(limit: int = 50,
                            sort_by: str = "revenue",
                            filters: dict | None = None) -> pd.DataFrame:
    where, params = _build_where(filters)
    sort_col = sort_by if sort_by in ("revenue","units_sold","gross_profit","orders") else "revenue"
    sql = f"""
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.sub_category,
            p.brand,
            p.selling_price,
            p.cost_price,
            p.profit_margin,
            p.stock_quantity,
            p.reorder_level,
            p.product_rating,
            p.product_status,
            SUM(o.total_amount)    AS revenue,
            SUM(o.quantity)        AS units_sold,
            SUM(o.gross_profit)    AS gross_profit,
            COUNT(o.order_id)      AS orders,
            SUM(o.discount_amount) AS total_discount
        FROM fact_orders o
        JOIN dim_product p ON o.product_id = p.product_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        {where}
        GROUP BY p.product_id, p.product_name, p.category, p.sub_category,
                 p.brand, p.selling_price, p.cost_price, p.profit_margin,
                 p.stock_quantity, p.reorder_level, p.product_rating, p.product_status
        ORDER BY {sort_col} DESC
        LIMIT ?
    """
    return query_df(sql, params + [limit])


# ── Profitability analysis ───────────────────────────────────────────────────

def get_profitability_analysis(filters: dict | None = None) -> pd.DataFrame:
    where, params = _build_where(filters)
    sql = f"""
        SELECT
            p.category,
            p.brand,
            p.product_name,
            p.profit_margin,
            SUM(o.total_amount)    AS revenue,
            SUM(o.gross_profit)    AS gross_profit,
            SUM(o.discount_amount) AS total_discount,
            SUM(o.quantity)        AS units_sold,
            CASE
                WHEN SUM(o.total_amount) > 0
                THEN SUM(o.gross_profit) / SUM(o.total_amount)
                ELSE 0
            END AS effective_margin
        FROM fact_orders o
        JOIN dim_product p ON o.product_id = p.product_id
        LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
        {where}
        GROUP BY p.category, p.brand, p.product_name, p.profit_margin
        ORDER BY effective_margin ASC
    """
    return query_df(sql, params)


# ── Period-over-period comparison ────────────────────────────────────────────

def get_period_comparison(period1_start: str, period1_end: str,
                          period2_start: str, period2_end: str) -> dict:
    def _fetch(s, e):
        sql = """
            SELECT
                COALESCE(SUM(total_amount),0) AS revenue,
                COUNT(order_id)               AS orders,
                COALESCE(SUM(quantity),0)     AS units_sold,
                COALESCE(AVG(total_amount),0) AS aov,
                COALESCE(SUM(gross_profit),0) AS gross_profit
            FROM fact_orders
            WHERE order_date BETWEEN ? AND ?
        """
        return query_df(sql, [s, e]).iloc[0].to_dict()

    p1, p2 = _fetch(period1_start, period1_end), _fetch(period2_start, period2_end)

    result = {"period1": p1, "period2": p2, "changes": {}}
    for key in p1:
        v1, v2 = p1[key], p2[key]
        if v1 != 0:
            result["changes"][key] = (v2 - v1) / abs(v1)
        else:
            result["changes"][key] = None
    return result
