# History event page: the thesis

Proposal, 2026-09-24. Nothing here is implemented. It supersedes the core
premise of `docs/proposals/HISTORY-PAGE-REVAMP.md` (2026-09-20), which built
the page as the episode read off the screen. The CEO's brief:

> "Why shouldn't our written history page just be different than audio except
> it covers the same topics. The audio is a dramatized/summarized version of
> the page. They are two independent products that talk to each other. We
> should give the story but with a lot more detail and rigor. Come up with
> that design, the page should read like a well gathered set of artifacts and
> counter opinions. Think of it as a historian's thesis."

Two constraints were added while this was written and bind every section
below. **Sources: "we need only credible top notch sources that can be cited
in thesis materials."** **Cost: "$0 always."** No paid database, no purchased
book, no paid API, no LLM call on the Gemini cap. Agent work runs on the Claude
Max CLI, which is already paid for.

Everything measured below was measured against the repo on 2026-09-24: 78
event records, 78 scripts, 1,261 bibliography entries, 239 distinct DOIs
resolved through doi.org and Crossref, 384 distinct archive.org links fetched.

---

## 1. Verdict

**The page should be a thesis, and the thesis cannot be written from what the
repo holds today.** Not because the record is short (it is one and a half
times the script) but because nothing in it is traced. There is no claim-level
citation anywhere in 78 events. No source carries a page number. No quotation
carries a locator. No source text is stored, so no quote can be checked
against anything but itself. And the bibliography's own identifiers fail at a
rate that means they were written from memory rather than resolved: of 239
distinct DOIs, 106 point at the work they claim, 50 point at a different work,
and 83 resolve to nothing. Of 384 archive.org links, 90 are dead.

Rule 1 sets the shape of the answer. A thesis cannot be longer than its
evidence, and silence beats a plausible reconstruction. So this design is
mostly a research product with a page on the end of it: an evidence ledger per
event, built from free and open sources only, verified by fetching rather
than by recall, and a thesis that may not contain a sentence the ledger does
not carry. The page is the rendering of that ledger. The audio stays what it
is, a dramatisation, and both products cite the same ledger.

The consequence the CEO should hear first: **the current 78 pages stay as the
Hearing until an event's thesis passes its gates, one event at a time**, and
the first three will take longer than the next thirty.

---

## 2. What exists, measured

### 2a. Across all 78 events

| Measure | Value |
|---|---|
| Record prose per event (`summary` + `significance` + five `narrative`) | 2,068 to 4,160 words, median 3,126 |
| Script per event | 1,704 to 2,318 words, median 2,115 |
| Record to script ratio | median 1.46 |
| Perspectives | 5 each; types across the catalogue: vanquished 108, victor 79, revisionist 68, academic 60, bystander 60, indigenous 15 |
| `primary_source_excerpts` | 297 (3 to 6 per event); every one carries author, work and date; **12 carry a URL** (11 events); 0 carry a page; 48 are institutional or legal documents (UN resolutions, judgments, edicts, reports) |
| `notable_quotes` | 772; every one has a `context` string; **0 carry a page or locator**; 27 speakers are anonymous or unnamed; 66 duplicate a primary excerpt; 8 are duplicated across two perspectives of the same event |
| Bibliography (`perspectives[].sources`) | 1,261 entries, 14 to 21 per event; 1,053 typed `book`, 50 `journal`, 48 `document`, 44 `archive`, 21 `report`, 11 `legal`; **0 carry a publisher, edition or page field** |
| Identifiers | 258 DOI fields (239 distinct), 415 archive.org links (384 distinct), 173 Open Library ids; 690 entries carry nothing at all |
| DOI resolution | 202 resolve, 36 return 404; **Crossref title match: 106 correct, 50 a different work, 83 no record.** 19 of the 81 JSTOR-prefixed DOIs land on Taylor and Francis, which means a book review, not the book |
| archive.org links | 293 live, 90 dead (23%) |
| Verifiable entries (DOI matches the claimed title, or a live archive copy) | **350 of 1,261 (28%)**; 188 carry a broken identifier; median 3.5 per event; **29 events have zero** |
| Wikipedia inside a source entry | 0 (key figures carry Wikipedia links, which is fine as a locator) |
| Key figures | 548, 399 with a Wikidata id |
| Media | 506 items; **242 are Unsplash or Pexels stock (48%)**; 252 are Wikimedia Commons; 180 public domain, 69 CC BY-SA, 6 fair use; 2 events have no media, 11 no hero image |
| Numerals in record prose | 39 to 244 per event, median 114, 8,963 in all; none is traced to a source |
| Script reuse of the record | scripts quote 226 of the 297 excerpts and 364 distinct notable quotes |

One further finding from reading the pair below: the Partition script says
Radcliffe had "census data from nineteen forty one, six years out of date";
the YAML says his maps "had not been resurveyed since 1931" and nowhere
contains 1941. H-10 did not fire because it matches capitalised words. A
number the record does not carry is in a published episode. This is the
class of defect the ledger exists to make impossible.

### 2b. Two events, closely

**Partition of India** (`partition-of-india.yaml`): 2,914 words of record
prose against a 2,196-word script. Four excerpts, none with a URL, one
secondhand (Radcliffe "quoted in Read and Fisher"). Sixteen sources, twelve
with an identifier, ten with a DOI: the DOI on *Freedom at Midnight* lands on
a Taylor and Francis page (a review); the entry titled "The struggle for
Pakistan: a Muslim homeland and global politics, by Ayesha Jalal" is authored
by Ishtiaq Ahmed, which is a review of Jalal's book cited as if it were the
book, and its DOI returns 404; a Routledge DOI on *Partitioned Lives* returns
404. Eleven media items, seven of them stock photographs of modern India with
no bearing on 1947. Ten quotes, seven figures. **Rich prose, and not one
sentence of it could pass a citation gate today.**

**Srebrenica** (`srebrenica-genocide.yaml`): the thinnest record by prose,
2,068 words, and the best evidence base in the catalogue by kind. Its five
excerpts are UN Security Council Resolution 819, Mladic's filmed statement (an
ICTY exhibit), Erdemovic's ICTY testimony, the Secretary-General's report
A/54/549, and the ICJ's 2007 judgment. Its seventeen sources include four
judgments and reports that are public documents. None carries an identifier
or a URL, so all seventeen count as unverifiable today, but every one of the
legal and UN documents can be fetched in full, for free, and held verbatim.
**Thin words, thick evidence.** Srebrenica is a better first pilot than
Partition.

The pair says what the ledger has to do: Partition needs its identifiers
rebuilt and its stock imagery removed; Srebrenica needs its documents fetched
and pinned. Neither needs more prose first.

---

## 3. The premise: two products, one ledger

Three things per event, in a strict order of authority:

1. **The evidence ledger** (`data/history/evidence/<slug>/`) is canonical.
   It holds every source the event may cite, each source's verification
   record, and the verbatim extracts that claims are pinned to. Nothing may
   be published about the event that the ledger does not carry.
2. **The thesis** (`data/history/theses/<slug>.md`) is the written product.
   Every factual sentence cites a ledger entry and, where the claim is a
   quote or a number, a stored extract.
3. **The script** (`data/history/scripts/<slug>.txt`) is the dramatised
   product. It is written for the ear, keeps its spelled numbers and its
   breath marks, and cites the same ledger: a DOCUMENT segment names the
   extract it reads, and H-01 moves from "is this quote in the YAML" to "is
   this quote in the ledger".

The two products talk to each other in two directions and depend on each
other in none:

- **The page carries the drama as marked excerpts.** Three to five "From the
  episode" moments per thesis: the cold open under the hero, one inside an
  argument section where the script's scene covers the same ground, the close
  before the bibliography. Each is the script's own lines, verbatim and
  spelled as spoken, set in the editorial voice with a play glyph that seeks
  the shared player to that chapter (`playHistory` and `seekTo` exist on
  `useAudio()` today). They are quotations of the programme and are labelled
  as such, so a spoken "nineteen forty seven" inside one is honest. Outside
  them the page writes 1947.
- **The episode points at the exhibits.** The player's chapter list already
  carries titles; a DOCUMENT chapter gains the exhibit number, so a listener
  on `/audio` can open Exhibit 4 while it is being read.
- **Neither is required by the other.** A thesis renders whole with no
  script (the fifteen events that had no episode in September proved the page
  cannot wait on audio). A script renders with no thesis, as all 78 do now.
  A gate asserts the thesis has no empty section caused by a missing
  episode.

The five YAML perspectives do not disappear. They become the first draft of
the historiography (section 8) and stay in the YAML for the Hearing and the
script until each event switches.

