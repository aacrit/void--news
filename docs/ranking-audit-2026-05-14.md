# void --news Ranking Audit — 2026-05-14

Read-only audit. Source: live `story_clusters` rows for the world edition,
ordered by `rank_world` DESC (the column `HomeContent.tsx` uses for ordering).
Pulled 2026-05-14 ~13:00 UTC against `xryzskhgfuafyotrcdvj.supabase.co`. This
is the feed the homepage was serving from the **2026-05-13 13:20 UTC pipeline
run** (next run still mid-flight at audit time).

## 1. Live top 50 — what the homepage is serving

| # | Cat | Src | rank_world | Headline |
|---|---|---|---|---|
| 1  | politics    | 23 | 66.15 | Xi Warns Trump Over Taiwan as Beijing Summit Opens |
| 2  | conflict    | 26 | 60.94 | Trump and Xi Agree Iran Must Not Have Nukes, Hormuz Must Stay Open |
| 3  | politics    | 19 | 60.13 | ICC-Wanted Philippine Senator Dela Rosa Flees Senate After Gunfire |
| 4  | politics    | 12 | 56.00 | Cuba Exhausts Fuel Reserves as Blackouts Trigger Havana Protests |
| 5  | conflict    | 12 | 55.83 | US Energy Secretary Warns Iran Weeks Away From Weapons-Grade Uranium |
| 6  | conflict    |  9 | 54.04 | Russia Launches Over 800 Drones at Ukraine, Killing at Least Six |
| 7  | politics    | 12 | 51.87 | Israel's Coalition Files Knesset Dissolution Bill, Triggering Early Election |
| 8  | health      | 15 | 51.69 | Hantavirus Cruise Ship Outbreak Reaches Eleven Cases, Three Dead |
| 9  | politics    | 25 | 51.65 | South Carolina Republicans Block Plan to Eliminate Clyburn's House Seat |
| 10 | conflict    | 25 | 51.54 | Russia Launches Over 200 Drones; Ukraine Strikes Russian Energy Infrastructure |
| 11 | politics    | 14 | 50.15 | Mamdani Presents Balanced NYC Budget Amid Albany Bailout |
| 12 | politics    | 23 | 49.22 | Modi Cuts Motorcade Size; Indian Leaders Reduce Convoys Amid Fuel Call |
| 13 | conflict    | 27 | 49.03 | Israel Accuses New York Times of Undermining Hamas Sexual Violence Report |
| 14 | general     | 21 | 48.90 | King Charles Pledges Urgent Action Against Jew-Hatred in London |
| 15 | politics    | 21 | 48.68 | UK Health Secretary Wes Streeting Resigns, Challenging Starmer's Leadership |
| 16 | politics    | 12 | 48.66 | Trump Invites Xi to White House in September After Beijing Summit Talks |
| 17 | politics    | 20 | 48.20 | Starmer Rules Out Resignation Amid Labour Rebellion After Local Election Losses |
| 18 | conflict    | 10 | 47.64 | Belgian Workers Strike as EU Russian LNG Imports Hit Record High |
| 19 | conflict    |  8 | 46.86 | Gaza Ceasefire Stalls as Jerusalem Flag March Draws Thousands |
| 20 | conflict    | 17 | 45.84 | Russian Ship Sunk Near Spain Carried Nuclear Reactor Parts for North Korea |
| 21 | conflict    | 14 | 45.32 | NIA Arrests Narco-Terrorist Iqbal Singh After Extradition From Portugal |
| 22 | politics    | 10 | 43.66 | Nigerian Court Jails Ex-Power Minister Mamman 75 Years for Fraud |
| 23 | conflict    | 15 | 43.37 | Pope Leo Condemns European Military Spending and AI Warfare |
| 24 | science     | 15 | 42.60 | New York Man Convicted of Operating Chinese Secret Police Station |
| 25 | politics    | 16 | 42.56 | Gunfire Erupts in Philippine Senate Amid Attempted ICC Arrest |
| 26 | science     | 29 | 41.89 | IEA Warns Oil Stocks Drain at Record Pace Amid Hormuz Disruptions |
| 27 | health      | 33 | 41.65 | French Authorities Confine 1,700 on Cruise Ship After Suspected Norovirus Death |
| 28 | conflict    |  8 | 41.04 | Israel Strikes Lebanon as Third Round of Washington Talks Opens |
| 29 | politics    |  6 | 40.51 | Former Private Prison Executive Named Acting ICE Director |
| 30 | conflict    | 23 | 39.94 | US Nuclear Submarine Arrives Gibraltar as Washington Rejects Iran Proposal |
| 31 | conflict    | 11 | 39.58 | Croatia Authorises €1.7 Billion Defence Loan Under EU SAFE Instrument |
| 32 | politics    | 21 | 39.50 | Poland Crypto Scandal Unfolds Amid US Regulatory Warnings |
| 33 | environment | 11 | 39.37 | Federal High Court Dismisses ADA Suit Against INEC Registration |
| 34 | conflict    | 35 | 39.13 | Trump Arrives in China for Xi Summit Amid Iran War |
| 35 | politics    | 21 | 38.65 | Trump Aides Concede Iran Remark Damages GOP Affordability Messaging |
| 36 | science     | 13 | 38.54 | Musk Attorney Opens Cross-Examination of Altman in OpenAI Trial |
| 37 | environment | 18 | 38.52 | Kuwait Accuses Iran of Bubiyan Island Infiltration, Arrests IRGC Members |
| 38 | politics    |  8 | 38.39 | Carney Meets Artemis Crew, Hosts Global Progress Summit |
| 39 | politics    | 15 | 38.36 | Knesset Approves Special Tribunal for October 7 Attackers |
| 40 | science     |  7 | 38.33 | Uttar Pradesh Storm Kills Over 100, Chief Minister Directs Relief Efforts |
| 41 | politics    |  4 | 38.21 | Nearly 50 Kilograms Cocaine Seized at Piraeus Port |
| 42 | politics    | 27 | 38.14 | Nvidia CEO Invests in British AI Startup; US AI Regulation Stalls |
| 43 | economy     | 11 | 37.26 | African Leaders Advocate Stronger Intra-Continental Trade |
| 44 | politics    |  2 | 37.21 | Mexico and U.S. Deny CIA Ran Cartel Assassination Operations |
| 45 | conflict    | 16 | 36.56 | BRICS Foreign Ministers Meet in India as Iran Presses Bloc |
| 46 | health      |  4 | 36.15 | Indian Pharma Fuels West Africa's Opioid Epidemic, 'Zombie Drug' Crisis |
| 47 | science     |  4 | 36.11 | PMO Economist Expresses Concern Over Public Preparedness |
| 48 | conflict    | 12 | 35.87 | EC Approves EUR 2.62 Billion Romania Recovery Payment |
| 49 | conflict    | 18 | 35.31 | Estonia Passes Conscript Language Law; Germany Scraps Heating Mandate |
| 50 | science     | 11 | 34.94 | Union Cabinet Approves ₹37,500 Crore Coal Gasification Scheme |

