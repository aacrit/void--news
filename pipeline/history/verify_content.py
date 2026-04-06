"""
void --history content verifier.

CLI tool that reads event YAML files and cross-references verifiable claims
against free APIs to flag potential hallucinations or fabrications. All 25
event YAMLs were written by AI agents -- every fact, quote, date, and
attribution could be hallucinated. This verifier catches fabrication before
content goes live.

APIs used (all free, no keys):
  OpenAlex  -- scholarly work metadata (271M works)
  CrossRef  -- DOI registry, title/author lookup
  Wikidata  -- structured entity data (people, events, deaths)
  Open Library -- book existence verification
  Nominatim -- reverse geocoding for coordinate checks

Usage:
    python pipeline/history/verify_content.py --event armenian-genocide
    python pipeline/history/verify_content.py --all
    python pipeline/history/verify_content.py --event hiroshima-nagasaki --quick
    python pipeline/history/verify_content.py --event armenian-genocide --output json
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import requests
import yaml


# ---------------------------------------------------------------------------
# Paths & sys.path
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PIPELINE_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _PIPELINE_DIR.parent

for p in [str(_PROJECT_ROOT), str(_PIPELINE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

EVENTS_DIR = _PROJECT_ROOT / "data" / "history" / "events"
VERIFICATION_DIR = _PROJECT_ROOT / "data" / "history" / "verification"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

# Status constants
VERIFIED = "VERIFIED"
NOT_FOUND = "NOT_FOUND"
AMBIGUOUS = "AMBIGUOUS"
DATE_MISMATCH = "DATE_MISMATCH"
YEAR_MISMATCH = "YEAR_MISMATCH"
MATCHES = "MATCHES"
DIFFERS = "DIFFERS"
NO_DATA = "NO_DATA"
WORK_EXISTS = "WORK_EXISTS"
WORK_NOT_FOUND = "WORK_NOT_FOUND"
AUTHOR_EXISTS = "AUTHOR_EXISTS"
AUTHOR_NOT_FOUND = "AUTHOR_NOT_FOUND"
ERROR = "ERROR"
SKIPPED = "SKIPPED"


@dataclass
class VerificationResult:
    """A single verification check result."""
    category: str          # "scholar", "key_figure", "publication", "death_toll", "coordinates", "primary_source"
    claim: str             # Human-readable description of the claim
    status: str            # VERIFIED, NOT_FOUND, AMBIGUOUS, etc.
    api_source: str        # Which API confirmed/denied
    details: str = ""      # Extra detail (e.g. Wikidata ID, fuzzy score)
    confidence: float = 0.0  # 0-1 match confidence

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None and v != ""}


# ---------------------------------------------------------------------------
# Rate-limited HTTP session
# ---------------------------------------------------------------------------

class RateLimitedSession:
    """Shared HTTP session with per-domain rate limiting."""

    def __init__(self, delay: float = 1.0):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "void-news-history-verifier/1.0 (content-verification; +https://github.com/void-news)",
        })
        self._last_request: dict[str, float] = {}  # domain -> timestamp
        self._default_delay = delay

    def _rate_limit(self, domain: str, delay: float | None = None):
        """Enforce minimum delay between requests to the same domain."""
        d = delay if delay is not None else self._default_delay
        last = self._last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < d:
            time.sleep(d - elapsed)
        self._last_request[domain] = time.time()

    def get_json(self, url: str, params: dict = None, timeout: int = 20, delay: float | None = None) -> dict | None:
        """Rate-limited GET returning JSON, or None on failure."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        self._rate_limit(domain, delay)
        try:
            resp = self._session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"    [timeout] {url}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    [HTTP {e.response.status_code}] {url}")
            return None
        except Exception as e:
            print(f"    [error] {url}: {e}")
            return None


# Global session
_session = RateLimitedSession(delay=1.0)


