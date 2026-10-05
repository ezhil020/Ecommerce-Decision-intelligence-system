"""
Data cleaning pipeline.
Handles: date conversion, currency parsing, column normalization, deduplication.
"""
import re
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Excel epoch: 1900-01-01 (Windows serial date, 1-based)
EXCEL_EPOCH = datetime(1899, 12, 30)


# ── Date helpers ────────────────────────────────────────────────────────────

def parse_date(val) -> str | None:
    """
    Parse a wide variety of date representations.
    Returns ISO date string "YYYY-MM-DD" or None if unparsable.
    """
    if pd.isna(val):
        return None
    # Already a date/datetime
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    # Numeric → Excel serial
    try:
        n = float(str(val).strip())
        if 10000 < n < 80000:                  # plausible Excel serial range
            dt = EXCEL_EPOCH + pd.Timedelta(days=n)
            return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    # String formats
    s = str(val).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y",
                "%d-%b-%Y", "%B %d, %Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    logger.warning("Unparsable date value: %r", val)
    return None


def date_to_id(date_str: str | None) -> int | None:
    """Convert 'YYYY-MM-DD' to int YYYYMMDD key."""
    if not date_str:
        return None
    return int(date_str.replace("-", ""))


def build_dim_date(dates: list[str]) -> pd.DataFrame:
    """
    Build a dim_date table from a list of ISO date strings.
    """
    clean = {d for d in dates if d}
    records = []
    for ds in clean:
        try:
            dt = datetime.strptime(ds, "%Y-%m-%d")
        except ValueError:
            continue
        records.append({
            "date_id":     int(dt.strftime("%Y%m%d")),
            "full_date":   ds,
            "year":        dt.year,
            "quarter":     (dt.month - 1) // 3 + 1,
            "month":       dt.month,
            "month_name":  dt.strftime("%B"),
            "week":        int(dt.strftime("%W")),
            "day":         dt.day,
            "day_of_week": dt.strftime("%A"),
        })
    df = pd.DataFrame(records).drop_duplicates("date_id")
    return df


# ── Currency helpers ────────────────────────────────────────────────────────

