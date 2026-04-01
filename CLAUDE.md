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
├── src/
│   ├── config.py                      # Store-level settings & feed defaults
│   ├── feed_generator.py              # Validates products.json → writes feed.xml
│   ├── fetch_shopify.py               # Shopify Admin API (OAuth) → products.json
│   └── dco-dashboard.jsx              # React: AI Feed Studio (Claude-powered title/desc optimizer)
├── n8n/
│   ├── gmc-feed-code-node.js          # n8n Code node: Shopify JSON → GMC XML string
│   └── disuri-gmc-feed-workflow.json  # Full n8n workflow (import into jcmarketing.app.n8n.cloud)
├── tests/
│   ├── sample_products.json           # 7-item test fixture (real SKUs)
│   └── optimized_copy.json            # AI-optimized titles/descriptions overlay
└── output/
    └── disuri_beauty_feed.xml         # Generated feed (gitignored)
```

## Usage

```bash
# Generate feed from sample data
python3 src/feed_generator.py -i tests/sample_products.json -o output/feed.xml

# Generate feed with AI-optimized titles/descriptions
python3 src/feed_generator.py -i tests/sample_products.json \
  --optimized tests/optimized_copy.json -o output/feed-optimized.xml

# Generate feed from live Shopify data (client_credentials OAuth)
export SHOPIFY_STORE_URL=https://disuri-beauty.myshopify.com
export SHOPIFY_CLIENT_ID=your_client_id
export SHOPIFY_CLIENT_SECRET=your_client_secret
python3 src/fetch_shopify.py          # authenticates → writes products.json
python3 src/feed_generator.py         # reads products.json → output/feed.xml
```

## Tech Stack

- Python 3.11+ (stdlib only — no pip dependencies)
- `xml.etree.ElementTree` + `minidom` for XML generation
- `urllib.request` for Shopify API calls (client_credentials OAuth)
- React + Claude API for AI Feed Studio (dco-dashboard.jsx)
- n8n for automated feed sync (every 6 hours)

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

## n8n Automation (Phase 2)

The `n8n/` folder contains a complete workflow for `jcmarketing.app.n8n.cloud`
that keeps the feed live forever:

```
Cron (6h) → Shopify OAuth → Fetch Products → Build XML → Upload R2/S3 → Ping GMC
                                                  ↘ Error → Slack DM
```

**Setup:**
1. Import `n8n/disuri-gmc-feed-workflow.json` into your n8n instance
2. Paste the contents of `n8n/gmc-feed-code-node.js` into the Code node
3. Set environment variables in n8n:
   - `SHOPIFY_STORE_URL`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`
   - `R2_ENDPOINT`, `R2_BUCKET` (Cloudflare R2 or S3-compatible)
   - `GMC_MERCHANT_ID`, `GMC_FEED_ID`, `GMC_ACCESS_TOKEN`
   - `SLACK_FEED_CHANNEL`
4. Configure Slack + S3/R2 credentials in n8n
5. The R2 public URL becomes your stable GMC feed URL — set it once in GMC

The Code node handles GTIN lookup, bundle flagging (`identifier_exists: no`),
compare_at_price → sale_price mapping, and optimized copy overlay. Error branch
fires a Slack DM before bad data reaches GMC.

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