---

## 4. Source admissibility

This section is the standard. Everything after it (data model, checks,
workflow) enforces it.

### 4a. Tiers

| Tier | What | Carries |
|---|---|---|
| **A. Primary record** | Documents contemporaneous with the event or produced by its institutions: archival papers, statutes, treaties, court judgments and testimony, official reports, resolutions, edicts, chronicles in scholarly translation, letters and diaries in a named repository, oral testimony with an archive accession, datasets from the body that collected them | A quote, a number, a dated fact. The tier a thesis is built on |
| **B. Peer-reviewed scholarship** | Monographs and edited volumes from university presses and scholarly publishers; articles in peer-reviewed journals; scholarly translations and critical editions | A claim, a number, an interpretation, when pinned to a page the researcher read |
| **C. Reference** | Established reference works and handbooks (Oxford, Cambridge, Brill, Encyclopaedia of Islam, Dictionary of National Biography and their peers) | A date, a name, a definition. Never the load-bearing source for an argument |
| **D. Positional** | Memoirs, party histories, state histories, advocacy scholarship, denialist literature, hagiography | Only as a labelled position in the historiography ("the X account holds"), never as fact, and only when a Tier A or B source is cited for what the position is |

**Excluded as a citation, on any claim:** Wikipedia and any wiki (a lead to a
Tier A or B source, and a locator for a person's dates, never cited);
blogs; popular history websites; lecture notes; AI output of any kind;
journalism that does not itself cite or witness (a reporter's eyewitness
dispatch is Tier A, a retrospective feature is not); advocacy material
presented as scholarship; a book review cited as the book; a source the
researcher has not opened.

**Partisan and contested scholarship** enters at Tier D by default. It rises
to Tier B only when it is peer reviewed and its claim is cited for what it
argues, in the historiography, with the counter-position beside it. Dodik's
"fabricated myth" line is in the Srebrenica record today as a quote; under
this standard it stays, as the denialist position's own words, cited to a
dated statement, beside the ICJ finding it denies. That is Rule 1's "publish
the disagreement", and it is also what stops the page from laundering a
position into a fact.

### 4b. The $0 rule and the free-readability rule

Every source is discovered, resolved and read through free and open
resources: Crossref and doi.org, OpenAlex, open-access journals and
repositories (DOAJ, university repositories, SSRN and arXiv where a field
uses them), Internet Archive and Open Library (including controlled lending),
HathiTrust public-domain full text, Google Books where the cited page is
visible in preview, JSTOR's open and early-journal content, national and
government archives (LOC, NARA, TNA, Gallica, Bundesarchiv, the National
Archives of India's Abhilekh Patal, and their peers), the Avalon Project,
FRUS, UN ODS and the ICTY, ICTR and ICJ document databases, and Wikimedia
Commons for media rights. No paid database, no purchased book, no paid API.

The rule this produces, stated once and put behind a check (T-05):

> **A claim may only cite a passage that a reader can read for free.** A
> paywalled monograph may be listed in the historiography as the work a
> position rests on. It may not carry a pinned quote or a page-level claim
> unless that passage was read from a free source (an Internet Archive loan,
> a HathiTrust or Google Books page, an open-access chapter, the author's
> deposited manuscript) and the ledger records where.

This costs coverage. Some of the best scholarship on some events is behind a
paywall with no preview. The thesis then says so in its section on the record
("the two standard monographs on the boundary award could not be read; the
positions below are taken from reviews and from the authors' open articles")
and argues from what it can show. That sentence is worth more to the reader
than a page number nobody can follow.

### 4c. The citation record

Every ledger entry carries, or fails validation:

```yaml
id: src-mansergh-1970                 # stable, cited from thesis and script
tier: A                                # A, B, C or D
kind: edited-documents                 # primary-document | judgment | testimony |
                                       # monograph | journal-article | edition |
                                       # reference | memoir | dataset | image | map
author: Nicholas Mansergh (ed.)
title: The Transfer of Power 1942-47
container: null                        # journal or volume title for an article or chapter
publisher: Her Majesty's Stationery Office
place: London
year: 1970
edition: 1st, 12 volumes
volume: XII
identifiers:
  isbn: ...
  doi: null
  archive_org: transferofpower12mans   # an item id, not a search URL
  hathitrust: null
  url: null                            # only a stable URL: a repository record, not a search
access:
  free_copy: https://archive.org/details/...   # where the cited pages were READ
  verified_at: 2026-10-03
  verified_by: crossref-title-match | archive-item-fetch | repository-record | manual-page-read
  verified_title: "..."                # the title the resolver returned
language: en
region_of_authorship: europe           # for the balance check
position: british-administrative       # for Tier D and B-in-historiography only
```

A claim is pinned by a **locator** on the citation marker: a page, a
paragraph number, a document number in an edited series, an article of a
treaty, a paragraph of a judgment, a timestamp in a recording. Locators are
required on Tier A and B citations and on every quote and number.

Verbatim text is stored as **extracts**, one file per pinned passage:

```
data/history/evidence/partition-of-india/extracts/src-un-res-47.p1.txt
```

with a four-line header (source id, locator, the URL it was read at, the
read date) and then the passage as printed. Public-domain and official
documents may be held whole. A copyrighted work is held only as the passage
cited, capped at 150 words per extract and 5 extracts per work; the cap is a
fair-dealing judgement and is a CEO decision (section 13). A quote in the
thesis must be a substring of an extract under the same normalisation H-01
uses (`script_format._norm`), and a number in a cited sentence must appear in
the cited extract as that digit string.

### 4d. Today's sources against the standard

Measured, not estimated, per section 2:

- **350 of 1,261 entries (28%) would pass verification** as pointing at the
  work they name, and none of those has a page, so **0 of 1,261 can carry a
  pinned claim today**.
- **188 carry an identifier that is wrong or dead**, which is worse than none:
  a wrong DOI is a factual error on the page.
- **690 carry no identifier at all.**
- By tier, roughly: the 48 legal and institutional excerpts and the 44
  `archive` plus 48 `document` plus 11 `legal` entries are Tier A in kind
  (about 150); the 1,053 books and 50 journal entries are Tier B in kind if
  they exist as named; the 11 `article`, 1 `film`, 1 `documentary`, 1
  `encyclopedia` and 1 `other` need reclassifying or removal.
- **Thinnest**: 29 events have zero verifiable sources. Twelve have fifteen
  entries and none verifiable, including `alexanders-conquests`,
  `assassination-of-caesar`, `black-death`, `civil-rights-movement`,
  `fall-of-tenochtitlan`, `inca-conquest-peru`, `iran-iraq-war` and
  `kingdom-of-kongo` (which also has no media). The ancient and medieval
  events cluster here because their sources are chronicles in translation
  with no DOI, which is exactly where the free-readability rule helps:
  Arrian, Suetonius, Bernal Diaz and the Florentine Codex are public domain
  and held whole on Internet Archive and Perseus.
- **Richest**: `cambodian-genocide` (13 verifiable of 17), `peloponnesian-war`,
  `armenian-genocide`, `scramble-for-africa` and `global-financial-crisis-2008`
  (12 each).
- **Media**: 242 stock items (48%) fail the standard outright. They are not
  evidence of anything. They leave every thesis page.

### 4e. The minimum evidence bar

An event may switch to the thesis page only when its ledger holds:

- at least **6 Tier A** entries, each with a stored extract;
- at least **8 Tier B** entries verified to exist as named, of which at least
  **4 carry a pinned, free-readable page**;
- at least **3 positions** in the historiography, each resting on at least
  one verified source authored by a holder of that position, not a critic;
- at least **2 sources from the event's own region or in its own language**
  (a translation counts when the original is named), or a stated reason in
  the record section why none could be found free;
- at least **3 exhibits** with full provenance, none stock;
- every contested figure in the thesis body expressed as the range the ledger
  supports;
- a verdict on every position, and at least **1 finding** with a stored,
  recomputable derivation (6b).

Srebrenica clears the Tier A bar with the documents it already names.
Partition clears nothing until its identifiers are rebuilt.

### 4f. Non-English free sources

Added 2026-09-24. The CEO asked whether "the translation thing we did
earlier" can be reused. That is `scripts/roster/anchor_pairs.py` (commit
315bd19), and it is not a translator: it matches the same news article
across languages by the names, numbers and dates the two texts share,
scoring shared capitalised tokens at 2, their five-character prefixes at 1
(so Zelensky and Selenskyj count), shared digit strings at 2 and shared
long words at 1, and it was measured at 100% precision on the pairs scoring
18 or more. The idea worth reusing is the invariant underneath it: **a
faithful rendering of a text preserves every name, number and date in it.**
That invariant is mechanically checkable, and it is what makes non-English
sources admissible without trusting a translation.

**1. Admission.** A non-English Tier A or B source enters the ledger on the
same terms as an English one, with `language` set. Its extract is stored
verbatim in the original language and script, with the original's locator.
Beside it the ledger may hold one English rendering, and the rendering is
labelled as exactly one of two things:

- **an official parallel translation**: the same document as issued by its
  own institution in English. UN documents exist in six official languages
  and ODS serves each; ICTY and IRMCT records exist in English, French and
  BCS; the ICJ issues in English and French; EU and League of Nations
  material likewise. Where one exists it is preferred, it is stored as its
  own extract with its own locator, and it may carry a pinned English
  quote;
- **a Void translation**: made by the agent at $0, stored with `rendering:
  void`, the agent's session and date, and never passed off as a quotation
  of a published English text. A Void translation may be exhibited beside
  the original and paraphrased in the argument; a quotation in the thesis
  from a Void translation prints the original first and the rendering
  under it, labelled, and the citation marker pins the original.

A published scholarly translation (Loeb, a critical edition, a translated
monograph) is a Tier B source in its own right, cited as the translator's
work, and is neither of the above.

**2. The parity check (T-20).** Every rendering must preserve every name,
number and date in the original. `ledger.py` extracts three sets from each
side: digit strings (with a locale pass so 1.500 and 1,500 and ١٥٠٠ are
one number), dates (with month names mapped per language and calendar
conversion flagged rather than done), and proper names as `anchor_pairs`
finds them, plus a transliteration table per script so that Jinnah and
جناح and Джинна match by a registered pairing, not by luck. A rendering
that drops or adds a member of any set fails; a rendering that changes a
number fails hard. Where an official parallel version exists, the Void
translation is checked against it as well, sentence count and entity set,
and the official version is what the page quotes. This is the anchor idea
turned from a matcher into a gate: the score is not a threshold to pass but
a set difference that must be empty.

**3. The catalogue, probed from this container on 2026-09-24.** Each entry
was fetched with a search or a document request; "reachable" means a real
response came back, not a challenge page. None of the candidates is paid.

| Repository | Languages | Result | Note |
|---|---|---|---|
| Gallica (BnF) | French, colonial-era print | reachable | SRU search API answered |
| Persée | French scholarship | reachable | search answered |
| Europeana | European archives, many languages | reachable | API answered on the demo key; a free key is required for volume |
| Deutsche Digitale Bibliothek | German | reachable | |
| SciELO | Spanish, Portuguese scholarship | reachable for articles | scielo.br serves pages; the search endpoint returns 403 to this container, so discovery goes through Redalyc or Crossref |
| Redalyc | Spanish, Portuguese scholarship | reachable | |
| CyberLeninka | Russian, Ukrainian scholarship | reachable | article pages served |
| J-STAGE | Japanese scholarship | reachable | search answered |
| National Diet Library Search and Digital | Japanese | reachable | OpenSearch API returned XML; dl.ndl.go.jp answered |
| JACAR | Japanese state records | reachable | home answered; the database paths need the real query form |
| Chinese Text Project | Classical Chinese | reachable | JSON API answered; rate limited, free |
| National Digital Library of India | Indian languages, English | reachable | some items need a free login |
| UN ODS | six official languages | reachable | S/RES/819 (1993) came back as a 116 KB PDF |
| ICTY case pages (icty.org) | English, French, BCS | reachable | the Krstic trial judgment came back as a 702 KB PDF |
| ICTY/IRMCT Court Records (ucr.irmct.org) | English, French, BCS | reachable, free registration | exhibits and transcripts sit behind a free account |
| Perseus | Greek, Latin, with parallel English | reachable | |
| The Latin Library | Latin | reachable | |
| Wikisource (per language) | many | reachable | a transcription, cited only with the scan it transcribes |
| Internet Archive | many | reachable | |
| Qatar Digital Library | Arabic, Gulf and India Office records | **blocked** | 403 on every path from this container |
| HathiTrust | many | **blocked** | 403 on catalog and full text from this container; usable by hand, not by CI. Section 4b's mention stands for a person, not for the checker |
| ICJ (icj-cij.org) | English, French | **blocked** | 403; ICJ judgments are reached through UN ODS where issued as UN documents, otherwise by hand |
| UN Digital Library | six | **blocked** | challenge page; ODS covers the same symbols |
| Abhilekh Patal (National Archives of India) | English, Indian languages | **blocked** | empty 202 and 404 from this container |

Blocked means blocked from the CI container today; a person can still read
those archives, and an extract read by hand carries `free_copy` as usual
with `read_by: hand`. The weekly ledger job re-probes the catalogue and
flips a row when access changes, so this table is data, not a promise.

**4. What it makes achievable.** T-07 fails an event where every Tier B
source is from one region or every position rests on one language, and the
bar in 4e asks for 2 sources from the event's own region or language. With
this catalogue those are met from Gallica for the Algerian War, from
CyberLeninka and the Ukrainian record for the Holodomor, from J-STAGE and
the NDL for Meiji, from Redalyc and SciELO for the Bolivarian revolutions,
from ICTY's BCS records for Srebrenica, from the Chinese Text Project for
the Mongol conquest as the Chinese sources saw it. The record section names
the language of every source it rests on, so the reader can see when an
event about India has been argued from London's papers.

**5. The limits.** The agent translates reliably enough for the parity gate
to be the only extra control in French, German, Spanish, Portuguese,
Italian, Dutch, Russian, Ukrainian, Polish, Bosnian, Croatian and Serbian,
and in classical Latin and Greek where Perseus supplies a printed parallel
to check against. It is weaker, and the parity gate plus a stated
`confidence: moderate` on the rendering is required, in Chinese, Japanese,
Arabic, Persian, Turkish, Hindi, Urdu, Bengali and Punjabi, where scripts,
calendars and transliteration make entity parity itself fallible. It is
not reliable in Khmer, Kinyarwanda, Amharic, te reo Maori, Quechua,
Nahuatl, Kongo, and in any language read from a poor scan (Fraktur,
nastaliq, early print). For those, and for any language the agent flags as
uncertain, a **second-pass back-translation** is required: a separate
session renders the English back into the original with no sight of the
source, and the ledger stores the back-translation and its parity result
against the original; a back-translation that loses an entity or a number
fails the rendering. Where no official parallel exists and the language is
in the unreliable list, the extract may be exhibited in the original with a
Void rendering labelled "unverified translation", and the thesis may cite
the original for what it names and dates but may not quote the rendering
in English. Silence beats a plausible translation.

---

## 5. The expansion workflow

The agents exist; the sequence and the tooling do not. Workflow
`/history-thesis <slug>`, five stages, every write reviewed by the next stage.

**Stage 0, ledger bootstrap (script, no agent).** `pipeline/history/ledger.py`
reads the event YAML and writes a first `ledger.yaml`: one entry per source
and per excerpt, tier guessed from `type`, every identifier resolved live
(doi.org plus Crossref title match, Open Library, archive.org item fetch,
HathiTrust catalogue), `verified_by` stamped or `unverified` written. It
prints the event's standing against the bar in section 4e. This is section 2
of this document made permanent.

**Stage 1, discovery (history-curator).** For each position and each argument
the event needs, search OpenAlex and Crossref by topic and by the cited
authors; search Internet Archive, HathiTrust, Gallica, LOC, the Avalon
Project, FRUS, UN ODS and the tribunal databases for primary documents;
search the event's own region (the National Archives of India, the Pakistan
National Archives' online holdings, JACAR for Japan, the Bundesarchiv,
Memorial's archive for the Soviet events, university repositories in the
region). Output: candidate entries with the URL where each can be read free.
No entry is written from memory: **a candidate with no fetched record is not
a candidate.**

**Stage 2, reading and pinning (history-curator for text, media-archaeologist
for documents, images, maps).** Open each free copy, read the passage the
claim needs, store the extract with its header. For an image or map: creator,
date, repository, accession, licence, and one line on what the image shows
and what it does not (a 2009 photograph of the Potocari memorial is evidence
of the memorial, not of 1995). This is the slow stage and the only one that
produces rigor.

**Stage 3, positions (perspective-analyst).** Turn the five YAML perspectives
into the historiography: named positions, each with its holders, the works it
rests on (ledger ids), the claim in one sentence, what it omits, and the
contested claims it shares with another position. Add positions the YAML
lacks where the ledger now supports one; drop none.

**Stage 3b, adjudication and analysis (history-curator).** Test every
position against the Tier A extracts and record its verdict in the ledger;
then derive the findings, each as an `analyses/` file with rows, method,
confidence and the evidence against, and run `ledger.py recompute` until it
is silent. This is the historian's stage (6b).

**Stage 4, writing (narrative-engineer).** The thesis in the grammar of
section 8, every sentence cited, register per section 8, numerals, no dash.
Then the episode marks: which script chapters the page quotes and where.

**Stage 5, audit (historiographic-auditor, read-only).** The ten dimensions
it already checks, plus the bar in section 4e and the balance rules in T-07
and T-08. Its verdict is recorded in the thesis front matter with a date;
the page cannot switch without it.

**Balance across regions and schools** is a ledger property, so it is
checked, not hoped for: `region_of_authorship` and `language` on every entry,
and T-07 fails an event where every Tier B source is from one region or every
position rests on Anglophone scholarship alone. Where the free-readability
rule leaves a regional literature out (a Persian monograph with no open copy),
the record section says so, in the page, by name.

**Cost.** Every catalogue above is free without a key or with a free key
(Europeana, DPLA, Smithsonian). Agent sessions run on the Claude Max CLI. The
Gemini daily cap is not touched: nothing here calls a model at runtime.

---

## 6. Where rigor comes from, and what a thin event gets

Rigor comes from Stage 2 and nowhere else: a person or agent opening a free
copy of a source and storing what it says beside where it says it. Everything
else is bookkeeping around that act.

A thin event (a ledger that clears the bar with little to spare) gets a
shorter thesis. Not a padded one. The page has no minimum length; the gate
has a maximum (8,000 words) and a rule that every section be present. A thin
thesis for Kingdom of Kongo might run 1,800 words with three exhibits, two of
them the Kongo kings' own letters to Lisbon (public domain, held on Internet
Archive in translation), and a record section that says plainly which
literatures could not be read free. That page is honest and it is still a
thesis. The Hearing keeps running for the event until then.

