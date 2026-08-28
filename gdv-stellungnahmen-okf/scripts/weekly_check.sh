#!/usr/bin/env bash
# weekly_check.sh - prüft ob neue GDV-Stellungnahmen verfügbar sind und refresht das Bündel.
#
# Ablauf:
#   1. Alten Katalog merken (blob_ids)
#   2. Neuen Katalog scrapen
#   3. Neue Dokumente zählen
#   4. Bei Fund: macOS-Benachrichtigung; wenn docling-serve läuft -> vollständige Pipeline
#
# Für den Crontab:
#   0 8 * * 1  /usr/bin/env bash /path/to/scripts/weekly_check.sh >> /path/to/logs/weekly_check.log 2>&1
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO/logs"
CATALOG="$REPO/GDV_Stellungnahmen/catalog.json"
DOCLING="${DOCLING_URL:-http://localhost:5001}"
PYTHON="${PYTHON:-python3}"

mkdir -p "$LOG_DIR"
TS=$(date -u +%FT%TZ)
echo "[$TS] weekly_check: start"

# --- Schritt 1: Vorhandene blob_ids aus dem alten Katalog merken ---
old_ids_file="$LOG_DIR/last_known_ids.txt"
if [ -f "$CATALOG" ]; then
    $PYTHON -c "
import json, sys
c = json.load(open('$CATALOG'))
ids = {d.get('blob_id') or d.get('pdf_url') for d in c.get('documents', [])}
print('\n'.join(sorted(str(i) for i in ids if i)))
" > "$old_ids_file"
    old_count=$($PYTHON -c "import json; c=json.load(open('$CATALOG')); print(c.get('count',0))")
else
    touch "$old_ids_file"
    old_count=0
fi
echo "[$(date -u +%FT%TZ)] Bekannte Dokumente: $old_count"

# --- Schritt 2: Neuen Katalog scrapen (kein docling nötig) ---
echo "[$(date -u +%FT%TZ)] Scrape läuft..."
$PYTHON "$REPO/scripts/scrape_gdv.py"

# --- Schritt 3: Neue IDs ermitteln ---
new_ids_file="$LOG_DIR/current_ids.txt"
$PYTHON -c "
import json, sys
c = json.load(open('$CATALOG'))
ids = {d.get('blob_id') or d.get('pdf_url') for d in c.get('documents', [])}
print('\n'.join(sorted(str(i) for i in ids if i)))
" > "$new_ids_file"
new_count=$($PYTHON -c "import json; c=json.load(open('$CATALOG')); print(c.get('count',0))")

added=$(comm -13 "$old_ids_file" "$new_ids_file" | wc -l | tr -d ' ')
removed=$(comm -23 "$old_ids_file" "$new_ids_file" | wc -l | tr -d ' ')

echo "[$(date -u +%FT%TZ)] Katalog: $old_count -> $new_count (+$added neu, -$removed entfernt)"

if [ "$added" -eq 0 ]; then
    echo "[$(date -u +%FT%TZ)] Keine neuen Dokumente. Fertig."
    exit 0
fi

# --- Schritt 4a: macOS-Benachrichtigung ---
osascript -e "display notification \"$added neue Stellungnahme(n) gefunden (gesamt $new_count). Bündel wird aktualisiert.\" with title \"GDV OKF Refresh\" sound name \"Glass\"" 2>/dev/null || true

# --- Schritt 4b: Pipeline nur wenn docling-serve erreichbar ---
if ! curl -sf --max-time 10 "$DOCLING/health" >/dev/null 2>&1; then
    echo "[$(date -u +%FT%TZ)] docling-serve nicht erreichbar ($DOCLING). Konvertierung übersprungen."
    osascript -e "display notification \"$added neue Stellungnahme(n) im Katalog, aber docling-serve läuft nicht. Bitte Colima starten und scripts/refresh.sh manuell ausführen.\" with title \"GDV OKF: Aktion nötig\" sound name \"Basso\"" 2>/dev/null || true
    echo "[$(date -u +%FT%TZ)] Tipp: colima start && docker start <docling-container> && scripts/refresh.sh"
    exit 1
fi

# --- Schritt 4c: Vollständige Pipeline (Konvertierung + Bundle + Validierung) ---
echo "[$(date -u +%FT%TZ)] docling-serve läuft. Starte vollständige Pipeline..."
$PYTHON "$REPO/scripts/convert_docling.py"
$PYTHON "$REPO/scripts/build_bundle.py"
$PYTHON "$REPO/scripts/okf_validate.py" "$REPO/bundles/gdv-stellungnahmen" --corpus

fails=$($PYTHON -c "import json,os; p='$REPO/GDV_Stellungnahmen/convert_failures.json'; print(len(json.load(open(p))) if os.path.exists(p) else 0)")
echo "[$(date -u +%FT%TZ)] Konversionsfehler noch offen: $fails"

osascript -e "display notification \"$added neue Stellungnahme(n) eingelesen. Bündel aktuell ($new_count Dokumente). Fehler: $fails\" with title \"GDV OKF Refresh abgeschlossen\" sound name \"Glass\"" 2>/dev/null || true

echo "[$(date -u +%FT%TZ)] weekly_check: fertig"
