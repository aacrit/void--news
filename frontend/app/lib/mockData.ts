import { Story } from "./types";

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
  },
  {
    id: "10",
    title: "Teachers' unions announce nationwide strike over AI classroom policies",
    summary:
      "Education unions in 14 states plan coordinated walkouts protesting mandatory AI-assisted grading systems and the lack of teacher input in technology adoption decisions.",
    source: { name: "NPR", count: 11 },
    category: "Society",
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
  },
  {
    id: "13",
    title: "Japan's population falls below 120 million as birth rate hits record low",
    summary:
      "New census data reveals Japan's population decline is accelerating faster than projected, prompting renewed debate over immigration reform and economic sustainability.",
    source: { name: "NHK", count: 9 },
    category: "Society",
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
  },
  {
    id: "21",
    title: "Texas grid operator warns of potential rolling blackouts ahead of summer heat",
    summary:
      "ERCOT projections indicate the state's power grid may face a 15 GW shortfall during peak demand, raising fears of a repeat of the 2021 grid failure under extreme conditions.",
    source: { name: "Houston Chronicle", count: 9 },
    category: "Energy",
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
  },
  {
    id: "22",
    title: "Taiwan Strait tensions rise as China expands military exercises",
    summary:
      "China's People's Liberation Army conducted live-fire drills in waters east of Taiwan for the third consecutive week, drawing sharp warnings from Washington and Taipei.",
    source: { name: "South China Morning Post", count: 16 },
    category: "Diplomacy",
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
