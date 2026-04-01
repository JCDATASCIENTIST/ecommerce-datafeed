"""
DISURI Beauty — Dynamic Creative Optimization (DCO) Generator.

Reads the product feed data + localized optimized copy and generates
ad creative assets ready for upload to Google Ads and Meta Ads.

Outputs:
  - Google Ads CSV: Performance Max / Responsive Search Ad assets
    (headlines ≤30 chars, long headlines ≤90 chars, descriptions ≤90 chars)
  - Meta Product Catalog CSV: enhanced titles/descriptions for DPA
  - Combined JSON: all creatives for dashboard preview

Usage:
    python dco_generator.py --country US                    # single market
    python dco_generator.py --country all                   # all markets
    python dco_generator.py --country MX --format google    # Google only
    python dco_generator.py --country all --format meta     # Meta only
"""

import argparse
import csv
import json
import os
import sys

from config import STORE_CONFIG, get_country_config, load_countries, convert_price
from feed_generator import load_products, load_optimized_copy, apply_optimized_copy

# ── Ad copy templates per language ──────────────────────────────────────────

TEMPLATES = {
    "en": {
        "headlines": [
            "{short_name}",
            "K-Beauty {category}",
            "DISURI {category}",
            "Shop {short_name}",
            "{key_benefit}",
            "Korean {category}",
            "Clinically-Backed",
            "Transparent Formula",
            "${price} {category}",
            "Free US Shipping",
        ],
        "long_headlines": [
            "{title} — Korean-Formulated Skincare",
            "Shop {short_name} | Clinically-Backed K-Beauty",
            "{key_benefit} with {short_name} | DISURI Beauty",
            "K-Beauty {category} with Published Concentrations",
        ],
        "descriptions": [
            "{short_name} — {key_benefit}. Korean-formulated with clinically-backed actives. Shop DISURI Beauty.",
            "Discover {short_name} by DISURI Beauty. {key_benefit}. Full ingredient transparency. ${price}.",
            "K-beauty {category_lower} with published concentrations. {key_benefit}. Free shipping. Shop now.",
        ],
        "cta": "Shop Now",
        "meta_overlay": "{key_benefit} | K-Beauty Formula | Free Shipping",
    },
    "es": {
        "headlines": [
            "{short_name}",
            "K-Beauty {category}",
            "DISURI {category}",
            "Compra {short_name}",
            "{key_benefit}",
            "{category} Coreano",
            "Fórmula Clínica",
            "Transparencia Total",
            "${price} {category}",
            "Skincare Coreano",
        ],
        "long_headlines": [
            "{title} — Skincare de Formulación Coreana",
            "{short_name} | K-Beauty Clínicamente Respaldado",
            "{key_benefit} con {short_name} | DISURI Beauty",
            "K-Beauty {category} con Concentraciones Publicadas",
        ],
        "descriptions": [
            "{short_name} — {key_benefit}. Formulación coreana con activos clínicamente respaldados. Compra DISURI Beauty.",
            "Descubre {short_name} de DISURI Beauty. {key_benefit}. Transparencia total de ingredientes. ${price}.",
            "K-beauty {category_lower} con concentraciones publicadas. {key_benefit}. Compra ahora.",
        ],
        "cta": "Comprar Ahora",
        "meta_overlay": "{key_benefit} | Fórmula K-Beauty | Skincare Coreano",
    },
    "pt": {
        "headlines": [
            "{short_name}",
            "K-Beauty {category}",
            "DISURI {category}",
            "Compre {short_name}",
            "{key_benefit}",
            "{category} Coreano",
            "Fórmula Clínica",
            "Transparência Total",
            "R${price} {category}",
            "Skincare Coreano",
        ],
        "long_headlines": [
            "{title} — Skincare de Formulação Coreana",
            "{short_name} | K-Beauty Clinicamente Comprovado",
            "{key_benefit} com {short_name} | DISURI Beauty",
            "K-Beauty {category} com Concentrações Publicadas",
        ],
        "descriptions": [
            "{short_name} — {key_benefit}. Formulação coreana com ativos clinicamente comprovados. Compre DISURI Beauty.",
            "Descubra {short_name} da DISURI Beauty. {key_benefit}. Transparência total de ingredientes. R${price}.",
            "K-beauty {category_lower} com concentrações publicadas. {key_benefit}. Compre agora.",
        ],
        "cta": "Comprar Agora",
        "meta_overlay": "{key_benefit} | Fórmula K-Beauty | Skincare Coreano",
    },
}

# ── Product key benefits (used in ad templates) ────────────────────────────

