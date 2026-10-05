"""
Forecasting module — sales trend forecasting using exponential smoothing (Holt-Winters)
and simple moving average as fallback.
"""
import logging
import numpy as np
import pandas as pd
from database.connection import query_df
from config.settings import FORECAST_PERIODS

logger = logging.getLogger(__name__)


def _get_monthly_revenue() -> pd.DataFrame:
    sql = """
        SELECT
            d.year || '-' || printf('%02d', d.month) AS period,
            d.year,
            d.month,
            SUM(o.total_amount) AS revenue,
            COUNT(o.order_id)   AS orders
        FROM fact_orders o
        JOIN dim_date d ON o.order_date_id = d.date_id
        WHERE o.order_status NOT IN ('Cancelled','Returned')
        GROUP BY d.year, d.month
        ORDER BY d.year, d.month
    """
    return query_df(sql)


def _next_periods(last_year: int, last_month: int, n: int) -> list[str]:
    """Generate next n month labels after the given year-month."""
    periods = []
    y, m = last_year, last_month
    for _ in range(n):
        m += 1
        if m > 12:
            m = 1
            y += 1
        periods.append(f"{y}-{m:02d}")
    return periods


def forecast_revenue(periods: int = FORECAST_PERIODS) -> dict:
    """
    Forecast monthly revenue using Holt-Winters Exponential Smoothing.
    Returns dict with 'historical', 'forecast', 'method'.
    """
    df = _get_monthly_revenue()

    if df.empty or len(df) < 3:
        return {
            "error": "Insufficient historical data for forecasting (need ≥ 3 months).",
            "historical": df,
            "forecast": pd.DataFrame(),
            "method": "none",
        }

    series = df["revenue"].values.astype(float)
    method = "unknown"

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        # Use additive trend; seasonal if enough data
        seasonal = "add" if len(series) >= 24 else None
        sp = 12 if seasonal else None
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=seasonal,
            seasonal_periods=sp,
            initialization_method="estimated",
        ).fit(optimized=True, use_brute=False)
        forecast_vals = model.forecast(periods)
        method = "Holt-Winters Exponential Smoothing"
    except Exception as exc:
        logger.warning("Holt-Winters failed (%s), falling back to moving average.", exc)
        # Simple 3-month moving average
        window = min(3, len(series))
        avg = float(np.mean(series[-window:]))
        # Add slight linear trend
        if len(series) >= 6:
            slope = np.polyfit(range(len(series)), series, 1)[0]
        else:
            slope = 0
        forecast_vals = np.array([avg + slope * (i + 1) for i in range(periods)])
        method = "Moving Average (fallback)"

    # Confidence interval (simple ±1 std of residuals or series std)
    std = float(np.std(series[-12:] if len(series) >= 12 else series))
    last_row = df.iloc[-1]
    future_periods = _next_periods(int(last_row["year"]), int(last_row["month"]), periods)

    forecast_df = pd.DataFrame({
        "period":   future_periods,
        "forecast": np.maximum(forecast_vals, 0),  # revenue can't be negative
        "lower":    np.maximum(forecast_vals - 1.96 * std, 0),
        "upper":    forecast_vals + 1.96 * std,
        "is_forecast": True,
    })

    historical_df = df[["period", "revenue"]].copy()
    historical_df["is_forecast"] = False

    return {
        "historical": historical_df,
        "forecast":   forecast_df,
        "method":     method,
    }


def forecast_orders(periods: int = FORECAST_PERIODS) -> dict:
    """Forecast monthly order count."""
    df = _get_monthly_revenue()

    if df.empty or len(df) < 3:
        return {
            "error": "Insufficient historical data for forecasting.",
            "historical": df,
            "forecast": pd.DataFrame(),
            "method": "none",
        }

    series = df["orders"].values.astype(float)
    method = "Moving Average"

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        model = ExponentialSmoothing(series, trend="add",
                                     initialization_method="estimated").fit(optimized=True)
        forecast_vals = model.forecast(periods)
        method = "Holt-Winters"
    except Exception:
        window = min(3, len(series))
        avg = float(np.mean(series[-window:]))
        forecast_vals = np.array([avg] * periods)

    std = float(np.std(series))
    last_row = df.iloc[-1]
    future_periods = _next_periods(int(last_row["year"]), int(last_row["month"]), periods)

    forecast_df = pd.DataFrame({
        "period":   future_periods,
        "forecast": np.maximum(forecast_vals, 0).round(),
        "lower":    np.maximum(forecast_vals - 1.96 * std, 0).round(),
        "upper":    (forecast_vals + 1.96 * std).round(),
        "is_forecast": True,
    })

    historical_df = df[["period", "orders"]].copy()
    historical_df["is_forecast"] = False

    return {
        "historical": historical_df,
        "forecast":   forecast_df,
        "method":     method,
    }
