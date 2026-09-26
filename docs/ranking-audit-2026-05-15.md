# void --news Ranking Audit — 2026-05-15 (post-fix)

> **Resolved 2026-05-18.** The 217-source badge regression and the over-merge symptoms documented below were fully addressed by the 9-commit clustering-hardening series on branch `claude/fix-clustering-regression-UzWY1`. Phase 5 sanity guard rewritten to `avg_articles_per_sub < 1.5`, Phase 2.6 anchor thresholds retuned (IDF 0.60→0.70, doc-freq 5%→2.5%, title-Jaccard 0.15→0.22), `MERGE_HARD_CEILING = 120` enforced across all 5 merge passes, ranker honors `mega_cluster_capped` with a 0.65x penalty, and `rerank.py` no longer writes `source_count` back to the DB (clustering owns it via Phase 5 cap + Phase 6 wire-aware collapse). Migrations 054 + 055 applied. Clustering validation suite expanded 31 → 33 fixtures (90.3% → 97.0%); new `validate-clustering.yml` CI gate blocks merge on CATASTROPHIC or WRONG-count regression. See `docs/PIPELINE-BRAIN.md` rev 7 and `CLAUDE.md` rev 44.

Read-only audit of the **first end-to-end pipeline run after c86883d**
(GitHub Actions run **25875159357 success**, completed ~19:30 UTC 2026-05-14).
Source: live `story_clusters` rows for the world edition, ordered by
`rank_world` DESC, pulled 2026-05-14 ~19:35 UTC against
`xryzskhgfuafyotrcdvj.supabase.co`. Scored against the 2026-05-14/15
consensus desk (Ground News, AJ, Reuters/AP/BBC/NPR/PBS/Bloomberg/CNN/CBS/WaPo,
UN OHCHR, Democracy Now headlines).

## Fixes shipped in c86883d

| # | Hypothesis | Implementation |
|---|---|---|
| H1 | US-wire pile-on inflated parochial US stories | `importance_ranker.py`: 0.80× penalty when >70% US sources AND <2 foreign country GPEs in cluster titles. `_geographic_impact` returns countries set, reused by penalty. |
| H2 | Trump-Xi splitting into 4-6 same-summit clusters | `story_cluster.py`: head-of-state + summit-token substring match in `merge_related_clusters`; `categorizer.py` adds `summit_diplomacy` as first EVENT_KEYWORDS group so the `MAX_SAME_EVENT=2` cap fires on summit subangles. |
| H3 | Disaster + geopolitics mis-categorised to `science`/`environment` | `categorize_article` pre-override: title regex for "killed/dead + N≥5" forces `conflict`. Extended title-override list with bombing, IRGC, narco-terror. |
| H4 | Country-disjoint fusions (Estonia + Germany; Poland + Georgia + US) | `story_cluster.py`: Phase-4 `split_disjoint_country_clusters` — title-only NER union-find, splits a cluster when exactly 2 groups of ≥2 articles emerge with pairwise-disjoint country sets. |

## 1. Live top 50 — what `'world' = ANY(sections)` returns now

