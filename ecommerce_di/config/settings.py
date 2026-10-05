"""
Central configuration for E-Commerce Decision Intelligence System.
All environment variables and application-wide constants live here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR.parent / "project_ecom_dataset"))
CUSTOMERS_CSV  = DATA_DIR / "Customers.csv"
ORDERS_CSV     = DATA_DIR / "Orders.csv"
PRODUCTS_CSV   = DATA_DIR / "Products.csv"
PAYMENTS_CSV   = DATA_DIR / "Payments.csv"

DATABASE_PATH  = Path(os.getenv("DATABASE_PATH", BASE_DIR / "ecommerce_di.db"))

# ── AI / LLM (Ollama) ──────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# ── Business thresholds ────────────────────────────────────────────────────
# Customer segmentation (percentile-based; overridable via UI)
HIGH_VALUE_REVENUE_PERCENTILE  = 75   # top 25 % by revenue → High Value
FREQUENT_ORDER_PERCENTILE      = 75   # top 25 % by order count → Frequent
NEW_CUSTOMER_DAYS              = 90   # registered within last 90 days → New

# Inventory
LOW_STOCK_MULTIPLIER           = 1.0  # stock < reorder_level * multiplier
OVERSTOCK_MULTIPLIER           = 3.0  # stock > 3× reorder_level AND low sales
HIGH_DEMAND_PERCENTILE         = 75   # top 25 % by units sold = high demand

# Anomaly detection
ANOMALY_ZSCORE_THRESHOLD       = 2.5

# Forecasting
FORECAST_PERIODS               = 12   # months ahead

# ── UI / App ───────────────────────────────────────────────────────────────
APP_TITLE      = "E-Commerce Decision Intelligence"
APP_ICON       = "📊"
CURRENCY_SYMBOL = "₹"
LOCALE         = "en_IN"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
