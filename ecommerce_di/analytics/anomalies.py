"""
Anomaly detection using statistical methods (Z-score, IQR).
"""
import numpy as np
import pandas as pd
from database.connection import query_df
from config.settings import ANOMALY_ZSCORE_THRESHOLD


def _zscore_anomalies(df: pd.DataFrame,
                       value_col: str,
                       period_col: str = "period",
                       threshold: float = ANOMALY_ZSCORE_THRESHOLD) -> pd.DataFrame:
    """Flag rows where |z-score| > threshold."""
    if df.empty or len(df) < 4:
        return pd.DataFrame()

    mean = df[value_col].mean()
    std  = df[value_col].std()
    if std == 0:
        return pd.DataFrame()

    df = df.copy()
    df["zscore"] = (df[value_col] - mean) / std
    df["is_anomaly"] = df["zscore"].abs() > threshold
    df["direction"]  = df["zscore"].apply(
        lambda z: "spike" if z > 0 else "drop"
    )
    anomalies = df[df["is_anomaly"]].copy()
    anomalies["metric"]    = value_col
    anomalies["magnitude"] = anomalies["zscore"].abs().round(2)
    return anomalies[[period_col, "metric", value_col, "zscore", "direction", "magnitude"]]


def get_revenue_anomalies() -> pd.DataFrame:
    sql = """
        SELECT
            d.year || '-' || printf('%02d', d.month) AS period,
            SUM(o.total_amount) AS revenue
        FROM fact_orders o
        JOIN dim_date d ON o.order_date_id = d.date_id
        GROUP BY period
        ORDER BY period
    """
    df = query_df(sql)
    return _zscore_anomalies(df, "revenue")


def get_refund_anomalies() -> pd.DataFrame:
    sql = """
        SELECT
            d.year || '-' || printf('%02d', d.month) AS period,
            SUM(fp.refund_amount) AS refund_amount
        FROM fact_payments fp
        JOIN dim_date d ON fp.payment_date_id = d.date_id
        GROUP BY period
        ORDER BY period
    """
    df = query_df(sql)
    return _zscore_anomalies(df, "refund_amount")


def get_payment_failure_anomalies() -> pd.DataFrame:
    sql = """
        SELECT
            d.year || '-' || printf('%02d', d.month) AS period,
            COUNT(CASE WHEN payment_status='Failed' THEN 1 END) * 1.0
            / NULLIF(COUNT(*), 0) AS failure_rate
        FROM fact_payments fp
        JOIN dim_date d ON fp.payment_date_id = d.date_id
        GROUP BY period
        ORDER BY period
    """
    df = query_df(sql)
    return _zscore_anomalies(df, "failure_rate")


def get_discount_anomalies() -> pd.DataFrame:
    sql = """
        SELECT
            d.year || '-' || printf('%02d', d.month) AS period,
            AVG(o.discount_amount) AS avg_discount
        FROM fact_orders o
        JOIN dim_date d ON o.order_date_id = d.date_id
        GROUP BY period
        ORDER BY period
    """
    df = query_df(sql)
    return _zscore_anomalies(df, "avg_discount")


def get_all_anomalies() -> pd.DataFrame:
    """Combine all anomaly types into one DataFrame."""
    frames = []
    for fn in [get_revenue_anomalies, get_refund_anomalies,
               get_payment_failure_anomalies, get_discount_anomalies]:
        try:
            df = fn()
            if not df.empty:
                frames.append(df)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values(["period", "magnitude"], ascending=[True, False])
    return result
