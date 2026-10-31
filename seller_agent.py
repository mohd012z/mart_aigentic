"""Read-only Shopee seller CSV analysis. No Shopee credentials or network access."""
import csv
import io
from collections import Counter
from decimal import Decimal, InvalidOperation

MAX_BYTES = 2_000_000
MAX_ROWS = 10_000

def parse_products(data: bytes):
    if len(data) > MAX_BYTES:
        raise ValueError("CSV exceeds 2 MB limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV header missing")
    aliases = {
        "name": ("product name", "product_name", "name", "item name"),
        "stock": ("stock", "stock quantity", "quantity", "available stock"),
        "price": ("price", "original price", "current price", "selling price"),
    }
    fields = {x.strip().lower(): x for x in reader.fieldnames if x}
    selected = {}
    for key, options in aliases.items():
        match = next((fields[a] for a in options if a in fields), None)
        if not match:
            raise ValueError("Missing required column: " + key)
        selected[key] = match
    products = []
    for row in reader:
        if len(products) >= MAX_ROWS:
            raise ValueError("CSV exceeds 10,000 rows")
        name = (row.get(selected["name"]) or "").strip()[:180]
        if not name:
            continue
        try:
            stock = int((row.get(selected["stock"]) or "").strip())
            price = Decimal((row.get(selected["price"]) or "").strip())
        except (ValueError, InvalidOperation) as exc:
            raise ValueError("Invalid stock or price for product: " + name) from exc
        if not price.is_finite() or stock < 0 or price < 0:
            raise ValueError("Negative or nonfinite values for product: " + name)
        products.append({"name": name, "stock": stock, "price": price})
    return products

def summarize(products, low_stock_threshold=5):
    if low_stock_threshold < 0:
        raise ValueError("Invalid threshold")
    low = [p for p in products if p["stock"] <= low_stock_threshold]
    inventory_value = sum((p["price"] * p["stock"] for p in products), Decimal("0"))
    return {
        "products": len(products),
        "units": sum(p["stock"] for p in products),
        "low_stock_count": len(low),
        "low_stock_names": [p["name"] for p in low[:15]],
        "inventory_list_price_value": str(inventory_value),
        "source": "user-imported CSV snapshot",
        "live": False,
    }

def listing_advice(name, description=""):
    name = name.strip()[:180]
    description = description.strip()[:2000]
    if not name:
        raise ValueError("Product name required")
    advice = ["Use an accurate product title with brand, model and key specifications when verified.",
              "Check category, variants, dimensions and product photos.",
              "Avoid unsupported guarantees, misleading claims and keyword stuffing."]
    if not description:
        advice.insert(0, "Add a factual description covering features, compatibility and care.")
    return {"product": name, "suggestions": advice, "auto_publish": False}
