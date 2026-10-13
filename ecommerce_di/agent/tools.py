"""
AI Business Agent — tool definitions exposed to Ollama / LLM function calling.
Each tool is a Python function that calls the analytics layer.
"""
import json
import logging
import pandas as pd
from analytics.sales import (
    get_executive_kpis, get_sales_trend, get_category_performance,
    get_brand_performance, get_product_performance, get_profitability_analysis,
    get_period_comparison,
)
from analytics.inventory import (
    get_inventory_risk, get_overstock_products, get_high_demand_low_stock,
    get_inventory_summary,
)
from analytics.customers import (
    get_customer_overview, get_customer_revenue, get_customer_segmentation,
    get_geographic_analysis, get_membership_analysis,
)
from analytics.payments import (
    get_payment_overview, get_payment_method_analysis,
    get_refund_analysis, get_order_status_breakdown,
)
from analytics.anomalies import get_all_anomalies
from forecasting.forecasting import forecast_revenue, forecast_orders

logger = logging.getLogger(__name__)


def _df_to_json(df: pd.DataFrame, max_rows: int = 25) -> str:
    """Convert DataFrame to compact JSON string for the LLM."""
    if df is None or df.empty:
        return json.dumps({"result": "No data available."})
    # Round floats
    df = df.copy()
    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(2)
    return df.head(max_rows).to_json(orient="records", indent=None)


# ─────────────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────────────

