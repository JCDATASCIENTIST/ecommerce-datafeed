"""
DISURI Beauty — Store-level configuration and feed defaults.

Product data now lives in products.json (written by fetch_shopify.py or
maintained manually). This file holds store constants and default values
that feed_generator.py falls back to when a product omits a field.
"""

import json
import os

STORE_CONFIG = {
    "store_name": "DISURI Beauty",
    "store_url": "https://disuribeauty.com",
    "feed_title": "DISURI Beauty Product Feed",
    "feed_description": "Google Merchant Center product feed for DISURI Beauty",
    "brand": "DISURI Beauty",
    "condition": "new",
    "availability": "in_stock",
    "currency": "USD",
    "country": "US",
    "language": "en",
    "output_file": "output/disuri_beauty_feed.xml",
    "default_shipping": [
        {"country": "US", "service": "Standard", "price": "0.00 USD"},
    ],
    "default_google_product_category": (
        "Health & Beauty > Personal Care > Cosmetics > Skin Care"
    ),
}


def load_countries(project_root: str | None = None) -> dict:
    """Load country configs from countries.json."""
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root, "countries.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_country_config(country_code: str, project_root: str | None = None) -> dict:
    """Return merged config for a specific country.

    Starts from STORE_CONFIG defaults and overlays country-specific values.
    """
    countries = load_countries(project_root)
    country = countries.get(country_code.upper())
    if not country:
        raise ValueError(
            f"Unknown country '{country_code}'. "
            f"Available: {', '.join(countries.keys())}"
        )

    return {
        **STORE_CONFIG,
        "name": country["name"],
        "country": country_code.upper(),
        "currency": country["currency"],
        "language": country["language"],
        "exchange_rate": country.get("exchange_rate", 1.0),
        "default_shipping": country["shipping"],
        "feed_title": country.get("feed_title", STORE_CONFIG["feed_title"]),
        "output_file": country.get("output_file", STORE_CONFIG["output_file"]),
        "optimized_copy": country.get("optimized_copy"),
    }


def convert_price(usd_price_str: str, exchange_rate: float, currency: str) -> str:
    """Convert a 'XX.XX USD' price string to local currency.

    For currencies like COP where decimals aren't used, rounds to whole number.
    """
    amount_str = usd_price_str.split()[0]
    amount = float(amount_str) * exchange_rate

    no_decimal_currencies = {"COP", "JPY", "KRW", "VND", "CLP"}
    if currency in no_decimal_currencies:
        return f"{int(round(amount))} {currency}"
    return f"{amount:.2f} {currency}"


# ── Google Product Taxonomy IDs (reference) ─────────────────────────────────
# 567   Health & Beauty > Personal Care > Cosmetics > Skin Care
# 2901  … > Skin Care > Facial Cleansers
# 2907  … > Skin Care > Lotion & Moisturizer
# 5976  … > Skin Care > Toners & Astringents
# 6262  … > Skin Care > Skin Care Masks & Peels
# 2912  … > Skin Care > Sunscreen
# 481   … > Skin Care > Acne Treatments & Kits
# 7429  … > Skin Care > Anti-Aging Skin Care Kits

# ── Custom Label Schema ─────────────────────────────────────────────────────
# custom_label_0  margin tier      (high_margin | medium_margin | low_margin)
# custom_label_1  lifecycle        (bestseller | core | new_arrival)
# custom_label_2  promo status     (full_price | on_sale | clearance)
# custom_label_3  collection name  (free text)
# custom_label_4  reserved         (free text)
