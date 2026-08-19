#!/usr/bin/env bash
# Production output verification gate — curl a live/preview URL and assert on the
# served HTML. Run it after a deploy (CI, see .github/workflows/verify-production.yml)
# or by hand against any URL, including a Cloudflare Pages preview, BEFORE promotion.
#
# Usage:
#   scripts/verify-production.sh [URL]
#   scripts/verify-production.sh https://<hash>.void-news.pages.dev/
#
# Exit 0 = clean, 1 = at least one served-output defect (details printed).
set -euo pipefail

URL="${1:-https://news.voidvision.org/}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -t voidverify.XXXXXX.html)"
trap 'rm -f "$TMP"' EXIT

echo "Fetching $URL ..."
# Cache-buster + no-cache so we never verify a stale CDN copy.
if ! curl -fsSL --max-time 30 -H 'Cache-Control: no-cache' \
        "${URL}?_verify=$(date +%s)" -o "$TMP"; then
  echo "ERROR: could not fetch $URL" >&2
  exit 2
fi

BYTES=$(wc -c < "$TMP")
echo "Fetched ${BYTES} bytes."
if [ "$BYTES" -lt 20000 ]; then
  echo "ERROR: response implausibly small (${BYTES} bytes) — not a rendered feed" >&2
  exit 2
fi

python "$HERE/verify_production.py" "$TMP" --url "$URL"
