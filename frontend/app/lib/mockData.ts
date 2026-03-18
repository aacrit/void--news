import type { Story, DeepDiveData } from "./types";

/* ---------------------------------------------------------------------------
   Deep Dive mock data — consensus, divergence, and source coverage
   per story cluster. 3-6 sources per story, across tiers.
   --------------------------------------------------------------------------- */

const deepDive1: DeepDiveData = {
  consensus: [
    "The EU-China agreement covers semiconductors, green technology, and agricultural exports",
    "Tariffs on key goods will be removed under the new framework",
    "Both sides confirmed the deal after months of negotiations",
  ],
  divergence: [
    "Western outlets emphasize EU leverage on tech-transfer standards; Chinese state media frames the deal as mutual benefit",
    "US-based sources question whether the deal undermines transatlantic trade solidarity",
    "Independent outlets highlight labor and environmental provisions that major outlets largely omit",
  ],
  sources: [
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 8, factualRigor: 92, framing: 18 } },
    { name: "Financial Times", url: "https://ft.com", tier: "international", biasScores: { politicalLean: 52, sensationalism: 12, opinionFact: 15, factualRigor: 90, framing: 22 } },
    { name: "CNN", url: "https://cnn.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 28, opinionFact: 20, factualRigor: 82, framing: 30 } },
    { name: "South China Morning Post", url: "https://scmp.com", tier: "international", biasScores: { politicalLean: 58, sensationalism: 14, opinionFact: 12, factualRigor: 85, framing: 35 } },
    { name: "The Intercept", url: "https://theintercept.com", tier: "independent", biasScores: { politicalLean: 30, sensationalism: 20, opinionFact: 30, factualRigor: 80, framing: 40 } },
  ],
};

const deepDive2: DeepDiveData = {
  consensus: [
    "The $1.2 trillion bill passed the Senate 71-28 with bipartisan support",
    "Funds are allocated for bridge repairs, broadband, and EV charging infrastructure",
    "The bill now moves to the House for consideration",
  ],
  divergence: [
    "Progressive outlets criticize the bill for not going far enough on climate provisions",
    "Conservative media frames the spending as potentially inflationary and fiscally irresponsible",
    "Independent sources question the earmark allocation process and which states benefit most",
  ],
  sources: [
    { name: "AP News", url: "https://apnews.com", tier: "us_major", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 5, factualRigor: 95, framing: 12 } },
    { name: "New York Times", url: "https://nytimes.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 18, opinionFact: 15, factualRigor: 90, framing: 22 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 72, sensationalism: 35, opinionFact: 28, factualRigor: 75, framing: 38 } },
    { name: "NPR", url: "https://npr.org", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 12, opinionFact: 10, factualRigor: 92, framing: 18 } },
    { name: "ProPublica", url: "https://propublica.org", tier: "independent", biasScores: { politicalLean: 35, sensationalism: 15, opinionFact: 18, factualRigor: 94, framing: 25 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 46, sensationalism: 14, opinionFact: 8, factualRigor: 90, framing: 16 } },
  ],
};

const deepDive3: DeepDiveData = {
  consensus: [
    "WHO officially lifted the global health emergency designation for mpox",
    "Vaccination campaigns in Africa are credited with declining case numbers",
    "Global case counts have dropped significantly over the past six months",
  ],
  divergence: [
    "Some outlets question whether the declaration is premature given ongoing cases in Central Africa",
    "International sources provide more context on regional vaccination disparities",
    "US outlets focus more on domestic implications while international media covers global access issues",
  ],
  sources: [
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 5, factualRigor: 94, framing: 12 } },
    { name: "Al Jazeera", url: "https://aljazeera.com", tier: "international", biasScores: { politicalLean: 44, sensationalism: 14, opinionFact: 8, factualRigor: 90, framing: 18 } },
    { name: "CNN", url: "https://cnn.com", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 20, opinionFact: 10, factualRigor: 88, framing: 15 } },
    { name: "The Lancet", url: "https://thelancet.com", tier: "independent", biasScores: { politicalLean: 50, sensationalism: 5, opinionFact: 3, factualRigor: 98, framing: 6 } },
  ],
};

const deepDive4: DeepDiveData = {
  consensus: [
    "The Fed Chair signaled openness to rate cuts in coming months",
    "Consumer price index data shows sustained decline toward the 2% target",
    "Markets reacted positively to the announcement",
  ],
  divergence: [
    "Conservative outlets warn the Fed may be moving too soon and risking renewed inflation",
    "Progressive outlets argue rate cuts should have come earlier to help working families",
    "Financial press debates the timing relative to employment data and wage growth",
  ],
  sources: [
    { name: "Wall Street Journal", url: "https://wsj.com", tier: "us_major", biasScores: { politicalLean: 58, sensationalism: 12, opinionFact: 20, factualRigor: 90, framing: 25 } },
    { name: "Bloomberg", url: "https://bloomberg.com", tier: "us_major", biasScores: { politicalLean: 52, sensationalism: 10, opinionFact: 15, factualRigor: 92, framing: 20 } },
    { name: "CNBC", url: "https://cnbc.com", tier: "us_major", biasScores: { politicalLean: 54, sensationalism: 22, opinionFact: 18, factualRigor: 85, framing: 28 } },
    { name: "The Markup", url: "https://themarkup.org", tier: "independent", biasScores: { politicalLean: 44, sensationalism: 8, opinionFact: 12, factualRigor: 94, framing: 15 } },
  ],
};

