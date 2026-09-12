# IP & Legal Compliance Audit -- void --news

Last updated: 2026-04-28 (rev 1)

Date: 2026-03-18
Auditor: Automated compliance review
Scope: Content aggregation legality, competitor IP differentiation, trademark, open source licenses, data privacy

---

## Risk Summary

| Category                     | Risk Level | Notes                                                                 |
|------------------------------|------------|-----------------------------------------------------------------------|
| Content Aggregation          | **MEDIUM** | Full-text storage is the primary concern; RSS headline use is low risk |
| Competitor IP Differentiation| **LOW**    | Approach is fundamentally different from all competitors               |
| Trademark                    | **LOW**    | "void --news" does not conflict with known trademarks                 |
| Open Source Licenses         | **LOW**    | All dependencies are permissively licensed (MIT/BSD/Apache 2.0)       |
| Data Privacy                 | **LOW**    | No user accounts, no PII collection, minimal localStorage use         |

**Overall Risk: LOW-MEDIUM** -- The only area requiring attention is the full-text article storage practice.

---

## 1. Content Aggregation

### 1.1 RSS Feed Usage Rights

**Finding: LOW RISK for headlines/summaries; MEDIUM RISK for full-text scraping**

The project fetches articles via RSS feeds using `pipeline/fetchers/rss_fetcher.py`. RSS feeds are published by outlets specifically for syndication, and there is a widely recognized implied license to aggregate headlines and summaries from RSS content. Key legal references:

- The Mondaq/FKKS analysis of implied copyright licenses establishes that publishing an RSS feed creates an implied non-exclusive license for aggregation of headlines and links.
- However, courts have rejected the argument that simply making content available via RSS without blocking aggregators automatically grants unlimited re-use rights (see *Meltwater/AP* litigation).

The RSS fetcher properly:
- Identifies itself with a descriptive User-Agent: `VoidNews/1.0 (+https://github.com/aacrit/void--news)`
- Truncates summaries to 1,000 characters maximum (`rss_fetcher.py` line 72)
- Only extracts: title, URL, summary, author, published date, and source ID

**This is compliant.** Fetching titles, summaries (truncated), and links from publicly offered RSS feeds is well within accepted aggregation practice and fair use norms.

### 1.2 Full-Text Scraping -- Primary Concern

**Finding: MEDIUM RISK**

The `pipeline/fetchers/web_scraper.py` scrapes full article text from source websites and stores it in the `articles.full_text` column in Supabase. This is the primary legal risk area.

**What the scraper does:**
- Checks `robots.txt` before scraping (lines 22-53) -- **GOOD**
- Uses a polite, identifying User-Agent (line 15) -- **GOOD**
- Extracts full article body text from `<article>`, `<main>`, or content-class elements (lines 56-121)
- Returns `full_text`, `word_count`, and `image_url`

**What `main.py` does with the full text:**
- Stores `full_text` in Supabase `articles` table (line 189) -- **CONCERN**
- Uses `full_text` for NLP bias analysis (passed to all 5 analyzers)
- Uses first 200 words of `full_text` for TF-IDF clustering (`story_cluster.py` line 39)

**Legal analysis:**

The *AP v. Meltwater* (2013) case is the most relevant precedent. The court ruled that reproducing and distributing substantial portions of copyrighted news articles exceeds fair use, even when done by automated systems. Key factors:

1. **Purpose and character**: Our use is partly transformative (NLP analysis producing bias scores is a new creative work derived from the text), but we also store and potentially display the full text.
2. **Amount used**: We store the entire article text -- this weighs against fair use.
3. **Market effect**: If full text is displayed to users, they have no reason to visit the original source, which harms the original publisher's market.

**Mitigating factors:**
- The bias analysis itself is clearly transformative -- converting article text into numerical scores is a fundamentally different use.
- The clustering engine only uses the first 200 words.
- The frontend links back to original sources.

### 1.3 robots.txt Compliance

**Finding: COMPLIANT with one caveat**