def parse_currency(val) -> float | None:
    """Strip ₹, commas, spaces and convert to float."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    # Remove currency symbol, spaces, commas
    s = re.sub(r"[₹\$£€,\s]", "", s)
    # Handle "₹ -" → 0
    s = re.sub(r"^-$", "0", s)
    if s == "" or s.upper() in ("NA", "N/A", "NAN", "NONE"):
        return None
    try:
        return float(s)
    except ValueError:
        logger.warning("Unparsable currency: %r", val)
        return None


# ── Text helpers ────────────────────────────────────────────────────────────

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, replace spaces/special chars with underscores."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def strip_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string columns."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


def clean_preferred_device(val: str | None) -> str | None:
    """
    Fix malformed device labels like 'Mobile Mobile App' → 'Mobile App'.
    """
    if not val or pd.isna(val):
        return val
    # Deduplicate repeated words
    parts = str(val).split()
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return " ".join(out)


# ── Loyalty points ──────────────────────────────────────────────────────────

def parse_loyalty_points(val) -> float | None:
    """Strip 'pts' suffix and return float."""
    if pd.isna(val):
        return None
    s = str(val).strip().lower().replace("pts", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


# ── Customers ───────────────────────────────────────────────────────────────

def clean_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    issues = []
    df = normalize_column_names(df)
    df = strip_text_columns(df)

    # Rename columns to canonical names
    rename = {
        "customer_id": "customer_id",
        "name": "name",
        "gender": "gender",
        "age": "age",
        "date_of_birth": "date_of_birth",
        "email": "email",
        "phone": "phone",
        "city": "city",
        "state": "state",
        "country": "country",
        "pincode": "pincode",
        "registration_date": "registration_date",
        "membership_label": "membership_label",
        "loyalty_points": "loyalty_points",
        "preferred_device": "preferred_device",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Duplicate customer_id
    dups = df.duplicated("customer_id", keep="first")
    if dups.any():
        issues.append({"table": "customers", "issue": "duplicate_customer_id",
                       "count": int(dups.sum())})
        df = df[~dups]

    # Dates
    df["date_of_birth"]    = df["date_of_birth"].apply(parse_date)
    df["registration_date"] = df["registration_date"].apply(parse_date)

    # Loyalty points
    df["loyalty_points"] = df["loyalty_points"].apply(parse_loyalty_points)

    # Preferred device dedup
    df["preferred_device"] = df["preferred_device"].apply(clean_preferred_device)

    # Age: must be positive integer
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    invalid_age = df["age"].isna() | (df["age"] <= 0)
    if invalid_age.any():
        issues.append({"table": "customers", "issue": "invalid_age",
                       "count": int(invalid_age.sum())})

    # Membership allowed values
    allowed_membership = {"New", "Silver", "Gold", "Platinum", "Elite", "VIP"}
    bad_mem = ~df["membership_label"].isin(allowed_membership) & df["membership_label"].notna()
    if bad_mem.any():
        issues.append({"table": "customers", "issue": "unexpected_membership_label",
                       "count": int(bad_mem.sum()),
                       "values": df.loc[bad_mem, "membership_label"].unique().tolist()})

    return df, issues


# ── Products ────────────────────────────────────────────────────────────────

def clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    issues = []
    df = normalize_column_names(df)
    df = strip_text_columns(df)

    rename = {
        "product_id": "product_id",
        "product_name": "product_name",
        "category": "category",
        "sub_category": "sub_category",
        "brand": "brand",
        "sku": "sku",
        "cost_price": "cost_price",
        "selling_price": "selling_price",
        "profit_margin": "profit_margin",
        "discount": "discount_pct",         # after normalization: 'discount'
        "discount_pct": "discount_pct",     # already renamed
        "stock_quantity_nos": "stock_quantity",   # normalized form
        "stock_quantity_nos_": "stock_quantity",  # alternate
        "reorder_level": "reorder_level",
        "product_rating": "product_rating",
        "launch_date": "launch_date",
        "product_status": "product_status",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Duplicates
    dups = df.duplicated("product_id", keep="first")
    if dups.any():
        issues.append({"table": "products", "issue": "duplicate_product_id",
                       "count": int(dups.sum())})
        df = df[~dups]

    # Numeric columns
    for col in ["cost_price", "selling_price", "profit_margin", "discount_pct",
                "stock_quantity", "reorder_level", "product_rating"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Validate
    bad_price = df["selling_price"].isna() | (df["selling_price"] <= 0)
    if bad_price.any():
        issues.append({"table": "products", "issue": "invalid_selling_price",
                       "count": int(bad_price.sum())})

    bad_cost = df["cost_price"].isna() | (df["cost_price"] < 0)
    if bad_cost.any():
        issues.append({"table": "products", "issue": "invalid_cost_price",
                       "count": int(bad_cost.sum())})

    bad_stock = df["stock_quantity"] < 0
    if bad_stock.any():
        issues.append({"table": "products", "issue": "negative_stock",
                       "count": int(bad_stock.sum())})

    df["launch_date"] = df["launch_date"].apply(parse_date)

    return df, issues


# ── Orders ──────────────────────────────────────────────────────────────────

def clean_orders(df: pd.DataFrame,
                 valid_customers: set,
                 valid_products: set) -> tuple[pd.DataFrame, list[dict]]:
    issues = []
    df = normalize_column_names(df)
    df = strip_text_columns(df)

    rename = {
        "order_id": "order_id",
        "order_date": "order_date",
        "customer_id": "customer_id",
        "product_id": "product_id",
        "product_name": "product_name",
        "quantity_nos": "quantity",     # normalized form
        "quantity_nos_": "quantity",    # alternate
        "unit_price": "unit_price",
        "discount_amount": "discount_amount",
        "tax_amount": "tax_amount",
        "shipping_charge": "shipping_charge",
        "payment_mode": "payment_mode",
        "order_status": "order_status",
        "total_amount": "total_amount",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    dups = df.duplicated("order_id", keep="first")
    if dups.any():
        issues.append({"table": "orders", "issue": "duplicate_order_id",
                       "count": int(dups.sum())})
        df = df[~dups]

    df["order_date"] = df["order_date"].apply(parse_date)

    for col in ["unit_price", "discount_amount", "tax_amount",
                "shipping_charge", "total_amount", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # FK validation
    bad_cust = ~df["customer_id"].isin(valid_customers)
    if bad_cust.any():
        issues.append({"table": "orders", "issue": "invalid_customer_id",
                       "count": int(bad_cust.sum())})
        df = df[~bad_cust]

    bad_prod = ~df["product_id"].isin(valid_products)
    if bad_prod.any():
        issues.append({"table": "orders", "issue": "invalid_product_id",
                       "count": int(bad_prod.sum())})
        df = df[~bad_prod]

    bad_qty = df["quantity"].isna() | (df["quantity"] <= 0)
    if bad_qty.any():
        issues.append({"table": "orders", "issue": "invalid_quantity",
                       "count": int(bad_qty.sum())})

    # Derived columns
    df["gross_revenue"] = df["unit_price"] * df["quantity"]
    df["net_revenue"]   = df["total_amount"]

    return df, issues


# ── Payments ────────────────────────────────────────────────────────────────

def clean_payments(df: pd.DataFrame,
                   valid_orders: set) -> tuple[pd.DataFrame, list[dict]]:
    issues = []
    df = normalize_column_names(df)
    df = strip_text_columns(df)

    # Drop unnamed columns
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

    rename = {
        "payment_id": "payment_id",
        "order_id": "order_id",
        "payment_date": "payment_date",
        "payment_mode": "payment_mode",
        "payment_status": "payment_status",
        "transaction_fee": "transaction_fee",
        "refund_amount": "refund_amount",
        "refund_date": "refund_date",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    dups = df.duplicated("payment_id", keep="first")
    if dups.any():
        issues.append({"table": "payments", "issue": "duplicate_payment_id",
                       "count": int(dups.sum())})
        df = df[~dups]

    df["payment_date"] = df["payment_date"].apply(parse_date)
    df["refund_date"]  = df["refund_date"].apply(
        lambda v: None if str(v).strip().upper() in ("NA", "N/A", "", "NAN") else parse_date(v)
    )

    df["transaction_fee"] = df["transaction_fee"].apply(parse_currency)
    df["refund_amount"]   = df["refund_amount"].apply(parse_currency).fillna(0)

    bad_ord = ~df["order_id"].isin(valid_orders)
    if bad_ord.any():
        issues.append({"table": "payments", "issue": "invalid_order_id",
                       "count": int(bad_ord.sum())})
        df = df[~bad_ord]

    allowed_status = {"Success", "Failed", "Pending", "Refunded"}
    bad_stat = ~df["payment_status"].isin(allowed_status) & df["payment_status"].notna()
    if bad_stat.any():
        issues.append({"table": "payments", "issue": "unexpected_payment_status",
                       "count": int(bad_stat.sum()),
                       "values": df.loc[bad_stat, "payment_status"].unique().tolist()})

    return df, issues