const deepDive5: DeepDiveData = {
  consensus: [
    "Both Ukraine and Russia committed to a 90-day ceasefire",
    "Turkey and UAE brokered the agreement through shuttle diplomacy",
    "The deal includes prisoner exchange and humanitarian corridor provisions",
  ],
  divergence: [
    "Western media frames this as a Ukrainian diplomatic victory; Russian state media emphasizes territorial concessions",
    "Some sources question the enforceability given past ceasefire failures",
    "Independent outlets highlight civilian perspectives and humanitarian needs that major outlets underreport",
  ],
  sources: [
    { name: "Al Jazeera", url: "https://aljazeera.com", tier: "international", biasScores: { politicalLean: 42, sensationalism: 25, opinionFact: 12, factualRigor: 82, framing: 30 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 46, sensationalism: 18, opinionFact: 10, factualRigor: 88, framing: 22 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 12, opinionFact: 6, factualRigor: 94, framing: 15 } },
    { name: "Washington Post", url: "https://washingtonpost.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 22, opinionFact: 18, factualRigor: 86, framing: 28 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 70, sensationalism: 40, opinionFact: 30, factualRigor: 70, framing: 45 } },
    { name: "Bellingcat", url: "https://bellingcat.com", tier: "independent", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 8, factualRigor: 96, framing: 12 } },
  ],
};

const deepDive6: DeepDiveData = {
  consensus: [
    "Three major fires broke out in Southern California, forcing evacuations",
    "Ventura and San Bernardino counties are the most affected areas",
    "Drought conditions contributed to the early start of wildfire season",
  ],
  divergence: [
    "Left-leaning outlets connect the fires directly to climate change policy failures",
    "Conservative outlets focus on forest management and regulatory barriers to controlled burns",
    "Local outlets provide granular evacuation details while national outlets focus on the broader trend",
  ],
  sources: [
    { name: "Los Angeles Times", url: "https://latimes.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 30, opinionFact: 18, factualRigor: 85, framing: 32 } },
    { name: "AP News", url: "https://apnews.com", tier: "us_major", biasScores: { politicalLean: 48, sensationalism: 15, opinionFact: 6, factualRigor: 92, framing: 14 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 68, sensationalism: 45, opinionFact: 32, factualRigor: 72, framing: 50 } },
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 35, sensationalism: 28, opinionFact: 22, factualRigor: 82, framing: 38 } },
  ],
};

const deepDive7: DeepDiveData = {
  consensus: [
    "ISRO successfully deployed a test satellite for space-based solar energy",
    "The satellite can beam solar energy to ground stations",
    "This marks a milestone in space-based renewable energy technology",
  ],
  divergence: [
    "Indian outlets frame this as a geopolitical achievement rivaling US and Chinese space programs",
    "Western outlets are more cautious about the technology's scalability and cost",
    "Scientific outlets focus on the technical challenges remaining before commercial viability",
  ],
  sources: [
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 42, sensationalism: 15, opinionFact: 8, factualRigor: 90, framing: 18 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 12, opinionFact: 6, factualRigor: 92, framing: 14 } },
    { name: "Nature", url: "https://nature.com", tier: "independent", biasScores: { politicalLean: 50, sensationalism: 5, opinionFact: 4, factualRigor: 98, framing: 6 } },
    { name: "CNN", url: "https://cnn.com", tier: "us_major", biasScores: { politicalLean: 44, sensationalism: 22, opinionFact: 14, factualRigor: 84, framing: 20 } },
  ],
};

const deepDive8: DeepDiveData = {
  consensus: [
    "The Supreme Court agreed to hear the Section 702 surveillance challenge",
    "The case concerns warrantless surveillance of Americans' international communications",
    "The outcome will have major implications for Fourth Amendment privacy rights",
  ],
  divergence: [
    "Civil liberties outlets frame the case as a critical check on government overreach",
    "National security-focused outlets emphasize the importance of surveillance tools for counterterrorism",
    "Legal analysis outlets disagree on the likely outcome based on the court's current composition",
  ],
  sources: [
    { name: "Washington Post", url: "https://washingtonpost.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 18, opinionFact: 15, factualRigor: 90, framing: 25 } },
    { name: "Wall Street Journal", url: "https://wsj.com", tier: "us_major", biasScores: { politicalLean: 58, sensationalism: 14, opinionFact: 20, factualRigor: 88, framing: 28 } },
    { name: "The Intercept", url: "https://theintercept.com", tier: "independent", biasScores: { politicalLean: 28, sensationalism: 25, opinionFact: 30, factualRigor: 82, framing: 40 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 8, opinionFact: 6, factualRigor: 94, framing: 12 } },
    { name: "NPR", url: "https://npr.org", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 12, opinionFact: 10, factualRigor: 92, framing: 18 } },
  ],
};

