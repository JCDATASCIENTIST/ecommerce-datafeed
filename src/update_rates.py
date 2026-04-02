"""
DISURI Beauty — Live Exchange Rate Updater.

Fetches current USD exchange rates from the Open Exchange Rates API (free,
no API key required) and updates countries.json in place.

Run before feed generation to ensure localized prices are current:
    python update_rates.py              # update and print summary
    python update_rates.py --dry-run    # preview without writing

Uses open.er-api.com — rates update daily. Falls back gracefully if the
API is unreachable (keeps existing rates).
"""

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime

RATE_API_URL = "https://open.er-api.com/v6/latest/USD"
COUNTRIES_FILE = "countries.json"


def fetch_usd_rates() -> dict[str, float]:
    """Fetch latest exchange rates vs USD. Returns dict of currency→rate."""
    req = urllib.request.Request(RATE_API_URL, headers={"User-Agent": "DISURI-Feed/1.0"})

    # Try certifi first (macOS fix), then default context
    contexts = []
    try:
        import certifi
        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except ImportError:
        pass
    contexts.append(ssl.create_default_context())

    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read())
            break
        except (ssl.SSLError, urllib.error.URLError):
            continue
    else:
        raise RuntimeError("Could not connect to exchange rate API")

    if data.get("result") != "success":
        raise RuntimeError(f"API returned: {data.get('result', 'unknown error')}")

    return data["rates"]


def update_countries(project_root: str, dry_run: bool = False) -> dict[str, dict]:
    """Update exchange rates in countries.json. Returns summary of changes."""
    countries_path = os.path.join(project_root, COUNTRIES_FILE)
    with open(countries_path, encoding="utf-8") as f:
        countries = json.load(f)

    print("Fetching live exchange rates...")
    rates = fetch_usd_rates()

    changes = {}
    for code, config in countries.items():
        currency = config["currency"]
        old_rate = config.get("exchange_rate", 1.0)

        if currency == "USD":
            continue

        new_rate = rates.get(currency)
        if new_rate is None:
            print(f"  [{code}] {currency} — not available, keeping {old_rate}")
            continue

        new_rate = round(new_rate, 4)
        pct_change = ((new_rate - old_rate) / old_rate) * 100 if old_rate else 0
        changes[code] = {
            "currency": currency,
            "old_rate": old_rate,
            "new_rate": new_rate,
            "pct_change": pct_change,
        }

        config["exchange_rate"] = new_rate
        print(f"  [{code}] {currency}: {old_rate} → {new_rate} ({pct_change:+.2f}%)")

    if not changes:
        print("No rates to update.")
        return changes

    if dry_run:
        print("\n[DRY RUN] No changes written.")
    else:
        with open(countries_path, "w", encoding="utf-8") as f:
            json.dump(countries, f, indent=2, ensure_ascii=False)
            f.write("\n")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"\nUpdated {len(changes)} rates in {COUNTRIES_FILE} at {now}")

    return changes


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dry_run = "--dry-run" in sys.argv

    try:
        update_countries(project_root, dry_run)
    except Exception as e:
        print(f"Error fetching rates: {e}")
        print("Keeping existing rates in countries.json.")
        sys.exit(1)


if __name__ == "__main__":
    main()
