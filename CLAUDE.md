# DISURI Beauty — Google Merchant Center Feed Generator

## Project Overview

XML feed generator for DISURI Beauty, a Shopify DTC skincare brand. Produces a
Google Merchant Center product data feed conforming to the RSS 2.0 + `g:` namespace
specification (xmlns:g="http://base.google.com/ns/1.0").

## Brand Context

DISURI Beauty is a Korean-formulated (K-beauty) DTC skincare brand with radical
ingredient transparency. Products contain clinically-backed actives at published
concentrations. English/Spanish bilingual brand. All product copy uses
FDA-compliant cosmetic language ("helps improve the appearance of", never
"treats" or "cures").

## Catalog — 7 Individual SKUs

| Handle | Title | GTIN | Price | Category | Taxonomy |
|---|---|---|---|---|---|
| `ultimate-snail-mucin-cream` | Ultimate Snail Mucin Cream | 850064676372 | $34.99 | Cream | …Lotion & Moisturizer |
| `triple-collagen-firming-cream` | Triple Collagen Firming Cream | 850064676334 | $44.99 | Cream | …Lotion & Moisturizer |
| `hyaluronic-acid-intense-cream` | Hyaluronic Acid Intense Cream | 850064676310 | $39.99 | Cream | …Lotion & Moisturizer |
| `triple-collagen-firming-foam` | Triple Collagen Firming Foam | 850064676365 | $14.99 | Cleanser | …Facial Cleansers |
| `triple-collagen-firming-toner` | Triple Collagen Firming Toner | 850064676327 | $27.99 | Toner | …Toners & Astringents |
| `triple-collagen-firming-eye-cream` | Triple Collagen Firming Eye Cream | 850064676341 | $33.99 | Eye Care | …Skin Care (parent) |
| `triple-collagen-firming-essence` | Triple Collagen Firming Essence | 850066107188 | $19.99 | Essence | …Skin Care (parent) |

**Bundles (3):** not yet defined — add to `products.json` when bundle handles,
prices, and constituent SKUs are finalized.

## Project Structure

```
/
├── CLAUDE.md                          # This file — project context & conventions
├── products.json                      # Product catalog (source of truth for feed)
├── countries.json                     # Multi-country configs (currency, language, shipping, rates)
├── build.sh                           # One-command pipeline: rates → feeds → DCO
├── src/
│   ├── config.py                      # Store-level settings, multi-country helpers
│   ├── feed_generator.py              # Validates products.json → writes per-country XML feeds
│   ├── fetch_shopify.py               # Shopify Admin API (OAuth) → products.json
│   ├── dco-dashboard.jsx              # React: AI Feed Studio (Claude-powered title/desc optimizer)
│   ├── dco_generator.py               # DCO ad creatives for Google Ads + Meta per market
│   └── update_rates.py                # Fetches live USD exchange rates → updates countries.json
├── .github/
│   └── workflows/
│       └── build-feeds.yml            # Daily cron: rates → feeds → DCO → deploy to GitHub Pages
├── preview/                           # Vite dev server for dashboard (also deployed to Vercel)
├── tests/
│   ├── sample_products.json           # 7-item test fixture (real SKUs)
│   ├── optimized_copy.json            # AI-optimized titles/descriptions (English)
│   ├── optimized_copy_es.json         # AI-optimized titles/descriptions (Spanish)
│   └── optimized_copy_pt.json         # AI-optimized titles/descriptions (Portuguese)
└── output/
    ├── feed-{us,mx,co,br,do}.xml      # Per-country GMC feeds (gitignored)
    ├── dco-google-{cc}.csv             # Google Ads Performance Max assets
    ├── dco-meta-{cc}.csv               # Meta Dynamic Product Ads catalog
    └── dco-{cc}.json                   # Combined DCO JSON for dashboard
```

## Usage

```bash
# Full pipeline: update rates → generate all country feeds → generate DCO creatives
./build.sh

# Generate feeds for a single country
python3 src/feed_generator.py -i tests/sample_products.json --country MX

# Generate feeds for all countries
python3 src/feed_generator.py -i tests/sample_products.json --country all

# Generate DCO ad creatives (Google Ads + Meta) for all countries
python3 src/dco_generator.py -i tests/sample_products.json --country all

# Update exchange rates only
python3 src/update_rates.py

# Generate feed from live Shopify data (client_credentials OAuth)
export SHOPIFY_STORE_URL=https://disuri-beauty.myshopify.com
export SHOPIFY_CLIENT_ID=your_client_id
export SHOPIFY_CLIENT_SECRET=your_client_secret
python3 src/fetch_shopify.py          # authenticates → writes products.json
./build.sh                            # rebuild everything
```