| # | Cat | Src | rank_world | Headline |
|---|---|---|---|---|
|  1 | politics    | 18 | 64.30 | Cuba Exhausts Fuel Reserves as Blackouts Trigger Havana Protests |
|  2 | health      | 19 | 63.12 | Hantavirus Cruise Ship Outbreak Reaches Eleven Cases, Three Dead |
|  3 | politics    | 15 | 58.82 | Trump, Xi Meet in Beijing; Xi Warns on Taiwan, Trade |
|  4 | politics    | 20 | 58.55 | ICC-Wanted Philippine Senator Dela Rosa Flees Senate After Gunfire |
|  5 | conflict    | 13 | 56.81 | Saudi Arabia Floats Iran Non-Aggression Pact as Ships Seized Near Hormuz |
|  6 | conflict    | 10 | 54.95 | US Energy Secretary Warns Iran Weeks Away From Weapons-Grade Uranium |
|  7 | science     | 25 | 53.87 | Trump and Xi Agree Iran Must Not Have Nukes, Hormuz Must Stay Open |
|  8 | politics    |  8 | 52.74 | Wes Streeting Resigns from UK Cabinet, Positions to Challenge Starmer |
|  9 | conflict    | 15 | 52.19 | Israel Strikes Lebanon as Third Round of Washington Talks Opens |
| 10 | conflict    |  8 | 50.72 | Iraq Parliament Approves Zaidi Government as Country Seeks IMF Aid |
| 11 | politics    | 28 | 49.34 | UK Health Secretary Wes Streeting Resigns, Challenging Starmer's Leadership |
| 12 | economy     | 13 | 47.89 | Italy Diplomatic and Cultural Activity Spans Four Continents on May 14 |
| 13 | environment |  7 | 46.98 | Renewables Surpass Coal in Global Power for First Time in a Century |
| 14 | science     | 16 | 46.79 | Russia Launches Over 800 Drones at Ukraine, Killing at Least Six |
| 15 | conflict    | 19 | 46.36 | Pope Leo Condemns European Military Spending and AI Warfare at Rome University |
| 16 | conflict    |  7 | 46.22 | Israel and Lebanon Open Third Round of Washington Talks as Ceasefire Nears Expiry |
| 17 | conflict    | 12 | 46.13 | Belgian Workers Strike as EU Russian LNG Imports Hit Record High |
| 18 | science     | 15 | 45.91 | Poland Registers First Same-Sex Marriage Under EU Court Order |
| 19 | politics    |  7 | 45.75 | IMF Warns of Adverse Global Scenario Amid Regional Diplomatic Activity |
| 20 | science     | 18 | 45.40 | Musk Attorney Opens Cross-Examination of Altman in OpenAI Trial |
| 21 | politics    | 14 | 45.40 | Mamdani Presents Balanced NYC Budget Amid Albany Bailout and Western Union Opposition |
| 22 | politics    | 10 | 44.97 | Kremlin Announces Putin Will Visit China Very Soon, Preparations Complete |
| 23 | culture     | 12 | 44.46 | Cuba Grid Collapses as Energy Minister Declares Nation Out of Fuel |
| 24 | conflict    | 16 | 43.38 | EC Approves EUR 2.62 Billion Romania Recovery Payment Amid Economic Contraction |
| 25 | conflict    |  9 | 41.62 | (3rd LD) Seoul official cites low possibility of non-Iranian actor involvement in attack on S. Korean vessel |
| 26 | politics    | 18 | 41.35 | Netanyahu Announces Defamation Lawsuit Against New York Times Over Palestinian Abuse Article |
| 27 | science     | 19 | 40.89 | New York Man Convicted of Operating Chinese Secret Police Station |
| 28 | science     | 16 | 40.66 | Bank of Canada Minutes Flag Alert on Rapid Inflation Dynamics Shift |
| 29 | culture     | 28 | 40.59 | Xi Warns Trump Over Taiwan as Beijing Summit Opens |
| 30 | environment |  8 | 40.49 | Carney Unveils National Electricity Strategy to Double Canada's Grid by 2050 |
| 31 | conflict    |  6 | 40.10 | Russian attack on Kyiv: death toll rises to 12, including children, 46 more injured - Українська правда |
| 32 | politics    | 18 | 40.10 | Trump Invites Xi to White House in September After Beijing Summit Talks |
| 33 | politics    |  4 | 39.61 | South Africa, Uganda Appoint New Judges; India Courts Address Cases |
| 34 | health      | 15 | 39.58 | FDA Commissioner Makary Resigns, Kyle Diamantas Named Acting Chief |
| 35 | science     |  3 | 39.31 | Mexico and U.S. Deny CIA Ran Cartel Assassination Operations on Mexican Soil |
| 36 | politics    | 15 | 38.56 | Iran Accuses UAE of Military Role as London Protests Draw 4,000 Officers |
| 37 | science     | 13 | 38.42 | BRICS Foreign Ministers Meet in India as Iran Presses Bloc on US and Israel |
| 38 | conflict    | 24 | 38.27 | Trump Aides Concede Iran Remark Damages GOP Affordability Messaging |
| 39 | science     |  7 | 37.51 | Uttar Pradesh Storm Kills Over 100, Chief Minister Directs Relief Efforts |
| 40 | politics    | 11 | 37.12 | Macron Ends Africa Tour in Addis Ababa Amid Tigray Tensions and Paris Controversies |
| 41 | conflict    |  7 | 37.07 | Sam Cooper: Carney has 'scaled up' Trudeau-era foreign interference |
| 42 | politics    | 10 | 37.07 | Vance Travels to Maine to Promote Anti-Fraud Push Amid 2028 Speculation |
| 43 | politics    |  4 | 36.64 | Malaysia Condemns Norway Over Revoked Naval Missile System Export License |
| 44 | conflict    | 11 | 36.25 | Croatia Authorises €1.7 Billion Defence Loan Under EU SAFE Instrument |
| 45 | politics    |  2 | 36.20 | A Philippine senator wanted by the International Criminal Court flees from Senate |
| 46 | economy     | 25 | 35.72 | Xi Warns Trump on Taiwan as Leaders Meet in Beijing |
| 47 | economy     |  6 | 35.66 | Musk, OpenAI Lawyers Begin Closing Arguments in Landmark AI Future Trial |
| 48 | conflict    |  3 | 34.26 | EU, French Leaders Comment on Russia; US Lawmakers Discuss Ending Wars |
| 49 | politics    |  6 | 33.94 | Gov. Moore changes campaign managers with June primaries closing in - Baltimore Sun |
| 50 | politics    |  6 | 33.47 | Sabah Postpones Federal Border Agency Rollout Over Autonomy Concerns |