## 2. Ground-truth consensus top-20 (May 13-14, 2026)

Built from Ground News (front page), Al Jazeera homepage (direct fetch), and
WebSearch corroboration spanning Reuters/AP/BBC/CNN/PBS/NPR/CBS/Bloomberg/WaPo/
Euronews/CNBC/Time/France 24/UN OHCHR. Reuters / AP / BBC / Guardian blocked
direct WebFetch, so the search-result aggregations stand in.

| # | Story | Outlets carrying as lead/near-lead |
|---|---|---|
| C1  | Trump-Xi Beijing summit (Taiwan warning, Hormuz, trade)            | AJ, CNN, NPR, CBS, NBC, Fox, CNBC, WaPo (universal) |
| C2  | Russia mass drone/missile barrage on Kyiv (1,400+, residential collapse) | AJ, NPR, CNN, Kyiv Post, Euronews, USNews, NewsTribune |
| C3  | Wes Streeting resigns as UK Health Sec; challenges Starmer         | AJ, CNN, CBS, PBS, ITV, HuffPost |
| C4  | Philippine senator Dela Rosa Senate gunfire / ICC warrant / escape | PBS, CNN, Time, NPR, AJ, France 24, CBS, Gulf News, Rappler |
| C5  | Cuba fuel runout, Havana blackouts, mass protests                  | Reuters, CNBC, France 24, Newsweek, CTV, Cyprus Mail, Arab News |
| C6  | Iran war / Hormuz / ceasefire on "life support"                    | CNN, Fox, PBS, CNBC (continuous coverage) |
| C7  | Sudan UN report — 880 civilians killed by drones Jan-Apr           | UN News, Bloomberg, AJ, Euronews, OHCHR, Defense Post |
| C8  | Hantavirus cruise outbreak (Andes virus, 11 cases, 3 dead)         | WHO, CDC, ECDC, CNN, CBS, Japan Times |
| C9  | Israeli strikes Lebanon highway (8 killed inc 2 children)          | NPR May-14 roundup, AJ |
| C10 | Pakistan Lakki Marwat bazaar bombing (9 killed)                    | WaPo, CGTN, Manila Times, Nation, Hill |
| C11 | Russia Sarmat ICBM test                                            | NPR/PBS May-13 roundups, Substack roundup |
| C12 | FDA Director Makary resigns                                        | May-13 roundup |
| C13 | Senate confirms Kevin Warsh as next Fed chair                      | May-14 roundup |
| C14 | Israel-Hamas / Gaza ceasefire status, Jerusalem flag march         | AJ, void --news carries |
| C15 | BRICS foreign ministers in India re: Iran                          | AJ explainer, void --news carries |
| C16 | King Charles antisemitism address in London                        | UK press, void --news carries |
| C17 | NYT-Israel-Hamas sexual violence report dispute                    | conservative press |
| C18 | UK Labour rebellion / local election losses fallout                | AJ, CNN, ITV |
| C19 | OpenAI / Altman / Musk trial cross-exam                            | tech press |
| C20 | IEA oil-stocks-draining warning (Hormuz knock-on)                  | wire services |