KEY_BENEFITS = {
    "en": {
        "ultimate-snail-mucin-cream": "Smoother, hydrated skin",
        "triple-collagen-firming-cream": "Firmer, more elastic skin",
        "hyaluronic-acid-intense-cream": "Intense lasting hydration",
        "triple-collagen-firming-foam": "Gentle deep cleansing",
        "triple-collagen-firming-toner": "Max absorption prep",
        "triple-collagen-firming-eye-cream": "Reduce fine lines & puffiness",
        "triple-collagen-firming-essence": "Deep hydration boost",
    },
    "es": {
        "ultimate-snail-mucin-cream": "Piel más suave e hidratada",
        "triple-collagen-firming-cream": "Piel más firme y elástica",
        "hyaluronic-acid-intense-cream": "Hidratación intensa duradera",
        "triple-collagen-firming-foam": "Limpieza suave y profunda",
        "triple-collagen-firming-toner": "Máxima absorción",
        "triple-collagen-firming-eye-cream": "Reduce líneas finas",
        "triple-collagen-firming-essence": "Hidratación profunda",
    },
    "pt": {
        "ultimate-snail-mucin-cream": "Pele mais suave e hidratada",
        "triple-collagen-firming-cream": "Pele mais firme e elástica",
        "hyaluronic-acid-intense-cream": "Hidratação intensa duradoura",
        "triple-collagen-firming-foam": "Limpeza suave e profunda",
        "triple-collagen-firming-toner": "Máxima absorção",
        "triple-collagen-firming-eye-cream": "Reduz linhas finas",
        "triple-collagen-firming-essence": "Hidratação profunda",
    },
}

SHORT_NAMES = {
    "ultimate-snail-mucin-cream": "Snail Mucin Cream",
    "triple-collagen-firming-cream": "Collagen Cream",
    "hyaluronic-acid-intense-cream": "HA Intense Cream",
    "triple-collagen-firming-foam": "Collagen Foam",
    "triple-collagen-firming-toner": "Collagen Toner",
    "triple-collagen-firming-eye-cream": "Collagen Eye Cream",
    "triple-collagen-firming-essence": "Collagen Essence",
}

CATEGORIES = {
    "ultimate-snail-mucin-cream": "Cream",
    "triple-collagen-firming-cream": "Cream",
    "hyaluronic-acid-intense-cream": "Cream",
    "triple-collagen-firming-foam": "Cleanser",
    "triple-collagen-firming-toner": "Toner",
    "triple-collagen-firming-eye-cream": "Eye Cream",
    "triple-collagen-firming-essence": "Essence",
}


# ── Creative generation ────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def generate_creatives(product: dict, lang: str, config: dict) -> dict:
    """Generate all ad creative variations for one product in one language."""
    pid = product["id"]
    templates = TEMPLATES.get(lang, TEMPLATES["en"])
    benefits = KEY_BENEFITS.get(lang, KEY_BENEFITS["en"])

    rate = config.get("exchange_rate", 1.0)
    currency = config["currency"]

    # Parse base USD price
    price_str = product.get("price", "0.00 USD").split()[0]
    if rate != 1.0 or currency != "USD":
        local_amount = float(price_str) * rate
        if currency in ("COP", "JPY", "KRW", "VND", "CLP"):
            price_display = f"{int(round(local_amount)):,}"
        else:
            price_display = f"{local_amount:.2f}"
    else:
        price_display = price_str

    vars = {
        "title": product["title"],
        "short_name": SHORT_NAMES.get(pid, product["title"]),
        "category": CATEGORIES.get(pid, "Skincare"),
        "category_lower": CATEGORIES.get(pid, "skincare").lower(),
        "key_benefit": benefits.get(pid, "K-Beauty skincare"),
        "price": price_display,
        "brand": "DISURI Beauty",
    }

    def fill(template: str) -> str:
        try:
            return template.format(**vars)
        except KeyError:
            return template

    headlines = [_truncate(fill(t), 30) for t in templates["headlines"]]
    long_headlines = [_truncate(fill(t), 90) for t in templates["long_headlines"]]
    descriptions = [_truncate(fill(t), 90) for t in templates["descriptions"]]

    return {
        "product_id": pid,
        "country": config["country"],
        "language": lang,
        "currency": currency,
        "price_local": f"{price_display} {currency}",
        "title": product["title"],
        "link": product.get("link", f"https://disuribeauty.com/products/{pid}"),
        "image_link": product.get("image_link", ""),
        "headlines": headlines,
        "long_headlines": long_headlines,
        "descriptions": descriptions,
        "cta": templates["cta"],
        "meta_overlay": fill(templates["meta_overlay"]),
    }


# ── Export: Google Ads CSV ─────────────────────────────────────────────────

