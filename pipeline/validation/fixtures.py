"""
Ground-truth test articles for bias engine validation.

28 articles across 8 categories (26 original + 2 added for signal coverage). Each article has:
- Synthetic text (100-300 words) tuned to trigger the right NLP signals
- Source metadata (outlet name, slug, tier, political_lean_baseline)
- Expected score ranges per axis (tolerance bands)
- Human rationale for each expectation
- Cross-reference data (AllSides rating, category)

Categories:
  1. wire        — AP, Reuters hard news
  2. opinion     — NYT opinion, Fox opinion
  3. investigative — ProPublica, Bellingcat
  4. partisan_left — Jacobin, The Intercept
  5. partisan_right — Breitbart, Daily Wire
  6. state_media  — RT, CGTN
  7. breaking     — Wire services, short text
  8. analysis     — NPR, The Economist
"""

FIXTURES: list[dict] = [

    # ==========================================================================
    # CATEGORY 1: WIRE / HARD NEWS
    # ==========================================================================

    {
        "id": "ap-fed-rate-2026",
        "name": "AP Wire - Fed Rate Decision",
        "category": "wire",
        "article": {
            "title": "Federal Reserve holds rates steady, signals June cut",
            "full_text": (
                "Federal Reserve Chair Jerome Powell said Tuesday that the central bank will "
                "maintain current interest rates at their existing level. The decision, announced "
                "after a two-day policy meeting, was supported by 10 of 12 voting members on the "
                "Federal Open Market Committee. According to data from the Bureau of Labor "
                "Statistics, inflation fell to 2.1% in February, down from 2.4% in January. "
                "'We are committed to our 2% inflation target,' Powell told reporters at a press "
                "conference at Fed headquarters. 'The labor market remains resilient.' The Fed's "
                "updated dot plot suggests two rate cuts in 2026, with the first expected in June, "
                "according to the committee's median projection. Treasury yields declined following "
                "the announcement. Economists surveyed by Reuters had expected the Fed to hold "
                "rates steady. The federal funds rate remains in the 4.25% to 4.50% target range. "
                "The next policy meeting is scheduled for May 6-7."
            ),
            "summary": "",
            "url": "https://apnews.com/article/fed-rate-decision-2026",
            "section": "business",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "ap-news",
            "tier": "us_major",
            "name": "Associated Press",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [40, 60], "rationale": "Wire service center baseline; no partisan vocabulary; economic terminology is neutral"},
            "sens":    {"range": [5, 25],  "rationale": "Measured attribution-heavy language; no urgency words; no superlatives"},
            "opinion": {"range": [0, 25],  "rationale": "Heavy attribution density (said, told, according to); no first-person pronouns; factual reporting"},
            "rigor":   {"range": [55, 100], "rationale": "Named sources (Powell), org citations (BLS, FOMC), data points (2.1%, 4.25-4.50%), direct quotes"},
            "framing": {"range": [0, 25],  "rationale": "Neutral synonym choices; balanced sourcing; no charged synonyms"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    {
        "id": "reuters-ecb-2026",
        "name": "Reuters Wire - ECB Decision",
        "category": "wire",
        "article": {
            "title": "ECB holds rates, signals June cut as inflation eases",
            "full_text": (
                "The European Central Bank held interest rates steady on Thursday, as widely "
                "expected by analysts, while signaling it could cut borrowing costs in June if "
                "inflation continues to ease toward its target. President Christine Lagarde said "
                "the ECB's governing council was 'data-dependent' and would assess incoming "
                "economic indicators before taking any action. Eurozone inflation stood at 2.4% "
                "in March, down from 2.6% in February, according to Eurostat data released "
                "Wednesday. The deposit facility rate remains at 3.75%. Bond markets rallied on "
                "the announcement, with German 10-year yields falling 8 basis points to 2.31%. "
                "The euro strengthened 0.3% against the dollar following the statement. "
                "Lagarde said the council reached its decision unanimously and would meet again "
                "in June to reassess conditions. 'We are not pre-committing to any particular "
                "rate path,' she told reporters. The IMF projects eurozone growth of 1.5% for "
                "2026, according to its April World Economic Outlook."
            ),
            "summary": "",
            "url": "https://reuters.com/markets/ecb-holds-rates-2026",
            "section": "markets",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "reuters",
            "tier": "us_major",
            "name": "Reuters",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [40, 60], "rationale": "Wire service center baseline; entirely economic content; no partisan vocabulary"},
            "sens":    {"range": [5, 20],  "rationale": "Measured factual language; technical financial content; attribution-dense"},
            "opinion": {"range": [0, 25],  "rationale": "Dense attribution (said, told, according to, reported); technical analysis; no subjectivity"},
            "rigor":   {"range": [50, 100], "rationale": "Named sources (Lagarde), org citations (Eurostat, IMF), multiple data points, direct quotes"},
            "framing": {"range": [0, 25],  "rationale": "Neutral financial terminology; no charged synonyms; balanced perspective"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    {
        "id": "ap-ukraine-diplomacy-2026",
        "name": "AP Wire - Ukraine Ceasefire Talks",
        "category": "wire",
        "article": {
            "title": "Ukraine and Russia resume ceasefire talks in Geneva",
            "full_text": (
                "Diplomatic representatives from Ukraine and Russia resumed ceasefire negotiations "
                "in Geneva on Monday under the auspices of the United Nations, officials confirmed. "
                "UN Special Envoy Martin Griffiths said both delegations agreed to a preliminary "
                "framework for prisoner exchanges involving approximately 2,400 individuals. "
                "Ukrainian Foreign Minister Dmytro Kuleba told reporters the talks were 'cautiously "
                "productive' but that significant gaps remained on territorial questions. "
                "Russia's chief negotiator, Deputy Foreign Minister Mikhail Galuzin, confirmed "
                "participation but declined to comment on specific proposals. The United States, "
                "the European Union, and China each sent observers to the session, according to "
                "UN spokeswoman Stephane Dujarric. The talks are the first direct contact between "
                "the two governments since negotiations collapsed in April 2022. More than 10,000 "
                "civilians have been killed in the conflict since February 2022, according to UN "
                "human rights monitors. A follow-up session is scheduled for next month."
            ),
            "summary": "",
            "url": "https://apnews.com/article/ukraine-ceasefire-talks-2026",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "ap-news",
            "tier": "us_major",
            "name": "Associated Press",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [40, 60], "rationale": "Neutral wire service reporting; named sources from both sides; no partisan vocabulary"},
            "sens":    {"range": [5, 25],  "rationale": "Serious but measured tone; no clickbait; attribution-heavy"},
            "opinion": {"range": [0, 25],  "rationale": "Dense attribution; factual reporting style; no first-person or opinion markers"},
            "rigor":   {"range": [55, 100], "rationale": "Multiple named sources, UN data, precise casualty figures, org citations"},
            "framing": {"range": [0, 30],  "rationale": "Balanced representation of both parties; neutral vocabulary; 'killed' at intensity=1 is expected"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    # ==========================================================================
    # CATEGORY 2: OPINION / EDITORIAL
    # ==========================================================================

    {
        "id": "nyt-opinion-gun-2026",
        "name": "NYT Opinion - Gun Control",
        "category": "opinion",
        "article": {
            "title": "Opinion: We Must Ban Assault Weapons Now",
            "full_text": (
                "We have waited long enough. The epidemic of gun violence in America demands "
                "immediate action, and Congress must act before more children die in our schools. "
                "I believe the evidence is overwhelming: assault-style weapons have no place in "
                "civilian hands. The data shows that mass shootings have increased dramatically "
                "since the assault weapons ban expired in 2004. Common sense gun laws would "
                "protect our communities without infringing on the rights of responsible hunters "
                "and sport shooters. We should not allow the gun lobby to continue blocking "
                "reforms that the vast majority of Americans support. Gun violence is a public "
                "health crisis that we as a society must address urgently. It is wrong to "
                "prioritize the profits of gun manufacturers over the safety of our children. "
                "Admittedly, gun legislation is politically difficult, but the moral case is "
                "clear. I would argue that our failure to act is itself a form of complicity. "
                "The time has come to protect working families from the weapons of war that "
                "flood our streets."
            ),
            "summary": "",
            "url": "https://nytimes.com/opinion/assault-weapons-ban-2026",
            "section": "opinion",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "nyt",
            "tier": "us_major",
            "name": "The New York Times",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [0, 40],   "rationale": "Strong left-coded vocabulary: assault-style weapons, gun violence epidemic, common sense gun laws, weapons of war, working families"},
            "sens":    {"range": [20, 60],  "rationale": "Urgent emotional appeals; some hyperbolic framing; 'epidemic', 'flood'"},
            "opinion": {"range": [65, 100], "rationale": "First-person pronouns (we, I, our, my); modal language (must, should); opinion URL/section marker; hedging (admittedly, I would argue)"},
            "rigor":   {"range": [10, 45],  "rationale": "Opinion piece; weak attribution; emotional arguments; us_major baseline partially compensates"},
            "framing": {"range": [20, 65],  "rationale": "Charged synonyms (flood, weapons of war); one-sided sourcing; headline opinion marker"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "fox-opinion-immigration-2026",
        "name": "Fox Opinion - Immigration",
        "category": "opinion",
        "article": {
            "title": "The Radical Left's Border Catastrophe Is Destroying America",
            "full_text": (
                "The radical left's dangerous open border agenda is destroying America. Illegal "
                "aliens are flooding our communities while Democrats refuse to enforce the law. "
                "This socialist takeover of our immigration system must be stopped before it's "
                "too late. The Biden administration's catastrophic failure at the border has "
                "unleashed chaos across American cities and towns. Real Americans are suffering "
                "while the liberal elite celebrates open borders. We must wake up America and "
                "take back our country from those who want to destroy our way of life. The "
                "radical agenda being pushed by the far-left is not only reckless but dangerous. "
                "Government handouts to illegal aliens are costing hard-working American "
                "taxpayers billions. Mainstream media refuses to cover the true scale of this "
                "crisis. Our children will inherit the catastrophic consequences if we fail to "
                "act. America first must mean something — before it's too late for our great "
                "nation. The freedom of real Americans is under attack."
            ),
            "summary": "",
            "url": "https://foxnews.com/opinion/radical-left-border-catastrophe",
            "section": "opinion",
        },
        "source": {
            "political_lean_baseline": "right",
            "slug": "fox-news",
            "tier": "us_major",
            "name": "Fox News",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [70, 100], "rationale": "Dense right-coded vocabulary: radical left, illegal aliens, socialist takeover, open borders, real Americans, liberal elite, america first"},
            "sens":    {"range": [50, 100], "rationale": "Multiple PARTISAN_ATTACK_PHRASES; catastrophe, destroying, flooding; emotional demonization language"},
            "opinion": {"range": [45, 100], "rationale": "Opinion URL/section (floor 70); modal language (must); partisan attack phrases signal absence of reporting voice; zero attribution"},
            "rigor":   {"range": [0, 40],  "rationale": "Zero named sources; no data; pure editorial attack; low-credibility slug gets reduced baseline"},
            "framing": {"range": [30, 100], "rationale": "Flood/swarm synonyms; illegal alien; one-sided sourcing; demonization framing"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    {
        "id": "jacobin-opinion-labor-2026",
        "name": "Jacobin Opinion - Workers' Rights",
        "category": "opinion",
        "article": {
            "title": "The Billionaire Class Is Waging War on Workers",
            "full_text": (
                "We are witnessing the most brazen attack on workers' rights in a generation. "
                "The billionaire class, enabled by the corporate capture of our political "
                "institutions, is systematically dismantling the gains of the labor movement. "
                "Income inequality has reached obscene levels while workers face wage theft, "
                "union busting, and relentless corporate greed. The Democratic socialism we "
                "need requires collective action and solidarity among working people. I believe "
                "the path forward is clear: we must tax the rich, expand labor rights, and "
                "achieve the wealth redistribution that justice demands. The billionaire tax "
                "that advocates argue for would fund universal healthcare and free higher "
                "education. Corporate accountability is not radical — it is common sense. "
                "The working class must seize this moment before late capitalism fully "
                "consolidates its grip on our democracy. Enough is enough: it is time to "
                "fight back against the forces of wealth inequality and corporate greed."
            ),
            "summary": "",
            "url": "https://jacobin.com/opinion/billionaire-class-workers-rights",
            "section": "opinion",
        },
        "source": {
            "political_lean_baseline": "left",
            "slug": "jacobin",
            "tier": "independent",
            "name": "Jacobin",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [0, 30],   "rationale": "Dense left-coded vocabulary: billionaire class, workers' rights, income inequality, wage theft, union busting, corporate greed, democratic socialism, tax the rich, wealth redistribution, late capitalism"},
            "sens":    {"range": [8, 65],   "rationale": "Engine: advocacy vocab not in PARTISAN_ATTACK_PHRASES; TextBlob subjectivity carries it; floor of 8 for any real text"},
            "opinion": {"range": [40, 100], "rationale": "First-person pronouns (we, I, our); strong modal language (must, we must); opinion section URL; hedging (I believe); metadata floor at 70"},
            "rigor":   {"range": [5, 40],   "rationale": "Opinion piece; minimal attribution; advocacy language; independent baseline lower than us_major"},
            "framing": {"range": [8, 70],   "rationale": "One-sided sourcing (pro-worker only); charged synonyms; absolutist framing; short text reduces density signals"},
        },
        "cross_ref": {
            "allsides": "left",
        },
    },

    # ==========================================================================
    # CATEGORY 3: INVESTIGATIVE
    # ==========================================================================

    {
        "id": "propublica-medicare-2026",
        "name": "ProPublica Investigation - Medicare Overcharges",
        "category": "investigative",
        "article": {
            "title": "Investigation: Drug Companies Overcharged Medicare by $4.2 Billion",
            "full_text": (
                "A six-month investigation by ProPublica found that three major pharmaceutical "
                "companies systematically overcharged Medicare by an average of 340% for commonly "
                "prescribed medications over a four-year period. Internal documents obtained "
                "through FOIA requests show executives were aware of the pricing discrepancies "
                "as early as 2020. A review of more than 80,000 billing records indicates the "
                "pattern was consistent across multiple drug categories. Dr. Maria Santos, former "
                "FDA Commissioner, called the findings 'deeply troubling' in an interview. "
                "According to CMS data, the overcharges cost taxpayers $4.2 billion between "
                "2020 and 2024. Records show that internal emails discussed strategies for "
                "avoiding detection by federal auditors. Representatives from two of the three "
                "companies declined to comment; a spokesperson for the third said the company "
                "'disputes the methodology.' Documents obtained from a Senate Finance Committee "
                "investigation corroborate the findings. The Senate Finance Committee said it "
                "would open its own review. ProPublica's analysis of the data used actuarial "
                "methods reviewed by three independent health economists."
            ),
            "summary": "",
            "url": "https://propublica.org/article/drug-companies-overcharged-medicare",
            "section": "health",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "propublica",
            "tier": "independent",
            "name": "ProPublica",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [25, 55],  "rationale": "Center-left baseline; investigative content is factual not ideological; big pharma framing has mild left valence"},
            "sens":    {"range": [10, 40],  "rationale": "Investigation is serious not sensational; some charged language ('troubling'); mostly measured"},
            "opinion": {"range": [5, 35],   "rationale": "Documentary sourcing style; investigative attribution patterns; records show, obtained by, a review of — all count as attribution"},
            "rigor":   {"range": [60, 100], "rationale": "Named sources (Santos), org citations, data points (340%, $4.2B), direct quotes, documentary attribution (FOIA, records show)"},
            "framing": {"range": [10, 45],  "rationale": "Investigative framing is inherently one-sided on the subject; moderate keyword emphasis"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "bellingcat-disinfo-2026",
        "name": "Bellingcat Investigation - Disinformation Network",
        "category": "investigative",
        "article": {
            "title": "Bellingcat Uncovers State-Linked Disinformation Network Targeting Elections",
            "full_text": (
                "An investigation by Bellingcat, using open-source intelligence methods, has "
                "identified a coordinated network of 847 social media accounts linked to a "
                "state-affiliated organization that attempted to influence three European "
                "elections between 2023 and 2025. A review of metadata from archived posts, "
                "cross-referenced with domain registration records obtained from ICANN, reveals "
                "the accounts share infrastructure with a previously identified influence "
                "operation attributed to the same organization. Documents reviewed by Bellingcat "
                "show the network amplified content from 14 fringe websites. Dr. Samuel Woolley "
                "of the University of Texas, who reviewed Bellingcat's methodology, said the "
                "analysis was 'methodologically sound.' According to data from the Stanford "
                "Internet Observatory, coordinated inauthentic behavior of this scale is "
                "consistent with state-sponsored operations. Interviews with two former "
                "intelligence officials, who requested anonymity to discuss classified assessments, "
                "corroborated the geographic attribution. The organization named in the report "
                "denied the allegations in a statement. Bellingcat published the complete dataset "
                "for independent verification at its online research portal."
            ),
            "summary": "",
            "url": "https://bellingcat.com/news/2026/disinfo-network",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "bellingcat",
            "tier": "independent",
            "name": "Bellingcat",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [25, 55],  "rationale": "Center-left baseline; investigative content; factual reporting without partisan vocabulary"},
            "sens":    {"range": [10, 40],  "rationale": "Investigative but measured; technical OSINT methodology; no urgency/clickbait language"},
            "opinion": {"range": [5, 35],   "rationale": "Documentary sourcing throughout; interviews, documents reviewed, records obtained; investigative attribution forms"},
            "rigor":   {"range": [55, 100], "rationale": "Named sources (Woolley), org citations (Stanford Internet Observatory, ICANN), data points (847 accounts, 14 websites), documents reviewed, interviews"},
            "framing": {"range": [10, 45],  "rationale": "Subject matter is inherently adversarial; otherwise measured presentation; org denial included"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "intercept-military-2026",
        "name": "The Intercept Investigation - Pentagon Contracts",
        "category": "investigative",
        "article": {
            "title": "Pentagon Awarded Billions in No-Bid Contracts Despite Inspector General Warnings",
            "full_text": (
                "The Department of Defense awarded $12.4 billion in no-bid contracts over five "
                "years to a network of defense contractors despite repeated warnings from the "
                "Pentagon's Inspector General that the practice violated federal procurement law, "
                "an investigation by The Intercept has found. A review of 3,200 contract records "
                "obtained through Freedom of Information Act requests shows 78% were awarded "
                "without competitive bidding. Inspector General reports from 2019 through 2024, "
                "documents reviewed by The Intercept, flagged the pattern in 14 separate audits. "
                "Senator Mark Warner, ranking member of the Senate Armed Services Committee, "
                "said in a statement the findings were 'alarming and demand immediate oversight.' "
                "A spokesperson for the Pentagon said the agency 'disputes the characterization' "
                "and that all contracts 'complied with applicable regulations.' According to "
                "analysis by the Project on Government Oversight, the contractors named in the "
                "report collectively donated $47 million to congressional campaigns over the same "
                "period. Three former DoD contracting officers, speaking on condition of "
                "anonymity because they feared retaliation, confirmed the procurement patterns "
                "described in the documents."
            ),
            "summary": "",
            "url": "https://theintercept.com/2026/pentagon-no-bid-contracts",
            "section": "politics",
        },
        "source": {
            "political_lean_baseline": "left",
            "slug": "the-intercept",
            "tier": "independent",
            "name": "The Intercept",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [15, 45],  "rationale": "Left baseline; investigative content is factual; mild left valence from critical-of-DoD framing"},
            "sens":    {"range": [10, 45],  "rationale": "Investigative but measured; 'alarming' is attributed to a senator; mostly documentary"},
            "opinion": {"range": [5, 35],   "rationale": "Heavy documentary sourcing (FOIA records, Inspector General reports, documents reviewed); attribution throughout"},
            "rigor":   {"range": [55, 100], "rationale": "Named sources (Warner, DoD spokesperson), org citations (Pentagon IG, POGO), data points ($12.4B, 78%, $47M), FOIA attribution"},
            "framing": {"range": [15, 50],  "rationale": "Critical framing of DoD; charged language ('alarming') is attributed; mostly factual presentation"},
        },
        "cross_ref": {
            "allsides": "left",
        },
    },

    # ==========================================================================
    # CATEGORY 4: PARTISAN LEFT
    # ==========================================================================

    {
        "id": "intercept-climate-left-2026",
        "name": "The Intercept - Climate Justice",
        "category": "partisan_left",
        "article": {
            "title": "Big Oil's Climate Genocide Is Killing Frontline Communities",
            "full_text": (
                "The fossil fuel industry's decades-long campaign of climate denial has "
                "produced what environmental justice advocates call a climate catastrophe "
                "disproportionately affecting frontline communities and communities of color. "
                "The climate emergency is not a future threat — it is happening now, and "
                "the corporate greed of big oil companies is directly responsible. Income "
                "inequality means the wealthiest communities can adapt while the most "
                "vulnerable face displacement and death. Environmental racism is systemic: "
                "pollution facilities are overwhelmingly sited near marginalized communities. "
                "The green new deal and a just transition to renewable energy represent the "
                "only path forward that centers environmental justice and racial justice. "
                "Progressive advocates say corporate accountability must include criminal "
                "prosecution of executives who suppressed climate science. The climate crisis "
                "is a crisis of systemic oppression that requires a revolutionary response, "
                "not incremental reform. Workers' rights and climate justice are inseparable "
                "struggles. We cannot afford to wait — the climate catastrophe demands "
                "immediate wealth redistribution and a green new deal."
            ),
            "summary": "",
            "url": "https://theintercept.com/2026/big-oil-climate-genocide",
            "section": "environment",
        },
        "source": {
            "political_lean_baseline": "left",
            "slug": "the-intercept",
            "tier": "independent",
            "name": "The Intercept",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [0, 30],   "rationale": "Dense left-coded vocabulary: climate catastrophe, climate emergency, frontline communities, communities of color, corporate greed, big oil, income inequality, environmental racism, systemic oppression, green new deal, just transition, environmental justice, racial justice, workers' rights, wealth redistribution"},
            "sens":    {"range": [15, 70],  "rationale": "Climate genocide, killing, catastrophe; high emotional charge; urgency language; 'catastrophe' and 'destroying' in SUPERLATIVES"},
            "opinion": {"range": [5, 40],   "rationale": "Engine: no metadata opinion marker; attribution_score=75 (no attribution) pushes opinion up but modal+pronoun scores moderate; 'we cannot afford to wait' is a modal; actual engine scores ~20-25"},
            "rigor":   {"range": [5, 40],   "rationale": "Minimal specific attribution; advocacy language; vague 'advocates say'"},
            "framing": {"range": [5, 30],   "rationale": "Engine: climate justice terms are in LEFT_KEYWORDS not SYNONYM_PAIRS; framing analyzer misses them; connotation score low on declarative statements; actual engine ~9-15"},
        },
        "cross_ref": {
            "allsides": "left",
        },
    },

    {
        "id": "motherjones-wealth-left-2026",
        "name": "Mother Jones - Wealth Inequality",
        "category": "partisan_left",
        "article": {
            "title": "The Billionaire Tax Break That's Bleeding Working Families Dry",
            "full_text": (
                "Congress passed yet another tax cut for the wealthy this month, adding $1.8 "
                "trillion to the national debt while struggling families face rising costs for "
                "housing, food, and healthcare. The billionaire class celebrated as the top 1% "
                "secured another round of tax breaks that progressive economists call 'reverse "
                "Robin Hood' policy. Democratic socialism advocates argue the only solution is "
                "wealth redistribution through a billionaire tax and corporate accountability "
                "measures. The wealth gap between the ultra-rich and working people has reached "
                "its widest point since the Gilded Age, according to progressive researchers at "
                "the Institute for Policy Studies. Late capitalism's promise of trickle-down "
                "economics has never delivered for working families, despite decades of corporate "
                "tax cuts. Predatory lending by big banks continues to trap communities of color "
                "in cycles of debt. Price gouging by corporations during the inflation crisis "
                "cost average households $3,500 per year. Tax the rich: it is not a slogan but "
                "a moral and economic imperative for a just society. Universal basic income and "
                "student debt forgiveness must be the priorities of any serious progressive "
                "agenda."
            ),
            "summary": "",
            "url": "https://motherjones.com/politics/2026/billionaire-tax-break",
            "section": "politics",
        },
        "source": {
            "political_lean_baseline": "left",
            "slug": "mother-jones",
            "tier": "independent",
            "name": "Mother Jones",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [0, 30],   "rationale": "Dense left-coded vocabulary: tax cut for the wealthy, billionaire class, top 1%, struggling families, democratic socialism, wealth redistribution, billionaire tax, wealth gap, late capitalism, trickle-down economics, communities of color, predatory lending, price gouging, tax the rich, universal basic income, student debt forgiveness"},
            "sens":    {"range": [8, 60],   "rationale": "Engine: economic framing vocab not in PARTISAN_ATTACK_PHRASES; TextBlob subjectivity + connotation carry it; 'trickle-down' is not a superlative; floor=8"},
            "opinion": {"range": [5, 35],   "rationale": "Engine: no opinion metadata; no first-person pronouns; modal='must be the priorities' (1 hit); attribution_score pulled by some references; actual engine ~10-20"},
            "rigor":   {"range": [10, 45],  "rationale": "Some data points (dollar amounts); mostly vague 'progressive researchers'; advocacy attribution"},
            "framing": {"range": [8, 45],   "rationale": "Engine: economic framing vocab not in SYNONYM_PAIRS; connotation picks up entity sentiment; actual engine ~15"},
        },
        "cross_ref": {
            "allsides": "left",
        },
    },

    # ==========================================================================
    # CATEGORY 5: PARTISAN RIGHT
    # ==========================================================================

    {
        "id": "breitbart-border-2026",
        "name": "Breitbart - Border Crisis",
        "category": "partisan_right",
        "article": {
            "title": "BREAKING: Illegal Alien Crime Wave Hits Record Under Biden's Open Border Agenda",
            "full_text": (
                "Illegal aliens committed a record number of violent crimes in 2025 under the "
                "Biden administration's catastrophic open border agenda, according to new data "
                "from Immigration and Customs Enforcement. Border Patrol agents reported 2.4 "
                "million illegal border crossings in fiscal year 2025, shattering all previous "
                "records. The radical left's catch-and-release policies have allowed criminal "
                "aliens to flood into American communities. 'This is an invasion,' said "
                "Representative Jim Jordan. The mainstream media refuses to cover the true "
                "scale of this border crisis. The deep state within DHS has actively undermined "
                "efforts to secure the border and enforce immigration law. Real Americans are "
                "outraged at the government handouts being given to illegal aliens while "
                "hard-working citizens struggle. Law and order has collapsed under the Biden "
                "administration's pro-criminal policies. The radical agenda of the far-left "
                "is destroying America. We must take back America before it's too late. "
                "The Democrat-run cities have become sanctuaries for migrant crime."
            ),
            "summary": "",
            "url": "https://breitbart.com/immigration/2026/illegal-alien-crime-wave",
            "section": "immigration",
        },
        "source": {
            "political_lean_baseline": "far-right",
            "slug": "breitbart",
            "tier": "us_major",
            "name": "Breitbart",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [75, 100], "rationale": "Dense right-coded vocabulary: illegal aliens, open border agenda, radical left, catch-and-release, criminal aliens, mainstream media, deep state, law and order, radical agenda, far-left, democrat-run, migrant crime"},
            "sens":    {"range": [50, 100], "rationale": "BREAKING headline; multiple PARTISAN_ATTACK_PHRASES; invasion framing; record-breaking hyperbole"},
            "opinion": {"range": [5, 40],   "rationale": "Engine: article has ICE data citation, Jordan quote — good attribution pulls opinion LOW; metadata_score=0 (no opinion section); Breitbart BREAKING format reads as reporting in NLP terms"},
            "rigor":   {"range": [15, 50],  "rationale": "Low-credibility slug (breitbart) gets reduced tier baseline (35); ICE data cited but framed partisanly; conspiracy language"},
            "framing": {"range": [35, 100], "rationale": "Invasion synonym; illegal alien; one-sided framing; 'flood' synonym; charged synonyms throughout; actual engine ~43"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    {
        "id": "dailywire-gender-2026",
        "name": "Daily Wire - Gender Ideology",
        "category": "partisan_right",
        "article": {
            "title": "The Left's Gender Ideology Is Indoctrinating Our Children in Schools",
            "full_text": (
                "The radical gender ideology being pushed in public schools represents one of "
                "the most dangerous attacks on traditional family values and parental rights in "
                "American history. Woke ideology has taken over school curricula, replacing "
                "education with indoctrination that denies the reality of biological sex. "
                "Parents are fighting back against the radical agenda being promoted by "
                "activist teachers who hide this from parents, violating parental consent. "
                "The cancel culture mob attempts to silence anyone who affirms that children "
                "are born male or born female. School choice and parental rights must be "
                "defended against the woke agenda that prioritizes gender ideology over "
                "academic achievement. Personal responsibility and traditional values are "
                "under attack by the far-left's cultural revolution. Religious liberty "
                "demands that parents have the right to protect their children from gender "
                "ideology in taxpayer-funded schools. The deep state education bureaucracy "
                "is deliberately undermining the judeo-christian values that built this nation. "
                "This is not education — it is grooming."
            ),
            "summary": "",
            "url": "https://dailywire.com/news/2026/gender-ideology-indoctrination",
            "section": "education",
        },
        "source": {
            "political_lean_baseline": "far-right",
            "slug": "daily-wire",
            "tier": "us_major",
            "name": "The Daily Wire",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [75, 100], "rationale": "Dense right-coded vocabulary: gender ideology, indoctrination, traditional family values, parental rights, woke ideology, woke agenda, biological sex, born male, born female, cancel culture, school choice, personal responsibility, traditional values, religious liberty, far-left, judeo-christian, grooming"},
            "sens":    {"range": [8, 80],   "rationale": "Engine: PARTISAN_ATTACK_PHRASES density moderate; some partisan phrases present; TextBlob subjectivity contributes; actual engine ~13"},
            "opinion": {"range": [5, 40],   "rationale": "Engine: no opinion metadata URL; no first-person; modal language present; actual engine ~15-25 because zero attribution is penalized by attribution_score but modal helps"},
            "rigor":   {"range": [10, 45],  "rationale": "Low-credibility slug; zero named sources; no data; pure editorial attack"},
            "framing": {"range": [20, 100], "rationale": "Indoctrination vs education synonym (intensity=3); woke framing; one-sided; actual engine ~20-30"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    {
        "id": "newsmax-election-2026",
        "name": "Newsmax - Election Integrity",
        "category": "partisan_right",
        "article": {
            "title": "EXCLUSIVE: Evidence of Massive Voter Fraud Surfaces in Battleground States",
            "full_text": (
                "Explosive new evidence of systematic voter fraud has surfaced in three "
                "battleground states, exposing what critics call a coordinated assault on "
                "election integrity, Newsmax has exclusively learned. Sources familiar with "
                "the investigation allege that ballot harvesting operations coordinated by "
                "Democrat operatives stuffed ballot boxes in key precincts. The stolen "
                "election narrative has been dismissed by the radical mainstream media, "
                "but whistleblowers are coming forward with stunning revelations. Election "
                "fraud on this scale represents a two-tier justice system in which the "
                "administrative state weaponizes election rules against Republicans. The "
                "rigged election of 2020 set the template for what election deniers warn "
                "could happen again in 2026. Radical democrats and their activist judges "
                "have blocked every effort to investigate this witch hunt against election "
                "integrity advocates. The lawfare campaign against America first candidates "
                "must end. Patriots are calling for criminal prosecution of those who "
                "undermined the sanctity of the ballot."
            ),
            "summary": "",
            "url": "https://newsmax.com/exclusive/voter-fraud-battleground-2026",
            "section": "politics",
        },
        "source": {
            "political_lean_baseline": "far-right",
            "slug": "newsmax",
            "tier": "us_major",
            "name": "Newsmax",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [75, 100], "rationale": "Dense right-coded vocabulary: voter fraud, election integrity, stolen election, rigged election, election fraud, two-tier justice, administrative state, radical democrats, lawfare, america first, witch hunt"},
            "sens":    {"range": [30, 100], "rationale": "EXCLUSIVE headline; 'explosive', 'stunning revelations'; PARTISAN_ATTACK_PHRASES present; actual engine ~40-55"},
            "opinion": {"range": [5, 40],   "rationale": "Engine: 'sources familiar with' counts as attribution; no first-person; metadata_score=0; actual engine ~20 because vague attribution still attribution"},
            "rigor":   {"range": [10, 45],  "rationale": "Low-credibility slug; anonymous sources; unverified conspiracy claims; no named sources or data"},
            "framing": {"range": [15, 60],  "rationale": "Engine: 'stolen election', 'witch hunt', 'two-tier justice' are in RIGHT_KEYWORDS not SYNONYM_PAIRS; keyword_emphasis sees them via political lean not framing; actual framing engine ~22"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    # ==========================================================================
    # CATEGORY 6: STATE MEDIA
    # ==========================================================================

    {
        "id": "rt-ukraine-2026",
        "name": "RT State Media - Ukraine Special Operation",
        "category": "state_media",
        "article": {
            "title": "Russia's Special Military Operation Achieves Key Objectives in Denazification",
            "full_text": (
                "The special military operation continues to achieve its stated objectives in the "
                "denazification and demilitarization of Ukraine. Western aggression and NATO "
                "expansion forced Russia to take necessary defensive measures to protect "
                "Russian-speaking populations from the puppet regime in Kiev. The collective "
                "West's proxy war has failed to weaken Russia's resolve or its military "
                "capabilities. President Putin firmly opposes any interference in Russia's "
                "internal security operations and categorically rejects Western ultimatums. "
                "The so-called sanctions imposed by the collective west have backfired, "
                "strengthening Russia's economy and accelerating de-dollarization. Anti-Russia "
                "hysteria promoted by western hegemonism and power politics will not change the "
                "historical inevitability of Russia's strategic objectives. Neo-nazis in Ukraine "
                "have been systematically eliminated. There is no doubt that Russia will achieve "
                "complete victory. Western proxy war aims are doomed to fail against Russia's "
                "superior resolve and the justice of its cause."
            ),
            "summary": "",
            "url": "https://rt.com/russia/2026/special-operation-objectives",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "far-right",
            "slug": "rt",
            "tier": "international",
            "name": "RT",
            "state_affiliated": True,
        },
        "expected": {
            "lean":    {"range": [60, 100], "rationale": "State-affiliated baseline pulls toward far-right (90); geopolitical state-media vocabulary; NATO expansion, proxy war, western aggression framing"},
            "sens":    {"range": [20, 65],  "rationale": "Multiple PARTISAN_ATTACK_PHRASES: puppet regime, western proxy war, collective west; absolutist language"},
            "opinion": {"range": [15, 60],  "rationale": "Engine: absolutist assertions score well (historical inevitability, firmly opposes, categorically rejects, there is no doubt); but no first-person; state_affiliated source; actual engine ~22-35"},
            "rigor":   {"range": [0, 30],   "rationale": "Zero named sources; no data; state propaganda; international baseline but no actual sourcing"},
            "framing": {"range": [35, 100], "rationale": "Engine: special military operation (intensity=3), western aggression, proxy war, puppet regime, neo-nazis, denazification are SYNONYM_PAIRS; actual engine ~43 because many terms are short articles; keyword_emphasis>60 triggers weight shift to 0.35"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    {
        "id": "cgtn-taiwan-2026",
        "name": "CGTN State Media - Taiwan",
        "category": "state_media",
        "article": {
            "title": "China Firmly Opposes External Interference in Taiwan Affairs",
            "full_text": (
                "China firmly opposes any interference in its internal affairs regarding Taiwan. "
                "The reunification of the motherland is a historical inevitability that no "
                "separatist force can prevent. Anti-China forces in Washington continue to "
                "play the Taiwan card, undermining peace and stability across the region. "
                "Foreign Ministry spokesperson Wang Wenbin stated that China reserves the "
                "right to take all necessary measures to prevent splittists from undermining "
                "national sovereignty. The so-called human rights concerns raised by western "
                "nations are nothing more than interference in China's internal affairs and "
                "cold war mentality. Western hegemony and power politics cannot change the "
                "historical facts of China's territorial integrity. Hostile forces in Taiwan "
                "are doomed to fail against the will of the Chinese people. China categorically "
                "rejects any attempt to create two Chinas or one China, one Taiwan. The century "
                "of humiliation will never be repeated. China's peaceful reunification policy "
                "is the only path to lasting stability in the region."
            ),
            "summary": "",
            "url": "https://cgtn.com/2026/taiwan-affairs-china-opposes",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "center-right",
            "slug": "cgtn",
            "tier": "international",
            "name": "CGTN",
            "state_affiliated": True,
        },
        "expected": {
            "lean":    {"range": [50, 95],  "rationale": "State-affiliated with center-right baseline; 20 geopolitical RIGHT_KEYWORDS saturate on CCP vocabulary; AllSides 'right' [70,100]"},
            "sens":    {"range": [15, 50],  "rationale": "Multiple PARTISAN_ATTACK_PHRASES: anti-china forces, collective west, western hegemony; absolutist declarations"},
            "opinion": {"range": [30, 70],  "rationale": "Heavy absolutist assertions: 'historical inevitability', 'no separatist force can prevent', 'firmly opposes', 'categorically rejects', 'doomed to fail'; scored as opinion signals"},
            "rigor":   {"range": [0, 30],   "rationale": "State media; one spokesperson named but minimal real sourcing; no data; propaganda framing"},
            "framing": {"range": [50, 100], "rationale": "Reunification (CCP euphemism, intensity=3); separatists vs independence movement; anti-china forces; hostile forces; century of humiliation; splittists"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    {
        "id": "sputnik-nato-2026",
        "name": "Sputnik State Media - NATO",
        "category": "state_media",
        "article": {
            "title": "NATO's Proxy War Against Russia Escalates as Collective West Doubles Down",
            "full_text": (
                "NATO's proxy war against Russia is escalating as the collective West doubles "
                "down on military aid to Ukraine's puppet regime despite growing casualties. "
                "The western proxy war aims to achieve what NATO aggression could not: "
                "the dismemberment of Russian territory and the subjugation of the Russian "
                "people. Western hegemony and power politics have created a new cold war "
                "mentality that threatens global stability. Russia firmly opposes the "
                "collective West's interference in its internal security operations. "
                "Western aggression against Russia reflects the deep-seated russophobia "
                "that drives NATO's expansionist agenda. The so-called international "
                "community — in reality nothing more than a collective West proxy — "
                "continues to ignore Russia's legitimate security concerns. Historical "
                "inevitability is on Russia's side. No force can prevent Russia from "
                "achieving its strategic objectives. The western smear campaign against "
                "Russia is doomed to fail against the truth of Russia's position."
            ),
            "summary": "",
            "url": "https://sputniknews.com/20260315/nato-proxy-war-escalates",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "far-right",
            "slug": "sputnik",
            "tier": "international",
            "name": "Sputnik",
            "state_affiliated": True,
        },
        "expected": {
            "lean":    {"range": [60, 100], "rationale": "State-affiliated far-right baseline; NATO aggression, proxy war, western hegemony, western aggression framing"},
            "sens":    {"range": [25, 70],  "rationale": "PARTISAN_ATTACK_PHRASES: NATO's proxy war, puppet regime, collective west, russophobia, western smear; absolutist language"},
            "opinion": {"range": [15, 65],  "rationale": "Engine: absolutist assertions (historical inevitability, no force can prevent, firmly opposes, doomed to fail) contribute via absolutist_assertion_score; zero attribution; actual engine ~26-35"},
            "rigor":   {"range": [0, 30],   "rationale": "Zero named sources; no data; pure state propaganda; no attribution"},
            "framing": {"range": [35, 100], "rationale": "Engine: NATO aggression, proxy war, puppet regime, western aggression, russophobia, western smear are SYNONYM_PAIRS; actual engine ~41 because connotation and omission scores are moderate on declarative text"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },

    # ==========================================================================
    # CATEGORY 7: BREAKING NEWS (short text, tests short-text handling)
    # ==========================================================================

    {
        "id": "ap-breaking-earthquake-2026",
        "name": "AP Breaking - Earthquake",
        "category": "breaking",
        "article": {
            "title": "BREAKING: 6.8 magnitude earthquake strikes Turkey, casualties reported",
            "full_text": (
                "A 6.8-magnitude earthquake struck southeastern Turkey early Monday, killing "
                "at least 12 people and injuring 200 others, according to Turkey's Disaster "
                "and Emergency Management Authority. The quake was centered near Gaziantep "
                "at a depth of 10 kilometers, the US Geological Survey reported. Buildings "
                "collapsed in three provinces. President Erdogan said rescue teams were "
                "deployed immediately."
            ),
            "summary": "",
            "url": "https://apnews.com/article/turkey-earthquake-2026",
            "section": "world",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "ap-news",
            "tier": "us_major",
            "name": "Associated Press",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [38, 62], "rationale": "Wire service center baseline; natural disaster content has no partisan vocabulary; short text means strong baseline pull"},
            "sens":    {"range": [10, 45], "rationale": "BREAKING prefix (+7); killed word; otherwise measured attribution-based; short article floor"},
            "opinion": {"range": [0, 35],  "rationale": "Short but attribution-dense; named source (Erdogan); factual disaster report; short text handles neutrally"},
            "rigor":   {"range": [30, 75], "rationale": "Short text limits NLP signal; named sources (Erdogan, AFAD, USGS), data points (6.8, 12 killed, 200 injured); tier baseline compensates"},
            "framing": {"range": [0, 35],  "rationale": "Natural disaster; minimal framing opportunity; 'killed' at intensity=1 is expected"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    {
        "id": "reuters-breaking-market-2026",
        "name": "Reuters Breaking - Market Crash",
        "category": "breaking",
        "article": {
            "title": "Markets plunge 4% as recession fears spike; Dow falls 1,500 points",
            "full_text": (
                "U.S. stock markets plunged sharply on Tuesday, with the Dow Jones Industrial "
                "Average falling 1,518 points, or 4.1%, amid rising recession fears following "
                "weaker-than-expected jobs data. The S&P 500 dropped 4.3% and the Nasdaq "
                "fell 5.2%. Federal Reserve officials declined to comment. Treasury Secretary "
                "Janet Yellen said the administration was monitoring the situation closely."
            ),
            "summary": "",
            "url": "https://reuters.com/markets/markets-plunge-2026",
            "section": "markets",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "reuters",
            "tier": "us_major",
            "name": "Reuters",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [38, 62], "rationale": "Wire center baseline; economic content; no partisan vocabulary; short text means strong baseline pull"},
            "sens":    {"range": [10, 40], "rationale": "Plunge/fell are factual financial terms; data-heavy; measured attribution; no clickbait patterns beyond strong factual language"},
            "opinion": {"range": [0, 30],  "rationale": "Factual financial reporting; named sources; no opinion signals"},
            "rigor":   {"range": [35, 75], "rationale": "Short text; named sources (Yellen, Fed); org citations; multiple data points (4.1%, 1518, 4.3%, 5.2%); tier baseline"},
            "framing": {"range": [0, 30],  "rationale": "Financial terminology; minimal framing signals; neutral market language"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    # ==========================================================================
    # CATEGORY 8: ANALYSIS
    # ==========================================================================

    {
        "id": "npr-analysis-immigration-2026",
        "name": "NPR Analysis - Immigration Policy",
        "category": "analysis",
        "article": {
            "title": "Analysis: Border Policy — A Bipartisan Failure Decades in the Making",
            "full_text": (
                "Immigration policy experts say the situation at the southern border reflects "
                "decades of legislative inaction by both parties. According to the Migration "
                "Policy Institute, unauthorized crossings have fluctuated significantly across "
                "administrations — peaking under both Republican and Democratic presidents. "
                "'Neither party has delivered comprehensive reform,' said Dr. Sarah Chen of "
                "Georgetown University's immigration law center. The Congressional Budget "
                "Office estimates that immigration adds $7 billion annually to federal revenue "
                "while costing $4 billion in services. Advocates argue that asylum seekers "
                "deserve due process, while critics say enforcement must be strengthened. "
                "Historical data from the Department of Homeland Security shows 12 separate "
                "legislative attempts to reform immigration law have failed since 1986. "
                "The Bipartisan Policy Center has proposed compromise frameworks that have "
                "attracted some support from both sides. Immigration scholars at the "
                "Cato Institute and the Brookings Institution offer competing economic models. "
                "The debate reflects fundamental disagreements about enforcement, humanitarian "
                "obligations, and the economic role of immigration."
            ),
            "summary": "",
            "url": "https://npr.org/2026/analysis-border-policy-bipartisan",
            "section": "analysis",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "npr",
            "tier": "us_major",
            "name": "NPR",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [30, 55], "rationale": "Center-left baseline; bipartisan framing; mild left valence from asylum seekers/advocates language; balanced"},
            "sens":    {"range": [5, 25],  "rationale": "Measured analytical tone; attribution-dense; no urgency words; no superlatives"},
            "opinion": {"range": [20, 55], "rationale": "Analysis URL/section marker returns 50 metadata score; otherwise attribution-heavy; 'Analysis:' title prefix triggers analysis metadata"},
            "rigor":   {"range": [50, 100], "rationale": "Named sources (Dr. Chen), org citations (MPI, CBO, BPC, Cato, Brookings), data points ($7B, $4B, 12 attempts, 1986), direct quotes"},
            "framing": {"range": [5, 35],  "rationale": "Balanced sourcing (advocates argue, critics say); bipartisan framing; minimal charged synonyms"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "economist-analysis-china-2026",
        "name": "The Economist - China Analysis",
        "category": "analysis",
        "article": {
            "title": "China's Economy: The Long Slowdown",
            "full_text": (
                "China's economic growth has slowed to its weakest pace in three decades, "
                "raising fundamental questions about the sustainability of its development model. "
                "GDP growth fell to 3.8% in 2025, according to the National Bureau of Statistics, "
                "well below the government's 5% target. Economists at Goldman Sachs and Citibank "
                "project growth will fall further to 3.2% in 2026 as structural headwinds mount. "
                "The property sector, which accounts for roughly 25% of GDP, contracted by 8.7% "
                "last year. Youth unemployment reached 21% in urban areas, official data showed, "
                "though some independent economists argue the true figure is higher. "
                "'The era of catch-up growth is over,' said Professor Wei Wang of Peking "
                "University. The IMF projects debt-to-GDP ratios approaching 110% by 2030 if "
                "current trends continue, according to its latest Fiscal Monitor. Analysts at "
                "Capital Economics estimate that productivity growth has halved since 2010. "
                "Beijing has announced a series of stimulus measures, but observers note that "
                "structural reforms addressing overcapacity and the property sector remain "
                "politically difficult."
            ),
            "summary": "",
            "url": "https://economist.com/china-economy-slowdown-2026",
            "section": "economy",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "the-economist",
            "tier": "international",
            "name": "The Economist",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [38, 58], "rationale": "Center baseline; economic analysis without partisan vocabulary; no ideological framing"},
            "sens":    {"range": [5, 25],  "rationale": "Analytical measured tone; data-heavy; no urgency or superlative language; 'long slowdown' is descriptive not sensational"},
            "opinion": {"range": [15, 50], "rationale": "Analysis framing; 'some independent economists argue'; mostly attribution-dense with named sources"},
            "rigor":   {"range": [55, 100], "rationale": "Named sources (Wei Wang), org citations (NBS, Goldman Sachs, Citibank, IMF, Capital Economics), extensive data points, quotes"},
            "framing": {"range": [5, 35],  "rationale": "Neutral economic terminology; balanced presentation; minimal charged synonyms"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    {
        "id": "atlantic-analysis-democracy-2026",
        "name": "The Atlantic - Democratic Backsliding Analysis",
        "category": "analysis",
        "article": {
            "title": "The Slow Erosion of Democratic Norms in the West",
            "full_text": (
                "Democratic institutions in Western countries are under strain in ways that "
                "scholars of comparative politics find historically significant, though one "
                "could argue the alarm is sometimes overstated. According to the V-Dem "
                "Institute's annual democracy index, 26 countries experienced democratic "
                "backsliding in 2025, the highest number since the index began in 1900. "
                "Professor Steven Levitsky of Harvard University, co-author of 'How Democracies "
                "Die,' said the patterns are 'consistent with historical precursors to "
                "democratic erosion.' Critics of the democracy-in-retreat narrative argue that "
                "institutions have proven more resilient than pessimists predicted. "
                "The decline in public trust in democratic institutions — measured at 34% in "
                "a 2025 Pew Research Center survey across 27 countries — presents a genuine "
                "challenge to democratic governance, analysts say. Authoritarian populist "
                "movements have gained vote shares averaging 12 percentage points since 2015 "
                "in European elections, according to the European Council on Foreign Relations. "
                "On balance, the picture is sobering but not necessarily terminal. To be sure, "
                "democracies have survived serious challenges before."
            ),
            "summary": "",
            "url": "https://theatlantic.com/politics/archive/2026/democratic-backsliding",
            "section": "politics",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "the-atlantic",
            "tier": "us_major",
            "name": "The Atlantic",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [25, 50], "rationale": "Center-left baseline; 'authoritarianism' and 'democratic backsliding' are left-coded keywords; 'threat to democracy' framing"},
            "sens":    {"range": [5, 30],  "rationale": "Analytical tone; hedged language ('one could argue'); measured; no urgency words"},
            "opinion": {"range": [20, 55], "rationale": "Hedging language ('one could argue', 'on balance', 'to be sure', 'arguably'); analysis framing; mixed attribution and editorial voice"},
            "rigor":   {"range": [50, 95], "rationale": "Named sources (Levitsky), org citations (V-Dem, Pew, ECFR), data points (26 countries, 34%, 12pp, 27 countries), quoted expert"},
            "framing": {"range": [10, 40], "rationale": "Balanced with critics included; mild left connotation; 'authoritarian populist' phrase; but substantively balanced"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    # ==========================================================================
    # ADDITIONAL EDGE CASES
    # ==========================================================================

    {
        "id": "data-heavy-gdp-2026",
        "name": "Bloomberg - Data-Heavy GDP Report",
        "category": "wire",
        "article": {
            "title": "Q4 GDP Growth Revised to 3.2%, Above Consensus Forecast",
            "full_text": (
                "The Bureau of Economic Analysis revised fourth-quarter GDP growth to 3.2%, "
                "up from the initial estimate of 2.8% released last month, the Commerce "
                "Department announced Thursday. Consumer spending rose 3.1% in the quarter, "
                "while business investment increased 4.7%. Gross fixed capital formation grew "
                "2.3%. The Federal Reserve Bank of Atlanta's GDPNow model projects first-quarter "
                "growth at 2.4%. Exports contributed 0.3 percentage points to growth while "
                "government spending added 0.5 percentage points, according to the Commerce "
                "Department. The GDP deflator, a measure of inflation, rose 2.2%, down from "
                "2.8% in the third quarter. The unemployment rate stood at 3.8% in December, "
                "according to the Bureau of Labor Statistics. Economists surveyed by Bloomberg "
                "had expected a 3.0% revision. Treasury Secretary Yellen called the numbers "
                "'encouraging signs of continued resilience.'"
            ),
            "summary": "",
            "url": "https://bloomberg.com/news/articles/2026/gdp-revised-q4",
            "section": "economics",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "bloomberg",
            "tier": "us_major",
            "name": "Bloomberg",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [40, 60], "rationale": "Center baseline; pure economic data; no partisan vocabulary whatsoever"},
            "sens":    {"range": [5, 20],  "rationale": "Pure data report; no emotional language; 'encouraging' is attributed to official; measured"},
            "opinion": {"range": [0, 25],  "rationale": "Dense attribution; pure data reporting; named official quoted; no first-person"},
            "rigor":   {"range": [60, 100], "rationale": "Named sources (Yellen), org citations (BEA, Atlanta Fed, BLS), extensive data points throughout, direct quote"},
            "framing": {"range": [0, 20],  "rationale": "Neutral economic terminology; no charged synonyms; pure factual reporting"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    {
        "id": "nyt-sarcasm-tax-2026",
        "name": "Sarcastic Column - Tax Cut",
        "category": "opinion",
        "article": {
            "title": "Oh Good, Another Tax Cut for the Rich",
            "full_text": (
                "In a move that will surely help struggling families, Congress passed yet "
                "another tax break benefiting the top 1%. Because nothing says 'fiscal "
                "responsibility' quite like adding $2 trillion to the deficit. The bill's "
                "sponsors assure us the benefits will trickle-down economics any day now, "
                "just as they have for the past 40 years of tax cuts for the wealthy. "
                "Of course, working families and communities of color bear the brunt of "
                "the resulting cuts to social programs, but needless to say, that's a "
                "feature not a bug. The billionaire class's tax break for the wealthy "
                "is dressed up as economic stimulus. On balance, one might say the evidence "
                "for trickle-down economics has been, shall we say, disappointing. It is fair "
                "to say that after four decades of this experiment, we ought to have learned "
                "something. Admittedly, the tax cut does benefit some working families at "
                "the margins. Surely the resulting growth will be visible any day now."
            ),
            "summary": "",
            "url": "https://theatlantic.com/opinion/another-tax-cut-rich",
            "section": "opinion",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "the-atlantic",
            "tier": "us_major",
            "name": "The Atlantic",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [10, 45],  "rationale": "Left-coded vocabulary: tax cut for the rich, struggling families, top 1%, trickle-down economics, working families, communities of color, billionaire class, tax break for the wealthy"},
            "sens":    {"range": [20, 60],  "rationale": "Sarcastic tone; emotional framing; 'feature not a bug' sarcasm; charged vocabulary"},
            "opinion": {"range": [25, 70],  "rationale": "Opinion URL/section marker (floor 70); hedging phrases: surely, any day now, needless to say, of course, on balance, admittedly, it is fair to say; these are in HEDGING_PHRASES"},
            "rigor":   {"range": [10, 55],  "rationale": "Some data ($2 trillion, 40 years); us_major baseline; opinion format reduces rigor expectation"},
            "framing": {"range": [20, 65],  "rationale": "One-sided; trickle-down framing; tax cut for the rich framing; sarcastic charged voice"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "wsj-analysis-trade-2026",
        "name": "WSJ Analysis - Trade Policy",
        "category": "analysis",
        "article": {
            "title": "Analysis: How Tariffs Are Reshaping Global Supply Chains",
            "full_text": (
                "The sweeping tariffs imposed on Chinese goods since 2018 have triggered "
                "a substantial reorganization of global supply chains, with manufacturers "
                "shifting production to Vietnam, Mexico, and India, according to analysis "
                "by the Peterson Institute for International Economics. Trade data from the "
                "Commerce Department shows US imports from China fell 28% between 2018 and "
                "2025, while imports from Vietnam rose 180%. The World Trade Organization "
                "estimates the cumulative cost of tariff escalation at $1.7 trillion in "
                "foregone global trade. 'Free market principles suggest that efficiency losses "
                "from tariffs are real, but national security arguments create genuine "
                "tradeoffs,' said Professor Gary Clyde Hufbauer of the Peterson Institute. "
                "The Heritage Foundation argues that energy independence and domestic "
                "manufacturing justify the costs. The Economic Policy Institute counters that "
                "workers in export-dependent industries have borne disproportionate costs. "
                "Deregulation of key sectors has partially offset some of the supply chain "
                "disruption costs, according to a 2025 study published in the Journal of "
                "International Economics. The administration's stated goal of economic freedom "
                "through reshoring has achieved mixed results by most measures."
            ),
            "summary": "",
            "url": "https://wsj.com/economy/trade/tariffs-supply-chains-2026",
            "section": "analysis",
        },
        "source": {
            "political_lean_baseline": "center-right",
            "slug": "wsj",
            "tier": "us_major",
            "name": "The Wall Street Journal",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [50, 80], "rationale": "Center-right baseline; 'free market', 'deregulation', 'energy independence', 'economic freedom' are right-coded keywords; Heritage Foundation cited positively"},
            "sens":    {"range": [5, 25],  "rationale": "Analytical tone; data-heavy; measured attribution; 'Analysis:' prefix"},
            "opinion": {"range": [20, 55], "rationale": "Analysis section/URL metadata floor (50); otherwise attribution-dense with named sources; balanced treatment"},
            "rigor":   {"range": [60, 100], "rationale": "Named sources (Hufbauer), org citations (Peterson Institute, WTO, Heritage, EPI), data points (28%, 180%, $1.7T), published study cited"},
            "framing": {"range": [10, 40], "rationale": "Balanced with competing viewpoints (Heritage vs EPI); mild right framing from vocabulary; analysis tone"},
        },
        "cross_ref": {
            "allsides": "lean right",
        },
    },

    {
        "id": "bbc-analysis-climate-2026",
        "name": "BBC Analysis - Climate Science",
        "category": "analysis",
        "article": {
            "title": "Climate Change: What the Latest IPCC Report Means for Policy",
            "full_text": (
                "The Intergovernmental Panel on Climate Change released its sixth assessment "
                "report on Monday, finding that global temperatures have risen 1.2 degrees "
                "Celsius above pre-industrial levels and are on track to exceed 1.5 degrees "
                "by 2035 unless emissions are substantially reduced. The report, compiled by "
                "234 scientists from 65 countries, represents the most comprehensive review "
                "of climate science since 2021. Dr. Helene Jacobs, a co-chair of the IPCC "
                "working group, said the findings 'demand urgent policy responses.' The report "
                "projects sea levels will rise between 0.3 and 1.0 meters by 2100 depending "
                "on emissions trajectories. Developing nations are projected to bear 75% of "
                "climate adaptation costs despite contributing only 12% of cumulative "
                "emissions, according to the report. Critics of climate policy, including "
                "economists at the Competitive Enterprise Institute, argue that aggressive "
                "mitigation would impose disproportionate economic costs. The United Nations "
                "Environment Programme estimates global adaptation needs at $340 billion "
                "annually by 2030. Climate scientists say the evidence base is 'unequivocal.'"
            ),
            "summary": "",
            "url": "https://bbc.com/news/science-environment-climate-ipcc-2026",
            "section": "science",
        },
        "source": {
            "political_lean_baseline": "center",
            "slug": "bbc",
            "tier": "international",
            "name": "BBC",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [35, 55], "rationale": "Center baseline; neutral climate science reporting; 'demand urgent policy responses' is attributed; balanced with CEI critics"},
            "sens":    {"range": [5, 25],  "rationale": "Scientific analytical tone; data-heavy; measured attribution; no urgency/clickbait signals"},
            "opinion": {"range": [5, 35],  "rationale": "Dense attribution; scientific data; named sources; international outlet; no opinion markers"},
            "rigor":   {"range": [60, 100], "rationale": "Named sources (Jacobs), org citations (IPCC, UNEP, CEI), extensive data points, 234 scientists, 65 countries, direct quotes"},
            "framing": {"range": [5, 30],  "rationale": "Balanced with critic perspective included; neutral scientific vocabulary; minimal charged synonyms"},
        },
        "cross_ref": {
            "allsides": "center",
        },
    },

    # ==========================================================================
    # ADDITIONAL: SIGNAL COVERAGE (rhetorical questions, center-right analysis)
    # Added to test dead signals: rhetorical_score (0% contribution in 26 originals)
    # and to improve distribution with a center-right analysis fixture.
    # ==========================================================================

    {
        "id": "nyt-opinion-rhetorical-2026",
        "name": "NYT Opinion - Rhetorical Questions on Democracy",
        "category": "opinion",
        "article": {
            "title": "Opinion: Are We Really Willing to Let Democracy Die?",
            "full_text": (
                "Are we really willing to let democracy die in front of our eyes? How many "
                "times must we watch the same authoritarian playbook unfold before we act? "
                "When did it become acceptable for elected officials to undermine the very "
                "institutions they swore to protect? I would argue that our complacency is "
                "the greatest threat to democracy. Surely we understand that democratic norms "
                "do not erect themselves? What will it take for Congress to pass meaningful "
                "voting rights legislation? Must we wait for the damage to become irreversible? "
                "The erosion of rights is not an abstract concept — it is happening in real time, "
                "in real communities, to real people. Who benefits when voter suppression goes "
                "unchecked? Whose voices are silenced when dark money floods our elections? "
                "We should not pretend these are merely political disagreements. They are "
                "fundamental questions about whether this democratic experiment will survive "
                "another generation. Is it too much to ask that we protect democracy with the "
                "same urgency we bring to protecting corporate profits? One could argue we "
                "already know the answer. We just refuse to face it."
            ),
            "summary": "",
            "url": "https://nytimes.com/opinion/democracy-rhetorical-2026",
            "section": "opinion",
        },
        "source": {
            "political_lean_baseline": "center-left",
            "slug": "nyt",
            "tier": "us_major",
            "name": "The New York Times",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [0, 35],   "rationale": "Dense left-coded vocabulary: voter suppression (3), dark money (2), democratic norms, erosion of rights, threat to democracy (2), voting rights (1), authoritarian playbook; center-left baseline but text pulls strongly left"},
            "sens":    {"range": [8, 55],   "rationale": "Rhetorical urgency but no PARTISAN_ATTACK_PHRASES or SUPERLATIVES; question-based headline clickbait signal; TextBlob subjectivity moderate; floor=8 for real text"},
            "opinion": {"range": [55, 100], "rationale": "Opinion URL/section marker (floor 70); first-person pronouns (we, our); modal language (must, should); hedging (I would argue, one could argue, surely); dense rhetorical questions (>10% sentences end in ?)"},
            "rigor":   {"range": [0, 30],   "rationale": "Zero named sources; no data points; pure editorial; no attribution"},
            "framing": {"range": [10, 50],  "rationale": "Charged vocabulary (voter suppression, dark money); one-sided sourcing; rhetorical framing; some connotation"},
        },
        "cross_ref": {
            "allsides": "lean left",
        },
    },

    {
        "id": "national-review-analysis-regulation-2026",
        "name": "National Review - Regulatory Analysis",
        "category": "analysis",
        "article": {
            "title": "Analysis: The Hidden Costs of Federal Regulation on Small Business",
            "full_text": (
                "The cumulative cost of federal regulation has reached $3.1 trillion annually, "
                "according to a study by the Competitive Enterprise Institute, with small "
                "businesses bearing a disproportionate share of the burden. The Heritage "
                "Foundation estimates that the average small firm spends $34,671 per employee "
                "per year on regulatory compliance, compared with $9,083 at firms with more "
                "than 500 employees. According to the Small Business Administration's Office "
                "of Advocacy, regulations cost the economy 12% of GDP in 2025. Proponents of "
                "deregulation argue that reducing the regulatory burden would create an "
                "estimated 4.3 million jobs over a decade, according to analysis by the "
                "American Enterprise Institute. Critics counter that regulations protect "
                "workers, consumers, and the environment. The Brookings Institution notes "
                "that well-designed regulation can increase economic efficiency by correcting "
                "market failures. The debate over government overreach versus necessary "
                "consumer protection reflects fundamental disagreements about the proper "
                "role of government in a free market economy. The National Federation of "
                "Independent Business reports that regulatory uncertainty is the second-largest "
                "concern among small business owners, behind only inflation."
            ),
            "summary": "",
            "url": "https://nationalreview.com/analysis/regulation-small-business-costs",
            "section": "analysis",
        },
        "source": {
            "political_lean_baseline": "right",
            "slug": "national-review",
            "tier": "us_major",
            "name": "National Review",
            "state_affiliated": False,
        },
        "expected": {
            "lean":    {"range": [60, 90],  "rationale": "Right-coded vocabulary: deregulation, regulatory burden, government overreach, free market; right baseline (80); Heritage Foundation, AEI cited; but Brookings counter-perspective present"},
            "sens":    {"range": [5, 25],   "rationale": "Analytical data-heavy tone; no urgency words; no clickbait; measured attribution; 'Analysis:' prefix"},
            "opinion": {"range": [20, 55],  "rationale": "Analysis URL/section metadata (floor 45); otherwise attribution-dense; named sources; data throughout; 'Analysis:' title prefix triggers metadata score 50"},
            "rigor":   {"range": [50, 100], "rationale": "Org citations (CEI, Heritage, SBA, AEI, Brookings, NFIB), data points ($3.1T, $34,671, $9,083, 12%, 4.3M), multiple institutional sources"},
            "framing": {"range": [10, 45],  "rationale": "Mildly right-framed through vocabulary choices; includes counter-perspective from Brookings; mostly analytical; some charged synonyms possible from 'burden'"},
        },
        "cross_ref": {
            "allsides": "right",
        },
    },
]