## 3. Per-slot scores (rubric: 0-100)

| # | Score | Rationale (60 chars headline + reason) |
|---|---|---|
| 1  | **95** | Xi-Trump Taiwan — consensus #1, ranked #1. Earned. |
| 2  | **92** | Trump-Xi Iran/Hormuz — same summit, sub-angle; ranked #2 is fair. |
| 3  | **88** | Philippine Senate gunfire — top-5 consensus (C4), ranked #3. Solid. |
| 4  | **80** | Cuba blackouts — top-10 consensus (C5), ranked #4 is slight over-weighting but defensible (24h-old breaking). |
| 5  | **70** | Iran uranium warning — adjacent to C6 but a narrow press-release angle; ranked above the bigger Ukraine drone barrage at #6. |
| 6  | **72** | "800 drones" Ukraine — this IS C2 (Kyiv barrage) but under-ranked vs consensus (should be top-3, sitting at #6). Source_count=9 dragged it down. |
| 7  | **65** | Knesset dissolution — real Israeli politics story, not in global consensus top-20 today. Defensible. |
| 8  | **78** | Hantavirus cruise — C8 consensus; #8 ranking is reasonable. |
| 9  | **45** | SC Republicans block Clyburn redistricting — domestic US politics, niche outside US edition; should not sit top-10 of world. |
| 10 | **75** | Second Russia/Ukraine cluster (200 drones + Ukraine counter-strike) — split of C2; over-coverage of same event in different cluster. |
| 11 | **35** | Mamdani NYC budget — hyper-local US story; does not belong in world top-15. |
| 12 | **55** | Modi motorcade — India-domestic context story; defensible but not consensus. |
| 13 | **58** | Israel/NYT sexual-violence dispute — real story (C17) but media-meta angle; rank too high. |
| 14 | **55** | King Charles antisemitism — UK ceremonial; runs in some consensus (C16). |
| 15 | **85** | Streeting resigns — C3 consensus story; ranked #15 is **under-ranked**; should be top-5. |
| 16 | **70** | Trump invites Xi to WH — sub-angle of C1, fair as a follow-on at #16. |
| 17 | **75** | Starmer refuses to resign — paired with #15 (C18); defensible #17. |
| 18 | **50** | Belgian strike / EU Russian LNG — niche European angle, real but not consensus. |
| 19 | **62** | Gaza ceasefire / Jerusalem flag march — C14; reasonable. |
| 20 | **65** | Russian ship sunk near Spain w/ NK reactor parts — distinctive scoop; not consensus but legit foreign policy. |
| 21 | **40** | India NIA narco-terrorist extradition — South-Asia regional, not world. |
| 22 | **40** | Nigeria ex-minister jailed — Africa regional, not consensus world. |
| 23 | **55** | Pope Leo on AI warfare — legitimate Vatican news, not top-20. |
| 24 | **50** | NY conviction of Chinese secret-police-station operator — US legal niche. **Mis-categorized as `science`.** |
| 25 | **30** | Duplicate of #3 — same Philippine Senate gunfire event re-clustered separately. **Cluster dedup failure.** |
| 26 | **70** | IEA oil-stocks warning — C20 consensus, src=29; defensibly under-ranked. |
| 27 | **65** | French cruise norovirus death — health, real, distinct from C8 but tied (src=33). |
| 28 | **70** | Israel strikes Lebanon — C9 consensus; under-ranked at #28 (should be top-15). |
| 29 | **45** | Acting ICE director appointment — US domestic. |
| 30 | **60** | US sub in Gibraltar / Iran proposal rejected — C6 sub-angle. |
| 31 | **45** | Croatia €1.7B defence loan — EU procurement, niche. |
| 32 | **40** | Poland crypto scandal — multi-topic blend cluster (US/Georgia/Poland), looks like a clustering artifact. |
| 33 | **20** | "Federal High Court Dismisses ADA Suit Against INEC" — **mis-categorized as `environment`**, Nigeria election law; near-zero global relevance at this rank. |
| 34 | **65** | Trump arrives in China — duplicate framing of C1/#1/#2/#16; src=35 is highest in feed but story is **triple-clustered** (1, 2, 16, 34 all same event). |
| 35 | **50** | Trump aides on Iran messaging — meta-political, src=21. |
| 36 | **55** | Altman / Musk OpenAI trial — C19, tech press only. |
| 37 | **65** | Kuwait accuses Iran (Bubiyan Island) — Gulf escalation, real, **mis-categorized as `environment`**. |
| 38 | **40** | Carney Artemis crew + Progress Summit — Canada-niche. |
| 39 | **60** | Knesset tribunal for Oct 7 attackers — Israel-domestic, real. |
| 40 | **70** | UP storm kills 100 — high-fatality natural disaster, **under-ranked**, src=7 only. **Mis-categorized as `science`**. |
| 41 | **25** | 50kg cocaine at Piraeus, src=2 — wire-blotter, doesn't deserve world top-50. |
| 42 | **50** | Nvidia / UK AI startup — business, src=27 inflated by tech-press piling on. |
| 43 | **45** | African leaders trade summit — communique-grade. |
| 44 | **35** | Mexico/US CIA-cartel denial, src=2 — single-source-claim-and-denial. |
| 45 | **60** | BRICS foreign ministers in India — C15; under-ranked. |
| 46 | **55** | Indian pharma West Africa opioid — investigative, real, src=4. |
| 47 | **15** | "PMO Economist Expresses Concern Over Public Preparedness" — vague, low-information headline, src=4. Should not be in top-50. |
| 48 | **40** | EC Romania €2.62B recovery — Brussels procedural. |
| 49 | **30** | "Estonia conscript language law; Germany scraps heating mandate" — **two unrelated stories fused into one cluster**. Clustering failure. |
| 50 | **35** | India coal gasification + Nagpur airport — cabinet announcement, India-domestic. |

## 4. Aggregate stats

| Stat | Value |
|---|---|
| Mean score      | **54.6** |
| Median score    | **55** |
| Std dev         | **18.4** |
| 90-100 (consensus + correct rank) | **1** (rank 1) |
| 70-89 (consensus, off rank)       | **17** |
| 50-69 (defensible, off consensus) | **18** |
| 30-49 (fluff/niche)               | **11** |
| 0-29 (broken)                     | **3** (ranks 25, 47, 33) |
| Slots scoring 70+ | **18 / 50 = 36%** |

### Top 3 misses (consensus story missing or buried in void --news top 50)

| # | Consensus story | Where in void --news? |
|---|---|---|
| M1 | **Sudan UN report — 880 civilians killed by drones (C7)** | **Not in top 50.** Major UN human-rights story carried by Bloomberg, AJ, Euronews, OHCHR. Total ranker blindspot. |
| M2 | **Pakistan Lakki Marwat bombing — 9 killed (C10)** | **Not in top 50.** WaPo, CGTN, Manila Times carried. South-Asia conflict event with hard casualty count. |
| M3 | **Senate confirms Kevin Warsh as Fed chair (C13)** | **Not in top 50.** Major US monetary-policy event. (FDA Makary resignation C12 also missing.) |

### Top 3 false positives (rank 1-10 with score < 50, OR top-15 with obvious defects)

| # | Slot | Why it shouldn't be there |
|---|---|---|
| F1 | **#9 SC Republicans block Clyburn redistricting (score 45)** | US-domestic redistricting at world rank 9 — over-weight on `source_count=25` for a hyper-local US story. |
| F2 | **#11 Mamdani NYC budget (score 35)** | Hyper-local US municipal politics at world rank 11. |
| F3 | **#13 Israel/NYT sexual-violence dispute (score 58)** | Media-meta angle ranked above the actual Israel-Lebanon strikes (#28) and Streeting resignation (#15). Conservative-press cluster gaming source_count. |

## 5. Root-cause hypotheses

### H1. Source_count dominates — US wire piles inflate parochial stories

Every false-positive above shares a pattern: large `source_count` from US outlets piling on a single US story (SC redistricting src=25; NYT-Hamas src=27; Mamdani src=14). The ranker reads "lots of sources = important." It can't see that 25 US sources covering a state-level redistricting fight is **less globally important** than 7 Indian sources covering a storm that killed 100 people (rank 40, UP storm). Likely culprit: `pipeline/ranker/importance_ranker.py` — `source_coverage_breadth` (20% weight) is not regionally normalised. **Fix surface:** divide source_count by edition-specific median, OR cap intra-cluster source_count contribution from the same country.

### H2. Cluster duplication of the Trump-Xi summit

Same event surfaces at ranks 1, 2, 16, 34 (and arguably 5, 30 as Iran-Hormuz subangles). That's **4-6 of the top 34 slots eaten by one event**. The deduplicator / story_cluster step is splitting "Xi warns Trump", "Trump-Xi agree on Hormuz", "Trump invites Xi to WH", "Trump arrives in China" into separate clusters when they should collapse into one umbrella story with sub-bullets. Likely culprit: `pipeline/clustering/deduplicator.py` or `story_cluster.py` — embedding similarity threshold too tight for same-event-different-angle. **Surface gain:** collapsing these four into one frees 3 top-30 slots for Sudan/Pakistan/Lebanon misses.

### H3. Category mis-routing — `science` and `environment` ate disaster + geopolitics

- #40 UP Storm (100 dead) tagged `science`
- #33 INEC court ruling tagged `environment` (it is election law)
- #37 Kuwait/IRGC infiltration tagged `environment`
- #24 NY/Chinese-secret-police-station tagged `science`

Likely culprit: `pipeline/categorizer/auto_categorize.py` keyword routing. Disasters with the word "storm" get pulled to weather/science; the word "island" pulled Bubiyan to environment. **Net effect:** ranker may apply a category-importance weight that downranks `science`/`environment` vs `politics`/`conflict`, pushing the UP storm to #40 when its fatality count alone justifies top-15.

### H4. Fused-but-unrelated clusters

#49 fuses Estonia conscript law with Germany heating mandate — two unrelated European stories. #32 fuses Poland crypto, US regulatory warnings, and Georgia. The clusterer is over-merging when stories share a regional tag + a generic noun (defence, regulation). Same `story_cluster.py` issue as H2 but the opposite failure mode — under-cluster the Trump-Xi material, over-cluster generic European policy.

### H5. The post-rerank Sonnet pass is not catching consensus gaps

`pipeline/rerank.py` (holistic re-rank) + the post-rerank Sonnet single-pass had the opportunity to look at the top 50 holistically and notice "Sudan UN report not here, Pakistan bombing not here." They didn't. Either the Sonnet prompt doesn't get a wide-enough candidate set (i.e. the rerank only sees the top-N already-ranked, not the bottom-100 candidates), or the prompt doesn't compare to external consensus desks. **This is the highest-leverage fix:** feed Sonnet the top 80 candidates AND a consensus brief ("today's wires lead with: A, B, C, D") and let it re-order with that anchor.

## 6. Honest verdict

void --news ranking is **directionally right on the #1 story** (Trump-Xi Taiwan — consensus #1, ranked #1) and roughly right on the Russia-Ukraine and Hormuz threads. But it's **leaking 3 of the top-15 slots to US-domestic stories** (Clyburn, Mamdani, NYT-Hamas) that no global newspaper desk would lead with on May 14, and **missing 3 of the top-20 consensus stories entirely** (Sudan, Pakistan bombing, Warsh Fed confirmation).

The single biggest structural bug is **H2 — Trump-Xi cluster splitting**: one event occupies 4-6 top-34 slots while three consensus stories don't make the top-50. Fix the deduplicator first; everything else is downstream tuning.

The single biggest **process** gap is **H5** — the Sonnet rerank doesn't anchor to external consensus. Even a one-line "today's wire desks lead with X, Y, Z" prefix in the rerank prompt would have caught the Sudan miss.