# ---------------------------------------------------------------------------
# Fuzzy matching utilities
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _title_similarity(a: str, b: str) -> float:
    """Compute title similarity using SequenceMatcher (0-1)."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _token_overlap(a: str, b: str) -> float:
    """Compute Jaccard token overlap (0-1)."""
    ta = set(_normalize(a).split())
    tb = set(_normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _author_match(query_author: str, result_author: str) -> bool:
    """Check if author names match (last-name matching, handles initials)."""
    qa = _normalize(query_author)
    ra = _normalize(result_author)
    if not qa or not ra:
        return False
    # Exact substring
    if qa in ra or ra in qa:
        return True
    # Last name match
    q_parts = qa.split()
    r_parts = ra.split()
    if q_parts and r_parts:
        # Compare last names
        if q_parts[-1] == r_parts[-1]:
            return True
        # Also check if any of the query last names appears in the result
        for qp in q_parts:
            if len(qp) > 2 and qp in r_parts:
                return True
    return False


def _extract_year(year_str: str) -> int | None:
    """Extract a 4-digit year from a string like '2006', '1922 (English translation 2009)', '1915-1930'."""
    if not year_str:
        return None
    m = re.search(r'(\d{4})', str(year_str))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# 1. Scholar/Author Verification (OpenAlex + CrossRef)
# ---------------------------------------------------------------------------

def verify_scholar_source(author: str, title: str, year: str | None) -> VerificationResult:
    """Verify a scholarly source citation via OpenAlex and CrossRef."""
    claim = f'{author} -- "{title}" ({year or "?"})'
    parsed_year = _extract_year(year) if year else None

    # --- OpenAlex ---
    params = {
        "search": title,
        "per_page": "5",
        "sort": "relevance_score:desc",
        "mailto": "void-news@proton.me",
    }
    if parsed_year:
        params["filter"] = f"publication_year:{parsed_year}"

    data = _session.get_json("https://api.openalex.org/works", params=params)
    if data:
        for work in data.get("results", [])[:5]:
            work_title = work.get("title", "")
            if not work_title:
                continue
            sim = _title_similarity(title, work_title)
            tok = _token_overlap(title, work_title)
            score = max(sim, tok)

            # Check author
            work_authors = [
                a.get("author", {}).get("display_name", "")
                for a in work.get("authorships", [])
            ]
            author_found = any(_author_match(author, wa) for wa in work_authors)

            if score >= 0.75 and author_found:
                return VerificationResult(
                    category="scholar",
                    claim=claim,
                    status=VERIFIED,
                    api_source="OpenAlex",
                    details=f'Matched: "{work_title}" by {", ".join(work_authors[:2])}',
                    confidence=score,
                )
            elif score >= 0.55:
                # Title similar but author may differ -- try without year filter
                if author_found:
                    return VerificationResult(
                        category="scholar",
                        claim=claim,
                        status=VERIFIED,
                        api_source="OpenAlex",
                        details=f'Fuzzy match: "{work_title}" (sim={score:.2f})',
                        confidence=score,
                    )

    # --- OpenAlex without year filter (in case year was wrong) ---
    if parsed_year:
        params_no_year = {
            "search": title,
            "per_page": "5",
            "sort": "relevance_score:desc",
            "mailto": "void-news@proton.me",
        }
        data = _session.get_json("https://api.openalex.org/works", params=params_no_year)
        if data:
            for work in data.get("results", [])[:5]:
                work_title = work.get("title", "")
                if not work_title:
                    continue
                sim = _title_similarity(title, work_title)
                tok = _token_overlap(title, work_title)
                score = max(sim, tok)
                work_authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in work.get("authorships", [])
                ]
                author_found = any(_author_match(author, wa) for wa in work_authors)
                if score >= 0.65 and author_found:
                    work_year = work.get("publication_year")
                    return VerificationResult(
                        category="scholar",
                        claim=claim,
                        status=VERIFIED,
                        api_source="OpenAlex",
                        details=f'Matched (year-relaxed): "{work_title}" ({work_year})',
                        confidence=score,
                    )

    # --- CrossRef ---
    cr_query = f"{title} {author}"
    data = _session.get_json("https://api.crossref.org/works", params={
        "query": cr_query,
        "rows": "5",
        "sort": "relevance",
        "mailto": "void-news@proton.me",
    })
    if data:
        for item in data.get("message", {}).get("items", [])[:5]:
            titles = item.get("title", [])
            item_title = titles[0] if titles else ""
            if not item_title:
                continue
            sim = _title_similarity(title, item_title)
            tok = _token_overlap(title, item_title)
            score = max(sim, tok)

            cr_authors = []
            for a in item.get("author", []):
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    cr_authors.append(name)
            author_found = any(_author_match(author, ca) for ca in cr_authors)

            if score >= 0.70 and author_found:
                return VerificationResult(
                    category="scholar",
                    claim=claim,
                    status=VERIFIED,
                    api_source="CrossRef",
                    details=f'Matched: "{item_title}" by {", ".join(cr_authors[:2])}',
                    confidence=score,
                )
            elif score >= 0.85:
                # Very high title match even without author confirmation
                return VerificationResult(
                    category="scholar",
                    claim=claim,
                    status=VERIFIED,
                    api_source="CrossRef",
                    details=f'Title match: "{item_title}" (sim={score:.2f})',
                    confidence=score,
                )
            elif score >= 0.50:
                return VerificationResult(
                    category="scholar",
                    claim=claim,
                    status=AMBIGUOUS,
                    api_source="CrossRef",
                    details=f'Fuzzy match: "{item_title}" (sim={score:.2f})',
                    confidence=score,
                )

    return VerificationResult(
        category="scholar",
        claim=claim,
        status=NOT_FOUND,
        api_source="OpenAlex+CrossRef",
        details="No matching work found in OpenAlex or CrossRef",
        confidence=0.0,
    )


# ---------------------------------------------------------------------------
# 2. Key Figure Verification (Wikidata)
# ---------------------------------------------------------------------------

def verify_key_figure(name: str, role: str, event_year: int | None = None) -> VerificationResult:
    """Verify a key historical figure exists in Wikidata."""
    claim = f'{name} -- {role[:80]}'

    # Try multiple search variants for better recall
    search_names = [name]
    # If name has a title/honorific like "Sr." or "Jr.", try without it
    clean = re.sub(r'\b(Sr\.|Jr\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s*', '', name).strip()
    if clean != name:
        search_names.append(clean)
    # Try individual name parts for compound names like "Talat Pasha"
    parts = name.split()
    if len(parts) >= 2:
        # Try each significant part as a separate search
        for part in parts:
            if len(part) > 3 and part not in ("Pasha", "Shah", "King", "Queen", "Emperor", "Sultan"):
                search_names.append(part)

    all_items = []
    for search_name in search_names:
        data = _session.get_json("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities",
            "search": search_name,
            "language": "en",
            "limit": "5",
            "format": "json",
        })
        if data:
            all_items.extend(data.get("search", []))
        if all_items:
            break  # Use first successful search

    if not all_items:
        return VerificationResult(
            category="key_figure", claim=claim, status=ERROR,
            api_source="Wikidata", details="API request failed",
        )

    # Deduplicate by entity ID
    seen_ids = set()
    unique_items = []
    for item in all_items:
        eid = item.get("id", "")
        if eid not in seen_ids:
            seen_ids.add(eid)
            unique_items.append(item)

    for item in unique_items:
        entity_id = item.get("id", "")
        label = item.get("label", "")
        desc = item.get("description", "")

        # Check if name matches (flexible: any word overlap or fuzzy part match)
        name_parts = set(_normalize(name).split())
        label_parts = set(_normalize(label).split())
        overlap = name_parts & label_parts
        # Need at least one significant word overlap (>3 chars)
        significant_overlap = any(len(w) > 3 for w in overlap)
        # Also check fuzzy match between name parts (handles Talat/Talaat, Pasha/Pasa)
        if not significant_overlap:
            for np in name_parts:
                if len(np) <= 3:
                    continue
                for lp in label_parts:
                    if len(lp) <= 3:
                        continue
                    if SequenceMatcher(None, np, lp).ratio() >= 0.75:
                        significant_overlap = True
                        break
                if significant_overlap:
                    break
        if not significant_overlap and not _author_match(name, label):
            continue

        # Fetch claims to check if it's a person and dates
        claims_data = _session.get_json("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities",
            "ids": entity_id,
            "props": "claims",
            "format": "json",
        })
        if not claims_data:
            continue

        entity = claims_data.get("entities", {}).get(entity_id, {})
        claims = entity.get("claims", {})

        # Check P31 (instance of) for Q5 (human)
        is_human = False
        for claim_val in claims.get("P31", []):
            val = claim_val.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(val, dict) and val.get("numeric-id") == 5:
                is_human = True
                break

        # Extract birth/death years
        birth_year = _extract_wikidata_year(claims, "P569")
        death_year = _extract_wikidata_year(claims, "P570")

        if is_human or birth_year or death_year:
            # Date overlap check
            if event_year and (birth_year or death_year):
                if birth_year and birth_year > event_year + 5:
                    return VerificationResult(
                        category="key_figure", claim=claim, status=DATE_MISMATCH,
                        api_source="Wikidata",
                        details=f"{entity_id} ({label}): born {birth_year}, event {event_year}",
                        confidence=0.3,
                    )
                if death_year and death_year < event_year - 5:
                    return VerificationResult(
                        category="key_figure", claim=claim, status=DATE_MISMATCH,
                        api_source="Wikidata",
                        details=f"{entity_id} ({label}): died {death_year}, event {event_year}",
                        confidence=0.3,
                    )

            date_info = ""
            if birth_year:
                date_info += f"b. {birth_year}"
            if death_year:
                date_info += f", d. {death_year}" if date_info else f"d. {death_year}"
            if date_info:
                date_info = f" ({date_info})"

            return VerificationResult(
                category="key_figure", claim=claim, status=VERIFIED,
                api_source="Wikidata",
                details=f"{entity_id}{date_info}: {desc}",
                confidence=0.9,
            )

    return VerificationResult(
        category="key_figure", claim=claim, status=NOT_FOUND,
        api_source="Wikidata",
        details="No matching person found in Wikidata",
        confidence=0.0,
    )


def _extract_wikidata_year(claims: dict, prop: str) -> int | None:
    """Extract year from a Wikidata time claim (P569=birth, P570=death)."""
    for claim_val in claims.get(prop, []):
        time_val = (
            claim_val.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("time", "")
        )
        if time_val:
            # Format: "+1921-03-15T00:00:00Z"
            m = re.search(r'[+-]?(\d{4})', time_val)
            if m:
                return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# 3. Publication Verification (Open Library)
# ---------------------------------------------------------------------------

def verify_publication(author: str, title: str, year: str | None) -> VerificationResult:
    """Verify a book exists via Open Library."""
    claim = f'{author} -- "{title}" ({year or "?"})'
    parsed_year = _extract_year(year) if year else None

    # Clean author name for query (remove parenthetical notes)
    clean_author = re.sub(r'\(.*?\)', '', author).strip()
    # Remove "as told to..." type suffixes
    clean_author = re.sub(r'\s+as told to\b.*', '', clean_author, flags=re.IGNORECASE).strip()

    data = _session.get_json("https://openlibrary.org/search.json", params={
        "title": title,
        "author": clean_author,
        "limit": "5",
    })
    if not data:
        return VerificationResult(
            category="publication", claim=claim, status=ERROR,
            api_source="Open Library", details="API request failed",
        )

    for doc in data.get("docs", [])[:5]:
        ol_title = doc.get("title", "")
        sim = _title_similarity(title, ol_title)
        tok = _token_overlap(title, ol_title)
        score = max(sim, tok)

        ol_authors = doc.get("author_name", [])
        author_found = any(_author_match(clean_author, oa) for oa in ol_authors)

        if score >= 0.60 and author_found:
            first_pub = doc.get("first_publish_year")
            if parsed_year and first_pub and abs(first_pub - parsed_year) > 5:
                return VerificationResult(
                    category="publication", claim=claim, status=YEAR_MISMATCH,
                    api_source="Open Library",
                    details=f'Found: "{ol_title}" ({first_pub}), YAML says {parsed_year}',
                    confidence=score,
                )
            return VerificationResult(
                category="publication", claim=claim, status=VERIFIED,
                api_source="Open Library",
                details=f'Found: "{ol_title}" by {", ".join(ol_authors[:2])} ({first_pub or "?"})',
                confidence=score,
            )
        elif score >= 0.80:
            # Very high title match even without author confirmation
            first_pub = doc.get("first_publish_year")
            return VerificationResult(
                category="publication", claim=claim, status=VERIFIED,
                api_source="Open Library",
                details=f'Title match: "{ol_title}" ({first_pub or "?"}) (sim={score:.2f})',
                confidence=score,
            )
        elif score >= 0.45:
            return VerificationResult(
                category="publication", claim=claim, status=AMBIGUOUS,
                api_source="Open Library",
                details=f'Fuzzy match: "{ol_title}" (sim={score:.2f})',
                confidence=score,
            )

    # Fallback: try title-only search in Open Library (without author filter)
    data2 = _session.get_json("https://openlibrary.org/search.json", params={
        "title": title,
        "limit": "5",
    })
    if data2:
        for doc in data2.get("docs", [])[:5]:
            ol_title = doc.get("title", "")
            sim = _title_similarity(title, ol_title)
            tok = _token_overlap(title, ol_title)
            score = max(sim, tok)
            if score >= 0.75:
                first_pub = doc.get("first_publish_year")
                ol_authors = doc.get("author_name", [])
                return VerificationResult(
                    category="publication", claim=claim, status=VERIFIED,
                    api_source="Open Library",
                    details=f'Title match: "{ol_title}" by {", ".join(ol_authors[:2])} ({first_pub or "?"})',
                    confidence=score,
                )

    return VerificationResult(
        category="publication", claim=claim, status=NOT_FOUND,
        api_source="Open Library",
        details="No matching book found in Open Library",
        confidence=0.0,
    )


# ---------------------------------------------------------------------------
# 4. Death Toll Cross-Reference (Wikidata)
# ---------------------------------------------------------------------------

def verify_death_toll(event_title: str, yaml_death_toll: str) -> VerificationResult:
    """Cross-reference death toll with Wikidata P1120 (number of deaths)."""
    claim = f'Death toll: {yaml_death_toll}'

    # Parse YAML death toll range
    yaml_range = _parse_death_toll(yaml_death_toll)
    if not yaml_range:
        return VerificationResult(
            category="death_toll", claim=claim, status=SKIPPED,
            api_source="n/a", details="Could not parse death toll from YAML",
        )

    # Search for the event in Wikidata
    data = _session.get_json("https://www.wikidata.org/w/api.php", params={
        "action": "wbsearchentities",
        "search": event_title,
        "language": "en",
        "limit": "5",
        "format": "json",
    })
    if not data:
        return VerificationResult(
            category="death_toll", claim=claim, status=ERROR,
            api_source="Wikidata", details="API request failed",
        )

    for item in data.get("search", []):
        entity_id = item.get("id", "")

        claims_data = _session.get_json("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities",
            "ids": entity_id,
            "props": "claims",
            "format": "json",
        })
        if not claims_data:
            continue

        entity = claims_data.get("entities", {}).get(entity_id, {})
        claims = entity.get("claims", {})

        # P1120 = number of deaths
        deaths = _extract_wikidata_quantity(claims, "P1120")
        # P1590 = number of casualties
        casualties = _extract_wikidata_quantity(claims, "P1590")

        wd_value = deaths or casualties
        if wd_value is not None:
            yaml_low, yaml_high = yaml_range
            # Check overlap
            if yaml_low <= wd_value <= yaml_high:
                return VerificationResult(
                    category="death_toll", claim=claim, status=MATCHES,
                    api_source="Wikidata",
                    details=f"Wikidata {entity_id}: {wd_value:,} (YAML range: {yaml_low:,}-{yaml_high:,})",
                    confidence=0.9,
                )
            elif yaml_low * 0.5 <= wd_value <= yaml_high * 2.0:
                return VerificationResult(
                    category="death_toll", claim=claim, status=AMBIGUOUS,
                    api_source="Wikidata",
                    details=f"Wikidata {entity_id}: {wd_value:,} (YAML: {yaml_low:,}-{yaml_high:,}) -- within 2x range",
                    confidence=0.5,
                )
            else:
                return VerificationResult(
                    category="death_toll", claim=claim, status=DIFFERS,
                    api_source="Wikidata",
                    details=f"Wikidata {entity_id}: {wd_value:,} vs YAML: {yaml_low:,}-{yaml_high:,}",
                    confidence=0.3,
                )

    return VerificationResult(
        category="death_toll", claim=claim, status=NO_DATA,
        api_source="Wikidata",
        details="Event not found or no death toll data in Wikidata",
        confidence=0.0,
    )


def _parse_death_toll(text: str) -> tuple[int, int] | None:
    """Parse death toll string like '600,000-1,500,000' into (low, high) tuple."""
    text = text.replace(",", "").replace(".", "").strip()
    # Range: "600000-1500000"
    m = re.match(r'(\d+)\s*[-–—to]+\s*(\d+)', text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # Single number
    m = re.match(r'(\d+)', text)
    if m:
        val = int(m.group(1))
        return (val, val)
    # Descriptions like "approximately 1 million"
    m = re.search(r'(\d+(?:\.\d+)?)\s*million', text, re.IGNORECASE)
    if m:
        val = int(float(m.group(1)) * 1_000_000)
        return (val, val)
    return None


def _extract_wikidata_quantity(claims: dict, prop: str) -> int | None:
    """Extract numeric quantity from Wikidata claims."""
    for claim_val in claims.get(prop, []):
        amount = (
            claim_val.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("amount", "")
        )
        if amount:
            try:
                return int(float(amount.lstrip("+")))
            except (ValueError, TypeError):
                pass
    return None


# ---------------------------------------------------------------------------
# 5. Coordinate Verification (Nominatim)
# ---------------------------------------------------------------------------

def verify_coordinates(lat: float, lng: float, event_location: str) -> VerificationResult:
    """Reverse geocode coordinates and check if they match the event location."""
    claim = f'({lat}, {lng}) -> {event_location}'

    data = _session.get_json("https://nominatim.openstreetmap.org/reverse", params={
        "lat": str(lat),
        "lon": str(lng),
        "format": "json",
        "zoom": "5",
        "accept-language": "en",
    }, delay=1.5)  # Nominatim is strict: 1 req/s

    if not data:
        return VerificationResult(
            category="coordinates", claim=claim, status=ERROR,
            api_source="Nominatim", details="API request failed",
        )

    display_name = data.get("display_name", "")
    address = data.get("address", {})
    country = address.get("country", "")
    state = address.get("state", "")
    city = address.get("city", "") or address.get("town", "") or address.get("village", "")

    # Construct location parts for matching
    location_parts = [p.strip().lower() for p in [city, state, country, display_name] if p]
    event_parts = [p.strip().lower() for p in re.split(r'[,/]', event_location)]

    # Check for overlap
    matched = False
    for ep in event_parts:
        ep_norm = _normalize(ep)
        for lp in location_parts:
            lp_norm = _normalize(lp)
            if ep_norm in lp_norm or lp_norm in ep_norm:
                matched = True
                break
            # Token overlap
            if _token_overlap(ep_norm, lp_norm) > 0.3:
                matched = True
                break
        if matched:
            break

    resolved = f"{city}, {state}, {country}".strip(", ")
    if matched:
        return VerificationResult(
            category="coordinates", claim=claim, status=MATCHES,
            api_source="Nominatim",
            details=f"Resolved to: {resolved}",
            confidence=0.85,
        )
    else:
        return VerificationResult(
            category="coordinates", claim=claim, status=DIFFERS,
            api_source="Nominatim",
            details=f"Resolved to: {resolved} (expected: {event_location})",
            confidence=0.3,
        )


# ---------------------------------------------------------------------------
# 6. Primary Source Quote Spot-Check
# ---------------------------------------------------------------------------

def verify_primary_source(author: str, work: str, date: str | None) -> VerificationResult:
    """Verify that a primary source work and author exist."""
    claim = f'{author} -- "{work}" ({date or "?"})'
    results = []

    # Check work existence via Open Library
    clean_work = re.sub(r'\(.*?\)', '', work).strip()
    clean_author = re.sub(r'\(.*?\)', '', author).strip()
    # Skip lookup for descriptions rather than titles (dispatches, memoranda, speeches)
    is_document_ref = any(
        kw in work.lower()
        for kw in ["dispatch", "memorandum", "cable", "letter", "speech", "as recorded by",
                    "statement", "annual report", "testimony", "conversation"]
    )

    work_status = WORK_NOT_FOUND
    work_details = ""

    if not is_document_ref:
        ol_data = _session.get_json("https://openlibrary.org/search.json", params={
            "title": clean_work,
            "limit": "5",
        })
        if ol_data:
            for doc in ol_data.get("docs", [])[:5]:
                ol_title = doc.get("title", "")
                sim = _title_similarity(clean_work, ol_title)
                if sim >= 0.55:
                    work_status = WORK_EXISTS
                    work_details = f'Open Library: "{ol_title}"'
                    break

        # Try CrossRef if not found
        if work_status == WORK_NOT_FOUND:
            cr_data = _session.get_json("https://api.crossref.org/works", params={
                "query": clean_work,
                "rows": "3",
                "mailto": "void-news@proton.me",
            })
            if cr_data:
                for item in cr_data.get("message", {}).get("items", [])[:3]:
                    titles = item.get("title", [])
                    cr_title = titles[0] if titles else ""
                    if cr_title and _title_similarity(clean_work, cr_title) >= 0.55:
                        work_status = WORK_EXISTS
                        work_details = f'CrossRef: "{cr_title}"'
                        break
    else:
        work_status = SKIPPED
        work_details = "Document/speech reference (not a published work)"

    # Check author existence via Wikidata
    author_status = AUTHOR_NOT_FOUND
    author_details = ""

    wd_data = _session.get_json("https://www.wikidata.org/w/api.php", params={
        "action": "wbsearchentities",
        "search": clean_author,
        "language": "en",
        "limit": "3",
        "format": "json",
    })
    if wd_data:
        for item in wd_data.get("search", []):
            if _author_match(clean_author, item.get("label", "")):
                author_status = AUTHOR_EXISTS
                author_details = f'{item["id"]}: {item.get("description", "")}'
                break

    # Combined status
    if work_status == WORK_EXISTS and author_status == AUTHOR_EXISTS:
        status = VERIFIED
    elif work_status == SKIPPED and author_status == AUTHOR_EXISTS:
        status = VERIFIED
    elif work_status == WORK_EXISTS or author_status == AUTHOR_EXISTS:
        status = AMBIGUOUS
    else:
        status = NOT_FOUND

    details_parts = []
    if work_details:
        details_parts.append(f"Work: {work_status} ({work_details})")
    else:
        details_parts.append(f"Work: {work_status}")
    details_parts.append(f"Author: {author_status}" + (f" ({author_details})" if author_details else ""))

    return VerificationResult(
        category="primary_source",
        claim=claim,
        status=status,
        api_source="Open Library + Wikidata",
        details="; ".join(details_parts),
        confidence=0.8 if status == VERIFIED else 0.4 if status == AMBIGUOUS else 0.0,
    )


# ---------------------------------------------------------------------------
# YAML extraction
# ---------------------------------------------------------------------------

def _load_event_yaml(filepath: Path) -> dict:
    """Load and parse a YAML event file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_verifiable_claims(event_data: dict) -> dict:
    """Extract all verifiable claims from an event YAML.

    Returns a dict with keys: sources, key_figures, death_toll, coordinates, primary_sources.
    """
    claims = {
        "sources": [],         # (author, title, year, type)
        "key_figures": [],     # (name, role)
        "death_toll": None,    # str
        "coordinates": None,   # (lat, lng)
        "primary_sources": [], # (author, work, date)
        "event_title": event_data.get("title", ""),
        "event_year": _extract_year(str(event_data.get("date_sort", ""))),
        "country": event_data.get("country", ""),
    }

    # Sources from all perspectives
    for perspective in event_data.get("perspectives", []):
        for src in perspective.get("sources", []):
            author = src.get("author", "")
            title = src.get("title", "")
            year = src.get("year", "")
            src_type = src.get("type", "book")
            if author and title:
                claims["sources"].append((author, title, str(year) if year else None, src_type))

    # Deduplicate sources by (author, title)
    seen = set()
    deduped = []
    for s in claims["sources"]:
        key = (_normalize(s[0]), _normalize(s[1]))
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    claims["sources"] = deduped

    # Key figures
    for fig in event_data.get("key_figures", []):
        name = fig.get("name", "")
        role = fig.get("role", "")
        if name:
            claims["key_figures"].append((name, role))

    # Death toll
    claims["death_toll"] = event_data.get("death_toll")

    # Coordinates
    coords = event_data.get("coordinates")
    if coords and isinstance(coords, dict):
        lat = coords.get("lat")
        lng = coords.get("lng") or coords.get("lon")
        if lat is not None and lng is not None:
            claims["coordinates"] = (float(lat), float(lng))

    # Primary source excerpts
    for excerpt in event_data.get("primary_source_excerpts", []):
        author = excerpt.get("author", "")
        work = excerpt.get("work", "")
        date = excerpt.get("date", "")
        if author and work:
            claims["primary_sources"].append((author, work, str(date) if date else None))

    return claims


