"""
DISURI Beauty — Google Merchant Center XML Feed Generator.

Reads a products.json file, validates every product against GMC required-field
rules, then builds an RSS 2.0 + g: namespace XML feed and writes it to disk.

Supports multi-country feeds with localized pricing, language, and shipping.

Usage:
    python feed_generator.py                                    # US defaults
    python feed_generator.py -i products.json -o feed.xml
    python feed_generator.py --country MX                       # Mexico feed
    python feed_generator.py --country all                      # All countries
"""

import argparse
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

from config import STORE_CONFIG, get_country_config, load_countries, convert_price

GOOGLE_NS = "http://base.google.com/ns/1.0"
NS_PREFIX = "g"

REQUIRED_FIELDS = ("id", "title", "description", "link", "image_link", "price")
VALID_AVAILABILITY = ("in_stock", "out_of_stock", "preorder", "backorder")
PRICE_RE = re.compile(r"^\d+\.?\d*\s[A-Z]{3}$")


# ── Validation ──────────────────────────────────────────────────────────────

def validate_product(product: dict, index: int, config: dict | None = None) -> list[str]:
    """Return a list of validation error/warning strings for one product."""
    cfg = config or STORE_CONFIG
    errors: list[str] = []
    pid = product.get("id", f"<index {index}>")

    for field in REQUIRED_FIELDS:
        if not product.get(field):
            errors.append(f"[{pid}] MISSING required field: {field}")

    price = product.get("price", "")
    if price and not PRICE_RE.match(price):
        errors.append(f"[{pid}] INVALID price format '{price}' — expected 'XX.XX CUR'")

    sale_price = product.get("sale_price")
    if sale_price and not PRICE_RE.match(sale_price):
        errors.append(f"[{pid}] INVALID sale_price format '{sale_price}'")

    if sale_price and not product.get("sale_price_effective_date"):
        errors.append(f"[{pid}] sale_price set but sale_price_effective_date is missing")

    avail = product.get("availability", "")
    if avail and avail not in VALID_AVAILABILITY:
        errors.append(
            f"[{pid}] INVALID availability '{avail}' — "
            f"must be one of {VALID_AVAILABILITY}"
        )

    cat = product.get("google_product_category", "")
    if cat and not cat.startswith("Health & Beauty > Personal Care"):
        errors.append(
            f"[{pid}] SUSPECT google_product_category '{cat}' — "
            f"expected path under 'Health & Beauty > Personal Care > Cosmetics > Skin Care'"
        )

    if product.get("is_bundle") and not product.get("identifier_exists"):
        errors.append(f"[{pid}] Bundle missing identifier_exists (should be 'no')")

    if not product.get("brand"):
        errors.append(f"[{pid}] WARNING: no brand — will fall back to store default")

    if not product.get("shipping") and not cfg.get("default_shipping"):
        errors.append(f"[{pid}] WARNING: no shipping defined (required unless set in GMC account)")

    return errors


def validate_all(products: list[dict], config: dict | None = None) -> tuple[list[str], bool]:
    """Validate every product. Returns (messages, has_errors)."""
    all_msgs: list[str] = []
    has_errors = False
    for i, p in enumerate(products):
        msgs = validate_product(p, i, config)
        if msgs:
            for m in msgs:
                is_warning = "WARNING" in m
                if not is_warning:
                    has_errors = True
            all_msgs.extend(msgs)
    return all_msgs, has_errors


# ── Price localization ─────────────────────────────────────────────────────

def localize_products(products: list[dict], config: dict) -> list[dict]:
    """Create a deep copy of products with localized prices and shipping."""
    rate = config.get("exchange_rate", 1.0)
    currency = config["currency"]
    country = config["country"]

    if rate == 1.0 and currency == "USD":
        return products

    localized = copy.deepcopy(products)
    for product in localized:
        # Convert main price
        if product.get("price"):
            product["price"] = convert_price(product["price"], rate, currency)

        # Convert sale price
        if product.get("sale_price"):
            product["sale_price"] = convert_price(product["sale_price"], rate, currency)

        # Replace shipping with country-specific
        product["shipping"] = config.get("default_shipping", [])

    return localized