def tool_get_sales_kpis(start_date: str = None, end_date: str = None,
                         category: list[str] = None, state: str = None) -> str:
    filters = {"start_date": start_date, "end_date": end_date,
               "category": category, "state": [state] if state else None}
    try:
        result = get_executive_kpis({k: v for k, v in filters.items() if v})
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_sales_trend(granularity: str = "monthly",
                          start_date: str = None, end_date: str = None,
                          category: str = None) -> str:
    filters = {"start_date": start_date, "end_date": end_date,
               "category": [category] if category else None}
    try:
        df = get_sales_trend(granularity, {k: v for k, v in filters.items() if v})
        return _df_to_json(df, 24)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_category_performance(start_date: str = None, end_date: str = None) -> str:
    filters = {"start_date": start_date, "end_date": end_date}
    try:
        df = get_category_performance({k: v for k, v in filters.items() if v})
        return _df_to_json(df, 30)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_product_performance(sort_by: str = "revenue",
                                  limit: int = 20,
                                  start_date: str = None,
                                  end_date: str = None) -> str:
    filters = {"start_date": start_date, "end_date": end_date}
    try:
        df = get_product_performance(limit, sort_by, {k: v for k, v in filters.items() if v})
        return _df_to_json(df, limit)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_inventory_risk() -> str:
    try:
        df = get_inventory_risk()
        return _df_to_json(df, 30)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_overstock() -> str:
    try:
        df = get_overstock_products()
        return _df_to_json(df, 20)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_high_demand_low_stock() -> str:
    try:
        df = get_high_demand_low_stock()
        return _df_to_json(df, 20)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_customer_analysis(segment: str = None) -> str:
    try:
        seg_df = get_customer_segmentation()
        if segment and not seg_df.empty:
            seg_df = seg_df[seg_df["segment"] == segment]
        overview = get_customer_overview()
        return json.dumps({
            "overview": overview,
            "segmentation_summary": seg_df.groupby("segment").agg(
                customers=("customer_id","count"),
                total_revenue=("total_revenue","sum"),
                avg_orders=("order_count","mean")
            ).reset_index().round(2).to_dict(orient="records") if not seg_df.empty else []
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_geographic_analysis() -> str:
    try:
        df = get_geographic_analysis()
        return _df_to_json(df, 30)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_payment_analysis() -> str:
    try:
        overview = get_payment_overview()
        methods  = get_payment_method_analysis()
        return json.dumps({
            "overview": overview,
            "by_method": json.loads(_df_to_json(methods, 20)),
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_refund_analysis() -> str:
    try:
        df = get_refund_analysis()
        return _df_to_json(df, 20)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_order_status_analysis() -> str:
    try:
        df = get_order_status_breakdown()
        return _df_to_json(df)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_profitability_analysis(start_date: str = None,
                                     end_date: str = None) -> str:
    filters = {"start_date": start_date, "end_date": end_date}
    try:
        df = get_profitability_analysis({k: v for k, v in filters.items() if v})
        return _df_to_json(df, 30)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_anomalies() -> str:
    try:
        df = get_all_anomalies()
        return _df_to_json(df, 30)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_get_forecast(metric: str = "revenue", periods: int = 6) -> str:
    try:
        if metric == "orders":
            result = forecast_orders(periods)
        else:
            result = forecast_revenue(periods)
        if "error" in result:
            return json.dumps({"error": result["error"]})
        hist = result["historical"].tail(12).round(2).to_dict(orient="records")
        fcast = result["forecast"].round(2).to_dict(orient="records")
        return json.dumps({"method": result["method"],
                           "historical": hist, "forecast": fcast}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_compare_periods(period1_start: str, period1_end: str,
                          period2_start: str, period2_end: str) -> str:
    try:
        result = get_period_comparison(period1_start, period1_end,
                                       period2_start, period2_end)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_execute_sql(query: str) -> str:
    """
    Execute any arbitrary read-only analytical SQL query on SQLite.
    Allows answering any ad-hoc question across all tables.
    """
    clean_q = query.strip().rstrip(";")
    upper_q = clean_q.upper()
    if not upper_q.startswith("SELECT") and not upper_q.startswith("WITH"):
        return json.dumps({"error": "Security restriction: Only read-only SELECT queries are permitted."})

    # Forbid dangerous statements
    for forbid in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH", "DETACH"]:
        if f" {forbid} " in f" {upper_q} ":
            return json.dumps({"error": f"Security restriction: Statement '{forbid}' is not permitted."})

    if "LIMIT" not in upper_q:
        clean_q += " LIMIT 25"

    try:
        from database.connection import query_df
        df = query_df(clean_q)
        return _df_to_json(df, max_rows=25)
    except Exception as e:
        return json.dumps({"error": f"SQL execution failed: {str(e)}", "query_attempted": clean_q})


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry (function calling mapping)
# ─────────────────────────────────────────────────────────────────────────────

TOOL_FUNCTIONS: dict[str, callable] = {
    "get_sales_kpis":             tool_get_sales_kpis,
    "get_sales_trend":            tool_get_sales_trend,
    "get_category_performance":   tool_get_category_performance,
    "get_product_performance":    tool_get_product_performance,
    "get_inventory_risk":         tool_get_inventory_risk,
    "get_overstock":              tool_get_overstock,
    "get_high_demand_low_stock":  tool_get_high_demand_low_stock,
    "get_customer_analysis":      tool_get_customer_analysis,
    "get_geographic_analysis":    tool_get_geographic_analysis,
    "get_payment_analysis":       tool_get_payment_analysis,
    "get_refund_analysis":        tool_get_refund_analysis,
    "get_order_status_analysis":  tool_get_order_status_analysis,
    "get_profitability_analysis": tool_get_profitability_analysis,
    "get_anomalies":              tool_get_anomalies,
    "get_forecast":               tool_get_forecast,
    "compare_periods":            tool_compare_periods,
    "execute_sql":                tool_execute_sql,
}



GEMINI_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "get_sales_kpis",
                "description": "Get executive KPIs: total revenue, orders, customers, AOV, profit, refunds, discount, return rate. Supports optional date range and category filter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                        "end_date":   {"type": "string", "description": "End date YYYY-MM-DD"},
                        "category":   {"type": "array", "items": {"type": "string"}, "description": "Filter by product categories"},
                        "state":      {"type": "string", "description": "Filter by state"},
                    },
                },
            },
            {
                "name": "get_sales_trend",
                "description": "Get revenue, orders and units sold over time. Use to identify growth, decline, peaks or seasonality.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "granularity": {"type": "string", "enum": ["daily","weekly","monthly","quarterly","yearly"]},
                        "start_date":  {"type": "string"},
                        "end_date":    {"type": "string"},
                        "category":    {"type": "string"},
                    },
                },
            },
            {
                "name": "get_category_performance",
                "description": "Revenue, profit, units and discount by product category and subcategory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string"},
                        "end_date":   {"type": "string"},
                    },
                },
            },
            {
                "name": "get_product_performance",
                "description": "Product-level performance: revenue, units, profit, margin. Sortable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sort_by":    {"type": "string", "enum": ["revenue","units_sold","gross_profit","orders"]},
                        "limit":      {"type": "integer", "description": "Max products to return"},
                        "start_date": {"type": "string"},
                        "end_date":   {"type": "string"},
                    },
                },
            },
            {
                "name": "get_inventory_risk",
                "description": "Products where stock is below reorder level. Shows stock deficit and recent demand.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_overstock",
                "description": "Products with excess inventory (high stock, low sales).",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_high_demand_low_stock",
                "description": "High-demand products with critically low stock — stockout risk.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_customer_analysis",
                "description": "Customer segmentation: High Value, Frequent, New, Returning, Low Engagement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "segment": {"type": "string", "description": "Optional: filter to one segment"},
                    },
                },
            },
            {
                "name": "get_geographic_analysis",
                "description": "Revenue, orders and customers by state and city.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_payment_analysis",
                "description": "Payment method performance: success/failure rates, transaction fees, volumes.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_refund_analysis",
                "description": "Refund amounts and rates by product category and payment method.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_order_status_analysis",
                "description": "Order count and revenue by status: Delivered, Returned, Cancelled, etc.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_profitability_analysis",
                "description": "Profitability by product/category/brand. Identifies high-revenue/low-margin products.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string"},
                        "end_date":   {"type": "string"},
                    },
                },
            },
            {
                "name": "get_anomalies",
                "description": "Detect statistically unusual business behaviour: revenue spikes/drops, refund spikes, payment failure spikes.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_forecast",
                "description": "Forecast future revenue or order volumes using time-series models.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric":  {"type": "string", "enum": ["revenue", "orders"]},
                        "periods": {"type": "integer", "description": "Number of months to forecast"},
                    },
                },
            },
            {
                "name": "compare_periods",
                "description": "Compare KPIs between two date periods.",
                "parameters": {
                    "type": "object",
                    "required": ["period1_start","period1_end","period2_start","period2_end"],
                    "properties": {
                        "period1_start": {"type": "string"},
                        "period1_end":   {"type": "string"},
                        "period2_start": {"type": "string"},
                        "period2_end":   {"type": "string"},
                    },
                },
            },
            {
                "name": "execute_sql",
                "description": "Execute any ad-hoc analytical read-only SQL query on the SQLite warehouse. Tables: dim_customer(customer_id, name, gender, age, city, state, country, registration_date, membership_label, loyalty_points, preferred_device), dim_product(product_id, product_name, category, sub_category, brand, sku, cost_price, selling_price, profit_margin, stock_quantity, reorder_level, product_rating), fact_orders(order_id, order_date, customer_id, product_id, product_name, quantity, unit_price, discount_amount, tax_amount, shipping_charge, payment_mode, order_status, total_amount, gross_profit), fact_payments(payment_id, order_id, payment_date, payment_mode, payment_status, transaction_fee, refund_amount, refund_date), dim_date(date_id, full_date, year, quarter, month, month_name, week, day, day_of_week).",
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "The read-only SELECT SQL query to execute."},
                    },
                },
            },
        ]
    }
]

# Standard OpenAI/Ollama function tool declarations
OLLAMA_TOOLS = [
    {"type": "function", "function": func}
    for func in GEMINI_TOOLS[0]["function_declarations"]
]
