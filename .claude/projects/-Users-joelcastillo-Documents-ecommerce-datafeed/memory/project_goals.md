---
name: Multi-country feed + channel marketing strategy
description: Joel's goal is multi-country product feeds, AI-optimized per market, feeding into channel marketing (GMC, Klaviyo, etc.)
type: project
---

Joel's end-state vision for the ecommerce-datafeed project:

1. **Multi-country product feeds** — localized GMC feeds for different markets (currency, language, shipping, tax)
2. **AI-optimized copy per market** — use Claude to optimize titles/descriptions per locale and channel
3. **Channel marketing** — use the feed data to power Google Shopping, Klaviyo emails, and potentially other channels (Meta, TikTok)

**Why:** DISURI Beauty is English/Spanish bilingual. Multi-market expansion is a growth priority. The feed is the single source of truth that powers all downstream marketing channels.

**How to apply:** Architecture decisions should support multi-locale and multi-channel from the start. Product data should flow: Shopify → centralized product JSON → per-country/per-channel feed generation → distribution (R2/S3 for GMC, Klaviyo catalog sync, etc.)