---

## 6b. The engine is a historian

Added 2026-09-24 on the CEO's direction: "this page is drafted by a
historian, or it is one. It should not just quote other historians, but
evaluate that against the artifacts and ensure they are true, and further
yet come up with fact based research and analysis of its own. The engine is
a historian." Everything before this section described a compiler with a
citation discipline. This section makes it a historian, and the anatomy,
data model, checks, voice decision and register sample below are revised to
match.

A historian does two things a compiler does not. First, when a scholar
says something, the historian goes to the artifact and reports whether the
artifact bears it out. Second, the historian looks at the primary record and
finds things in it that no scholar in the bibliography has stated, by
counting, tabulating, dating and comparing document against document. Both
are done in the open, with the working shown, and neither ever produces a
new fact asserted on the historian's authority.

### 6b.1 Adjudication: every position is tested against the artifacts

Each position in the historiography carries a verdict, and the verdict is
the historian's, not the position's own. The vocabulary has four words and
no others:

| Verdict | Means | Must cite |
|---|---|---|
| **Supported** | A Tier A artifact in the ledger says what the position says it says | the extract, with locator |
| **Contradicted** | A Tier A artifact in the ledger says otherwise | the extract, printed beside the claim |
| **Qualified** | The artifacts bear out part of the claim and are silent or contrary on the rest; the verdict says which part | the extract for the supported part, the extract or the gap for the rest |
| **Untestable from the free record** | No admissible artifact that could be read free bears on the claim | the record section's statement of what could not be read, by name |

