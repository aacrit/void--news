"""
void --history source upgrade pipeline.

Closes the loop between the verifier (which flags NOT_FOUND/AMBIGUOUS claims)
and the enricher (which discovers sources from APIs). Reads verification reports,
queries CrossRef/OpenAlex/Open Library/Internet Archive/Wikidata to resolve
flagged items, and adds machine-verifiable identifiers (DOIs, ISBNs, OL IDs,
archive URLs, Wikidata QIDs) to ALL sources.

Outputs a human-readable YAML patch file for review. Optionally applies patches
to the event YAML (metadata fields only -- never touches narrative text).

Usage:
    python pipeline/history/upgrade_sources.py --event armenian-genocide
    python pipeline/history/upgrade_sources.py --all
    python pipeline/history/upgrade_sources.py --apply armenian-genocide
    python pipeline/history/upgrade_sources.py --event armenian-genocide --dry-run
"""

import argparse
import json
import logging
import re
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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
UPGRADES_DIR = _PROJECT_ROOT / "data" / "history" / "upgrades"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="  %(levelname)-5s %(message)s",
)
log = logging.getLogger("upgrade_sources")

# ---------------------------------------------------------------------------
# Rate-limited HTTP session (reuses pattern from verify_content.py)
# ---------------------------------------------------------------------------


class RateLimitedSession:
    """Shared HTTP session with per-domain rate limiting."""

    def __init__(self, delay: float = 1.0):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "void-news-history-upgrader/1.0 (source-upgrade; academic-research; +https://github.com/void-news)",
        })
        self._last_request: dict[str, float] = {}
        self._default_delay = delay

    def _rate_limit(self, domain: str, delay: float | None = None):
        d = delay if delay is not None else self._default_delay
        last = self._last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < d:
            time.sleep(d - elapsed)
        self._last_request[domain] = time.time()

    def get_json(self, url: str, params: dict = None, timeout: int = 20, delay: float | None = None) -> dict | None:
        """Rate-limited GET returning JSON, or None on failure."""
        domain = urlparse(url).netloc
        self._rate_limit(domain, delay)
        try:
            resp = self._session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            log.warning("  [timeout] %s", url)
            return None
        except requests.exceptions.HTTPError as e:
            log.warning("  [HTTP %s] %s", e.response.status_code, url)
            return None
        except Exception as e:
            log.warning("  [error] %s: %s", url, e)
            return None


_session = RateLimitedSession(delay=1.0)

# ---------------------------------------------------------------------------
# Fuzzy matching utilities (same as verify_content.py)
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _author_match(query_author: str, result_author: str) -> bool:
    qa = _normalize(query_author)
    ra = _normalize(result_author)
    if not qa or not ra:
        return False
    if qa in ra or ra in qa:
        return True
    q_parts = qa.split()
    r_parts = ra.split()
    if q_parts and r_parts:
        if q_parts[-1] == r_parts[-1]:
            return True
        for qp in q_parts:
            if len(qp) > 2 and qp in r_parts:
                return True
    return False


def _extract_year(year_str: str) -> int | None:
    if not year_str:
        return None
    m = re.search(r'(\d{4})', str(year_str))
    return int(m.group(1)) if m else None


def _clean_author(author: str) -> str:
    """Remove parenthetical notes and 'as told to' suffixes for API queries."""
    clean = re.sub(r'\(.*?\)', '', author).strip()
    clean = re.sub(r'\s+as told to\b.*', '', clean, flags=re.IGNORECASE).strip()
    return clean


# ---------------------------------------------------------------------------
# Resolution result types
# ---------------------------------------------------------------------------

@dataclass
class SourceResolution:
    """Resolution result for a single source citation."""
    original: dict  # {author, title, year}
    perspective: str = ""  # perspective viewpoint name
    source_index: int = 0  # index within that perspective's sources list
    doi: Optional[str] = None
    isbn: Optional[str] = None
    openlibrary_id: Optional[str] = None
    archive_url: Optional[str] = None
    crossref_verified: bool = False
    openalex_verified: bool = False
    exact_title: Optional[str] = None
    exact_year: Optional[int] = None
    exact_author: Optional[str] = None
    status: str = "UNRESOLVABLE"  # ENRICHED, PARTIALLY_ENRICHED, UNRESOLVABLE
    changes: list = field(default_factory=list)


@dataclass
class FigureResolution:
    """Resolution result for a key figure."""
    original: dict  # {name, role}
    figure_index: int = 0
    wikidata_qid: Optional[str] = None
    born: Optional[int] = None
    died: Optional[int] = None
    description: Optional[str] = None
    wikipedia_url: Optional[str] = None
    status: str = "UNRESOLVABLE"
    changes: list = field(default_factory=list)