## Tech Stack

- Python 3.11+ (stdlib only — no pip dependencies)
- `xml.etree.ElementTree` + `minidom` for XML generation
- `urllib.request` for Shopify API calls (client_credentials OAuth)
- React + Claude API for AI Feed Studio (dco-dashboard.jsx)
- GitHub Actions for automated daily feed builds + GitHub Pages hosting

## AI-Optimized Copy Workflow

The DCO Dashboard (`src/dco-dashboard.jsx`) uses Claude to generate SEO-optimized
titles and descriptions for each product. The workflow:

1. Open the DCO Dashboard and click "Optimize" per product or "Optimize All"
2. Review the AI-generated titles (max 150 chars) and descriptions (500-800 chars)
3. Export as `optimized_copy.json` via the dashboard's export button
4. Run the feed generator with `--optimized optimized_copy.json` to overlay the
   AI copy onto the feed XML

The `optimized_copy.json` schema:

```json
[
  {
    "id": "product-handle",
    "optimized_title": "SEO-Optimized Title | DISURI Beauty",
    "optimized_description": "AI-written description with K-beauty keywords...",
    "seo_keywords": ["keyword1", "keyword2", ...]
  }
]
```

## Automation (GitHub Actions)

Daily cron at 6:00 AM UTC via `.github/workflows/build-feeds.yml`:

1. Fetches live exchange rates → updates `countries.json`
2. Generates per-country XML feeds (US, MX, CO, BR, DO)
3. Generates DCO ad creatives (Google Ads CSV + Meta CSV)
4. Deploys feeds to GitHub Pages as stable public URLs for GMC

Can also be triggered manually from the GitHub Actions tab or on push when
feed-related files change.

## Feed Format

- RSS 2.0 envelope with `xmlns:g="http://base.google.com/ns/1.0"`
- One `<item>` per product/bundle
- Nested `<g:shipping>` elements with `<g:country>`, `<g:service>`, `<g:price>`
- `<g:custom_label_0>` through `<g:custom_label_4>` for campaign segmentation

## Google Product Taxonomy (Skin Care subtree)

Use the **full path** (not the numeric ID) in `google_product_category`:

| ID   | Path | Used by |
|------|------|---------|
| 567  | Health & Beauty > Personal Care > Cosmetics > Skin Care | Eye Cream, Essence, bundles |
| 2901 | … > Skin Care > Facial Cleansers | Collagen Foam |
| 2907 | … > Skin Care > Lotion & Moisturizer | Snail Mucin Cream, Collagen Cream, HA Cream |
| 5976 | … > Skin Care > Toners & Astringents | Collagen Toner |
| 6262 | … > Skin Care > Skin Care Masks & Peels | (none currently) |
| 2912 | … > Skin Care > Sunscreen | (none currently) |

## Custom Label Schema

| Label             | Purpose         | Values |
|-------------------|-----------------|--------|
| `custom_label_0`  | Margin tier     | `high_margin`, `medium_margin`, `low_margin` |
| `custom_label_1`  | Lifecycle       | `bestseller`, `core`, `new_arrival` |
| `custom_label_2`  | Promo status    | `full_price`, `on_sale`, `clearance` |
| `custom_label_3`  | Collection      | `snail-mucin`, `triple-collagen`, `hyaluronic-acid` |
| `custom_label_4`  | Reserved        | free text |

## Validation Rules

`feed_generator.py` runs these checks before writing XML (errors abort, warnings don't):

- **Required fields**: `id`, `title`, `description`, `link`, `image_link`, `price`
- **Price format**: must match `XX.XX USD` (regex `^\d+\.\d{2}\s[A-Z]{3}$`)
- **Availability**: must be `in_stock`, `out_of_stock`, `preorder`, or `backorder`
- **Taxonomy guard**: `google_product_category` must start with
  `Health & Beauty > Personal Care`
- **Sale price**: `sale_price_effective_date` is required when `sale_price` is set
- **Bundles**: `identifier_exists` must be present on bundle items
- **Shipping** (warning): flags products with no shipping defined
- **Brand** (warning): falls back to store default if missing

## Conventions

- All prices in USD, formatted as `"XX.XX USD"` per GMC spec.
- Product IDs use Shopify handles (e.g. `triple-collagen-firming-cream`).
- All 7 SKUs have real GTINs → `identifier_exists: yes` auto-set.
- Bundle items (when added) set `g:is_bundle` to `true` and `g:identifier_exists`
  to `no`.
- Entity-escaped XML (default `ElementTree` behavior) is used instead of CDATA —
  both are GMC-compliant.
- Product copy uses FDA-compliant cosmetic language only.
