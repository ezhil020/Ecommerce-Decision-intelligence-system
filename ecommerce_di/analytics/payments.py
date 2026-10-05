"""
Payment and refund analytics.
"""
import pandas as pd
from database.connection import query_df


def get_payment_overview(filters: dict | None = None) -> dict:
    sql = """
        SELECT
            COUNT(*)                                              AS total_payments,
            SUM(CASE WHEN payment_status='Success' THEN 1 ELSE 0 END)  AS successful,
            SUM(CASE WHEN payment_status='Failed'  THEN 1 ELSE 0 END)  AS failed,
            SUM(CASE WHEN payment_status='Pending' THEN 1 ELSE 0 END)  AS pending,
            COALESCE(SUM(transaction_fee), 0)                    AS total_fees,
            COALESCE(SUM(refund_amount),   0)                    AS total_refunds,
            COALESCE(AVG(transaction_fee), 0)                    AS avg_fee
        FROM fact_payments
    """
    return query_df(sql).iloc[0].to_dict()


def get_payment_method_analysis() -> pd.DataFrame:
    sql = """
        SELECT
            fp.payment_mode,
            COUNT(*)                                                       AS total_payments,
            SUM(CASE WHEN fp.payment_status='Success' THEN 1 ELSE 0 END)  AS successful,
            SUM(CASE WHEN fp.payment_status='Failed'  THEN 1 ELSE 0 END)  AS failed,
            ROUND(
                100.0 * SUM(CASE WHEN fp.payment_status='Failed' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            )                                                              AS failure_rate_pct,
            COALESCE(SUM(fp.transaction_fee), 0)                           AS total_fees,
            COALESCE(SUM(o.total_amount), 0)                               AS total_volume
        FROM fact_payments fp
        JOIN fact_orders o ON fp.order_id = o.order_id
        GROUP BY fp.payment_mode
        ORDER BY total_volume DESC
    """
    return query_df(sql)


def get_refund_analysis(filters: dict | None = None) -> pd.DataFrame:
    sql = """
        SELECT
            p.category,
            p.sub_category,
            fp.payment_mode,
            COUNT(CASE WHEN fp.refund_amount > 0 THEN 1 END)  AS refund_count,
            COALESCE(SUM(fp.refund_amount), 0)                 AS total_refund,
            COALESCE(AVG(fp.refund_amount), 0)                 AS avg_refund,
            COUNT(o.order_id)                                   AS total_orders,
            ROUND(
                100.0 * COUNT(CASE WHEN fp.refund_amount > 0 THEN 1 END)
                / NULLIF(COUNT(o.order_id), 0), 2
            ) AS refund_rate_pct
        FROM fact_payments fp
        JOIN fact_orders o ON fp.order_id = o.order_id
        JOIN dim_product p ON o.product_id = p.product_id
        GROUP BY p.category, p.sub_category, fp.payment_mode
        ORDER BY total_refund DESC
    """
    return query_df(sql)


def get_refund_trend(granularity: str = "monthly") -> pd.DataFrame:
    group_map = {
        "monthly":   "d.year || '-' || printf('%02d', d.month)",
        "quarterly": "d.year || '-Q' || d.quarter",
        "yearly":    "CAST(d.year AS TEXT)",
    }
    group_expr = group_map.get(granularity, group_map["monthly"])
    sql = f"""
        SELECT
            {group_expr}            AS period,
            COUNT(fp.payment_id)    AS payments,
            SUM(fp.refund_amount)   AS refund_amount,
            COUNT(CASE WHEN fp.refund_amount > 0 THEN 1 END) AS refund_count
        FROM fact_payments fp
        JOIN dim_date d ON fp.payment_date_id = d.date_id
        GROUP BY {group_expr}
        ORDER BY {group_expr}
    """
    return query_df(sql)


def get_order_status_breakdown(filters: dict | None = None) -> pd.DataFrame:
    sql = """
        SELECT
            order_status,
            COUNT(*)            AS orders,
            SUM(total_amount)   AS revenue,
            SUM(quantity)       AS units
        FROM fact_orders
        GROUP BY order_status
        ORDER BY orders DESC
    """
    return query_df(sql)