Three rules follow. **The page never repeats a scholar as settled.** A
position's claim is always printed as that position's claim, in that
position's name, with its verdict beside it; a claim that has earned
Supported is still printed as the position's claim with the artifact under
it, because the artifact is the authority and the scholar is the reader of
it. **A contradiction shows the artifact beside the claim.** Not a note, not
a link: the extract itself, in the exhibit frame, in the same block as the
sentence it contradicts, so the reader sees the two together. **Untestable
is a finding, not a shrug.** It is the most common verdict the free record
will yield, and each one names the artifact that would settle it and where
that artifact sits behind a paywall or in a closed archive. That list is
the reading list for the next pass.

Adjudication also runs on the thesis's own three claims from section 2 of
the page. A claim the artifacts do not support is not a claim the thesis
makes.

Two further rules, approved by the CEO on 2026-09-24, because a Tier A
document is evidence of what its author recorded and not neutral truth.

**Rule A, whose record.** Every verdict names who produced the documents it
rests on: the colonial administration, the tribunal, survivor testimony,
the perpetrator state, the victorious party's press. The ledger carries
this as `record_of` on every Tier A entry, and the verdict marker prints
it ("Contradicted by the tribunal's own record" reads differently from
"Contradicted by the ministry that ordered it"). When every document
behind a verdict comes from one side of the event, the verdict is capped at
**Qualified**, never Contradicted, and the page says why in the verdict
sentence: "the only documents this record holds on the point are the
administration's own". A position can be found wanting by its own side's
papers, and often is; it cannot be found wanting by the other side's papers
alone. Check T-18.