The `_check_robots_txt()` function in `web_scraper.py`:
- Fetches and parses `robots.txt` for each domain (cached per domain)
- Checks `can_fetch()` for the VoidNews user agent before scraping
- Respects disallow rules

**Caveat:** If `robots.txt` cannot be fetched (network error, 404, etc.), the scraper assumes crawling is allowed (line 45-46). While this is the behavior of most well-known crawlers (including Googlebot), a more conservative approach would be to assume disallowed on fetch failure.

### 1.4 AP/Reuters Specific Concerns

**Finding: MEDIUM RISK**

The `sources.json` includes both AP and Reuters:
- AP News RSS via RSSHub proxy: `https://rsshub.app/apnews/topics/apf-topnews`
- Reuters RSS: `https://www.reutersagency.com/feed/?best-topics=political-general`

Wire services have strict content licensing terms. The AP, in particular, has aggressively enforced its copyright (see *AP v. Meltwater*).

**Key considerations:**
- Using RSSHub as an intermediary to access AP feeds does not change the copyright status of the underlying content. The AP content is still copyrighted by the AP.
- Fetching headlines and summaries from their RSS feeds for linking purposes is likely acceptable.
- Scraping and storing full article text from AP/Reuters articles carries elevated risk compared to other sources due to their history of enforcement.

### 1.5 Recommendations for Content Aggregation

1. **HIGH PRIORITY**: Do not store `full_text` permanently after analysis is complete. Process the text through the bias engine and clustering, then discard or truncate to a short excerpt (2-3 sentences). Store bias scores, not source text.
2. **HIGH PRIORITY**: Never display full article text to end users on the frontend. Always link to the original source.
3. **MEDIUM PRIORITY**: Consider adding a `crawl-delay` parameter check from `robots.txt` to be a more respectful crawler.
4. **LOW PRIORITY**: On `robots.txt` fetch failure, consider defaulting to disallowed rather than allowed.
5. **LOW PRIORITY**: Add a mechanism for publishers to request exclusion (a contact email or web form).

---

## 2. Competitor IP Differentiation

### 2.1 Ground News

**Risk: LOW**

| Aspect | Ground News | void --news | Differentiation |
|--------|-------------|-------------|-----------------|
| Bias rating method | Per-outlet labels sourced from third parties (AllSides, Ad Fontes, MBFC) | Per-article NLP analysis using custom rule-based heuristics | Fundamentally different methodology |
| "Blind Spot" feature | Shows stories covered only by left or right outlets | No equivalent feature | No overlap |
| Source ownership transparency | Shows who owns each outlet | Not a feature | No overlap |
| Business model | Freemium subscription | Free, open source | Different model |
| Analysis axes | Single left/center/right label per outlet | 5-axis per-article scoring (political lean, sensationalism, opinion/fact, factual rigor, framing) | Much more granular |

No publicly found patents from Ground News. Their "Blind Spot" feature is a branded editorial product, not a patented algorithm. Our project does not replicate this feature.

### 2.2 AllSides

**Risk: LOW-MEDIUM -- requires awareness**

AllSides claims a patent on their media bias rating methodology. Their approach uses:
- Blind Bias Surveys of Americans
- Editorial Reviews by a multipartisan panel
- Third-party data from universities

**Our approach is fundamentally different:**
- We use automated, rule-based NLP heuristics (keyword lexicons, TextBlob sentiment, spaCy NER, TF-IDF)
- We rate individual articles, not outlets
- We produce 5 numerical scores, not a single left/center/right label
- We use no surveys, no editorial panels, no third-party bias ratings
- Our entire methodology is open source and algorithmically reproducible

The AllSides patent likely covers their specific survey-based methodology. Algorithmic text analysis for political lean detection is a well-established NLP technique in academic literature that predates AllSides. Our implementation uses standard, published NLP approaches (keyword matching, sentiment analysis, TF-IDF) that are not covered by their patent.

**Recommendation:** Do not use AllSides' proprietary bias ratings as an input. Do not reference their specific rating scale or labels. Our current implementation does neither.