const deepDive9: DeepDiveData = {
  consensus: [
    "New fabrication plants from TSMC and Intel are now operational",
    "The semiconductor shortage that lasted three years is easing",
    "Automakers and electronics manufacturers expect relief from tlhe supply improvements",
  ],
  divergence: [
    "US outlets emphasize the domestic economic benefits and job creation from Arizona fabs",
    "European outlets focus on Germany's fab and EU strategic autonomy in semiconductors",
    "Industry analysts disagree on whether overcapacity may become the next challenge",
  ],
  sources: [
    { name: "Bloomberg", url: "https://bloomberg.com", tier: "us_major", biasScores: { politicalLean: 52, sensationalism: 8, opinionFact: 12, factualRigor: 94, framing: 18 } },
    { name: "DW", url: "https://dw.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 8, factualRigor: 90, framing: 15 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 6, opinionFact: 5, factualRigor: 96, framing: 10 } },
    { name: "The Markup", url: "https://themarkup.org", tier: "independent", biasScores: { politicalLean: 44, sensationalism: 12, opinionFact: 15, factualRigor: 88, framing: 22 } },
  ],
};

const deepDive10: DeepDiveData = {
  consensus: [
    "Education unions in 14 states plan coordinated walkouts",
    "The strikes target mandatory AI-assisted grading systems",
    "Teachers cite a lack of input in technology adoption decisions",
  ],
  divergence: [
    "Left-leaning outlets frame this as a labor rights issue and support teacher autonomy",
    "Right-leaning outlets argue unions are resisting beneficial technology and holding students back",
    "Tech-focused outlets provide more nuanced analysis of AI grading effectiveness",
  ],
  sources: [
    { name: "NPR", url: "https://npr.org", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 18, opinionFact: 15, factualRigor: 88, framing: 25 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 72, sensationalism: 42, opinionFact: 35, factualRigor: 68, framing: 48 } },
    { name: "Washington Post", url: "https://washingtonpost.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 22, opinionFact: 20, factualRigor: 85, framing: 30 } },
    { name: "The Markup", url: "https://themarkup.org", tier: "independent", biasScores: { politicalLean: 42, sensationalism: 10, opinionFact: 12, factualRigor: 92, framing: 18 } },
  ],
};

const deepDive11: DeepDiveData = {
  consensus: [
    "Satellite data confirms a 42% reduction in Amazon deforestation year-over-year",
    "Strengthened enforcement and community programs are credited for the decline",
    "Deforestation is at its lowest level in fifteen years",
  ],
  divergence: [
    "Brazilian government sources emphasize policy success; opposition outlets question data methodology",
    "Environmental groups warn the progress is fragile and could reverse with political changes",
    "International outlets provide more context on the global significance than domestic ones",
  ],
  sources: [
    { name: "DW", url: "https://dw.com", tier: "international", biasScores: { politicalLean: 46, sensationalism: 12, opinionFact: 8, factualRigor: 90, framing: 16 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 14, opinionFact: 6, factualRigor: 92, framing: 14 } },
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 38, sensationalism: 18, opinionFact: 12, factualRigor: 88, framing: 22 } },
  ],
};

const deepDive12: DeepDiveData = {
  consensus: [
    "The Pentagon demonstrated a new hypersonic missile interceptor system",
    "The system responds to advances by China and Russia in hypersonic weapons",
    "Defense officials describe it as a significant technological breakthrough",
  ],
  divergence: [
    "Conservative outlets celebrate the defense advancement and advocate for increased military spending",
    "Progressive outlets question the cost and whether it escalates an arms race",
    "International outlets focus on the geopolitical implications for global security balance",
  ],
  sources: [
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 70, sensationalism: 40, opinionFact: 28, factualRigor: 74, framing: 45 } },
    { name: "AP News", url: "https://apnews.com", tier: "us_major", biasScores: { politicalLean: 50, sensationalism: 12, opinionFact: 6, factualRigor: 94, framing: 14 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 18, opinionFact: 10, factualRigor: 88, framing: 22 } },
    { name: "Center for Public Integrity", url: "https://publicintegrity.org", tier: "independent", biasScores: { politicalLean: 40, sensationalism: 15, opinionFact: 20, factualRigor: 90, framing: 30 } },
  ],
};

const deepDive13: DeepDiveData = {
  consensus: [
    "Japan's population has fallen below 120 million for the first time",
    "The birth rate has hit a new record low",
    "The decline is accelerating faster than government projections",
  ],
  divergence: [
    "Japanese domestic outlets focus on the economic implications and pension system strain",
    "Western outlets frame it as a cautionary tale for other developed nations",
    "Some sources advocate immigration reform while others emphasize pronatalist policies",
  ],
  sources: [
    { name: "NHK", url: "https://nhk.or.jp", tier: "international", biasScores: { politicalLean: 50, sensationalism: 14, opinionFact: 8, factualRigor: 94, framing: 14 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 18, opinionFact: 10, factualRigor: 90, framing: 18 } },
    { name: "New York Times", url: "https://nytimes.com", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 22, opinionFact: 16, factualRigor: 88, framing: 24 } },
  ],
};

const deepDive14: DeepDiveData = {
  consensus: [
    "Bipartisan legislation targets Google and Meta's ad exchange monopolies",
    "The bill would force major tech companies to divest advertising infrastructure",
    "Sponsors argue the current structure inflates costs for small businesses",
  ],
  divergence: [
    "Tech-critical outlets support the bill as overdue antitrust action",
    "Business outlets warn of unintended consequences for the digital advertising ecosystem",
    "Independent outlets provide more detail on lobbying efforts by tech companies against the bill",
  ],
  sources: [
    { name: "The Intercept", url: "https://theintercept.com", tier: "independent", biasScores: { politicalLean: 30, sensationalism: 22, opinionFact: 30, factualRigor: 82, framing: 35 } },
    { name: "Wall Street Journal", url: "https://wsj.com", tier: "us_major", biasScores: { politicalLean: 58, sensationalism: 14, opinionFact: 18, factualRigor: 88, framing: 25 } },
    { name: "Bloomberg", url: "https://bloomberg.com", tier: "us_major", biasScores: { politicalLean: 52, sensationalism: 10, opinionFact: 14, factualRigor: 92, framing: 20 } },
    { name: "The Markup", url: "https://themarkup.org", tier: "independent", biasScores: { politicalLean: 40, sensationalism: 8, opinionFact: 10, factualRigor: 96, framing: 14 } },
  ],
};