@dataclass
class PrimarySourceResolution:
    """Resolution result for a primary source excerpt."""
    original: dict  # {author, work, date}
    excerpt_index: int = 0
    archive_url: Optional[str] = None
    openlibrary_id: Optional[str] = None
    doi: Optional[str] = None
    status: str = "UNRESOLVABLE"
    changes: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1: Ingest verification report
# ---------------------------------------------------------------------------

def load_verification_report(slug: str) -> dict | None:
    """Load the verification report JSON for an event."""
    report_path = VERIFICATION_DIR / f"{slug}.json"
    if not report_path.exists():
        return None
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_event_yaml(slug: str) -> dict | None:
    """Load the event YAML file."""
    yaml_path = EVENTS_DIR / f"{slug}.yaml"
    if not yaml_path.exists():
        return None
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Step 2: Source resolution via CrossRef, OpenAlex, Open Library, IA
# ---------------------------------------------------------------------------

def resolve_source_crossref(author: str, title: str, year: str | None) -> dict:
    """Query CrossRef for DOI and metadata."""
    clean = _clean_author(author)
    data = _session.get_json("https://api.crossref.org/works", params={
        "query.bibliographic": title,
        "query.author": clean,
        "rows": "5",
        "mailto": "void-news@proton.me",
    })
    if not data:
        return {}

    parsed_year = _extract_year(year) if year else None

    for item in data.get("message", {}).get("items", [])[:5]:
        titles = item.get("title", [])
        item_title = titles[0] if titles else ""
        if not item_title:
            continue

        sim = _title_similarity(title, item_title)
        if sim < 0.50:
            continue

        # Check author
        cr_authors = []
        for a in item.get("author", []):
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                cr_authors.append(name)
        author_found = any(_author_match(clean, ca) for ca in cr_authors)

        if sim >= 0.65 and author_found:
            doi = item.get("DOI", "")
            # Extract year
            date_parts = item.get("published-print", {}).get("date-parts", [[]])
            if not date_parts[0]:
                date_parts = item.get("published-online", {}).get("date-parts", [[]])
            cr_year = date_parts[0][0] if date_parts and date_parts[0] else None

            return {
                "doi": doi,
                "exact_title": item_title,
                "exact_year": cr_year,
                "exact_author": ", ".join(cr_authors[:3]) if cr_authors else None,
                "similarity": sim,
                "crossref_verified": True,
            }

    return {}


def resolve_source_openalex(author: str, title: str, year: str | None) -> dict:
    """Query OpenAlex for metadata and DOI."""
    params = {
        "search": title,
        "per_page": "5",
        "sort": "relevance_score:desc",
        "mailto": "void-news@proton.me",
    }
    parsed_year = _extract_year(year) if year else None
    if parsed_year:
        params["filter"] = f"publication_year:{parsed_year}"

    data = _session.get_json("https://api.openalex.org/works", params=params)
    if not data:
        return {}

    clean = _clean_author(author)

    for work in data.get("results", [])[:5]:
        work_title = work.get("title", "")
        if not work_title:
            continue

        sim = _title_similarity(title, work_title)
        if sim < 0.55:
            continue

        work_authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])
        ]
        author_found = any(_author_match(clean, wa) for wa in work_authors)

        if sim >= 0.55 and author_found:
            doi_raw = work.get("doi", "")
            doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""
            oa_id = work.get("id", "")
            pub_year = work.get("publication_year")

            return {
                "doi": doi,
                "openalex_id": oa_id,
                "exact_title": work_title,
                "exact_year": pub_year,
                "exact_author": ", ".join(work_authors[:3]) if work_authors else None,
                "similarity": sim,
                "openalex_verified": True,
            }

    # Retry without year filter
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
                if sim < 0.55:
                    continue
                work_authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in work.get("authorships", [])
                ]
                author_found = any(_author_match(clean, wa) for wa in work_authors)
                if sim >= 0.55 and author_found:
                    doi_raw = work.get("doi", "")
                    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""
                    return {
                        "doi": doi,
                        "exact_title": work_title,
                        "exact_year": work.get("publication_year"),
                        "openalex_verified": True,
                    }

    return {}


