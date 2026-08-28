#!/usr/bin/env bash
# refresh.sh - end-to-end refresh of the gdv-stellungnahmen bundle.
#
# Idempotent and incremental: scrape the catalog, convert only new PDFs (md cache),
# rebuild the bundle, validate. Intended for a scheduler (cron / CI schedule /
# Kubernetes CronJob). Requires the local docling-serve (Colima) to be running.
#
# Usage:  scripts/refresh.sh
# Exit non-zero if the bundle does not validate, so a scheduler can alert.
set -euo pipefail

cd "$(dirname "$0")/.."
BUNDLE="bundles/gdv-stellungnahmen"
DOCLING="${DOCLING_URL:-http://localhost:5001}"

echo "[refresh] $(date -u +%FT%TZ) starting"

# 1. docling-serve reachable?
if ! curl -sf --max-time 10 "$DOCLING/health" >/dev/null; then
  echo "[refresh] ERROR: docling-serve not reachable at $DOCLING (start Colima / the container)" >&2
  exit 2
fi

# 2. scrape catalog
python3 scripts/scrape_gdv.py

# 3. convert only new PDFs (cache skips existing markdown)
python3 scripts/convert_docling.py

# 4. rebuild bundle
python3 scripts/build_bundle.py

# 5. validate (must be 0 errors)
python3 scripts/okf_validate.py "$BUNDLE" --corpus

# 6. surface conversion failures, if any
fails=$(python3 -c "import json,os; p='GDV_Stellungnahmen/convert_failures.json'; print(len(json.load(open(p))) if os.path.exists(p) else 0)")
echo "[refresh] conversion failures pending retry: $fails"

echo "[refresh] $(date -u +%FT%TZ) done"
# A scheduler can now: git add -A && git commit only if there is a diff.