## 2. Consensus top-20 (rebuilt for 2026-05-14/15 UTC)

Built from Ground News, AJ homepage, Democracy Now headlines, WebSearch
aggregation of Reuters/AP/BBC/NPR/PBS/CNN/CBS/Bloomberg/WaPo/Euronews/Time/
CNBC/France 24, UN OHCHR press release archive.

| # | Story | Outlets carrying as lead/near-lead |
|---|---|---|
| C1  | Trump-Xi Beijing summit (Taiwan / Hormuz / Iran / trade)             | AJ, CNN, NPR, Democracy Now, CBS, NBC, Fox, CNBC, WaPo (universal) |
| C2  | **Senate confirms Kevin Warsh as Fed chair (54-45)**                 | WaPo, CNBC, NPR, AJ, CBS, Democracy Now, Time (universal) |
| C3  | Russia mass drone+missile barrage on Kyiv — 12 dead inc children     | NPR, CNN, Euronews, Українська правда, OPB, KPBS, GPB |
| C4  | Israel drone strikes on Lebanon highway — 12 killed inc 2 children   | AJ, NPR, WaPo, RTÉ, 1News, Business Standard, antiwar.com |
| C5  | Cuba fuel runout — "absolutely no fuel"; blackouts; Havana protests  | AJ, CP24, CNBC, Arab News, Jamaica Observer, CiberCuba |
| C6  | **Latvia PM Silina resigns over Ukraine drone incidents**            | AJ, WaPo, Bloomberg, Euronews, France 24, Irish Times, Boston Globe, USNews |
| C7  | Wes Streeting resigns as UK Health Sec; challenges Starmer           | AJ, CNN, CBS, PBS, ITV, HuffPost |
| C8  | Philippine senator Dela Rosa Senate gunfire / ICC warrant            | PBS, CNN, Time, NPR, AJ, France 24, CBS, Rappler |
| C9  | Hantavirus cruise outbreak (Andes virus, 11 cases, 3 dead, MV Hondius) | WHO, CDC, ECDC, CNN, CBS, NBC, Japan Times |
| C10 | UP storm kills 104+, India PM Modi, rescue ops                       | Daily Star, The Week, Pakistan Today, BusinessWorld, Kathmandu Post |
| C11 | **Sudan UN OHCHR: 880 civilians killed by drones Jan-Apr**           | UN News, OHCHR, Euronews, USNews, Bloomberg, AJ |
| C12 | **Senate rejects Iran War Powers Resolution for 7th time (49-50)**   | AJ, CBS, WaPo, Townhall, Hill, Democracy Now, Time |
| C13 | **Pakistan Lakki Marwat market bombing — 9 killed, 23 injured**      | AJ, WaPo, Washington Times, Express Tribune, Daily Pakistan |
| C14 | FDA Commissioner Makary resigns                                      | NPR, NBC, CBS, WaPo, CNBC, Democracy Now |
| C15 | Iraq parliament approves Zaidi government (partial)                  | AJ, Al Arabiya, National, Daily Sabah |
| C16 | Renewables overtake coal first time in century (IEA / Ember)         | Carbon Brief, Ember, IEA, Reccessary, Eco-Business |
| C17 | Gaza / Jerusalem Day march / Israeli nationalists                    | AJ, Democracy Now |
| C18 | Mexico-US CIA cartel assassination denial / Sheinbaum                | CNN, NPR, Democracy Now |
| C19 | OpenAI / Altman / Musk trial closing arguments                       | tech press |
| C20 | BRICS foreign ministers meet in India on Iran                        | AJ explainer |