def resolve_source_openlibrary(author: str, title: str) -> dict:
    """Query Open Library for ISBNs and OL IDs."""
    clean = _clean_author(author)
    data = _session.get_json("https://openlibrary.org/search.json", params={
        "title": title,
        "author": clean,
        "limit": "5",
    })
    if not data:
        return {}

    for doc in data.get("docs", [])[:5]:
        ol_title = doc.get("title", "")
        sim = _title_similarity(title, ol_title)
        if sim < 0.50:
            continue

        ol_authors = doc.get("author_name", [])
        author_found = any(_author_match(clean, oa) for oa in ol_authors)

        if sim >= 0.50 and (author_found or sim >= 0.80):
            isbns = doc.get("isbn", [])
            isbn = isbns[0] if isbns else None
            # Prefer ISBN-13
            for i in isbns:
                if len(i.replace("-", "")) == 13:
                    isbn = i
                    break

            ol_key = doc.get("key", "")  # e.g. "/works/OL12345W"
            edition_key = doc.get("edition_key", [])
            ol_id = edition_key[0] if edition_key else ""
            # Also try cover_edition_key which is more specific
            cover_ed = doc.get("cover_edition_key", "")
            if cover_ed:
                ol_id = cover_ed

            result = {}
            if isbn:
                result["isbn"] = isbn
            if ol_id:
                result["openlibrary_id"] = ol_id
            if result:
                result["exact_title"] = ol_title
                return result

    # Fallback: title-only search
    data2 = _session.get_json("https://openlibrary.org/search.json", params={
        "title": title,
        "limit": "5",
    })
    if data2:
        for doc in data2.get("docs", [])[:5]:
            ol_title = doc.get("title", "")
            sim = _title_similarity(title, ol_title)
            if sim >= 0.75:
                isbns = doc.get("isbn", [])
                isbn = isbns[0] if isbns else None
                for i in isbns:
                    if len(i.replace("-", "")) == 13:
                        isbn = i
                        break
                edition_key = doc.get("edition_key", [])
                ol_id = edition_key[0] if edition_key else ""
                cover_ed = doc.get("cover_edition_key", "")
                if cover_ed:
                    ol_id = cover_ed

                result = {}
                if isbn:
                    result["isbn"] = isbn
                if ol_id:
                    result["openlibrary_id"] = ol_id
                if result:
                    result["exact_title"] = ol_title
                    return result

    return {}


def resolve_source_internet_archive(author: str, title: str) -> dict:
    """Query Internet Archive for full-text access URLs."""
    clean = _clean_author(author)
    # Simplify title for IA search (remove subtitles after colon for better recall)
    short_title = title.split(":")[0].strip() if ":" in title else title

    data = _session.get_json(
        "https://archive.org/advancedsearch.php",
        params={
            "q": f"title:({short_title}) AND creator:({clean})",
            "fl[]": "identifier,title,creator,date",
            "output": "json",
            "rows": "3",
        },
    )
    if not data:
        return {}

    docs = data.get("response", {}).get("docs", [])
    for doc in docs[:3]:
        ia_title = doc.get("title", "")
        if isinstance(ia_title, list):
            ia_title = ia_title[0] if ia_title else ""
        sim = _title_similarity(title, ia_title)
        if sim >= 0.45:
            identifier = doc.get("identifier", "")
            if identifier:
                return {
                    "archive_url": f"https://archive.org/details/{identifier}",
                }

    # Retry with just the title
    data2 = _session.get_json(
        "https://archive.org/advancedsearch.php",
        params={
            "q": f"title:({short_title})",
            "fl[]": "identifier,title,creator,date",
            "output": "json",
            "rows": "3",
        },
    )
    if data2:
        docs2 = data2.get("response", {}).get("docs", [])
        for doc in docs2[:3]:
            ia_title = doc.get("title", "")
            if isinstance(ia_title, list):
                ia_title = ia_title[0] if ia_title else ""
            sim = _title_similarity(title, ia_title)
            if sim >= 0.60:
                identifier = doc.get("identifier", "")
                if identifier:
                    return {
                        "archive_url": f"https://archive.org/details/{identifier}",
                    }

    return {}