**Rule B, a gap is published, not treated as disproof.** When the free
record is thin for one side, the page states the gap by name ("no open
archive holds the Muslim League's district correspondence for 1947") in the
record section and in the verdict, instead of letting the missing documents
read as the account being wrong. Absence of evidence never moves a verdict
to Contradicted: a Contradicted verdict must cite an artifact that says
otherwise, not the lack of one that says so. A position whose evidence
would sit in a closed or paywalled archive is Untestable, with `would_settle`
naming the archive, and that sentence is printed. Check T-19.

### 6b.2 Original analysis: findings from the primary record

A finding is a statement the historian derives from Tier A extracts by a
stated method, where no source in the ledger states it. The allowed methods
are the ones whose working can be stored and re-run:

- **a count**: how many documents in the record do X (how many of the
  eleven Srebrenica execution sites named in the ICTY judgment appear in
  the Dutch battalion's own reports);
- **a cross-tabulation**: two properties of the same set of extracts against
  each other (which positions cite which decades of scholarship; which
  sources are in the event's own language);
- **a reconstructed timeline**: dates carried by the extracts put in order,
  with the intervals computed (the gap between a boundary's announcement
  and its publication);
- **a document-against-document comparison**: two artifacts on the same
  event set side by side, with the points where they agree, differ and are
  silent listed.

A finding is not a claim about the world beyond the arithmetic. "The line
was published fifteen days before the only neutral force was disbanded" is a
finding. "The state abandoned the Punjab" is not; it is an interpretation
and it takes the `{i}` mark, sits beside the finding, and carries no
number the finding does not.

Every finding is stored in the ledger as a derivation, so it recomputes:

```yaml
# data/history/evidence/partition-of-india/analyses/f-01-line-and-force.yaml
id: f-01
title: The line, the force and the interval between them
method: timeline          # count | crosstab | timeline | comparison
rows:
  - { date: 1947-06-03, event: partition announced,            from: src-summary ¶1 }
  - { date: 1947-08-15, event: independence,                   from: src-summary ¶2 }
  - { date: 1947-08-17, event: Radcliffe Line published,       from: src-summary ¶2 }
  - { date: 1947-09-01, event: Punjab Boundary Force disbanded, from: src-summary ¶4 }
derive:
  - { name: notice_days,           expr: "days(1947-06-03, 1947-08-15)", value: 73 }
  - { name: line_to_disbanding,    expr: "days(1947-08-17, 1947-09-01)", value: 15 }
confidence: high          # high | moderate | low, with the reason
confidence_reason: date arithmetic on dates the record states as days
against:
  - text: The force reported to the Joint Defence Council, not to either dominion, and both governments accused it of bias, so its end is not explained by the interval alone
    from: src-perspective-british ¶4
statement: >
  The boundary was published two days after independence and fifteen days
  before the one neutral force in the Punjab was disbanded.
```

`ledger.py recompute <slug>` re-evaluates every `derive` line from the rows
and fails when a stored `value` disagrees, and every `from` must be an
extract id that resolves. A finding whose rows cannot all be traced does not
exist.

### 6b.3 How this squares with Rule 1

Rule 1 says every factual claim traces to a source and silence beats a
plausible reconstruction. An adjudication or a finding is not a new fact; it
is the historian's reading of facts that already trace, and the page treats
it as exactly that:

- **The working is shown.** A verdict prints its extract; a finding prints
  its rows and its arithmetic, in an expandable method block, and the
  ledger holds the derivation that CI recomputes.
- **Confidence is stated**, in words the reader can weigh: high for
  arithmetic on dated documents, moderate where an extract is a translation
  or a secondhand report, low where the rows are few. A low-confidence
  finding may print; a finding with no stated confidence may not.
- **The evidence against it is printed**, in the same block, before the
  reader can scroll past. A finding with an empty `against` list must say
  in that field that the historian looked and found none, and name where.
- **It is marked as the thesis's own analysis**, never as a sourced fact.
  A finding's statement carries no citation marker; it carries the finding
  id, and the register sets it apart (6b.5). Nothing in the argument may
  cite a finding as if it were a source.
- **Silence beats an unsupported inference.** An inference the artifacts do
  not carry is cut, not hedged into place. The `{i}` mark is for the one
  sentence that draws the reader's eye to what the evidence shows; it is
  not a licence to say what the evidence does not.

### 6b.4 Who does it

Stage 3b of the workflow in section 5, between positions and writing, done
by history-curator (the chief researcher role) with historiographic-auditor
checking every verdict against its extract in Stage 5. No LLM call at
runtime; the arithmetic runs in `ledger.py`.

### 6b.5 How the page presents it

- **A verdict marker on every position**: a Barlow eyebrow in the
  position's block, "Verdict: Contradicted", followed by one sentence in
  the historian's voice and the artifact in an exhibit frame directly
  under it. Untestable prints the named artifact that would settle it.
- **An analysis block** for each finding: the statement in Inter with a
  brass rule and the eyebrow "Finding 2 · Timeline · Confidence high", then
  a native `<details>` labelled "Method" holding the rows as a table with a
  note per row, the derived values, and the "Against" paragraph. Open by
  default in print.
- **A Findings part of the anatomy** (section 7, item 5) that gathers the
  findings after the argument and before the historiography, so the reader
  meets what the record shows before meeting what the scholars claim of it.

---

## 7. Anatomy of the page

Top to bottom. Heading levels in brackets.

1. **Hero** (h1). Kept: image (an exhibit, never stock), date, title,
   subtitle, Listen. Under it, "From the episode": the cold open, three or
   four lines, play glyph.
2. **The question** (h2). 100 to 150 words: what the thesis asks, in one
   question, and the three claims it will make, numbered. Playfair, measure
   40ch.
3. **The record** (h2). What evidence this thesis is built on and what it
   is not: counts by tier, the documents held whole, what could not be read
   free, what the record does not contain at all (the state that could not
   count its dead). Written from the ledger, so it cannot flatter.
4. **The argument** (h2), sections 1 to n (h3). Formal prose, Inter, 65ch,
   numerals, full dates, every sentence carrying a note. Exhibits inline
   where the argument reaches them. One "From the episode" excerpt at most
   per section.
5. **Findings** (h2). The thesis's own analysis, one block per finding
   (6b.2): the statement, its confidence, an expandable method with the rows
   traced to extracts, and the evidence against it. At least one, or the
   event does not publish (T-17).
6. **Exhibits** (figure, numbered across the page). A document: the extract
   in Plex Mono on deep paper, attribution first, locator, link to the free
   copy. An image or map: the item, then the provenance line and the "shows /
   does not show" line. A table: a real `<table>` with the source per row.
7. **The historiography** (h2). Positions 1 to n (h3), each: holders, rests
   on, claims, omits, and **the verdict** (6b.1) with the artifact it rests
   on printed under it. Then **Where the record disagrees** (h3): each
   contested claim as a ruled block, one row per position, its figure or
   claim, its source, its verdict. The thesis body never states a contested
   figure as one number; it points here.
8. **What the record omits** (h2). Statements about the ledger, not about
   the world: no source in this record is by a Dalit refugee; no source dates
   the Gurdaspur decision. Each is attached to the position it cuts against.
9. **From the episode** (aside): the close, with the play glyph, before the
   end matter.
10. **Notes** (h2): the footnotes, numbered, short form with locator, each
    linking to its source below and to its exhibit where one exists.
11. **Sources** (h2): the ledger rendered as a bibliography by tier, full
    citation, the free-copy link, the verification date. Only verified
    entries print. Unverified entries do not print as "further reading";
    they do not print.
12. **The record** end matter, kept from the Hearing: key figures, threads,
    next event.

`significance` and `legacy_points` are not rendered, for the reason the prior
proposal gave: they are the moral, and a thesis earns its conclusion inside
the argument.

### 7a. Register sample (Partition of India)

**This is a register sample, not publishable copy.** Its citations are to
fields of `data/history/events/partition-of-india.yaml`, because no ledger
exists yet; the YAML is itself uncited, so every note below would fail T-05
today. It exists to show the voice, the note discipline and the shape of a
counter-position.

> ### The question
>
> Sir Cyril Radcliffe, a barrister who had never visited India, drew the
> boundary between the two dominions in five weeks.[1] The line was published
> on August 17, 1947, two days after the independence ceremonies in Karachi
> and Delhi.[2] Between August and November 1947 an estimated 14 to 15
> million people crossed it.[3] The dead are counted between 200,000 and 2
> million, and the record says why the range is that wide: most deaths were
> never registered.[4]
>
> This thesis asks whether the speed of the transfer caused the killing or
> answered it. It makes three claims. First, that the date was chosen in
> London and Delhi for reasons the record states. Second, that the force
> meant to hold the Punjab was never large enough to do so. Third, that the
> one boundary decision every account contests, Gurdaspur, is the one for
> which the record holds no document.
>
> ### 1. The date
>
> The transfer had been scheduled for June 1948.[5] Mountbatten moved it
> forward to August 1947 and later said the reason was to preserve
> "momentum".[6] The announcement came on June 3, 1947, with 73 days'
> notice.[7] The British account holds that the alternative was worse: by
> spring 1947 British district officers in the Punjab were reporting that
> they could not guarantee security beyond the monsoon.[8] The Indian
> nationalist account reads the same decision as reckless, driven by the
> Attlee government's wish to bring troops home.[9] The record carries both
> readings and no document that settles them.{i}
>
> The army that was to hold the province was being divided as the province
> burned. Of the 55,000 troops in the Punjab, roughly half were being
> reassigned to Pakistan.[10] The Punjab Boundary Force, 25,000 men under
> Major General Rees, covered a zone of 38,000 square miles[11] and was
> disbanded on September 1, 1947, after less than a month.[12] Nehru accused
> it of failing to protect Hindus and Sikhs; Jinnah charged it with
> anti-Muslim bias.[13]
>
> **Exhibit 1. Radcliffe on his own work, 1947.**
> "The division of India is, in my opinion, the greatest blunder in the whole
> history of the British Empire."[14]
> *Provenance:* private correspondence, quoted in Read and Fisher, *The
> Proudest Day*. Secondhand: the record holds the line as those historians
> quote it, not from the letter. *Ledger status:* unverified. This exhibit
> would not print until the passage is read in a free copy of *The Proudest
> Day* and pinned to its page.
>
> ### Where the record disagrees: the Gurdaspur award
>
> Radcliffe allocated Gurdaspur district to India. That gave India its only
> road link to Kashmir.[15]
>
> | Position | Holds | Rests on | Omits |
> |---|---|---|---|
> | British administrative | Radcliffe worked under five weeks, four deadlocked judges and maps not resurveyed since 1931; the award has been contested by Pakistani historians since[15] | Menon, Mansergh (ed.)[16] | Why Gurdaspur, of all districts, went the way it did |
> | Indian nationalist | The award was a minimal correction to an otherwise anti-Indian boundary[17] | Nehru, Azad, Guha[18] | That the link it created is the one the first war was fought over |
> | Pakistani nationalist | Kashmir was 77% Muslim under a Hindu ruler; its accession on October 26, 1947 was signed under duress; UN Resolution 47 (1948) called for a plebiscite India has never held[19] | Jalal, the Quaid-e-Azam speeches[20] | That the Lahore Resolution's logic of Muslim-majority areas did not name Kashmir |
>
> No position in the record cites a document for the award itself.{i}
> Radcliffe burned his papers and did not return to India.[21]
>
> **Verdicts.** The record's Tier A artifacts are four quotations: Nehru
> on August 14, 1947, Radcliffe's private line as Read and Fisher quote it,
> Gandhi at a Calcutta prayer meeting, and Jinnah on August 11, 1947.[22]
> All four are the words of the leaders of the three parties to the
> decision; none is an administrative record, a survivor's account or a
> district file, and this record holds no document from the Punjab itself.
> None bears on Gurdaspur. *British administrative: untestable from the
> free record.* The artifact that would test it is the Punjab Boundary
> Commission's report and Radcliffe's award, in Mansergh's Transfer of
> Power, volume XII, which this record names and does not hold.[16]
> *Indian nationalist: untestable*, for the same artifact. *Pakistani
> nationalist: qualified.* Its plebiscite claim rests on UN Security
> Council Resolution 47 of 1948, a public document this record names but
> does not hold;[19] its duress claim is stated in the record only as "in
> the Pakistani telling", which is the position describing itself.[19]
> The verdict on all three moves the day the ledger holds the award and the
> resolution, and not before.
>
> **Finding 1 · Timeline · Confidence high.** The boundary was published
> two days after independence and fifteen days before the one neutral force
> in the Punjab was disbanded. {f-01}
> *Method.* Four dated events the record states as days: partition
> announced June 3, 1947;[7] independence August 15, 1947;[2] the
> Radcliffe Line published August 17, 1947;[2] the Punjab Boundary Force
> disbanded September 1, 1947.[12] Derived: notice, 73 days (the record
> states the same figure);[7] line to disbanding, 15 days. No source in the
> record states the second interval.
> *Against.* The force reported to the Joint Defence Council, not to either
> dominion, and both governments accused it of bias,[13] so the interval
> alone does not explain its end. The record gives "overwhelmed by the scale
> of killing" as the reason for disbanding.[12]
>
> **Finding 2 · Count · Confidence moderate.** One neutral soldier for every
> 1.5 square miles of the zone the force was asked to hold. {f-02}
> *Method.* 25,000 troops[11] across 38,000 square miles,[11] both from the
> British account's own narrative; 38,000 divided by 25,000 is 1.52.
> Moderate, because both figures sit in a position's narrative rather than
> in an artifact this record holds, and the zone's boundaries are not
> stated.
> *Against.* The British Indian Army had 55,000 troops in the Punjab at the
> same time,[10] so the neutral force was not the only armed presence; the
> record says half of those were themselves being reassigned.[10]
>
> **Notes.** [1] summary ¶1. [2] summary ¶2. [3] summary ¶3. [4] summary ¶5.
> [5] summary ¶4. [6] summary ¶4, quoting Mountbatten as the record quotes
> him. [7] summary ¶1. [8] perspectives[0].narrative ¶2. [9]
> perspectives[1].narrative ¶4. [10] summary ¶4. [11]
> perspectives[0].narrative ¶4. [12] summary ¶4. [13]
> perspectives[0].narrative ¶4. [14] primary_source_excerpts[1]. [15]
> perspectives[0].narrative ¶3. [16] perspectives[0].sources. [17]
> perspectives[1].narrative ¶4. [18] perspectives[1].sources. [19]
> perspectives[2].narrative ¶6. [20] perspectives[2].sources. [21]
> perspectives[0].narrative ¶3. [22] primary_source_excerpts[0..3].

Four things the sample shows on purpose. The `{i}` mark: an interpretive
sentence, the historian's own, allowed only where it carries no numeral and
no quotation and sits in a paragraph that has cited sentences. The "Omits"
column is written as what the position's own sources do not address, which
is checkable against the ledger, not as an accusation. The verdicts are
mostly *untestable*, which is the honest result of a record that holds four
quotations and no award, and each untestable names the artifact that would
change it. And the two findings say nothing the arithmetic does not: the
first is date subtraction, the second a division, each with its rows, its
confidence and the record's own evidence against it, and neither is cited
anywhere in the argument as a fact. In the real thesis the rows would trace
to extract ids and `ledger.py recompute` would re-derive 73, 15 and 1.52
in CI; here they trace to YAML fields, so the sample stays unpublishable.

---

## 8. Data model

```
data/history/evidence/<slug>/
  ledger.yaml            # entries per 4c, plus positions[] (each with a verdict) and contested[]
  extracts/<src-id>.<locator>.txt
  analyses/<f-id>.yaml   # one derivation per finding, per 6b.2: rows, derive, confidence, against
data/history/theses/<slug>.md
```

A position record in `ledger.yaml` carries its verdict as data, not prose:

```yaml
positions:
  - id: british-administrative
    claim: The award was made under constraints the record states
    verdict: untestable         # supported | contradicted | qualified | untestable
    rests_on: [src-menon-1957, src-mansergh-1970]
    tested_against: []          # extract ids; required for every verdict but untestable
    would_settle: src-mansergh-1970 vol. XII   # required for untestable
    gap: no open archive holds the Boundary Commission's working papers   # Rule B, printed
```

Every Tier A entry carries `record_of` (Rule A): who produced it, from a
short controlled list per event (`colonial-administration`, `tribunal`,
`survivor-testimony`, `perpetrator-state`, `victor-press`, `neutral-body`,
and so on), and a verdict prints the `record_of` of every extract it rests
on. A non-English extract carries `language`, and any rendering beside it
carries `rendering: official | void`, its own locator or session and date,
and its parity result (4f).

The thesis is Markdown with a strict front matter and four extensions the
parser (`pipeline/history/thesis_format.py`, a sibling of `script_format.py`)
recognises:

```markdown
---
slug: srebrenica-genocide
status: draft | audited | published
audited_by: historiographic-auditor
audited_at: 2026-10-14
question: ...
claims: [..., ..., ...]
episode_marks:
  - { chapter: 0, where: hero }
  - { chapter: 4, where: argument-2 }
  - { chapter: 14, where: close }
---
## The record
...
## 1. The safe area
The Security Council declared Srebrenica a safe area on April 16, 1993.[^src-un-res-819 ¶1]
::: exhibit src-un-res-819 ¶1
::: episode chapter=4
The record carries no order from Zagreb to Potocari that day.{i}
## Findings
::: finding f-01
The interval is the record's, not the scholars'.{i}
## Historiography
::: position bosniak-legal
::: contested death-toll
```

`[^id locator]` is the citation marker; `::: exhibit` pulls an extract into
a numbered figure; `::: position` renders a ledger position with its verdict
and, for a contradiction, the extract beside the claim; `::: finding`
renders an analysis file with its method block; `::: contested` renders a
contested record;
`::: episode` pulls a chapter's lines from the script export that already
exists (`frontend/build-data/history-scripts/<slug>.json`). The exporter
(`export_thesis.py`) resolves every marker, numbers the notes, and writes
`frontend/build-data/history-theses/<slug>.json`; a thesis whose front
matter is not `published` is not exported, and the route renders the Hearing.

The script's DOCUMENT marker gains an optional extract id as a fourth field.
During transition H-01 accepts either the YAML excerpt or a ledger extract;
after the pilot it accepts only the ledger. The five YAML perspectives are
imported into `ledger.yaml` `positions[]` by Stage 3 and remain in the YAML
until the last event switches; parity between the two is a check, not a hope.

---

## 9. Rigor controls

New file `tests/test_history_thesis.py`, prefix **T** (the H prefix is taken
twice already, by the script gates and by `verify_sections.py`). All run in
`auto-merge-claude.yml` offline; T-05's network half runs in a new weekly
`history-ledger-verify.yml` that re-resolves identifiers and re-fetches free
copies, and rewrites `verified_at`.

| Check | Fails on | Prevents |
|---|---|---|
| T-01 | a citation marker whose id is not in the ledger, or whose locator names no stored extract when the sentence holds a quote or a number | a note that leads nowhere |
| T-02 | a sentence in The record, The argument, Historiography or Omits with no marker and no `{i}`; an `{i}` sentence carrying a numeral or a quotation; a paragraph that is all `{i}` | an unsourced fact dressed as narrative |
| T-03 | a numeral in a cited sentence absent from every cited extract as that digit string (each end of a range checked) | a wrong number (E-13's rule) |
| T-04 | a quoted span not a substring, under `_norm`, of a cited extract | an invented or improved quotation (H-01, E-14) |
| T-05 | a cited entry with `verified_by` empty, `verified_title` not matching, or a pinned locator on an entry with no `free_copy` | citing memory; citing what nobody can read |
| T-06 | a spelled-out year or cardinal outside a quotation or an episode block; an em or en dash; a kill-list word; the time-relative and hedge shapes `test_history_copy.py` already gates | transcript register; the dash ban; a stale count |
| T-07 | fewer than 3 positions; a position with no verified source by a holder; any position over twice the words of the shortest; every Tier B source from one region; every position resting on one language | tokenism, the victor's page |
| T-08 | a contested claim with fewer than 2 positions, or two positions sharing a source; a contested figure appearing in the body as a single value | false precision |
| T-09 | an exhibit missing creator or repository, date or "undated", licence, or locator; a stock domain (Unsplash, Pexels, Pixabay) anywhere in a thesis page's media | a photograph of the wrong century |
| T-10 | an episode mark whose chapter is not in the manifest or whose lines are not verbatim in the script; a section whose only content is an episode block | a seek to the wrong place; a page that needs the audio |
| T-11 | an Omits statement that names a source id the ledger holds | an omission that is not one |
| T-12 | a source entry from an excluded domain or kind (wiki, blog, AI, review-as-book), or a Tier C or D entry cited on a number or a quote in The record or The argument. In the historiography a Tier D entry may be quoted in its own words, because that is what a labelled position is; L-16 then requires a Tier A or B extract cited for what the position is (`described_by`) | the wrong tier on the wrong claim |
| T-13 | an event marked `published` below the bar in 4e (counts per tier, extracts, positions, regional entries, exhibits) | a thin thesis shipped as a full one |
| T-14 | the served JSON differing from the thesis (a port of `test_history_export_parity.py`) | a correction that never reached the page |
| T-15 | a position with no verdict, a verdict outside the four words, a Supported, Contradicted or Qualified verdict whose `tested_against` names no Tier A extract, an Untestable with no `would_settle`, or a Contradicted position rendered without its extract in the same block | a scholar repeated as settled; a contradiction the reader cannot see |
| T-16 | a finding with no `method`, a row whose `from` resolves to no extract, a `derive` value that `ledger.py recompute` does not reproduce, no `confidence`, an empty `against` with no statement of where the historian looked, or a finding id cited as a source anywhere in the argument | analysis that cannot be re-run; an inference dressed as a fact |
| T-17 | an event marked `published` with no finding, or with a finding whose statement carries a numeral absent from its own `derive` and `rows` | a thesis that only compiles; a number the working does not produce |
| T-18 | a Tier A entry with no `record_of`; a verdict whose marker does not print the producers of its `tested_against` extracts; a Contradicted verdict whose `tested_against` extracts all share one `record_of` side | one side's papers read as neutral truth (Rule A) |
| T-19 | a Contradicted verdict with an empty `tested_against`, or one whose sentence contains no artifact and only a statement of absence ("no document records", "the record holds nothing"); an Untestable verdict with no `would_settle`; a record section that does not name every `gap` the ledger lists | a gap read as disproof (Rule B) |
| T-20 | a non-English extract with no `language`; a rendering not labelled `official` or `void`; a `void` rendering whose set of names, numbers or dates is not exactly the original's (any member dropped, added or changed); a `void` rendering where an `official` parallel exists; a low-resource-language rendering with no stored back-translation and parity result; an English quotation in the thesis pinned to a `void` rendering rather than to the original | a translation passed off as a quotation; a number lost in translation |

Served, in `scripts/verify_sections.py`, **TH-01..TH-04** on a sampled
thesis page: one h1 and the question text present (not a shell); note count
in the HTML equals the marker count in the source and every note anchor
resolves; every exhibit carries a provenance line; every source link is
absolute and no dash anywhere in text or accessible names. `verify-headless`
gains one journey: a note, its sidenote, its source, the play glyph.

---

## 10. Visual and interaction design

Within the History skin: paper `#F2EDE0`, ink `#2C2418`, umber accent, aged
brass, the four voices, `--hist-measure: 36rem`.

**1440.** The named-line grid the Hearing already uses (`[rail] [text]
[rail]`), with the right rail given a job: sidenotes. A citation number in
the text (`<sup><a>`) is mirrored by its note in the right column, Inter at
`--text-sm`, the number in Barlow, aligned to the line that cites it,
hairline brass rule to the left. The left rail is `SpineRail` with thesis
stations: Question, Record, 1..n, Historiography, Disagreements, Omits, Notes,
Sources. Exhibits break to the full grid width inside a frame: 1px brass
border, Barlow eyebrow "Exhibit 3 · Judgment · ICJ, 26 February 2007",
document text in Plex Mono on `--hist-paper-deep`, provenance in Inter
`--text-xs` under a hairline. Contested blocks are tables with a hairline per
row and the position name in that position's `--hist-persp-*` colour beside
the name, never instead of it. Episode blocks: Playfair italic, brass left
rule, play glyph (44px, labelled "Listen from Scene 4, 4:12"), the reveal
pattern already in `history.css`.

**375.** One column, 16px gutters, no horizontal scroll. Sidenotes become
footnotes under Notes; the citation number links down, the note links back
with a labelled "return" link; tapping a number also opens the note inline as
a native `<details>` under the paragraph, so the reader is never sent to the
end and back. Exhibits keep the frame, lose the inset; a table scrolls inside
its frame, not the page. The rail becomes the 3px strip and readout the
Hearing already renders. Episode blocks are full width with the glyph above
the text.

**Print.** The sheet `brand.css` already defines: chrome gone, white paper,
`PrintMast` with the page's address. Sidenotes collapse to footnotes; every
source prints its free-copy URL in Plex Mono; exhibits keep their frames;
episode blocks print without the glyph, with "Episode, Scene 4" in the
eyebrow.

**Accessibility.** Heading order as in section 7. Notes are `<a
href="#n12" aria-describedby>` with `<sup>`; sidenotes `role="note"`; exhibits
`<figure>` with `<figcaption>` holding the provenance; contested blocks are
real `<table>` elements with `<th scope>`; the rail is `<nav aria-label>`;
the play glyph is a button with a text label; colour is never the only
carrier (every position is named). Focus rings from the system tokens. Reduced
motion: reveals instant, no scrolling on the reader's behalf.

**Reuse.** `SpineRail`, `HeroListen`, `Lightbox`, `PrintMast`, the Quote block
from `Hearing.tsx` (becomes the document exhibit), the end-matter Record block.
`PrimarySourceBlock` is the exhibit frame's ancestor and is absorbed.
`OmissionsPanel`'s hollow-bullet language survives in Omits.
`PerspectiveComparison` and `RedactedDossier` stay unmounted.

---

## 11. Production plan

**Phase 0, one session.** `ledger.py` bootstrap and its report over all 78,
committed as `docs/data/history-ledger.csv`. This turns section 2 into a
standing register. Also: strip the 242 stock media items from every event
(they fail the Hearing's own H-03 spirit too) and delete the 188 broken
identifiers rather than leave a wrong DOI on a live page. That is a Rule 1
fix on the current pages and does not wait for the thesis.

**Phase 1, pilot, three events.** `srebrenica-genocide` (Tier A documents
fetchable whole; tests the legal-document path), `partition-of-india`
(rich prose, broken identifiers; tests the monograph and free-readability
path), `mongol-conquest-baghdad` (a chronicle event whose record and script
already disagree on one line, per the 09-21 audit; tests translated primary
sources and the ancient-medieval thinness). Honest estimate per pilot event:
Stage 1 discovery one session, Stage 2 reading and pinning two to three
sessions, Stage 3 and 4 two sessions, Stage 5 one. Six to seven sessions
each; the tooling (parser, exporter, checks, page components, CSS) another
six alongside. **Roughly 25 to 30 agent sessions to the first three published
theses.**

**Phase 2, rollout.** Batches of six by era, richest ledgers first (the five
in section 4d), thinnest last. Expect three to four sessions per event once
the path is worn, so **78 events is on the order of 250 to 300 sessions**.
At one session a day that is most of a year; with parallel agents in the
workflow, a quarter. This is the number the CEO is deciding on.

**Transition.** Per-event switch on `status: published` in the thesis front
matter, read by the route at build. An event below that renders the Hearing
exactly as today. The masthead, hero, rail, player and end matter are shared,
so the two page kinds sit in one catalogue without a seam. `verify_sections`
samples both kinds. Nothing is deleted from the Hearing until the last event
switches; the class-parity test the open items already call for goes in
before any CSS is removed.

**Risks.** The free-readability rule will exclude some standard works and the
page must say so rather than cite around it. Fair-dealing exposure from
stored extracts (capped, cited, in a public repo) is a legal judgement, not
an engineering one. Reading and pinning is slow and is the only step that
cannot be automated; the temptation to let an agent "recall" a page number
is the exact failure the ledger exists to prevent, and T-05's `free_copy`
requirement is the only structural defence. The script and the ledger will
disagree on some lines (the 1941 census line already does); each disagreement
is a re-cut, and the episode mark for that chapter is withheld until it is
cut. Page length triples; the rail and the notes are what make it navigable,
and both are tested.

---

## 12. What I would refuse to build

- A thesis sentence with a fact and no note, however famous the fact.
- A citation to a work nobody on the team opened.
- A page number recalled rather than read.
- A stock photograph on a page that calls itself evidence.
- A single figure for a contested count.
- A "further reading" list of unverified works.
- A page that needs the episode to make sense, or an episode that needs the
  page.
- A scholar's claim printed without a verdict, or a verdict without its
  artifact.
- A position contradicted by the other side's papers alone, or by the
  absence of papers.
- A Void translation quoted as if a published English text said it.
- A finding without its rows, its confidence and the evidence against it.

---

## 13. Decisions for the CEO

**Decided by the CEO, 2026-09-24.** All eleven recommendations adopted, with
one change to decision 1: the 188 wrong or dead identifiers are **stripped
from their entries, not deleted with them**. The entry keeps its author and
title and is marked unverified until the ledger rebuild resolves it, so
nothing false stays linked and no real work is lost. Stock media: all 242
removed now. Extracts: 150 words, 5 per work, in the public repo. Pilot: all
three events, Srebrenica first; the 78-event rollout is decided on the
pilot's measured cost. Standing constraint: **$0, always**.

Each with a recommendation.

1. **Approve the ledger rebuild as the prerequisite**, knowing 72% of today's
   bibliography fails verification and 188 identifiers are wrong on live
   pages. *Recommend yes, and do Phase 0's deletions now, thesis or not.*
2. **Adopt the admissibility tiers and the free-readability rule as
   written**, accepting that some standard monographs will appear only in
   the historiography, unpinned. *Recommend yes; the page states the gap.*
3. **Extract storage for copyrighted works**: 150 words per extract, 5 per
   work, cited and locatored, in the public repo. *Recommend yes; if counsel
   says otherwise, hold extracts in build-data only and print the locator.*
4. **Remove all Unsplash and Pexels media from History**, 242 items, which
   thins galleries on the Hearing today. *Recommend yes, immediately.*
5. **The thesis voice**: impersonal, authored as Void News, no historian
   byline; but a historian's voice that argues, adjudicates and finds, not
   a compiler's that lists. *Amended 2026-09-24 on the CEO's direction that
   the engine is a historian (6b). The page tests each scholar against the
   artifacts and states a verdict; it derives its own findings from the
   primary record with the working shown; it still never asserts a fact on
   its own authority, and a named author would be a claim the record cannot
   support.*
6. **Positions replace the five perspectives on thesis pages**, with the
   YAML kept for the Hearing and the script until the last switch.
   *Recommend yes.*
7. **The pilot three**: Srebrenica, Partition, Mongol Baghdad. *Recommend
   as listed; Srebrenica first.*
8. **The pace**: 25 to 30 sessions to three published theses, 250 to 300 to
   78. *Recommend approving the pilot only, and deciding the rollout on the
   pilot's measured cost.*
9. **H-01 moves to the ledger** after the pilot, so the audio is gated on the
   same evidence as the page. *Recommend yes.*
10. **When the ledger contradicts a live episode** (as with the 1941 line),
    the thesis ships and the episode is flagged for a re-cut. *Recommend the
    page never waits on the audio.*
11. **The 78 episodes: keep, revise or redo** (section 14). *Recommend keep
    the format and the scripts, and re-cut each episode once, after its
    thesis passes, against the ledger. No full redo.*

---

## 14. Do the episodes need a revamp, or a redo?

Judged against the admissibility standard above, on the scripts as
committed, the manifest as served, and the gaps `docs/HISTORY-AUDIO.md` and
the episode register already record.

### 14a. What the scripts trace to

**Quotes.** Every line read in the document voice (536 across 78 scripts)
passes H-01, which means it exists in the event YAML. That is the whole
chain. The YAML's excerpts carry a URL in 12 of 297 cases and a page in none,
so **536 of 536 read-aloud quotes trace to the record and 0 trace to an
admissible, freely readable source with a locator.** They are not known to be
wrong. They are unverifiable in the sense section 4 defines, and T-04 plus
T-05 would fail all 78 scripts on their first run.

**Numbers.** A coarse converter (spelled cardinals and years back to digits,
accepting "6 million" as well as "6,000,000") checked 3,890 spoken numbers in
narrator lines against the digits each event's YAML carries: **158 (4.1%)
are not in the record, across 52 scripts.** Some of the residue is the
converter's ("a hundred years"), some is the year 2026 spoken in six scripts
as "still contested in twenty twenty six", which the 09-21 audit cut from the
YAML and never from the scripts, and some is real: Partition's "four hundred
million" people and its "census data from nineteen forty one" have no digit
behind them in the record. H-10 matches capitalised words and cannot see any
of this. Under T-03 the residue would be a hard failure, so a thesis-grade
audio gate needs a number check the scripts have never had.

**Structure and the known gaps.** All 78 pass H-01 to H-09; 39 predate
H-11 and were never checked against it; four rendered episodes run over the
15.0 minute ceiling (under the 15.5 gate); two have never been ear-checked;
the Mongol Baghdad script still carries the "some sources say" line the YAML
lost. None of this is a format failure. All of it is a script that was
written before a rule and never re-read under it.

### 14b. Is the drama any good

Yes, and this is the reason not to redo. Three scripts read whole for this
section (Partition, Srebrenica, the Black Death) do what the brief asks: a
cold open that refuses the received version with a particular ("A resolution
is a sentence. It cannot stop a bulldozer."), scenes that arrive late, a
document read in another voice with its speaker named first, a rest where a
lesser script would explain, five accounts each given its own case, and a
turn that names what each leaves out without averaging them. The Black
Death's turn ends on the Mongol account being "the widest and the least
certain", and says why. The register is consistent across the catalogue
because H-05, H-06 and H-09 make it structural. Rewriting 78 of these to
gain rigor would throw away the thing that took the longest to get right and
that the thesis page is not trying to be.

### 14c. Does the format still fit when the page is canonical

It fits better. Today the script is the only long form the event has, so it
carries a weight it was not built for: the numbers, the estimates, the
historiographic caveats. Once the thesis exists, the episode can be the
dramatisation the CEO named and nothing else, and every DOCUMENT it reads
points at an exhibit the listener can open. The one structural change the
new arrangement asks for is the fourth field on the DOCUMENT marker (the
extract id) and a number gate; the grammar, the voices, the rests and the
turn stay.

### 14d. Verdict: keep the format and the scripts, re-cut each episode once

Not a redo. Not a bulk revision either, because a revision against the YAML
would be a revision against the thing that is being replaced. **Targeted
re-cut, one episode at a time, only after that event's thesis passes its
gates**, in this order:

1. The thesis is published; its ledger holds the extracts.
2. The script is re-read against the ledger under T-03 (numbers), T-04 and
   T-05 (quotes to a held, free-readable extract), H-11 (the 39 that predate
   it), and the time-relative gate (the six that speak a present year). Each
   DOCUMENT marker gains its extract id. A line the ledger cannot carry is
   cut, not softened. The four over-length episodes are trimmed to 15.0 in
   the same pass.
3. The historian's work feeds the cut (6b). A finding may be spoken, in
   narration, only in the form the page states it and with its confidence
   said aloud ("by the record's own dates, fifteen days"), and the script
   marks it with the finding id so T-17's numeral rule applies to the
   spoken line as well. The turn gains the verdicts: where the page finds
   a position contradicted by an artifact, the turn says so and the
   document voice reads the artifact; where the page finds it untestable,
   the turn says the record does not hold what would settle it. An account
   still gets its case uninterrupted; the verdict comes after all five, as
   the turn always has.
4. Kokoro re-renders the episode, the promo is re-stitched, the manifest
   fingerprint changes, `tests/test_history_audio.py` re-verifies the served
   file, and the page's episode marks are re-aligned to the new chapters.

Expected change per script: a handful of lines, not a rewrite. The Partition
script loses or re-sources two numbers and gains four extract ids. Scripts
whose events fail the evidence bar are not touched at all: their episodes
keep running against the YAML, exactly as now, with the Hearing beside them.

**Cost, all $0.** Authoring: one agent session per episode for the re-read
and the cut, folded into Stage 4 of the thesis workflow, so it adds roughly
78 sessions across the rollout rather than a separate programme. Rendering:
`render-history-audio.yml` already fans the catalogue over a ten-wide matrix
at about ninety minutes for all 78 and roughly ten minutes for one, on
GitHub-hosted CPU; a re-cut episode is one manual dispatch. No paid voice,
no API.

**What the listener gains.** Every quote they hear can be opened on the page
at the passage it was read from. Every number they hear is a number the
record holds as digits. The six episodes that say "twenty twenty six" stop
ageing. The 39 pre-H-11 scripts say aloud which of their witnesses are
paraphrased or secondhand. And the chapter list names the exhibit, so a
listener on `/audio` can go from the voice to the document in one tap. What
they do not lose is the thing they came for: the drama is left alone.
