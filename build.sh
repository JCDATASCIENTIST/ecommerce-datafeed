#!/bin/bash
# DISURI Beauty — Full feed + DCO build pipeline
# Usage: ./build.sh [input_file]

set -e
cd "$(dirname "$0")"

INPUT="${1:-tests/sample_products.json}"

echo "═══════════════════════════════════════════"
echo "  DISURI Beauty — Feed Build Pipeline"
echo "═══════════════════════════════════════════"

echo ""
echo "Step 1/3: Updating exchange rates..."
python3 src/update_rates.py

echo ""
echo "Step 2/3: Generating country feeds..."
python3 src/feed_generator.py -i "$INPUT" --country all

echo ""
echo "Step 3/3: Generating DCO ad creatives..."
python3 src/dco_generator.py -i "$INPUT" --country all

echo ""
echo "═══════════════════════════════════════════"
echo "  Build complete! Output files:"
echo "═══════════════════════════════════════════"
echo ""
echo "  XML Feeds:"
ls -1 output/feed-*.xml 2>/dev/null | sed 's/^/    /'
echo ""
echo "  DCO Creatives:"
ls -1 output/dco-*.csv output/dco-*.json 2>/dev/null | sed 's/^/    /'
echo ""