def resolve_source(author: str, title: str, year: str | None,
                   perspective: str, source_index: int) -> SourceResolution:
    """Resolve a single source by querying all 4 APIs in order."""
    res = SourceResolution(
        original={"author": author, "title": title, "year": year or ""},
        perspective=perspective,
        source_index=source_index,
    )

    log.info("  Resolving: %s -- \"%s\" (%s)", author, title[:60], year or "?")

    # 1. CrossRef -> DOI
    cr = resolve_source_crossref(author, title, year)
    if cr:
        if cr.get("doi"):
            res.doi = cr["doi"]
            res.changes.append("added DOI")
        if cr.get("exact_title") and _title_similarity(title, cr["exact_title"]) < 0.95:
            res.exact_title = cr["exact_title"]
            if res.exact_title != title:
                res.changes.append("expanded title")
        res.crossref_verified = cr.get("crossref_verified", False)
        if cr.get("exact_year"):
            res.exact_year = cr["exact_year"]

    # 2. OpenAlex -> DOI (if CrossRef didn't get it) + OpenAlex ID
    oa = resolve_source_openalex(author, title, year)
    if oa:
        if not res.doi and oa.get("doi"):
            res.doi = oa["doi"]
            res.changes.append("added DOI")
        res.openalex_verified = oa.get("openalex_verified", False)
        if not res.exact_title and oa.get("exact_title"):
            if _title_similarity(title, oa["exact_title"]) < 0.95:
                res.exact_title = oa["exact_title"]
                if "expanded title" not in res.changes:
                    res.changes.append("expanded title")
        if not res.exact_year and oa.get("exact_year"):
            res.exact_year = oa["exact_year"]

    # 3. Open Library -> ISBN + OL ID
    ol = resolve_source_openlibrary(author, title)
    if ol:
        if ol.get("isbn"):
            res.isbn = ol["isbn"]
            res.changes.append("added ISBN")
        if ol.get("openlibrary_id"):
            res.openlibrary_id = ol["openlibrary_id"]
            res.changes.append("added Open Library ID")

    # 4. Internet Archive -> archive URL
    ia = resolve_source_internet_archive(author, title)
    if ia:
        if ia.get("archive_url"):
            res.archive_url = ia["archive_url"]
            res.changes.append("added archive URL")

    # Determine status
    if res.changes:
        has_id = bool(res.doi or res.isbn or res.openlibrary_id or res.archive_url)
        has_multiple = sum(bool(x) for x in [res.doi, res.isbn, res.openlibrary_id, res.archive_url]) >= 2
        if has_multiple:
            res.status = "ENRICHED"
        elif has_id:
            res.status = "PARTIALLY_ENRICHED"
        else:
            res.status = "PARTIALLY_ENRICHED"
    else:
        res.status = "UNRESOLVABLE"

    status_icon = {"ENRICHED": "++", "PARTIALLY_ENRICHED": "+", "UNRESOLVABLE": "--"}
    log.info("    [%s] %s | %s", status_icon.get(res.status, "?"), res.status,
             ", ".join(res.changes) if res.changes else "no identifiers found")

    return res


# ---------------------------------------------------------------------------
# Step 3: Key figure enrichment via Wikidata
# ---------------------------------------------------------------------------

def resolve_key_figure(name: str, role: str, figure_index: int) -> FigureResolution:
    """Resolve a key figure via Wikidata."""
    res = FigureResolution(
        original={"name": name, "role": role},
        figure_index=figure_index,
    )

    log.info("  Resolving figure: %s", name)

    # Search Wikidata
    search_names = [name]
    clean = re.sub(r'\b(Sr\.|Jr\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s*', '', name).strip()
    if clean != name:
        search_names.append(clean)

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
            break

    if not all_items:
        log.info("    [--] No Wikidata results")
        return res

    # Deduplicate
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

        # Name matching
        name_parts = set(_normalize(name).split())
        label_parts = set(_normalize(label).split())
        overlap = name_parts & label_parts
        significant_overlap = any(len(w) > 3 for w in overlap)

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

        # Fetch claims
        claims_data = _session.get_json("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities",
            "ids": entity_id,
            "props": "claims|sitelinks",
            "format": "json",
        })
        if not claims_data:
            continue

        entity = claims_data.get("entities", {}).get(entity_id, {})
        claims = entity.get("claims", {})
        sitelinks = entity.get("sitelinks", {})

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
            res.wikidata_qid = entity_id
            res.changes.append("added Wikidata QID")

            if desc:
                res.description = desc

            if birth_year:
                res.born = birth_year
                res.changes.append("added birth year")
            if death_year:
                res.died = death_year
                res.changes.append("added death year")

            # Wikipedia URL
            en_wiki = sitelinks.get("enwiki", {})
            if en_wiki.get("title"):
                wiki_title = en_wiki["title"].replace(" ", "_")
                res.wikipedia_url = f"https://en.wikipedia.org/wiki/{wiki_title}"
                res.changes.append("added Wikipedia URL")

            res.status = "ENRICHED" if len(res.changes) >= 3 else "PARTIALLY_ENRICHED"

            log.info("    [++] %s (%s, b.%s d.%s)", entity_id, desc[:50] if desc else "?",
                     birth_year or "?", death_year or "?")
            return res

    res.status = "UNRESOLVABLE"
    log.info("    [--] No matching person found")
    return res


def _extract_wikidata_year(claims: dict, prop: str) -> int | None:
    """Extract year from a Wikidata time claim."""
    for claim_val in claims.get(prop, []):
        time_val = (
            claim_val.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("time", "")
        )
        if time_val:
            m = re.search(r'[+-]?(\d{4})', time_val)
            if m:
                return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Step 2b: Primary source enrichment
# ---------------------------------------------------------------------------