# ---------------------------------------------------------------------------
# Verification orchestrator
# ---------------------------------------------------------------------------

def verify_event(
    event_path: Path,
    quick: bool = False,
) -> dict:
    """
    Run all verification checks on a single event YAML file.

    Args:
        event_path: Path to the event YAML file.
        quick: If True, skip slow APIs (Nominatim, death toll Wikidata lookup).

    Returns a verification report dict.
    """
    event_data = _load_event_yaml(event_path)
    slug = event_data.get("slug", event_path.stem)
    title = event_data.get("title", slug)
    claims = extract_verifiable_claims(event_data)

    results: list[VerificationResult] = []

    # --- 1. Scholar/Source Verification ---
    sources = claims["sources"]
    print(f"\nSCHOLARS & SOURCES ({len(sources)} citations)")
    for author, src_title, year, src_type in sources:
        print(f'  Checking: {author} -- "{src_title}" ({year or "?"})...')
        if src_type in ("report", "document"):
            # For reports/documents, use primary source check
            r = verify_primary_source(author, src_title, year)
        else:
            r = verify_scholar_source(author, src_title, year)
        results.append(r)
        _print_status(r)

    # --- 2. Key Figure Verification ---
    figures = claims["key_figures"]
    print(f"\nKEY FIGURES ({len(figures)} people)")
    for name, role in figures:
        print(f"  Checking: {name}...")
        r = verify_key_figure(name, role, claims["event_year"])
        results.append(r)
        _print_status(r)

    # --- 3. Publication Verification (books from sources) ---
    books = [(a, t, y) for a, t, y, st in claims["sources"] if st == "book"]
    if books:
        print(f"\nPUBLICATION VERIFICATION ({len(books)} books)")
        for author, src_title, year in books:
            print(f'  Checking: {author} -- "{src_title}"...')
            r = verify_publication(author, src_title, year)
            results.append(r)
            _print_status(r)

    # --- 4. Death Toll ---
    if claims["death_toll"] and not quick:
        print(f"\nDEATH TOLL")
        print(f"  YAML: {claims['death_toll']}")
        r = verify_death_toll(title, claims["death_toll"])
        results.append(r)
        _print_status(r)
    elif claims["death_toll"] and quick:
        print(f"\nDEATH TOLL -- skipped (--quick)")

    # --- 5. Coordinate Verification ---
    if claims["coordinates"] and not quick:
        lat, lng = claims["coordinates"]
        country = claims["country"]
        print(f"\nCOORDINATES")
        print(f"  ({lat}, {lng}) -> checking against '{country}'...")
        r = verify_coordinates(lat, lng, country)
        results.append(r)
        _print_status(r)
    elif claims["coordinates"] and quick:
        print(f"\nCOORDINATES -- skipped (--quick)")

    # --- 6. Primary Source Quote Spot-Check ---
    primary = claims["primary_sources"]
    if primary and not quick:
        print(f"\nPRIMARY SOURCES ({len(primary)} quotes)")
        for author, work, date in primary:
            print(f'  Checking: {author} -- "{work}"...')
            r = verify_primary_source(author, work, date)
            results.append(r)
            _print_status(r)
    elif primary and quick:
        print(f"\nPRIMARY SOURCES -- skipped (--quick)")

    # --- Summary ---
    verified = sum(1 for r in results if r.status in (VERIFIED, MATCHES, WORK_EXISTS, AUTHOR_EXISTS))
    ambiguous = sum(1 for r in results if r.status in (AMBIGUOUS, YEAR_MISMATCH))
    not_found = sum(1 for r in results if r.status in (NOT_FOUND, WORK_NOT_FOUND, AUTHOR_NOT_FOUND))
    errors = sum(1 for r in results if r.status in (ERROR,))
    differs = sum(1 for r in results if r.status in (DIFFERS, DATE_MISMATCH))
    skipped = sum(1 for r in results if r.status in (SKIPPED,))
    no_data = sum(1 for r in results if r.status in (NO_DATA,))
    total = len(results)
    scorable = total - skipped - no_data - errors
    confidence = verified / scorable if scorable > 0 else 0.0

    print(f"\n{'=' * 55}")
    print(f"SUMMARY: {verified}/{scorable} verified, {ambiguous} ambiguous, {not_found} not found, {differs} differ, {errors} errors")
    print(f"CONFIDENCE: {confidence:.0%} ({verified} verified / {scorable} scorable)")

    report = {
        "slug": slug,
        "title": title,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "confidence": round(confidence, 3),
        "total_claims": total,
        "verified": verified,
        "ambiguous": ambiguous,
        "not_found": not_found,
        "differs": differs,
        "errors": errors,
        "skipped": skipped,
        "no_data": no_data,
        "details": [r.to_dict() for r in results],
    }

    return report