### 2.3 Ad Fontes Media

**Risk: LOW**

Ad Fontes Media has:
- Registered copyright on the "Media Bias Chart" visual representation
- Registered trademark on "MEDIA BIAS CHART"
- Pending patent applications for chart generation methods and the "Content Analysis Rating Tool"

**Our project does not:**
- Use or reproduce the Media Bias Chart
- Use the term "Media Bias Chart"
- Use Ad Fontes' visual layout, axes, or methodology
- Reference their rating data

Our 5-axis bias scoring system (0-100 per axis) is structurally different from Ad Fontes' 2-axis chart (reliability vs. political bias). No infringement risk.

### 2.4 NewsGuard

**Risk: LOW**

NewsGuard uses human journalists to rate 35,000+ sources on 9 apolitical credibility criteria, producing a 0-100 "Nutrition Label" score per outlet.

**Our approach differs because:**
- We perform automated analysis, not human editorial review
- We rate individual articles, not outlets
- We measure different dimensions (political lean, sensationalism, opinion/fact, factual rigor, framing)
- We do not use a "Nutrition Label" branding or visual format
- Our source curation is separate from our bias scoring -- we curate for credibility independently

No known patents from NewsGuard were found in searches. No infringement risk.

### 2.5 Google News

**Risk: LOW**

Google News aggregates and clusters news stories. Story clustering using TF-IDF and cosine similarity is a general, well-published NLP technique from academic literature (e.g., the TDT -- Topic Detection and Tracking -- research program dating to the 1990s). These methods are not patentable as novel inventions. Our `story_cluster.py` uses standard scikit-learn `TfidfVectorizer` and `AgglomerativeClustering` -- textbook implementations.

---

## 3. Trademark Analysis

### 3.1 "void --news"

**Risk: LOW**

