"""
Inventory analytics — stock risk, overstock, high-demand/low-stock.
"""
import pandas as pd
from database.connection import query_df
from config.settings import LOW_STOCK_MULTIPLIER, OVERSTOCK_MULTIPLIER, HIGH_DEMAND_PERCENTILE


def get_inventory_risk(filters: dict | None = None) -> pd.DataFrame:
    """Products where stock_quantity < reorder_level."""
    sql = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.sub_category,
            p.brand,
            p.stock_quantity,
            p.reorder_level,
            p.selling_price,
            p.product_status,
            p.reorder_level - p.stock_quantity AS stock_deficit,
            COALESCE(s.units_sold_30d, 0)       AS units_sold_30d,
            COALESCE(s.units_sold_90d, 0)       AS units_sold_90d
        FROM dim_product p
        LEFT JOIN (
            SELECT
                product_id,
                SUM(CASE WHEN order_date >= DATE('now','-30 days') THEN quantity ELSE 0 END) AS units_sold_30d,
                SUM(CASE WHEN order_date >= DATE('now','-90 days') THEN quantity ELSE 0 END) AS units_sold_90d
            FROM fact_orders
            WHERE order_status NOT IN ('Cancelled','Returned')
            GROUP BY product_id
        ) s ON p.product_id = s.product_id
        WHERE p.stock_quantity < p.reorder_level * ?
          AND p.product_status = 'Active'
        ORDER BY stock_deficit DESC
    """
    return query_df(sql, [LOW_STOCK_MULTIPLIER])


def get_overstock_products(top_n: int = 50) -> pd.DataFrame:
    """Products with high stock and low sales (potential overstock)."""
    sql = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.brand,
            p.stock_quantity,
            p.reorder_level,
            p.selling_price,
            COALESCE(s.units_sold_90d, 0) AS units_sold_90d,
            p.stock_quantity * p.cost_price AS inventory_value
        FROM dim_product p
        LEFT JOIN (
            SELECT product_id,
                   SUM(quantity) AS units_sold_90d
            FROM fact_orders
            WHERE order_date >= DATE('now','-90 days')
              AND order_status NOT IN ('Cancelled','Returned')
            GROUP BY product_id
        ) s ON p.product_id = s.product_id
        WHERE p.stock_quantity > p.reorder_level * ?
          AND COALESCE(s.units_sold_90d, 0) < p.reorder_level
        ORDER BY inventory_value DESC
        LIMIT ?
    """
    return query_df(sql, [OVERSTOCK_MULTIPLIER, top_n])


def get_high_demand_low_stock(top_n: int = 30) -> pd.DataFrame:
    """High-demand products with critically low stock."""
    sql = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.brand,
            p.stock_quantity,
            p.reorder_level,
            COALESCE(s.units_sold_30d, 0) AS units_sold_30d,
            COALESCE(s.units_sold_90d, 0) AS units_sold_90d,
            CASE
                WHEN COALESCE(s.units_sold_30d, 0) > 0
                THEN CAST(p.stock_quantity AS REAL) / (s.units_sold_30d / 30.0)
                ELSE NULL
            END AS days_of_stock
        FROM dim_product p
        JOIN (
            SELECT product_id,
                   SUM(CASE WHEN order_date >= DATE('now','-30 days') THEN quantity ELSE 0 END) AS units_sold_30d,
                   SUM(CASE WHEN order_date >= DATE('now','-90 days') THEN quantity ELSE 0 END) AS units_sold_90d
            FROM fact_orders
            WHERE order_status NOT IN ('Cancelled','Returned')
            GROUP BY product_id
        ) s ON p.product_id = s.product_id
        WHERE p.stock_quantity <= p.reorder_level
          AND s.units_sold_30d > 0
        ORDER BY units_sold_30d DESC, stock_quantity ASC
        LIMIT ?
    """
    return query_df(sql, [top_n])


def get_inventory_summary() -> dict:
    sql = """
        SELECT
            COUNT(*)                                                        AS total_products,
            SUM(CASE WHEN product_status='Active' THEN 1 ELSE 0 END)       AS active_products,
            SUM(CASE WHEN stock_quantity < reorder_level THEN 1 ELSE 0 END) AS below_reorder,
            SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END)             AS out_of_stock,
            SUM(stock_quantity * cost_price)                                AS total_inventory_value
        FROM dim_product
    """
    return query_df(sql).iloc[0].to_dict()
