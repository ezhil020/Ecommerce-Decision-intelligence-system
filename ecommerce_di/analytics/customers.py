"""
Customer analytics — segmentation, geographic, demographic, loyalty.
"""
import pandas as pd
from database.connection import query_df
from config.settings import (
    HIGH_VALUE_REVENUE_PERCENTILE,
    FREQUENT_ORDER_PERCENTILE,
    NEW_CUSTOMER_DAYS,
)


def get_customer_overview(filters: dict | None = None) -> dict:
    sql = """
        SELECT
            COUNT(DISTINCT c.customer_id)       AS total_customers,
            AVG(c.age)                          AS avg_age,
            AVG(c.loyalty_points)               AS avg_loyalty_points,
            COUNT(DISTINCT c.state)             AS states_covered,
            COUNT(DISTINCT c.city)              AS cities_covered
        FROM dim_customer c
    """
    return query_df(sql).iloc[0].to_dict()


def get_customer_revenue(top_n: int = 50, filters: dict | None = None) -> pd.DataFrame:
    sql = f"""
        SELECT
            c.customer_id,
            c.name,
            c.gender,
            c.age,
            c.state,
            c.city,
            c.membership_label,
            c.loyalty_points,
            c.preferred_device,
            c.registration_date,
            COUNT(o.order_id)      AS order_count,
            SUM(o.total_amount)    AS total_revenue,
            AVG(o.total_amount)    AS avg_order_value,
            SUM(o.quantity)        AS total_units
        FROM dim_customer c
        JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.gender, c.age, c.state, c.city,
                 c.membership_label, c.loyalty_points, c.preferred_device, c.registration_date
        ORDER BY total_revenue DESC
        LIMIT ?
    """
    return query_df(sql, [top_n])


def get_customer_segmentation() -> pd.DataFrame:
    """
    Segment customers into meaningful behavioral cohorts based on spend level
    and loyalty engagement:
      - VIP Champions: Top-tier revenue & High loyalty points
      - High Spenders: Top-tier revenue, lower loyalty (upsell to loyalty)
      - Loyal Advocates: High loyalty points, moderate spend
      - Core Customers: Steady spenders above median
      - Budget / Casual Shoppers: Entry-level spenders
    """
    sql = """
        SELECT
            c.customer_id,
            c.name,
            c.membership_label,
            c.loyalty_points,
            c.preferred_device,
            c.registration_date,
            COUNT(o.order_id)   AS order_count,
            COALESCE(SUM(o.total_amount), 0) AS total_revenue,
            MAX(o.order_date)   AS last_order_date
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.membership_label,
                 c.loyalty_points, c.preferred_device, c.registration_date
    """
    df = query_df(sql)
    if df.empty:
        return df

    rev_top = df["total_revenue"].quantile(0.80)
    rev_mid = df["total_revenue"].quantile(0.50)
    loyalty_high = df["loyalty_points"].quantile(0.65)

    def segment(row):
        rev = row["total_revenue"]
        loy = row["loyalty_points"]
        if rev >= rev_top and loy >= loyalty_high:
            return "VIP Champions"
        elif rev >= rev_top:
            return "High Spenders"
        elif loy >= loyalty_high:
            return "Loyal Advocates"
        elif rev >= rev_mid:
            return "Core Customers"
        else:
            return "Budget / Casual"

    df["segment"] = df.apply(segment, axis=1)
    return df


def get_device_channel_analysis() -> pd.DataFrame:
    """Breakdown of customer orders, revenue and average spend by device and membership."""
    sql = """
        SELECT
            c.preferred_device,
            c.membership_label,
            COUNT(DISTINCT c.customer_id) AS customers,
            COUNT(o.order_id)             AS orders,
            ROUND(SUM(o.total_amount), 0) AS revenue,
            ROUND(AVG(o.total_amount), 0) AS avg_spend,
            ROUND(AVG(c.loyalty_points), 0) AS avg_loyalty
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.preferred_device, c.membership_label
        ORDER BY c.preferred_device, revenue DESC
    """
    return query_df(sql)


def get_geographic_analysis() -> pd.DataFrame:
    sql = """
        SELECT
            c.state,
            c.city,
            COUNT(DISTINCT c.customer_id) AS customers,
            COUNT(o.order_id)             AS orders,
            SUM(o.total_amount)           AS revenue,
            AVG(o.total_amount)           AS avg_order_value
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.state, c.city
        ORDER BY revenue DESC
    """
    return query_df(sql)


def get_demographic_analysis() -> pd.DataFrame:
    sql = """
        SELECT
            c.gender,
            c.membership_label,
            c.preferred_device,
            CASE
                WHEN c.age < 25 THEN 'Under 25'
                WHEN c.age < 35 THEN '25-34'
                WHEN c.age < 45 THEN '35-44'
                WHEN c.age < 55 THEN '45-54'
                ELSE '55+'
            END AS age_group,
            COUNT(DISTINCT c.customer_id) AS customers,
            SUM(o.total_amount)           AS revenue,
            COUNT(o.order_id)             AS orders,
            AVG(c.loyalty_points)         AS avg_loyalty_points
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.gender, c.membership_label, c.preferred_device, age_group
        ORDER BY revenue DESC
    """
    return query_df(sql)


def get_membership_analysis() -> pd.DataFrame:
    sql = """
        SELECT
            c.membership_label,
            COUNT(DISTINCT c.customer_id) AS customers,
            SUM(o.total_amount)           AS revenue,
            COUNT(o.order_id)             AS orders,
            AVG(o.total_amount)           AS avg_order_value,
            AVG(c.loyalty_points)         AS avg_loyalty_points
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.membership_label
        ORDER BY revenue DESC
    """
    return query_df(sql)