const deepDive15: DeepDiveData = {
  consensus: [
    "Leaders from 38 African nations gathered in Cape Town for the summit",
    "The summit focused on coordinated responses to climate-driven threats",
    "Rising sea levels, drought, and extreme heat were the primary concerns",
  ],
  divergence: [
    "African media emphasizes the need for wealthy nations to fund adaptation efforts",
    "Western outlets focus on the geopolitical dimensions and competition for influence",
    "Environmental outlets highlight the disproportionate impact on communities that contributed least to emissions",
  ],
  sources: [
    { name: "France24", url: "https://france24.com", tier: "international", biasScores: { politicalLean: 44, sensationalism: 14, opinionFact: 10, factualRigor: 88, framing: 22 } },
    { name: "Al Jazeera", url: "https://aljazeera.com", tier: "international", biasScores: { politicalLean: 42, sensationalism: 18, opinionFact: 12, factualRigor: 86, framing: 26 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 12, opinionFact: 8, factualRigor: 90, framing: 16 } },
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 38, sensationalism: 20, opinionFact: 14, factualRigor: 84, framing: 28 } },
  ],
};

const deepDive16: DeepDiveData = {
  consensus: [
    "The FDA approved the first gene therapy for sickle cell disease in children",
    "The treatment edits patients' own stem cells with a 94% success rate in trials",
    "Cost and access remain significant barriers to widespread adoption",
  ],
  divergence: [
    "Health equity outlets emphasize that the disease disproportionately affects Black communities",
    "Business outlets focus on the commercial prospects and pricing of the therapy",
    "Conservative outlets question FDA approval speed relative to other pending treatments",
  ],
  sources: [
    { name: "CNN", url: "https://cnn.com", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 20, opinionFact: 12, factualRigor: 88, framing: 18 } },
    { name: "New York Times", url: "https://nytimes.com", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 15, opinionFact: 10, factualRigor: 92, framing: 16 } },
    { name: "NPR", url: "https://npr.org", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 12, opinionFact: 8, factualRigor: 94, framing: 14 } },
    { name: "ProPublica", url: "https://propublica.org", tier: "independent", biasScores: { politicalLean: 36, sensationalism: 18, opinionFact: 15, factualRigor: 90, framing: 24 } },
  ],
};

const deepDive17: DeepDiveData = {
  consensus: [
    "The ECB maintained its benchmark rate at 2.75%",
    "Persistent wage growth concerns influenced the decision",
    "Manufacturing output continues to contract across the eurozone",
  ],
  divergence: [
    "Hawkish analysts argue the ECB should have raised rates further",
    "Dovish economists say holding rates risks deepening the manufacturing recession",
    "Southern European outlets are more critical of the decision's impact on their economies",
  ],
  sources: [
    { name: "Financial Times", url: "https://ft.com", tier: "international", biasScores: { politicalLean: 52, sensationalism: 6, opinionFact: 12, factualRigor: 96, framing: 14 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 8, opinionFact: 6, factualRigor: 94, framing: 10 } },
    { name: "DW", url: "https://dw.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 10, opinionFact: 8, factualRigor: 92, framing: 16 } },
    { name: "Bloomberg", url: "https://bloomberg.com", tier: "us_major", biasScores: { politicalLean: 54, sensationalism: 10, opinionFact: 14, factualRigor: 92, framing: 18 } },
  ],
};

const deepDive18: DeepDiveData = {
  consensus: [
    "Dangerous PFAS levels were found in groundwater near 47 military installations",
    "An estimated 2 million residents are affected by the contamination",
    "The contamination stems from firefighting foam used on military bases for decades",
  ],
  divergence: [
    "Progressive outlets push for immediate government accountability and cleanup funding",
    "Defense-aligned outlets emphasize the military's operational needs that led to PFAS use",
    "Scientific outlets debate the health risk thresholds and what constitutes a dangerous level",
  ],
  sources: [
    { name: "ProPublica", url: "https://propublica.org", tier: "independent", biasScores: { politicalLean: 34, sensationalism: 28, opinionFact: 18, factualRigor: 94, framing: 30 } },
    { name: "Washington Post", url: "https://washingtonpost.com", tier: "us_major", biasScores: { politicalLean: 38, sensationalism: 22, opinionFact: 15, factualRigor: 90, framing: 25 } },
    { name: "AP News", url: "https://apnews.com", tier: "us_major", biasScores: { politicalLean: 48, sensationalism: 14, opinionFact: 6, factualRigor: 94, framing: 14 } },
  ],
};

const deepDive19: DeepDiveData = {
  consensus: [
    "North Korea launched a submarine-based ballistic missile in the Sea of Japan",
    "Japan and South Korea immediately condemned the test",
    "The UN Security Council convened an emergency session in response",
  ],
  divergence: [
    "US outlets emphasize phillips military readiness and deterrence posture",
    "Asian outlets provide more regional context and diplomatic nuance",
    "Independent analysts debate whether the test represents a genuine capability advance",
  ],
  sources: [
    { name: "Yonhap", url: "https://en.yna.co.kr", tier: "international", biasScores: { politicalLean: 48, sensationalism: 30, opinionFact: 10, factualRigor: 86, framing: 28 } },
    { name: "NHK", url: "https://nhk.or.jp", tier: "international", biasScores: { politicalLean: 50, sensationalism: 25, opinionFact: 8, factualRigor: 90, framing: 24 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 14, opinionFact: 6, factualRigor: 94, framing: 12 } },
    { name: "CNN", url: "https://cnn.com", tier: "us_major", biasScores: { politicalLean: 44, sensationalism: 38, opinionFact: 18, factualRigor: 82, framing: 32 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 68, sensationalism: 44, opinionFact: 28, factualRigor: 72, framing: 42 } },
  ],
};

const deepDive20: DeepDiveData = {
  consensus: [
    "Gene-edited wheat showed 30% yield increase under water-stressed conditions",
    "Field trial results were published in a peer-reviewed journal",
    "The research has implications for global food security under climate change",
  ],
  divergence: [
    "Scientific outlets note rivalry between research groups and prior claims of similar breakthroughs",
    "Environmental outlets raise concerns about the ecological impact of gene-edited crops",
    "Agricultural industry sources are optimistic about commercial applications within 5 years",
  ],
  sources: [
    { name: "Nature", url: "https://nature.com", tier: "independent", biasScores: { politicalLean: 50, sensationalism: 8, opinionFact: 4, factualRigor: 98, framing: 6 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 14, opinionFact: 8, factualRigor: 90, framing: 14 } },
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 40, sensationalism: 18, opinionFact: 12, factualRigor: 86, framing: 20 } },
  ],
};

