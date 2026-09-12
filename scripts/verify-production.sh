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

# Feed size comes from the one config the pipeline, the frontend and this gate
# all read. A 20-story page is roughly 40% the bytes of the old 50-story one,
# so the flat 20000-byte floor would have been the wrong shape after the cut;
# derive it instead (~1 KB per card, well under a real render).
REPO="$(cd "$HERE/.." && pwd)"
EXPECT=$(python3 -c "import json;print(json.load(open('$REPO/frontend/config/feed.json'))['displayed'])" 2>/dev/null || echo "")
MIN_BYTES=15000
if [ -n "$EXPECT" ]; then
  MIN_BYTES=$(( EXPECT * 1000 ))
fi
if [ "$BYTES" -lt "$MIN_BYTES" ]; then
  echo "ERROR: response implausibly small (${BYTES} bytes, floor ${MIN_BYTES}) — not a rendered feed" >&2
  exit 2
fi

if [ -n "$EXPECT" ]; then
  python3 "$HERE/verify_production.py" "$TMP" --url "$URL" --expect-count "$EXPECT"
else
  python3 "$HERE/verify_production.py" "$TMP" --url "$URL"
fi