def export_google_csv(all_creatives: list[dict], output_path: str) -> str:
    """Export Google Ads Performance Max asset CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Campaign", "Asset Group", "Country", "Language",
            "Headline 1", "Headline 2", "Headline 3", "Headline 4", "Headline 5",
            "Long Headline 1", "Long Headline 2",
            "Description 1", "Description 2", "Description 3",
            "Final URL", "CTA",
        ])

        for c in all_creatives:
            hl = c["headlines"]
            lh = c["long_headlines"]
            desc = c["descriptions"]
            writer.writerow([
                f"DISURI - {c['country']} - Shopping",
                f"{c['product_id']}",
                c["country"],
                c["language"],
                hl[0] if len(hl) > 0 else "",
                hl[1] if len(hl) > 1 else "",
                hl[2] if len(hl) > 2 else "",
                hl[3] if len(hl) > 3 else "",
                hl[4] if len(hl) > 4 else "",
                lh[0] if len(lh) > 0 else "",
                lh[1] if len(lh) > 1 else "",
                desc[0] if len(desc) > 0 else "",
                desc[1] if len(desc) > 1 else "",
                desc[2] if len(desc) > 2 else "",
                c["link"],
                c["cta"],
            ])

    print(f"  Google Ads CSV: {output_path} ({len(all_creatives)} asset groups)")
    return output_path


# ── Export: Meta Product Catalog CSV ───────────────────────────────────────

def export_meta_csv(all_creatives: list[dict], output_path: str) -> str:
    """Export Meta Dynamic Product Ads catalog overlay CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "title", "description", "link", "image_link",
            "price", "availability", "brand", "condition",
            "custom_label_0",
        ])

        for c in all_creatives:
            writer.writerow([
                c["product_id"],
                c["title"],
                c["descriptions"][0] if c["descriptions"] else "",
                c["link"],
                c["image_link"],
                c["price_local"],
                "in stock",
                "DISURI Beauty",
                "new",
                c["meta_overlay"],
            ])

    print(f"  Meta Catalog CSV: {output_path} ({len(all_creatives)} products)")
    return output_path


# ── Export: Combined JSON ──────────────────────────────────────────────────

def export_json(all_creatives: list[dict], output_path: str) -> str:
    """Export all creatives as JSON for dashboard preview."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_creatives, f, indent=2, ensure_ascii=False)

    print(f"  DCO JSON: {output_path} ({len(all_creatives)} entries)")
    return output_path


# ── Main pipeline ──────────────────────────────────────────────────────────

def generate_dco(
    input_path: str,
    country_code: str,
    project_root: str,
    formats: list[str] | None = None,
) -> dict[str, str]:
    """Generate DCO creatives for one country. Returns dict of output paths."""
    cfg = get_country_config(country_code, project_root)
    lang = cfg["language"]
    products = load_products(input_path)

    # Apply localized optimized copy
    if cfg.get("optimized_copy"):
        opt_path = os.path.join(project_root, cfg["optimized_copy"])
        if os.path.exists(opt_path):
            copy_map = load_optimized_copy(opt_path)
            apply_optimized_copy(products, copy_map)

    print(f"\n[{country_code}] Generating DCO creatives — {lang.upper()}/{cfg['currency']}")

    creatives = [generate_creatives(p, lang, cfg) for p in products]
    output_formats = formats or ["google", "meta", "json"]
    paths = {}

    cc = country_code.lower()
    if "google" in output_formats:
        paths["google"] = export_google_csv(
            creatives, os.path.join(project_root, f"output/dco-google-{cc}.csv")
        )
    if "meta" in output_formats:
        paths["meta"] = export_meta_csv(
            creatives, os.path.join(project_root, f"output/dco-meta-{cc}.csv")
        )
    if "json" in output_formats:
        paths["json"] = export_json(
            creatives, os.path.join(project_root, f"output/dco-{cc}.json")
        )

    return paths


def generate_dco_all(
    input_path: str,
    project_root: str,
    formats: list[str] | None = None,
) -> None:
    """Generate DCO creatives for all configured countries."""
    countries = load_countries(project_root)
    for code in countries:
        generate_dco(input_path, code, project_root, formats)
    print(f"\nGenerated DCO creatives for {len(countries)} markets.")


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="Generate DCO ad creatives from product feed data"
    )
    parser.add_argument(
        "-i", "--input",
        default=os.path.join(project_root, "products.json"),
        help="Path to products.json (default: %(default)s)",
    )
    parser.add_argument(
        "--country",
        required=True,
        help="Country code (US, MX, CO, BR, DO) or 'all'",
    )
    parser.add_argument(
        "--format",
        default=None,
        choices=["google", "meta", "json"],
        help="Output only this format (default: all formats)",
    )
    args = parser.parse_args()

    formats = [args.format] if args.format else None

    if args.country.lower() == "all":
        generate_dco_all(args.input, project_root, formats)
    else:
        generate_dco(args.input, args.country.upper(), project_root, formats)


if __name__ == "__main__":
    main()