const deepDive21: DeepDiveData = {
  consensus: [
    "ERCOT projects a potential 15 GW power shortfall during peak summer demand",
    "The Texas grid remains vulnerable to extreme weather events",
    "Officials are warning of possible rolling blackouts",
  ],
  divergence: [
    "Conservative outlets blame renewable energy mandates for grid instability",
    "Progressive outlets point to deregulation and fossil fuel infrastructure failures",
    "Energy analysts debate whether natural gas or renewable intermittency is the primary risk factor",
  ],
  sources: [
    { name: "Houston Chronicle", url: "https://houstonchronicle.com", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 30, opinionFact: 15, factualRigor: 85, framing: 28 } },
    { name: "AP News", url: "https://apnews.com", tier: "us_major", biasScores: { politicalLean: 48, sensationalism: 14, opinionFact: 6, factualRigor: 94, framing: 12 } },
    { name: "Fox News", url: "https://foxnews.com", tier: "us_major", biasScores: { politicalLean: 70, sensationalism: 42, opinionFact: 30, factualRigor: 70, framing: 48 } },
    { name: "The Markup", url: "https://themarkup.org", tier: "independent", biasScores: { politicalLean: 42, sensationalism: 10, opinionFact: 12, factualRigor: 92, framing: 18 } },
  ],
};

const deepDive22: DeepDiveData = {
  consensus: [
    "China conducted live-fire military drills east of Taiwan for a third consecutive week",
    "The exercises drew sharp warnings from both Washington and Taipei",
    "Tensions in the Taiwan Strait have reached their highest point in years",
  ],
  divergence: [
    "Chinese outlets frame the exercises as legitimate sovereignty defense",
    "Western outlets portray the drills as provocative and destabilizing",
    "Taiwanese media focuses on domestic preparedness and public sentiment",
  ],
  sources: [
    { name: "South China Morning Post", url: "https://scmp.com", tier: "international", biasScores: { politicalLean: 56, sensationalism: 28, opinionFact: 16, factualRigor: 80, framing: 38 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 22, opinionFact: 10, factualRigor: 88, framing: 24 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 12, opinionFact: 6, factualRigor: 94, framing: 14 } },
    { name: "Washington Post", url: "https://washingtonpost.com", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 24, opinionFact: 16, factualRigor: 86, framing: 28 } },
    { name: "New York Times", url: "https://nytimes.com", tier: "us_major", biasScores: { politicalLean: 40, sensationalism: 20, opinionFact: 14, factualRigor: 88, framing: 26 } },
  ],
};

const deepDive23: DeepDiveData = {
  consensus: [
    "The first tranche of a $26 billion opioid settlement is reaching communities",
    "Funds are going to treatment centers and recovery programs",
    "Rural and underserved counties are the primary recipients",
  ],
  divergence: [
    "Local outlets celebrate the impact but warn funds are insufficient for the scale of the crisis",
    "Legal outlets debate whether the settlement amounts constitute adequate accountability",
    "Conservative outlets question the effectiveness of government-run treatment programs",
  ],
  sources: [
    { name: "PBS NewsHour", url: "https://pbs.org", tier: "us_major", biasScores: { politicalLean: 44, sensationalism: 10, opinionFact: 8, factualRigor: 92, framing: 14 } },
    { name: "NPR", url: "https://npr.org", tier: "us_major", biasScores: { politicalLean: 42, sensationalism: 12, opinionFact: 10, factualRigor: 90, framing: 16 } },
    { name: "ProPublica", url: "https://propublica.org", tier: "independent", biasScores: { politicalLean: 36, sensationalism: 18, opinionFact: 14, factualRigor: 92, framing: 22 } },
  ],
};