def resolve_primary_source(author: str, work: str, date: str | None,
                           excerpt_index: int) -> PrimarySourceResolution:
    """Resolve a primary source excerpt via Open Library + Internet Archive."""
    res = PrimarySourceResolution(
        original={"author": author, "work": work, "date": date or ""},
        excerpt_index=excerpt_index,
    )

    # Skip dispatches/letters/speeches -- only resolve published works
    is_document_ref = any(
        kw in work.lower()
        for kw in ["dispatch", "memorandum", "cable", "letter", "speech", "as recorded by",
                    "statement", "annual report", "testimony", "conversation"]
    )
    if is_document_ref:
        log.info("  Skipping document reference: %s", work[:60])
        res.status = "UNRESOLVABLE"
        return res

    log.info("  Resolving primary source: %s -- \"%s\"", author, work[:60])

    # Open Library
    ol = resolve_source_openlibrary(author, work)
    if ol:
        if ol.get("openlibrary_id"):
            res.openlibrary_id = ol["openlibrary_id"]
            res.changes.append("added Open Library ID")
        if ol.get("isbn"):
            # Primary sources rarely have ISBNs, but include if found
            pass

    # Internet Archive
    ia = resolve_source_internet_archive(author, work)
    if ia:
        if ia.get("archive_url"):
            res.archive_url = ia["archive_url"]
            res.changes.append("added archive URL")

    # CrossRef for DOI
    cr = resolve_source_crossref(author, work, date)
    if cr:
        if cr.get("doi"):
            res.doi = cr["doi"]
            res.changes.append("added DOI")

    if res.changes:
        res.status = "ENRICHED" if len(res.changes) >= 2 else "PARTIALLY_ENRICHED"
    else:
        res.status = "UNRESOLVABLE"

    status_icon = {"ENRICHED": "++", "PARTIALLY_ENRICHED": "+", "UNRESOLVABLE": "--"}
    log.info("    [%s] %s", status_icon.get(res.status, "?"),
             ", ".join(res.changes) if res.changes else "no identifiers found")

    return res


# ---------------------------------------------------------------------------
# Step 4: Generate YAML patch
# ---------------------------------------------------------------------------

def generate_patch(slug: str, event_data: dict,
                   source_resolutions: list[SourceResolution],
                   figure_resolutions: list[FigureResolution],
                   primary_resolutions: list[PrimarySourceResolution]) -> dict:
    """Generate a structured YAML patch dict."""

    source_patches = []
    for sr in source_resolutions:
        if not sr.changes:
            continue

        before = dict(sr.original)
        after = dict(sr.original)

        if sr.exact_title and sr.exact_title != sr.original.get("title"):
            after["title"] = sr.exact_title
        if sr.doi:
            after["doi"] = sr.doi
        if sr.isbn:
            after["isbn"] = sr.isbn
        if sr.openlibrary_id:
            after["openlibrary"] = sr.openlibrary_id
        if sr.archive_url:
            after["archive_url"] = sr.archive_url

        source_patches.append({
            "perspective": sr.perspective,
            "index": sr.source_index,
            "before": before,
            "after": after,
            "changes": sr.changes,
        })

    figure_patches = []
    for fr in figure_resolutions:
        if not fr.changes:
            continue

        before = dict(fr.original)
        after = dict(fr.original)

        if fr.wikidata_qid:
            after["wikidata"] = fr.wikidata_qid
        if fr.born:
            after["born"] = fr.born
        if fr.died:
            after["died"] = fr.died
        if fr.wikipedia_url:
            after["wikipedia"] = fr.wikipedia_url

        figure_patches.append({
            "index": fr.figure_index,
            "before": before,
            "after": after,
            "changes": fr.changes,
        })

    primary_patches = []
    for pr in primary_resolutions:
        if not pr.changes:
            continue

        before = dict(pr.original)
        after = dict(pr.original)

        if pr.archive_url:
            after["archive_url"] = pr.archive_url
        if pr.openlibrary_id:
            after["openlibrary"] = pr.openlibrary_id
        if pr.doi:
            after["doi"] = pr.doi

        primary_patches.append({
            "index": pr.excerpt_index,
            "before": before,
            "after": after,
            "changes": pr.changes,
        })

    # Summary stats
    total_sources = len(source_resolutions)
    enriched = sum(1 for s in source_resolutions if s.status == "ENRICHED")
    partially = sum(1 for s in source_resolutions if s.status == "PARTIALLY_ENRICHED")
    unresolvable = sum(1 for s in source_resolutions if s.status == "UNRESOLVABLE")
    doi_added = sum(1 for s in source_resolutions if s.doi)
    isbn_added = sum(1 for s in source_resolutions if s.isbn)
    archive_added = sum(1 for s in source_resolutions if s.archive_url)
    archive_added += sum(1 for p in primary_resolutions if p.archive_url)
    wikidata_added = sum(1 for f in figure_resolutions if f.wikidata_qid)

    patch = {
        "event": slug,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "upgrades": {},
        "summary": {
            "total_sources": total_sources,
            "enriched": enriched,
            "partially_enriched": partially,
            "unresolvable": unresolvable,
            "doi_added": doi_added,
            "isbn_added": isbn_added,
            "archive_url_added": archive_added,
            "wikidata_added": wikidata_added,
        },
    }

    if source_patches:
        patch["upgrades"]["sources"] = source_patches
    if figure_patches:
        patch["upgrades"]["key_figures"] = figure_patches
    if primary_patches:
        patch["upgrades"]["primary_sources"] = primary_patches

    return patch