# ── XML construction ────────────────────────────────────────────────────────

def build_feed(products: list[dict], config: dict | None = None) -> ET.Element:
    """Build the complete RSS 2.0 XML tree with g: namespace items."""
    cfg = config or STORE_CONFIG
    ET.register_namespace(NS_PREFIX, GOOGLE_NS)

    rss = ET.Element("rss", attrib={"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = cfg["feed_title"]
    ET.SubElement(channel, "link").text = cfg["store_url"]
    ET.SubElement(channel, "description").text = cfg.get(
        "feed_description",
        f"Google Merchant Center product feed for {cfg['store_name']}"
    )

    for product in products:
        _add_item(channel, product, cfg)

    return rss


def _add_item(channel: ET.Element, product: dict, config: dict) -> None:
    """Append a single <item> element to the channel."""
    item = ET.SubElement(channel, "item")

    _g(item, "id", product["id"])
    _g(item, "title", product["title"])
    _g(item, "description", product["description"])
    _g(item, "link", product["link"])
    _g(item, "image_link", product["image_link"])

    for img in product.get("additional_image_links") or []:
        _g(item, "additional_image_link", img)

    _g(item, "availability",
       product.get("availability") or config["availability"])
    _g(item, "price", product["price"])

    if product.get("sale_price"):
        _g(item, "sale_price", product["sale_price"])
    if product.get("sale_price_effective_date"):
        _g(item, "sale_price_effective_date", product["sale_price_effective_date"])

    _g(item, "brand", product.get("brand") or config["brand"])
    _g(item, "condition",
       product.get("condition") or config["condition"])

    if product.get("google_product_category"):
        _g(item, "google_product_category", product["google_product_category"])
    elif config.get("default_google_product_category"):
        _g(item, "google_product_category",
           config["default_google_product_category"])

    if product.get("product_type"):
        _g(item, "product_type", product["product_type"])

    if product.get("gtin"):
        _g(item, "gtin", product["gtin"])
    if product.get("mpn"):
        _g(item, "mpn", product["mpn"])

    if product.get("is_bundle"):
        _g(item, "is_bundle", "true")
        _g(item, "identifier_exists",
           product.get("identifier_exists", "no"))
    else:
        has_identifiers = product.get("gtin") or product.get("mpn")
        _g(item, "identifier_exists", "yes" if has_identifiers else "no")

    _add_shipping(item, product, config)

    for i in range(5):
        key = f"custom_label_{i}"
        if product.get(key):
            _g(item, key, product[key])

    if product.get("shipping_weight"):
        _g(item, "shipping_weight", product["shipping_weight"])


def _add_shipping(item: ET.Element, product: dict, config: dict) -> None:
    """Build nested <g:shipping> elements."""
    entries = product.get("shipping") or config.get("default_shipping") or []
    for entry in entries:
        shipping = ET.SubElement(item, f"{{{GOOGLE_NS}}}shipping")
        _g(shipping, "country", entry["country"])
        if entry.get("service"):
            _g(shipping, "service", entry["service"])
        _g(shipping, "price", entry["price"])


def _g(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Create a g:-namespaced subelement."""
    elem = ET.SubElement(parent, f"{{{GOOGLE_NS}}}{tag}")
    elem.text = str(text)
    return elem


# ── Output ──────────────────────────────────────────────────────────────────

def prettify(element: ET.Element) -> str:
    """Return a pretty-printed XML string with proper declaration."""
    rough = ET.tostring(element, encoding="unicode")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ", encoding=None)


def load_products(input_path: str) -> list[dict]:
    """Load product list from a JSON file."""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_path}, got {type(data).__name__}")
    return data


def load_optimized_copy(path: str) -> dict[str, dict]:
    """Load AI-optimized titles/descriptions keyed by product ID."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {item["id"]: item for item in data if item.get("id")}


def apply_optimized_copy(
    products: list[dict],
    copy_map: dict[str, dict],
) -> int:
    """Overlay optimized titles/descriptions onto products in-place.
    Returns the number of products updated."""
    count = 0
    for product in products:
        opt = copy_map.get(product.get("id", ""))
        if not opt:
            continue
        if opt.get("optimized_title"):
            product["title"] = opt["optimized_title"]
        if opt.get("optimized_description"):
            product["description"] = opt["optimized_description"]
        count += 1
    return count


def generate_feed(
    input_path: str,
    output_path: str,
    optimized_path: str | None = None,
    config: dict | None = None,
) -> str:
    """Full pipeline: load → localize → (overlay optimized copy) → validate → build XML → write."""
    cfg = config or STORE_CONFIG
    products = load_products(input_path)

    # Localize prices for non-US markets
    products = localize_products(products, cfg)

    if optimized_path:
        copy_map = load_optimized_copy(optimized_path)
        updated = apply_optimized_copy(products, copy_map)
        print(f"  Applied optimized copy to {updated}/{len(products)} products")

    msgs, has_errors = validate_all(products, cfg)
    if msgs:
        header = "VALIDATION ERRORS" if has_errors else "VALIDATION WARNINGS"
        print(f"\n{'=' * 60}")
        print(f"  {header}  ({len(msgs)} issue{'s' if len(msgs) != 1 else ''})")
        print(f"{'=' * 60}")
        for m in msgs:
            print(f"  • {m}")
        print(f"{'=' * 60}\n")

    if has_errors:
        print("Aborting feed generation due to validation errors.")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    rss = build_feed(products, cfg)
    xml_str = prettify(rss)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"  Feed written to {output_path}  ({len(products)} items, {cfg['currency']})")
    return output_path


def generate_country_feed(
    country_code: str,
    input_path: str,
    project_root: str,
) -> str:
    """Generate a feed for a specific country using its config."""
    cfg = get_country_config(country_code, project_root)
    output_path = os.path.join(project_root, cfg["output_file"])

    # Use country-specific optimized copy if available
    optimized_path = None
    if cfg.get("optimized_copy"):
        opt_path = os.path.join(project_root, cfg["optimized_copy"])
        if os.path.exists(opt_path):
            optimized_path = opt_path

    print(f"\n[{country_code}] {cfg['name']} — {cfg['language'].upper()}/{cfg['currency']}")
    return generate_feed(input_path, output_path, optimized_path, cfg)


def generate_all_feeds(input_path: str, project_root: str) -> list[str]:
    """Generate feeds for all configured countries."""
    countries = load_countries(project_root)
    results = []
    for code in countries:
        path = generate_country_feed(code, input_path, project_root)
        results.append(path)
    print(f"\nGenerated {len(results)} country feeds.")
    return results


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="Generate Google Merchant Center XML feeds from products.json"
    )
    parser.add_argument(
        "-i", "--input",
        default=os.path.join(project_root, "products.json"),
        help="Path to products.json input file (default: %(default)s)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to output XML feed (overrides country config)",
    )
    parser.add_argument(
        "--optimized",
        default=None,
        help="Path to optimized_copy.json (AI-optimized titles/descriptions)",
    )
    parser.add_argument(
        "--country",
        default=None,
        help="Country code (US, MX, CO, BR, DO) or 'all' for every configured country",
    )
    args = parser.parse_args()

    # Multi-country mode
    if args.country:
        if args.country.lower() == "all":
            generate_all_feeds(args.input, project_root)
        else:
            generate_country_feed(args.country.upper(), args.input, project_root)
        return

    # Legacy single-feed mode
    output = args.output or os.path.join(project_root, STORE_CONFIG["output_file"])
    generate_feed(args.input, output, args.optimized)


if __name__ == "__main__":
    main()