A search for "void news" trademarks found:
- "THE VOID" -- registered by Hyper Reality Partners LLC (registration #4918987) for entertainment/VR experiences. Different class, different industry.
- "VOID MAGAZINE" -- registered by Void Media LLC for a magazine publication. Different name and format.

No trademark registration was found for "void news" or "void --news" in the news aggregation, technology, or media services classes. The unusual formatting with double dashes (`--`) further distinguishes the name.

**Recommendation:** Before commercial launch, conduct a formal trademark search through the USPTO TESS database and consider filing a trademark application for "void --news" in Class 38 (telecommunications/information services) and/or Class 42 (computer services).

### 3.2 "Press & Precision"

**Risk: LOW**

No trademark was found for "Press & Precision" as a design system name. Trademarks exist for "Trademark Press" (printing company) and "Precision Trademarks" (trademark services company), but neither covers design systems or software.

This is an internal design system name, not a consumer-facing brand. Trademark risk is negligible for internal/developer-facing nomenclature.

### 3.3 "Bias Stamp"

**Risk: LOW**

No trademark was found for "Bias Stamp" in any class. The component (`BiasStamp.tsx`) is a UI element name, not a consumer-facing brand name. No trademark concern.

---

## 4. Open Source License Audit

### 4.1 Python Pipeline Dependencies

| Package | License | Type | Commercial Use | Viral/Copyleft | Status |
|---------|---------|------|---------------|----------------|--------|
| feedparser >= 6.0 | BSD-2-Clause | Permissive | Allowed | No | CLEAR |
| beautifulsoup4 >= 4.12 | MIT | Permissive | Allowed | No | CLEAR |
| requests >= 2.31 | Apache 2.0 | Permissive | Allowed | No | CLEAR |
| supabase >= 2.0 | MIT | Permissive | Allowed | No | CLEAR |
| python-dotenv >= 1.0 | BSD-3-Clause | Permissive | Allowed | No | CLEAR |
| spacy >= 3.7 | MIT | Permissive | Allowed | No | CLEAR |
| textblob >= 0.18 | MIT | Permissive | Allowed | No | CLEAR |
| nltk >= 3.8 | Apache 2.0 | Permissive | Allowed | No | CLEAR |
| scikit-learn >= 1.3 | BSD-3-Clause | Permissive | Allowed | No | CLEAR |
| numpy >= 1.24 | BSD-3-Clause | Permissive | Allowed | No | CLEAR |

**Note on NLTK:** NLTK source code is Apache 2.0, but NLTK documentation is distributed under Creative Commons Attribution-Noncommercial-No Derivative Works 3.0. This only restricts redistribution of their documentation, not use of the library itself.

**Note on spaCy models:** The `en_core_web_sm` model used by the pipeline is distributed under the MIT license by Explosion (spaCy's maintainers). CLEAR.

### 4.2 Frontend Dependencies

| Package | License | Type | Commercial Use | Viral/Copyleft | Status |
|---------|---------|------|---------------|----------------|--------|
| next 16.1.7 | MIT | Permissive | Allowed | No | CLEAR |
| react 19.2.3 | MIT | Permissive | Allowed | No | CLEAR |
| react-dom 19.2.3 | MIT | Permissive | Allowed | No | CLEAR |
| @phosphor-icons/react ^2.1.10 | MIT | Permissive | Allowed | No | CLEAR |
| @supabase/supabase-js ^2.99.2 | MIT | Permissive | Allowed | No | CLEAR |
| pg ^8.20.0 | MIT | Permissive | Allowed | No | CLEAR |

**Dev dependencies** (eslint, typescript, @types/*) are build-time only and do not ship in the production bundle. All are MIT-licensed.

### 4.3 License Compliance Summary

- **No GPL/AGPL/LGPL dependencies found.** No viral/copyleft license risk.
- **No commercial-use-restricted dependencies found.**
- **All licenses are permissive** (MIT, BSD-2-Clause, BSD-3-Clause, Apache 2.0).
- These licenses are mutually compatible and compatible with both open-source and proprietary distribution.

### 4.4 Fonts

The project uses Google Fonts loaded via Next.js `next/font/google`:
- **Playfair Display** -- SIL Open Font License 1.1 (permissive, allows commercial use)
- **Inter** -- SIL Open Font License 1.1 (permissive, allows commercial use)
- **JetBrains Mono** -- SIL Open Font License 1.1 (permissive, allows commercial use)

All fonts are CLEAR for commercial use.

### 4.5 Recommendation

The project currently has no LICENSE file at the repository root. If the project is intended to be open source (as indicated in CLAUDE.md), a LICENSE file should be added. Recommended: MIT License, which is compatible with all current dependencies.

---

## 5. Data Privacy

### 5.1 User Data Collection

**Finding: NO user data is collected.**

- No user accounts, login, authentication, or signup flows exist.
- No cookies are set (confirmed by code review of all frontend files).
- No analytics scripts (no Google Analytics, no tracking pixels, no telemetry).
- The only client-side storage is `localStorage.getItem('void-news-theme')` for persisting the user's light/dark mode preference. This is a non-identifying functional preference, not personal data.

### 5.2 PII from Articles

**Finding: LOW RISK**

The `articles` table stores an `author` field (populated from RSS feed `entry.author`). This is publicly available metadata from published news articles -- the author names are already public information published by the news outlets themselves.

The `sources` table stores outlet metadata (name, URL, credibility notes) -- all publicly available information.

No private individual PII is collected or stored.

### 5.3 GDPR Compliance

**Finding: COMPLIANT**

GDPR applies when processing personal data of EU individuals. Since void --news:
- Collects no personal data from users
- Has no user accounts or profiles
- Sets no tracking cookies
- Runs no analytics
- Stores no IP addresses
- Only stores publicly available journalist bylines from published articles

The project falls outside the scope of most GDPR obligations. The publicly available author names from news articles are covered by the "journalism exemption" (GDPR Article 85) and the "legitimate interests" basis (Article 6(1)(f)).

### 5.4 CCPA Compliance

**Finding: COMPLIANT**

The CCPA applies to businesses that collect personal information of California consumers. Since void --news collects no personal information from any users, CCPA obligations do not apply.

### 5.5 Recommendations

1. Add a minimal privacy policy page to the frontend stating: "void --news does not collect personal data. No cookies, no tracking, no accounts. Theme preference is stored locally in your browser."
2. If analytics are ever added in the future, a cookie consent banner and privacy policy update would be required.

---

## 6. Specific Code Review Findings

### 6.1 `pipeline/fetchers/web_scraper.py`

| Check | Status | Details |
|-------|--------|---------|
| Respects robots.txt | PASS | `_check_robots_txt()` checks before every scrape |
| Identifies itself | PASS | User-Agent: `VoidNews/1.0 (+https://github.com/aacrit/void--news)` |
| Rate limiting | PARTIAL | No explicit rate limiting or crawl-delay between requests |
| robots.txt failure handling | CAUTION | Defaults to "allowed" when robots.txt cannot be fetched |

### 6.2 `pipeline/fetchers/rss_fetcher.py`

| Check | Status | Details |
|-------|--------|---------|
| Identifies itself | PASS | User-Agent header set with project URL |
| Accepts RSS content types | PASS | Accept header includes RSS/XML types |
| Parallel fetching | PASS | Capped at 10 workers, 30s timeout per feed |
| Summary truncation | PASS | Summaries truncated to 1,000 characters |
| HTML stripping | PASS | HTML tags stripped from summaries |

### 6.3 `pipeline/main.py`

| Check | Status | Details |
|-------|--------|---------|
| Full text storage | CAUTION | `full_text` stored in Supabase articles table (line 189) |
| Bias analysis use | PASS | Full text used for legitimate transformative NLP analysis |
| Clustering use | PASS | Only first 200 words used for TF-IDF clustering |
| Author storage | NOTE | Author names stored -- publicly available metadata, low risk |

---

## 7. Consolidated Recommendations

### High Priority

1. **Limit full-text retention.** After running bias analysis and clustering, truncate `full_text` to a short excerpt (2-3 sentences / 300 characters) or delete it entirely. Store the derived bias scores but not the copyrighted source text. This is the single most important change to reduce legal risk.

2. **Never display full article text on the frontend.** Always link users to the original source URL. The current frontend appears to do this correctly (no evidence of full-text display), but this should be an explicit policy.

### Medium Priority

3. **Add a LICENSE file** to the repository root (recommend MIT).

4. **Add a minimal privacy policy** page to the frontend.

5. **Add rate limiting** to the web scraper (e.g., 1-2 second delay between requests to the same domain) to be a more respectful crawler.

6. **Monitor AP/Reuters terms of service.** Wire services are the most litigious about content reuse. Consider whether full-text scraping of wire service articles is necessary, or whether RSS summaries provide sufficient text for bias analysis.

### Low Priority

7. **Add a publisher opt-out mechanism** (a contact method for publishers to request exclusion from the aggregator).

8. **Consider a formal trademark filing** for "void --news" in relevant USPTO classes before commercial launch.

9. **On robots.txt fetch failure**, consider defaulting to disallowed (conservative approach) rather than allowed.

10. **Document the bias methodology publicly** to differentiate from AllSides' patented survey-based approach. Clear public documentation of the algorithmic, rule-based NLP methodology strengthens the position that the approaches are fundamentally different.

---

## 8. Conclusion

The void --news project is in good legal standing across most dimensions. All dependencies are permissively licensed, no competitor IP is being infringed, the project name does not conflict with known trademarks, and no user data is collected.

The primary area requiring attention is the storage of full article text. The current practice of scraping and permanently storing full article bodies from copyrighted news sources creates moderate legal risk. This can be mitigated by treating full text as transient pipeline data -- process it through the NLP engines, extract the scores, then discard or aggressively truncate the source text.

The bias analysis methodology itself is clearly transformative and uses standard, published NLP techniques that do not infringe on any competitor's intellectual property.