def save_patch(patch: dict) -> Path:
    """Save the patch YAML to data/history/upgrades/."""
    UPGRADES_DIR.mkdir(parents=True, exist_ok=True)
    slug = patch["event"]
    output_path = UPGRADES_DIR / f"{slug}.patch.yaml"

    # Write with a header comment
    header = (
        f"# Source Upgrade Patch for: {slug}\n"
        f"# Generated: {patch['generated']}\n"
        f"# Review each change before applying.\n"
        f"# Run: python3 pipeline/history/upgrade_sources.py --apply {slug}\n\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(patch, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    return output_path


# ---------------------------------------------------------------------------
# Step 5: Apply patches
# ---------------------------------------------------------------------------

def apply_patch(slug: str, dry_run: bool = False) -> bool:
    """Apply a patch YAML to the event YAML file.

    Only adds metadata fields (doi, isbn, archive_url, openlibrary, wikidata,
    born, died, wikipedia). Never modifies narrative text, perspectives, or
    editorial content.

    Returns True if changes were applied.
    """
    patch_path = UPGRADES_DIR / f"{slug}.patch.yaml"
    if not patch_path.exists():
        log.error("No patch file found: %s", patch_path)
        return False

    yaml_path = EVENTS_DIR / f"{slug}.yaml"
    if not yaml_path.exists():
        log.error("Event YAML not found: %s", yaml_path)
        return False

    with open(patch_path, "r", encoding="utf-8") as f:
        # Skip comment lines at top
        content = f.read()
    patch = yaml.safe_load(content)

    with open(yaml_path, "r", encoding="utf-8") as f:
        event_text = f.read()
    event_data = yaml.safe_load(event_text)

    upgrades = patch.get("upgrades", {})
    changes_made = 0

    # Apply source upgrades
    for src_patch in upgrades.get("sources", []):
        perspective_name = src_patch.get("perspective", "")
        src_index = src_patch.get("index", 0)
        after = src_patch.get("after", {})

        # Find the perspective
        for perspective in event_data.get("perspectives", []):
            if perspective.get("viewpoint") == perspective_name:
                sources = perspective.get("sources", [])
                if src_index < len(sources):
                    src = sources[src_index]
                    applied = []

                    # Only add metadata fields -- SAFE fields list
                    for field_name in ("doi", "isbn", "openlibrary", "archive_url"):
                        if after.get(field_name) and field_name not in src:
                            if not dry_run:
                                src[field_name] = after[field_name]
                            applied.append(field_name)

                    # Expand title if the API returned a more precise version
                    if after.get("title") and after["title"] != src.get("title"):
                        api_title = after["title"]
                        current_title = src.get("title", "")
                        # Only expand if the API title contains the original
                        if _normalize(current_title) in _normalize(api_title):
                            if not dry_run:
                                src["title"] = api_title
                            applied.append("title (expanded)")

                    if applied:
                        changes_made += len(applied)
                        action = "Would apply" if dry_run else "Applied"
                        log.info("  %s to %s[%d]: %s", action, perspective_name, src_index, ", ".join(applied))
                break

    # Apply key figure upgrades
    for fig_patch in upgrades.get("key_figures", []):
        fig_index = fig_patch.get("index", 0)
        after = fig_patch.get("after", {})

        figures = event_data.get("key_figures", [])
        if fig_index < len(figures):
            fig = figures[fig_index]
            applied = []

            for field_name in ("wikidata", "born", "died", "wikipedia"):
                if after.get(field_name) and field_name not in fig:
                    if not dry_run:
                        fig[field_name] = after[field_name]
                    applied.append(field_name)

            if applied:
                changes_made += len(applied)
                action = "Would apply" if dry_run else "Applied"
                log.info("  %s to key_figure[%d] (%s): %s", action, fig_index, fig.get("name", "?"), ", ".join(applied))

    # Apply primary source upgrades
    for ps_patch in upgrades.get("primary_sources", []):
        ps_index = ps_patch.get("index", 0)
        after = ps_patch.get("after", {})

        excerpts = event_data.get("primary_source_excerpts", [])
        if ps_index < len(excerpts):
            exc = excerpts[ps_index]
            applied = []

            for field_name in ("archive_url", "openlibrary", "doi"):
                if after.get(field_name) and field_name not in exc:
                    if not dry_run:
                        exc[field_name] = after[field_name]
                    applied.append(field_name)

            if applied:
                changes_made += len(applied)
                action = "Would apply" if dry_run else "Applied"
                log.info("  %s to primary_source[%d] (%s): %s", action, ps_index, exc.get("work", "?")[:40], ", ".join(applied))

    if changes_made > 0 and not dry_run:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(event_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)
        log.info("  Wrote %d changes to %s", changes_made, yaml_path)
    elif dry_run:
        log.info("  [DRY RUN] %d changes would be applied", changes_made)
    else:
        log.info("  No changes to apply")

    return changes_made > 0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def upgrade_event(slug: str, dry_run: bool = False) -> dict | None:
    """Run the full upgrade pipeline for one event.

    1. Load verification report (run verifier if missing)
    2. Resolve all sources via 4 APIs
    3. Resolve key figures via Wikidata
    4. Resolve primary sources
    5. Generate and save YAML patch
    """
    # Load event YAML
    event_data = load_event_yaml(slug)
    if not event_data:
        log.error("Event YAML not found: %s", slug)
        return None

    title = event_data.get("title", slug)
    log.info("Upgrading sources: %s (%s)", title, slug)

    # Load verification report (informational -- we resolve ALL sources regardless)
    report = load_verification_report(slug)
    if report:
        log.info("  Verification report: %d verified, %d ambiguous, %d not found",
                 report.get("verified", 0), report.get("ambiguous", 0), report.get("not_found", 0))
    else:
        log.info("  No verification report found -- will resolve all sources from scratch")

    # Collect all unique sources across perspectives
    source_resolutions: list[SourceResolution] = []
    seen_sources: set[tuple[str, str]] = set()

    for perspective in event_data.get("perspectives", []):
        viewpoint = perspective.get("viewpoint", "unknown")
        for i, src in enumerate(perspective.get("sources", [])):
            author = src.get("author", "")
            src_title = src.get("title", "")
            year = str(src.get("year", "")) if src.get("year") else None

            if not author or not src_title:
                continue

            # Deduplicate across perspectives
            key = (_normalize(author), _normalize(src_title))
            if key in seen_sources:
                continue
            seen_sources.add(key)

            sr = resolve_source(author, src_title, year, viewpoint, i)
            source_resolutions.append(sr)

    # Key figures
    figure_resolutions: list[FigureResolution] = []
    for i, fig in enumerate(event_data.get("key_figures", [])):
        name = fig.get("name", "")
        role = fig.get("role", "")
        if name:
            fr = resolve_key_figure(name, role, i)
            figure_resolutions.append(fr)

    # Primary source excerpts
    primary_resolutions: list[PrimarySourceResolution] = []
    for i, excerpt in enumerate(event_data.get("primary_source_excerpts", [])):
        author = excerpt.get("author", "")
        work = excerpt.get("work", "")
        date = str(excerpt.get("date", "")) if excerpt.get("date") else None
        if author and work:
            pr = resolve_primary_source(author, work, date, i)
            primary_resolutions.append(pr)

    # Generate patch
    patch = generate_patch(slug, event_data, source_resolutions, figure_resolutions, primary_resolutions)

    if not dry_run:
        output_path = save_patch(patch)
        log.info("  Patch saved: %s", output_path)
    else:
        log.info("  [DRY RUN] Patch generated (not saved)")

    return patch


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_patch_summary(patch: dict):
    """Print a human-readable summary of a patch."""
    slug = patch.get("event", "?")
    summary = patch.get("summary", {})
    upgrades = patch.get("upgrades", {})

    print()
    print(f"  Source Upgrade Patch: {slug}")
    print(f"  {'=' * 50}")
    print(f"  Total sources:      {summary.get('total_sources', 0)}")
    print(f"  Enriched:           {summary.get('enriched', 0)}")
    print(f"  Partially enriched: {summary.get('partially_enriched', 0)}")
    print(f"  Unresolvable:       {summary.get('unresolvable', 0)}")
    print(f"  DOIs added:         {summary.get('doi_added', 0)}")
    print(f"  ISBNs added:        {summary.get('isbn_added', 0)}")
    print(f"  Archive URLs added: {summary.get('archive_url_added', 0)}")
    print(f"  Wikidata QIDs:      {summary.get('wikidata_added', 0)}")

    # Show source changes
    for src in upgrades.get("sources", []):
        print(f"\n    [{src.get('perspective', '?')}] source #{src.get('index', 0)}")
        before = src.get("before", {})
        after = src.get("after", {})
        print(f"      Before: {before.get('author', '?')} -- \"{before.get('title', '?')}\"")
        changes = src.get("changes", [])
        for c in changes:
            if c == "added DOI":
                print(f"      + DOI: {after.get('doi', '?')}")
            elif c == "added ISBN":
                print(f"      + ISBN: {after.get('isbn', '?')}")
            elif c == "added Open Library ID":
                print(f"      + Open Library: {after.get('openlibrary', '?')}")
            elif c == "added archive URL":
                print(f"      + Archive: {after.get('archive_url', '?')}")
            elif c == "expanded title":
                print(f"      ~ Title: \"{after.get('title', '?')}\"")
            else:
                print(f"      + {c}")

    # Show figure changes
    for fig in upgrades.get("key_figures", []):
        before = fig.get("before", {})
        after = fig.get("after", {})
        print(f"\n    key_figure #{fig.get('index', 0)}: {before.get('name', '?')}")
        if after.get("wikidata"):
            print(f"      + Wikidata: {after['wikidata']}")
        if after.get("born"):
            print(f"      + Born: {after['born']}")
        if after.get("died"):
            print(f"      + Died: {after['died']}")
        if after.get("wikipedia"):
            print(f"      + Wikipedia: {after['wikipedia']}")

    # Show primary source changes
    for ps in upgrades.get("primary_sources", []):
        before = ps.get("before", {})
        after = ps.get("after", {})
        print(f"\n    primary_source #{ps.get('index', 0)}: \"{before.get('work', '?')[:50]}\"")
        if after.get("archive_url"):
            print(f"      + Archive: {after['archive_url']}")
        if after.get("openlibrary"):
            print(f"      + Open Library: {after['openlibrary']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="void --history source upgrade pipeline -- resolve flagged sources, "
                    "add DOIs/ISBNs/archive URLs, generate YAML patches",
    )
    parser.add_argument(
        "--event", type=str,
        help="Event slug to upgrade (e.g., armenian-genocide)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Upgrade all events in data/history/events/",
    )
    parser.add_argument(
        "--apply", type=str, metavar="SLUG",
        help="Apply a previously generated patch to the event YAML",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing files",
    )

    args = parser.parse_args()

    # --apply mode
    if args.apply:
        print()
        print("void --history source upgrade -- APPLY MODE")
        print("=" * 55)
        print(f"  Event: {args.apply}")
        print(f"  Mode:  {'dry run' if args.dry_run else 'LIVE -- will modify YAML'}")
        print()

        success = apply_patch(args.apply, dry_run=args.dry_run)
        if success and not args.dry_run:
            print()
            print("  Patch applied. Review the changes in the YAML file.")
        elif args.dry_run:
            print()
            print("  Dry run complete. No files modified.")
        else:
            print()
            print("  No changes to apply.")
        return

    # Validate args
    if not args.event and not args.all:
        parser.print_help()
        print("\nSpecify --event <slug>, --all, or --apply <slug>")
        sys.exit(1)

    # Determine event files
    if args.event:
        yaml_path = EVENTS_DIR / f"{args.event}.yaml"
        if not yaml_path.exists():
            log.error("Event file not found: %s", yaml_path)
            available = sorted(p.stem for p in EVENTS_DIR.glob("*.yaml"))
            if available:
                log.info("Available events: %s", ", ".join(available))
            sys.exit(1)
        slugs = [args.event]
    else:
        slugs = sorted(p.stem for p in EVENTS_DIR.glob("*.yaml"))
        if not slugs:
            log.error("No YAML files found in %s", EVENTS_DIR)
            sys.exit(1)

    # Header
    print()
    print("void --history source upgrade pipeline")
    print("=" * 55)
    print(f"  Events:   {len(slugs)}")
    print(f"  Mode:     {'dry run' if args.dry_run else 'generate patches'}")
    print(f"  Output:   {UPGRADES_DIR}")
    print()

    # Process
    all_patches = []
    for slug in slugs:
        try:
            patch = upgrade_event(slug, dry_run=args.dry_run)
            if patch:
                all_patches.append(patch)
                print_patch_summary(patch)
        except Exception as e:
            log.error("Failed to upgrade %s: %s", slug, e)
            import traceback
            traceback.print_exc()

    # Final summary
    if all_patches:
        total_enriched = sum(p.get("summary", {}).get("enriched", 0) for p in all_patches)
        total_partial = sum(p.get("summary", {}).get("partially_enriched", 0) for p in all_patches)
        total_unresolvable = sum(p.get("summary", {}).get("unresolvable", 0) for p in all_patches)
        total_doi = sum(p.get("summary", {}).get("doi_added", 0) for p in all_patches)
        total_isbn = sum(p.get("summary", {}).get("isbn_added", 0) for p in all_patches)

        print(f"\n{'=' * 55}")
        print("UPGRADE SUMMARY")
        print(f"  Events processed: {len(all_patches)}")
        print(f"  Enriched:         {total_enriched}")
        print(f"  Partial:          {total_partial}")
        print(f"  Unresolvable:     {total_unresolvable}")
        print(f"  DOIs added:       {total_doi}")
        print(f"  ISBNs added:      {total_isbn}")

    print()
    if args.dry_run:
        print("  Dry run complete. No files written.")
    else:
        print(f"  Patches saved to {UPGRADES_DIR}/")
        print("  Review patches, then apply with: python3 pipeline/history/upgrade_sources.py --apply <slug>")


if __name__ == "__main__":
    main()