def _print_status(r: VerificationResult):
    """Print a single verification result line."""
    icons = {
        VERIFIED: "V", MATCHES: "V", WORK_EXISTS: "V", AUTHOR_EXISTS: "V",
        AMBIGUOUS: "?", YEAR_MISMATCH: "?",
        NOT_FOUND: "X", WORK_NOT_FOUND: "X", AUTHOR_NOT_FOUND: "X",
        DIFFERS: "!", DATE_MISMATCH: "!",
        ERROR: "E", SKIPPED: "-", NO_DATA: "-",
    }
    icon = icons.get(r.status, " ")
    print(f"    [{icon}] {r.status} ({r.api_source}) -- {r.details[:100]}")


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def save_report(report: dict) -> Path:
    """Save verification report to JSON file."""
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    slug = report["slug"]
    output_path = VERIFICATION_DIR / f"{slug}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="void --history content verifier -- cross-reference YAML claims "
                    "against free APIs to flag hallucinations",
    )
    parser.add_argument(
        "--event", type=str,
        help="Event slug to verify (e.g., armenian-genocide)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Verify all events in data/history/events/",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip slow APIs (Nominatim, death toll, primary sources)",
    )
    parser.add_argument(
        "--output", type=str, choices=["console", "json"], default="console",
        help="Output format (default: console; json saves to data/history/verification/)",
    )

    args = parser.parse_args()

    if not args.event and not args.all:
        parser.print_help()
        print("\nSpecify --event <slug> or --all")
        sys.exit(1)

    # Determine event files
    if args.event:
        event_path = EVENTS_DIR / f"{args.event}.yaml"
        if not event_path.exists():
            print(f"Event file not found: {event_path}")
            available = sorted(p.stem for p in EVENTS_DIR.glob("*.yaml"))
            if available:
                print(f"Available: {', '.join(available)}")
            sys.exit(1)
        event_paths = [event_path]
    else:
        event_paths = sorted(EVENTS_DIR.glob("*.yaml"))
        if not event_paths:
            print(f"No YAML files found in {EVENTS_DIR}")
            sys.exit(1)

    # Header
    print()
    print("void --history content verifier")
    print("=" * 55)
    print(f"  Events:  {len(event_paths)}")
    print(f"  Mode:    {'quick' if args.quick else 'full'}")
    print(f"  Output:  {args.output}")

    # Process
    reports = []
    for event_path in event_paths:
        slug = event_path.stem
        print(f"\n{'=' * 55}")
        print(f"VERIFYING: {slug}")
        print(f"{'=' * 55}")

        try:
            report = verify_event(event_path, quick=args.quick)
            reports.append(report)

            if args.output == "json":
                out_path = save_report(report)
                print(f"\n  Report saved: {out_path}")

        except Exception as e:
            print(f"\n  ERROR verifying {slug}: {e}")
            import traceback
            traceback.print_exc()

    # Final summary for --all
    if len(reports) > 1:
        print(f"\n{'=' * 55}")
        print("ALL EVENTS SUMMARY")
        print(f"{'=' * 55}")
        total_v = sum(r["verified"] for r in reports)
        total_c = sum(r["total_claims"] - r.get("skipped", 0) - r.get("no_data", 0) - r.get("errors", 0) for r in reports)
        total_nf = sum(r["not_found"] for r in reports)
        total_a = sum(r["ambiguous"] for r in reports)
        for r in reports:
            conf = r["confidence"]
            bar = "#" * int(conf * 20)
            print(f"  {r['slug']:<35s} {conf:>5.0%} [{bar:<20s}] ({r['verified']}/{r['total_claims']} claims)")
        overall = total_v / total_c if total_c > 0 else 0
        print(f"\n  Overall: {total_v}/{total_c} verified ({overall:.0%}), {total_a} ambiguous, {total_nf} not found")

    print()
    print("  Done. Review flagged items manually -- NOT_FOUND does not mean fabricated.")
    print("  Many legitimate historical works are not indexed in OpenAlex/CrossRef/Open Library.")


if __name__ == "__main__":
    main()