const deepDive24: DeepDiveData = {
  consensus: [
    "The Northern Sea Route became navigable in mid-March for the first time",
    "Arctic ice coverage has hit a new record low",
    "The route opening raises both commercial and environmental concerns",
  ],
  divergence: [
    "Environmental outlets frame this as an alarming climate milestone",
    "Business outlets emphasize the shipping and economic opportunities",
    "Scientific outlets debate the rate of Arctic warming versus model predictions",
  ],
  sources: [
    { name: "The Guardian", url: "https://theguardian.com", tier: "international", biasScores: { politicalLean: 38, sensationalism: 28, opinionFact: 14, factualRigor: 86, framing: 28 } },
    { name: "BBC", url: "https://bbc.com", tier: "international", biasScores: { politicalLean: 48, sensationalism: 16, opinionFact: 8, factualRigor: 92, framing: 16 } },
    { name: "Reuters", url: "https://reuters.com", tier: "international", biasScores: { politicalLean: 50, sensationalism: 10, opinionFact: 6, factualRigor: 94, framing: 12 } },
    { name: "Bloomberg", url: "https://bloomberg.com", tier: "us_major", biasScores: { politicalLean: 54, sensationalism: 14, opinionFact: 12, factualRigor: 90, framing: 20 } },
  ],
};

const deepDiveMap: Record<string, DeepDiveData> = {
  "1": deepDive1, "2": deepDive2, "3": deepDive3, "4": deepDive4,
  "5": deepDive5, "6": deepDive6, "7": deepDive7, "8": deepDive8,
  "9": deepDive9, "10": deepDive10, "11": deepDive11, "12": deepDive12,
  "13": deepDive13, "14": deepDive14, "15": deepDive15, "16": deepDive16,
  "17": deepDive17, "18": deepDive18, "19": deepDive19, "20": deepDive20,
  "21": deepDive21, "22": deepDive22, "23": deepDive23, "24": deepDive24,
};

