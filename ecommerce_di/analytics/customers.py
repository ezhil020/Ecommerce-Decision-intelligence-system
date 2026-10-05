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
    Segment customers into: High Value, Frequent, New, Returning, Low Engagement.
    Uses percentile thresholds from config.
    """
    sql = """
        SELECT
            c.customer_id,
            c.name,
            c.membership_label,
            c.registration_date,
            COUNT(o.order_id)   AS order_count,
            SUM(o.total_amount) AS total_revenue,
            MAX(o.order_date)   AS last_order_date,
            JULIANDAY('now') - JULIANDAY(c.registration_date) AS days_since_registration
        FROM dim_customer c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.membership_label,
                 c.registration_date
    """
    df = query_df(sql)
    if df.empty:
        return df

    rev_p  = df["total_revenue"].quantile(HIGH_VALUE_REVENUE_PERCENTILE / 100)
    ord_p  = df["order_count"].quantile(FREQUENT_ORDER_PERCENTILE / 100)

    def segment(row):
        if row["days_since_registration"] is not None and row["days_since_registration"] <= NEW_CUSTOMER_DAYS:
            return "New"
        if row["total_revenue"] >= rev_p:
            return "High Value"
        if row["order_count"] >= ord_p and row["order_count"] > 1:
            return "Frequent"
        if row["order_count"] > 1:
            return "Returning"
        return "Low Engagement"

    df["segment"] = df.apply(segment, axis=1)
    return df


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
