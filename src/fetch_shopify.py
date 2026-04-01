"""
DISURI Beauty — Shopify Admin REST API product fetcher.

Pulls /products.json and /inventory_levels.json from the Shopify Admin API,
merges inventory quantities into each product variant, then writes a
products.json file compatible with feed_generator.py.

Authentication uses the Shopify client_credentials OAuth flow. A short-lived
access token (24 h TTL) is obtained at the start of each run.

Environment variables (set in .env or export directly):
    SHOPIFY_STORE_URL       e.g. https://disuri-beauty.myshopify.com
    SHOPIFY_CLIENT_ID       App client ID from Dev Dashboard → Settings
    SHOPIFY_CLIENT_SECRET   App client secret from Dev Dashboard → Settings
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse

from config import STORE_CONFIG

API_VERSION = "2024-10"

AVAILABILITY_MAP = {
    True: "in_stock",
    False: "out_of_stock",
}

STORE_URL = os.environ.get("SHOPIFY_STORE_URL", "")
CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET", "")

_access_token: str = ""


# ── OAuth ───────────────────────────────────────────────────────────────────

def _obtain_access_token() -> str:
    """Exchange client credentials for a short-lived access token (24 h)."""
    global _access_token
    if _access_token:
        return _access_token

    url = f"{STORE_URL.rstrip('/')}/admin/oauth/access_token"
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(
            f"OAuth token exchange failed ({e.code}): {body_text}",
            file=sys.stderr,
        )
        raise

    _access_token = data["access_token"]
    scopes = data.get("scope", "")
    expires = data.get("expires_in", "?")
    print(f"  Token obtained (scopes: {scopes}, expires in {expires}s)")
    return _access_token


# ── API helpers ─────────────────────────────────────────────────────────────

def _api_get(endpoint: str) -> dict:
    """Make an authenticated GET request to the Shopify Admin REST API."""
    token = _obtain_access_token()
    url = f"{STORE_URL.rstrip('/')}/admin/api/{API_VERSION}/{endpoint}"
    req = urllib.request.Request(url, headers={
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"Shopify API error {e.code} on {endpoint}: {body_text}", file=sys.stderr)
        raise


def _paginated_get(endpoint: str, root_key: str) -> list[dict]:
    """Fetch all pages of a Shopify list endpoint via Link-header pagination."""
    token = _obtain_access_token()
    results: list[dict] = []
    url = f"{STORE_URL.rstrip('/')}/admin/api/{API_VERSION}/{endpoint}"
    while url:
        req = urllib.request.Request(url, headers={
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            results.extend(data.get(root_key, []))
            link = resp.headers.get("Link", "")
            url = _parse_next_link(link)
    return results


def _parse_next_link(link_header: str) -> str | None:
    """Extract the 'next' URL from a Shopify Link header."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split("<")[1].split(">")[0].strip()
    return None


# ── Data fetchers ───────────────────────────────────────────────────────────

def fetch_products() -> list[dict]:
    """Fetch all products from Shopify."""
    return _paginated_get("products.json?limit=250", "products")


def fetch_inventory_levels(location_ids: list[int] | None = None) -> dict[int, int]:
    """Fetch inventory levels and return a map of inventory_item_id → available qty."""
    if not location_ids:
        locations = _api_get("locations.json").get("locations", [])
        location_ids = [loc["id"] for loc in locations]

    levels: dict[int, int] = {}
    for loc_id in location_ids:
        items = _paginated_get(
            f"inventory_levels.json?location_ids={loc_id}&limit=250",
            "inventory_levels",
        )
        for item in items:
            inv_id = item["inventory_item_id"]
            levels[inv_id] = levels.get(inv_id, 0) + (item.get("available") or 0)
    return levels


# ── Transform ───────────────────────────────────────────────────────────────

def transform_product(
    shopify_product: dict,
    inventory_map: dict[int, int],
) -> list[dict]:
    """
    Convert a Shopify product (with variants) into one or more GMC-compatible
    product dicts. Each variant becomes a separate feed item.
    """
    items: list[dict] = []
    base_url = STORE_CONFIG["store_url"].rstrip("/")

    for variant in shopify_product.get("variants", []):
        inv_item_id = variant.get("inventory_item_id")
        qty = inventory_map.get(inv_item_id, 0) if inv_item_id else 0

        images = shopify_product.get("images", [])
        main_image = images[0]["src"] if images else ""
        additional = [img["src"] for img in images[1:]] if len(images) > 1 else []

        price_val = variant.get("price", "0.00")
        compare_price = variant.get("compare_at_price")

        item: dict = {
            "id": variant.get("sku") or str(variant["id"]),
            "title": shopify_product["title"],
            "description": _strip_html(shopify_product.get("body_html", "")),
            "link": f"{base_url}/products/{shopify_product['handle']}",
            "image_link": main_image,
            "additional_image_links": additional,
            "price": f"{float(price_val):.2f} USD",
            "availability": AVAILABILITY_MAP.get(qty > 0, "out_of_stock"),
            "condition": "new",
            "brand": shopify_product.get("vendor") or STORE_CONFIG["brand"],
            "gtin": variant.get("barcode"),
            "mpn": variant.get("sku"),
            "google_product_category": STORE_CONFIG.get(
                "default_google_product_category",
                "Health & Beauty > Personal Care > Cosmetics > Skin Care",
            ),
            "product_type": shopify_product.get("product_type", ""),
            "is_bundle": False,
            "shipping": STORE_CONFIG.get("default_shipping", []),
        }

        if compare_price and float(compare_price) > float(price_val):
            item["sale_price"] = item["price"]
            item["price"] = f"{float(compare_price):.2f} USD"

        items.append(item)

    return items


def _strip_html(html: str) -> str:
    """Naive HTML tag stripper for product body_html."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    if not STORE_URL or not CLIENT_ID or not CLIENT_SECRET:
        print(
            "Missing Shopify credentials. Set these environment variables:\n"
            "  export SHOPIFY_STORE_URL=https://your-store.myshopify.com\n"
            "  export SHOPIFY_CLIENT_ID=your_client_id\n"
            "  export SHOPIFY_CLIENT_SECRET=your_client_secret",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Authenticating with {STORE_URL}...")
    _obtain_access_token()

    print("Fetching products...")
    shopify_products = fetch_products()
    print(f"  → {len(shopify_products)} products found")

    print("Fetching inventory levels...")
    inventory = fetch_inventory_levels()
    print(f"  → {len(inventory)} inventory items mapped")

    feed_products: list[dict] = []
    for sp in shopify_products:
        feed_products.extend(transform_product(sp, inventory))

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "products.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feed_products, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(feed_products)} items to {output_path}")


if __name__ == "__main__":
    main()