export const mockStories: Story[] = [
  {
    id: "1",
    title: "EU and China reach landmark trade agreement after months of tense negotiations",
    summary:
      "The European Union and China have finalized a comprehensive trade deal covering semiconductors, green technology, and agricultural exports. The agreement removes tariffs on key goods while establishing new standards for technology transfer.",
    source: { name: "Reuters", count: 24 },
    category: "Economy",
    publishedAt: "2026-03-18T06:00:00Z",
    biasScores: {
      politicalLean: 48,
      sensationalism: 15,
      opinionFact: 12,
      factualRigor: 88,
      framing: 22,
    },
    section: "world",
    importance: 100,
    deepDive: deepDive1,
  },
  {
    id: "2",
    title: "Senate passes sweeping infrastructure bill with bipartisan support",
    summary:
      "A $1.2 trillion infrastructure package cleared the Senate 71-28, allocating funds for bridge repairs, broadband expansion, and electric vehicle charging networks across all 50 states.",
    source: { name: "AP News", count: 18 },
    category: "Politics",
    publishedAt: "2026-03-18T04:30:00Z",
    biasScores: {
      politicalLean: 45,
      sensationalism: 20,
      opinionFact: 8,
      factualRigor: 92,
      framing: 18,
    },
    section: "us",
    importance: 95,
    deepDive: deepDive2,
  },
  {
    id: "3",
    title: "WHO declares end to mpox global health emergency as vaccination campaigns succeed",
    summary:
      "The World Health Organization has officially lifted the global health emergency status for mpox, citing successful vaccination rollouts in Africa and declining case numbers worldwide.",
    source: { name: "BBC", count: 15 },
    category: "Health",
    publishedAt: "2026-03-18T05:15:00Z",
    biasScores: {
      politicalLean: 50,
      sensationalism: 12,
      opinionFact: 5,
      factualRigor: 95,
      framing: 10,
    },
    section: "world",
    importance: 90,
    deepDive: deepDive3,
  },
  {
    id: "4",
    title: "Federal Reserve signals potential rate cut amid cooling inflation data",
    summary:
      "Fed Chair indicated openness to lowering interest rates in the coming months as consumer price index shows sustained decline toward the 2% target.",
    source: { name: "Wall Street Journal", count: 21 },
    category: "Economy",
    publishedAt: "2026-03-17T22:00:00Z",
    biasScores: {
      politicalLean: 52,
      sensationalism: 25,
      opinionFact: 18,
      factualRigor: 85,
      framing: 30,
    },
    section: "us",
    importance: 88,
    deepDive: deepDive4,
  },
  {
    id: "5",
    title: "Ukraine and Russia agree to 90-day ceasefire brokered by Turkey and UAE",
    summary:
      "After weeks of shuttle diplomacy, both sides have committed to a temporary halt in hostilities. The agreement includes provisions for prisoner exchanges and humanitarian corridor access.",
    source: { name: "Al Jazeera", count: 28 },
    category: "Conflict",
    publishedAt: "2026-03-18T03:00:00Z",
    biasScores: {
      politicalLean: 42,
      sensationalism: 30,
      opinionFact: 15,
      factualRigor: 78,
      framing: 35,
    },
    section: "world",
    importance: 98,
    deepDive: deepDive5,
  },
  {
    id: "6",
    title: "California wildfire season begins early as drought conditions persist",
    summary:
      "Three major fires have broken out across Southern California, forcing evacuations in Ventura and San Bernardino counties. Climate scientists warn this could be the most severe season in a decade.",
    source: { name: "Los Angeles Times", count: 12 },
    category: "Environment",
    publishedAt: "2026-03-17T20:00:00Z",
    biasScores: {
      politicalLean: 38,
      sensationalism: 45,
      opinionFact: 22,
      factualRigor: 80,
      framing: 40,
    },
    section: "us",
    importance: 82,
    deepDive: deepDive6,
  },
  {
    id: "7",
    title: "India launches ambitious solar power satellite prototype into orbit",
    summary:
      "ISRO successfully deployed a test satellite capable of beaming solar energy to ground stations, marking a milestone in space-based renewable energy technology.",
    source: { name: "The Guardian", count: 14 },
    category: "Tech",
    publishedAt: "2026-03-18T01:00:00Z",
    biasScores: {
      politicalLean: 50,
      sensationalism: 18,
      opinionFact: 10,
      factualRigor: 90,
      framing: 15,
    },
    section: "world",
    importance: 85,
    deepDive: deepDive7,
  },
  {
    id: "8",
    title: "Supreme Court to hear challenge to federal surveillance law Section 702",
    summary:
      "The justices agreed to review whether warrantless surveillance of Americans' international communications violates the Fourth Amendment, in a case with major implications for privacy rights.",
    source: { name: "Washington Post", count: 16 },
    category: "Politics",
    publishedAt: "2026-03-17T18:00:00Z",
    biasScores: {
      politicalLean: 40,
      sensationalism: 22,
      opinionFact: 20,
      factualRigor: 88,
      framing: 28,
    },
    section: "us",
    importance: 80,
    deepDive: deepDive8,
  },
  {
    id: "9",
    title: "Global semiconductor shortage eases as new fabs come online in Arizona and Germany",
    summary:
      "TSMC and Intel report increased output from newly operational fabrication plants, signaling relief for automakers and electronics manufacturers after three years of supply constraints.",
    source: { name: "Bloomberg", count: 19 },
    category: "Tech",
    publishedAt: "2026-03-17T16:00:00Z",
    biasScores: {
      politicalLean: 55,
      sensationalism: 10,
      opinionFact: 15,
      factualRigor: 92,
      framing: 20,
    },
    section: "world",
    importance: 78,
    deepDive: deepDive9,
  },
  {
    id: "10",
    title: "Teachers' unions announce nationwide strike over AI classroom policies",
    summary:
      "Education unions in 14 states plan coordinated walkouts protesting mandatory AI-assisted grading systems and the lack of teacher input in technology adoption decisions.",
    source: { name: "NPR", count: 11 },
    category: "Culture",
    publishedAt: "2026-03-17T14:00:00Z",
    biasScores: {
      politicalLean: 35,
      sensationalism: 38,
      opinionFact: 30,
      factualRigor: 75,
      framing: 42,
    },
    section: "us",
    importance: 76,
    deepDive: deepDive10,
  },
  {
    id: "11",
    title: "Brazilian Amazon deforestation drops to lowest level in fifteen years",
    summary:
      "Satellite data confirms a 42% reduction in forest loss compared to the previous year, attributed to strengthened enforcement and community-led conservation programs.",
    source: { name: "DW", count: 10 },
    category: "Environment",
    publishedAt: "2026-03-17T12:00:00Z",
    biasScores: {
      politicalLean: 45,
      sensationalism: 14,
      opinionFact: 8,
      factualRigor: 90,
      framing: 18,
    },
    section: "world",
    importance: 74,
    deepDive: deepDive11,
  },
  {
    id: "12",
    title: "Pentagon unveils next-generation hypersonic missile defense system",
    summary:
      "The Department of Defense demonstrated a new interceptor capable of tracking and neutralizing hypersonic threats, responding to advances by China and Russia in the weapons category.",
    source: { name: "Fox News", count: 13 },
    category: "Conflict",
    publishedAt: "2026-03-17T10:00:00Z",
    biasScores: {
      politicalLean: 68,
      sensationalism: 42,
      opinionFact: 25,
      factualRigor: 72,
      framing: 48,
    },
    section: "us",
    importance: 72,
    deepDive: deepDive12,
  },
  {
    id: "13",
    title: "Japan's population falls below 120 million as birth rate hits record low",
    summary:
      "New census data reveals Japan's population decline is accelerating faster than projected, prompting renewed debate over immigration reform and economic sustainability.",
    source: { name: "NHK", count: 9 },
    category: "Culture",
    publishedAt: "2026-03-17T08:00:00Z",
    biasScores: {
      politicalLean: 50,
      sensationalism: 20,
      opinionFact: 12,
      factualRigor: 94,
      framing: 16,
    },
    section: "world",
    importance: 70,
    deepDive: deepDive13,
  },
  {
    id: "14",
    title: "Bipartisan bill aims to break up major tech monopolies in online advertising",
    summary:
      "Senators introduced legislation that would force Google and Meta to divest their ad exchanges, arguing the current structure stifles competition and inflates costs for small businesses.",
    source: { name: "The Intercept", count: 8 },
    category: "Tech",
    publishedAt: "2026-03-17T06:00:00Z",
    biasScores: {
      politicalLean: 32,
      sensationalism: 28,
      opinionFact: 35,
      factualRigor: 78,
      framing: 38,
    },
    section: "us",
    importance: 68,
    deepDive: deepDive14,
  },
  {
    id: "15",
    title: "South Africa hosts first pan-African climate adaptation summit",
    summary:
      "Leaders from 38 nations gathered in Cape Town to coordinate responses to rising sea levels, drought, and extreme heat events disproportionately affecting the continent.",
    source: { name: "France24", count: 11 },
    category: "Environment",
    publishedAt: "2026-03-16T20:00:00Z",
    biasScores: {
      politicalLean: 44,
      sensationalism: 16,
      opinionFact: 10,
      factualRigor: 86,
      framing: 24,
    },
    section: "world",
    importance: 66,
    deepDive: deepDive15,
  },
  {
    id: "16",
    title: "FDA approves first gene therapy for sickle cell disease in children",
    summary:
      "The one-time treatment, which edits patients' own stem cells, showed a 94% success rate in clinical trials. Cost and access concerns remain significant barriers.",
    source: { name: "CNN", count: 17 },
    category: "Health",
    publishedAt: "2026-03-16T18:00:00Z",
    biasScores: {
      politicalLean: 48,
      sensationalism: 22,
      opinionFact: 12,
      factualRigor: 88,
      framing: 20,
    },
    section: "us",
    importance: 64,
    deepDive: deepDive16,
  },
  {
    id: "17",
    title: "European Central Bank holds rates steady despite mixed economic signals",
    summary:
      "The ECB maintained its benchmark interest rate at 2.75%, citing persistent wage growth concerns even as manufacturing output continues to contract across the eurozone.",
    source: { name: "Financial Times", count: 14 },
    category: "Economy",
    publishedAt: "2026-03-16T16:00:00Z",
    biasScores: {
      politicalLean: 52,
      sensationalism: 8,
      opinionFact: 10,
      factualRigor: 95,
      framing: 14,
    },
    section: "world",
    importance: 62,
    deepDive: deepDive17,
  },
  {
    id: "18",
    title: "Investigation reveals widespread PFAS contamination near military bases",
    summary:
      "A ProPublica investigation found dangerous levels of forever chemicals in groundwater near 47 active military installations, affecting an estimated 2 million residents.",
    source: { name: "ProPublica", count: 7 },
    category: "Health",
    publishedAt: "2026-03-16T14:00:00Z",
    biasScores: {
      politicalLean: 35,
      sensationalism: 35,
      opinionFact: 20,
      factualRigor: 92,
      framing: 32,
    },
    section: "us",
    importance: 60,
    deepDive: deepDive18,
  },
  {
    id: "19",
    title: "North Korea conducts submarine-launched ballistic missile test in Sea of Japan",
    summary:
      "The launch drew immediate condemnation from Japan and South Korea. US Pacific Command raised alert levels as the UN Security Council convened an emergency session.",
    source: { name: "Yonhap", count: 20 },
    category: "Conflict",
    publishedAt: "2026-03-16T12:00:00Z",
    biasScores: {
      politicalLean: 50,
      sensationalism: 40,
      opinionFact: 14,
      factualRigor: 82,
      framing: 36,
    },
    section: "world",
    importance: 58,
    deepDive: deepDive19,
  },
  {
    id: "20",
    title: "CRISPR breakthrough enables high-yield drought-resistant wheat varieties",
    summary:
      "Researchers published results from field trials showing gene-edited wheat producing 30% more grain under water-stressed conditions, with implications for global food security.",
    source: { name: "Nature", count: 6 },
    category: "Science",
    publishedAt: "2026-03-16T10:00:00Z",
    biasScores: {
      politicalLean: 50,
      sensationalism: 12,
      opinionFact: 5,
      factualRigor: 96,
      framing: 8,
    },
    section: "world",
    importance: 56,
    deepDive: deepDive20,
  },
  {
    id: "21",
    title: "Texas grid operator warns of potential rolling blackouts ahead of summer heat",
    summary:
      "ERCOT projections indicate the state's power grid may face a 15 GW shortfall during peak demand, raising fears of a repeat of the 2021 grid failure under extreme conditions.",
    source: { name: "Houston Chronicle", count: 9 },
    category: "Environment",
    publishedAt: "2026-03-16T08:00:00Z",
    biasScores: {
      politicalLean: 42,
      sensationalism: 38,
      opinionFact: 18,
      factualRigor: 80,
      framing: 35,
    },
    section: "us",
    importance: 54,
    deepDive: deepDive21,
  },
  {
    id: "22",
    title: "Taiwan Strait tensions rise as China expands military exercises",
    summary:
      "China's People's Liberation Army conducted live-fire drills in waters east of Taiwan for the third consecutive week, drawing sharp warnings from Washington and Taipei.",
    source: { name: "South China Morning Post", count: 16 },
    category: "Conflict",
    publishedAt: "2026-03-16T06:00:00Z",
    biasScores: {
      politicalLean: 55,
      sensationalism: 35,
      opinionFact: 18,
      factualRigor: 76,
      framing: 42,
    },
    section: "world",
    importance: 52,
    deepDive: deepDive22,
  },
  {
    id: "23",
    title: "Nationwide opioid settlement funds begin reaching rural communities",
    summary:
      "The first tranche of a $26 billion settlement with major pharmaceutical distributors is now funding treatment centers and recovery programs in underserved rural counties.",
    source: { name: "PBS NewsHour", count: 8 },
    category: "Health",
    publishedAt: "2026-03-15T22:00:00Z",
    biasScores: {
      politicalLean: 46,
      sensationalism: 14,
      opinionFact: 10,
      factualRigor: 90,
      framing: 16,
    },
    section: "us",
    importance: 50,
    deepDive: deepDive23,
  },
  {
    id: "24",
    title: "Arctic shipping route opens two months early as ice coverage hits new low",
    summary:
      "The Northern Sea Route became navigable in mid-March for the first time in recorded history, raising both commercial opportunities and environmental alarm.",
    source: { name: "The Guardian", count: 12 },
    category: "Environment",
    publishedAt: "2026-03-15T18:00:00Z",
    biasScores: {
      politicalLean: 40,
      sensationalism: 30,
      opinionFact: 15,
      factualRigor: 85,
      framing: 28,
    },
    section: "world",
    importance: 48,
    deepDive: deepDive24,
  },
];

/**
 * Return time-ago string from ISO date.
 */
export function timeAgo(dateStr: string): string {
  const now = new Date("2026-03-18T08:00:00Z");
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}