**Three named misses from baseline tracked here:**
- C2 Warsh — **rank_world=65.76 (would be #1) but 'world' MISSING from sections** → invisible in feed.
- C11 Sudan — not in top 50 (still); main UN report cluster never built.
- C13 Pakistan bombing — not in top 50 (src=1 single article).

## 3. Per-slot scores (rubric: 0-100)

| # | Score | Δ-tag | Rationale |
|---|---|---|---|
|  1 | **85** | H1 | Cuba blackouts — C5 consensus; AJ/CNBC carry. Climbed +3 from baseline #4. Earned. |
|  2 | **78** | = | Hantavirus C9; rank #8→#2 is over-ranked but consensus story. |
|  3 | **95** | H2 | Trump-Xi Beijing — C1 consensus #1; correct rank at #3, behind two breakers. |
|  4 | **88** | = | Dela Rosa C8 — unchanged from baseline; correct. |
|  5 | **75** | NEW | Saudi Iran-NAP / Hormuz angle — consensus-adjacent (C1 subset). |
|  6 | **62** | = | US Energy Sec uranium press-release — slipped #5→#6, still narrow press angle. |
|  7 | **72** | H2 | Iran/Hormuz subangle of C1; H2-tagged but still a separate cluster — partial. |
|  8 | **88** | H1 | Streeting C7 consensus — **+7 climb (#15→#8) ✓ H1 fix as forecast**. |
|  9 | **90** | H3 | Israel-Lebanon C4 (12 dead inc 2 kids) — **+19 climb (#28→#9) ✓ H3 fix landed**. |
| 10 | **75** | NEW | Iraq Zaidi PM C15 — real, ~today; correct mid-pack. |
| 11 | **40** | ? | **DUPLICATE of #8** — Streeting cluster split (src=28 here vs src=8 at #8). Clustering recurrence. |
| 12 | **15** | NEW | Italy "four continents diplomatic activity" — communique-grade aggregate; doesn't belong top-15. |
| 13 | **60** | NEW | Renewables>coal C16 (IEA/Ember) — real, defensible. |
| 14 | **78** | = | Russia 800-drones (C3 precursor) — should be top-5 by consensus today; mid-pack. |
| 15 | **50** | = | Pope Leo AI warfare — ceremonial; same as baseline #23. |
| 16 | **35** | ? | Likely sub-cluster of #9 — clustering split returns. |
| 17 | **50** | = | Belgian LNG niche, real, not consensus. |
| 18 | **60** | NEW | Poland first same-sex marriage — real EU-court story; mis-cat as science. |
| 19 | **45** | NEW | IMF communique — vague aggregate. |
| 20 | **55** | = | OpenAI trial C19; mis-cat as science. |
| 21 | **35** | H1? | **Mamdani still here — H1 penalty fired (no foreign GPE in title) but rank only dropped #11→#21**. Penalty 0.80× insufficient: 14 src × 0.80 still beats high-quality 7-src global. |
| 22 | **60** | NEW | Putin China visit announced — real diplomatic story. |
| 23 | **30** | ? | **DUPLICATE of #1** — Cuba grid collapses cluster split (src=12 vs src=18 at #1). |
| 24 | **40** | = | Romania €2.62B procurement — same as baseline. |
| 25 | **35** | NEW | "(3rd LD) Seoul official..." — Korean vessel attack; **raw Yonhap wire prefix bleeding through to title**. |
| 26 | **45** | = | Netanyahu NYT defamation suit — same as baseline #13. |
| 27 | **50** | ? | NY Chinese police station conviction — mis-cat science still; **duplicate of #35** (same story). |
| 28 | **40** | NEW | BoC minutes — niche, mis-cat science. |
| 29 | **30** | H2-partial | **3rd Trump-Xi cluster** — H2 demoted (#1→#29) but didn't merge. Cluster gain shows in ranking, not in dedup. |
| 30 | **45** | NEW | Carney Canada electricity strategy — Canada-niche. |
| 31 | **75** | H3 | Kyiv attack May 14 C3 — under-ranked at #31 (should be top-5 today). |
| 32 | **25** | H2-partial | **4th Trump-Xi cluster** — should have merged. |
| 33 | **15** | NEW | "South Africa, Uganda Appoint New Judges; India Courts Address Cases" — meaningless three-country roundup. |
| 34 | **70** | NEW | FDA Makary C14 consensus — real, mid-rank OK. |
| 35 | **40** | = | Mexico/US CIA C18 same as baseline #44. |
| 36 | **50** | NEW | Iran-UAE accusations + London protests — fused unclearly. |
| 37 | **60** | = | BRICS in India C20; mid-rank OK. |
| 38 | **35** | = | Same as baseline #35. |
| 39 | **78** | H3 | UP storm C10 — climbed #40→#39 (only +1). **H3 fix did NOT catch this — title regex requires "killed/dead + N", but headline reads "Storm Kills Over 100"** — should match. Verify regex below. |
| 40 | **45** | NEW | Macron Africa tour — real but not consensus. |
| 41 | **15** | NEW | "Sam Cooper: Carney has 'scaled up' Trudeau-era foreign interference" — **opinion column byline format** in headline; should be filtered/marked as content_type=opinion. |
| 42 | **30** | NEW | Vance Maine + 2028 speculation. |
| 43 | **40** | NEW | Malaysia condemns Norway — niche bilateral. |
| 44 | **40** | = | Croatia €1.7B same as baseline #31. |
| 45 | **25** | ? | **DUPLICATE of #4** Philippine senator (src=2 vs src=20 at #4). |
| 46 | **20** | H2-partial | **5th Trump-Xi cluster** — H2 missed entirely. |
| 47 | **35** | ? | **DUPLICATE of #20** OpenAI closing arguments. |
| 48 | **15** | NEW | "EU, French Leaders Comment on Russia; US Lawmakers Discuss Ending Wars" — aggregated multi-story headline. |
| 49 | **10** | NEW | Maryland Gov Moore primary campaign — hyper-local US. **Should be filtered (no foreign GPE + US-only)**. |
| 50 | **30** | NEW | Sabah Malaysia federal border — regional, not world. |

## 4. Aggregate stats

| Stat | 2026-05-14 baseline | 2026-05-15 post-fix | Δ |
|---|---|---|---|
| Mean score        | 54.6 | **49.2** | **-5.4** ✗ |
| Median score      | 55   | **45.0** | **-10**  ✗ |
| Std dev           | 18.4 | **22.8** | +4.4 (wider spread) |
| 90-100 slots      | 1    | **2**    | +1 ✓ |
| 70-89 slots       | 17   | **11**   | -6 |
| 50-69 slots       | 18   | **10**   | -8 |
| 30-49 slots       | 11   | **19**   | +8 ✗ |
| 0-29 broken slots | **3** | **8**   | **+5** ✗ |
| Slots ≥70 (%)     | **36%** | **26%** | **-10pp** ✗ |

The fix landed on the **specific stories it targeted** (Streeting +7, Lebanon
+19) but the top 50 quality fell on average because **eight other defects**
that the c86883d fixes did NOT target (sections/world tag, cluster splitting,
duplicate clusters, opinion-byline headlines, wire-prefix bleed, aggregated
multi-story rollups) became more visible once the previous noise (5 Beijing
clusters at the top) cleared.

## 5. Target hit/miss table

| # | Target | Result | Status |
|---|---|---|---|
| T1 | Mean score ≥ 70 | 49.2 | **MISS** (-20.8) |
| T2 | Slots ≥70 cover ≥60% | 26% | **MISS** (-34pp) |
| T3 | Zero broken slots <30 | 8 broken | **MISS** (5 net worse) |
| T4 | ≥2 of 3 named misses in top 30 (Sudan / Pakistan / Warsh) | 0 of 3 (Warsh has rank_world=65.76 but tag missing; Sudan + Pakistan absent) | **MISS** |
| T5 | Beijing summit clusters ≤ 2 in top 50 | **7 clusters** (#3, #5 Hormuz, #7, #29, #32, #46, #22 Putin) — strictly Xi/Beijing/summit = 5 | **MISS** |

Zero of five numerical targets hit.

## 6. Per-cause attribution

| Cause | Slots tagged | Net effect | Verdict |
|---|---|---|---|
| **H1** US-wire pile-on penalty | Streeting #8 (+7) | Streeting climbed correctly; SC redistricting fell off (no longer in top 50 ✓); Mamdani only fell #11→#21 (penalty too weak: 0.80× × 14 src still beats 7-src global) | Partial ✓ |
| **H2** Summit clustering merge | Trump-Xi/Beijing reduced from 4-6 in top 34 baseline to **5 in top 46 post-fix** | Ranking weights demoted duplicates (good), but `merge_related_clusters` did not actually merge them. The post-clustering rank step is doing the work; the H2 dedup logic isn't firing. | Failed (mechanism wrong, but symptom partially treated by ranker demotion) |
| **H3** Disaster mis-category | Lebanon +19 (#28→#9) ✓; **UP storm only +1** (#40→#39) | Lebanon was the test case → worked. UP storm title is "Storm Kills Over 100" — the regex `killed/dead + N≥5` should match "Kills Over 100" but `Kills` vs `killed/dead` is the issue. Regex doesn't include verb conjugation `Kills`. Quick fix: add `(?:kill\w*|dead|dies)`. | Half-landed |
| **H4** Country-disjoint split | Estonia/Germany cluster from baseline #49 is gone (split or dropped); Poland crypto fusion from baseline #32 gone | No visible mis-fusion of unrelated EU stories in new top 50. **H4 appears clean.** | ✓ |
| **NEW defect 1: sections-world gap** | Warsh (rank_world=65.76, would be #1), wholesale prices, Murdaugh, Medicare freeze — **all carry strong rank_world but missing 'world' tag** | World feed is filtering out the highest-scoring globally-relevant US stories because `sections` is built from article origins, not from importance score. Single-edition stories with high cross-coverage are invisible. | New finding |
| **NEW defect 2: duplicate clusters** | Streeting #8+#11; Cuba #1+#23; OpenAI #20+#47; Phil senator #4+#45; Beijing summit ×5 | Same event surfaces twice with different titles. The H2 fix targeted Trump-Xi specifically; broader same-event-multiple-clusters problem persists. | New finding |
| **NEW defect 3: garbage headlines** | "(3rd LD) Seoul..." #25; "Sam Cooper:" #41; "South Africa, Uganda Appoint New Judges; India..." #33; "EU, French Leaders Comment..." #48; "Italy ... Spans Four Continents" #12 | Wire-service prefixes, opinion bylines, and multi-story aggregated headlines bleed into world top-50 with high-enough source counts. | New finding |

## 7. Residual issues + recommended next iteration

### Issue A: `'world'` tag is silently absent from biggest stories

`pipeline/main.py` Step 8 (~line 2284-2293) builds `sections` as the union of
`art.get("section", ...)` across cluster articles. A story whose articles all
come from `us`/`europe`/`south-asia` sources never gets tagged `world` even
if its `rank_world` is the highest in the database. **Warsh confirmation
(`rank_world=65.76`) would be the #1 story** but is invisible in the world
feed because its 15 articles all came from US/EU sources.

**Recommended fix** (~3 lines in `main.py`):
```python
# After building all_sections from article sections, force-add 'world'
# when the story crosses an importance threshold OR spans 2+ regional editions.
if len(all_sections) >= 2 and "world" not in all_sections:
    all_sections.append("world")
if cluster.get("rank_world", 0) >= 50 and "world" not in all_sections:
    all_sections.append("world")
```

This is **the single highest-leverage change** for next iteration. It does not
require any retraining or scoring change — purely tag membership. Validation
suite would not regress (no fixture depends on world tag absence).

### Issue B: H1 penalty 0.80× is too weak for Mamdani-class stories

Mamdani at src=14 with H1 penalty: 14×0.80 = 11.2 effective sources, still
ranks #21. The penalty needs to be **0.60× when 100% US sources AND zero
foreign GPEs in title**. Current rule is 0.80× when >70% US AND <2 foreign
GPEs — too permissive on US-only stories. **Targeted file**:
`pipeline/ranker/importance_ranker.py`, the `_us_wire_penalty` block.

### Issue C: H2 merge logic isn't firing; ranker demotion masking failure

The smoke test in commit message said "Trump-Xi consolidated from 4 top-50
slots to 1." Today's production data shows **5 separate Beijing summit
clusters in the top 46** (#3, #7, #29, #32, #46) plus a Putin-China cluster
at #22. The `merge_related_clusters` head-of-state+summit-token logic isn't
triggering during the production clustering phase. The demotion that's
happening on duplicates 4-5 (`claim_consensus` cross-edition demotion) is
masking the failure — duplicates 4-5 ranked at 35-40, not at the top.

**Verification needed**: log how many cluster pairs the new
`_HEAD_OF_STATE_NAMES + _SUMMIT_TOKENS` rule actually merged in production.
A counter in `merge_related_clusters` printed to stdout would surface
this on the next run.

### Issue D: UP storm regex missed verb conjugation

H3 rule: title regex match for "killed/dead + N≥5". UP storm title is
**"Storm Kills Over 100"**. Verb `Kills` not in `(killed|dead|dies)` set.
Need `(?:kill\w*|dead|dies|fatalit\w*)`. One-line edit in
`pipeline/categorizer/auto_categorize.py`.

### Issue E: Garbage-headline filter not in pipeline

Five low-score slots (#12, #25, #33, #41, #48) are pure formatting/aggregation
defects, not ranking errors. Patterns observable:
- Wire prefixes: `^\(\d+(?:st|nd|rd|th) LD\)` (Yonhap) → strip on ingest
- Opinion column bylines: `^[A-Z][a-z]+ [A-Z][a-z]+:\s` (e.g. "Sam Cooper:") → tag content_type=opinion
- Multi-story headline aggregations: 2+ semicolons OR 2+ disjoint country names + ";" → demote

**Recommended next iteration**:
1. Tag `world` membership by rank threshold + cross-edition cardinality (highest leverage).
2. Sharpen H1 penalty to 0.60× when zero foreign GPE.
3. Fix H3 regex to include `kill\w*` verb conjugation.
4. Garbage-headline ingestion filter (5 broken slots → 0).
5. Logging counter on `merge_related_clusters` to verify H2 firing.

### Honest verdict on c86883d

The fixes landed on **the exact stories used as test cases** (Streeting
climbed, Lebanon climbed, redistricting/SC dropped). But the patch did not
generalise:

- **H1 worked for Streeting** because the headline contains "UK" (foreign
  GPE), letting the penalty fall off cleanly. It **partially worked** for
  Mamdani (dropped #11→#21) because the title carries no foreign GPE, but
  the 0.80× penalty wasn't strong enough to expel a 14-source story.
- **H2 missed structurally** — the merge logic doesn't run in production
  the way the dry-run suggested. The ranker's `claim_consensus`
  cross-edition demotion is doing the work the dedup should have done.
- **H3 worked for Lebanon** (matching "Israel Strikes Lebanon" with
  cluster bodies that contain "killed/dead + 12"). It **missed UP storm**
  because the title's verb is "Kills" (present-tense), and the regex
  pattern in the commit description only mentioned past-tense forms.
- **H4 appears clean** — no fused-country false-positives observed.

The bigger lesson: **the post-fix top 50 is, on aggregate, worse-scoring
than the pre-fix top 50** (mean 49.2 vs 54.6), even though the targeted
stories improved. The reason is that clearing the Beijing-summit logjam
at ranks 1-2 made room for previously-hidden defects to surface — Italy
diplomatic aggregate at #12, Korean wire prefix at #25, opinion byline
at #41, governor primary at #49. Quality control needs **breadth of
filters** before the next round of weight-tuning will show net wins.

**The single highest-leverage fix for the next iteration**: tag `world`
on the `sections` field based on `rank_world` threshold + cross-edition
cardinality. Warsh confirmation (the entire #C2 story of May 14) is
sitting at `rank_world=65.76` — would be the unambiguous #1 in the feed —
but is silently filtered out of the world section by membership rules
designed for a different purpose.
