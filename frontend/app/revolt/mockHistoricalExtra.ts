/* ===========================================================================
   void --revolt — additional historical mock entries (MVP bench).
   Kept separate from mockData.ts for readability; spread into MOCK_HISTORICAL.
   =========================================================================== */

import type { Revolution } from './types';

export const MOCK_HISTORICAL_EXTRA: Revolution[] = [
  {
  id: "russian-revolution",
  slug: "russian-revolution",
  title: "The Russian Revolution",
  subtitle: "Eight months separated a liberal republic from a one-party dictatorship",
  era: "modern-nationalist",
  region: "europe",
  country: "Russia",
  revoltType: "communist",
  status: "concluded",
  dateDisplay: "February 1917 to 1923 (civil war conclusion)",
  dateStart: 1917,
  dateEnd: 1923,
  summary: "Bread shortages and 1.7 million war dead broke the Romanov monarchy in five days of Petrograd strikes. A Provisional Government tried to keep fighting Germany while soldiers deserted by the hundred thousand. On October 25, Bolshevik Red Guards seized the Winter Palace with fewer than ten casualties, then spent five years defeating White armies, Allied interventionists, and rival socialists to hold the state they had taken.",
  significance: "The first Marxist government to hold state power for more than a few weeks, and the template every subsequent 20th-century communist seizure of power copied or reacted against.",
  analyticalOutlook: "A movement that seized power in a near-vacuum, then spent five years and roughly 7 to 12 million civil war deaths converting a fragile coup into a durable one-party state.",
  grievances: [
    { kind: "War exhaustion", intensity: 95, evidence: "1.7 million Russian soldiers killed by early 1917; desertions ran over 200,000 in the month before the February uprising." },
    { kind: "Food scarcity", intensity: 90, evidence: "Petrograd bread rationing cut to 1 pound per person per day in February 1917; women textile workers began the strike that triggered the revolution on International Women's Day." },
    { kind: "Land hunger", intensity: 85, evidence: "Roughly 80 percent of Russians were peasants; nobles and the church held disproportionate farmland while peasant plots shrank across the 1861 to 1917 period." },
    { kind: "Autocratic rigidity", intensity: 75, evidence: "Nicholas II dissolved or restricted the Duma repeatedly after 1906 and refused ministers responsible to it even as the war effort collapsed." }
  ],
  actors: [
    { actorType: "vanguard", name: "Bolshevik Party", description: "Lenin's faction of the Russian Social Democratic Labour Party, roughly 24,000 members in February 1917, over 350,000 by October.", roleInArc: "Organized the October seizure of power under the slogan 'Peace, Land, Bread'", defected: false },
    { actorType: "old-regime", name: "Provisional Government", description: "Liberal-to-moderate-socialist government formed after the Tsar's abdication, led successively by Lvov and Kerensky.", roleInArc: "Held nominal power for eight months, lost legitimacy by continuing the war", defected: false },
    { actorType: "masses", name: "Petrograd Soviet", description: "Elected council of workers' and soldiers' deputies, meeting alongside the Provisional Government from February 1917.", roleInArc: "Formed the 'dual power' rival authority the Bolsheviks eventually captured", defected: false },
    { actorType: "military-defectors", name: "Imperial Russian Army", description: "Roughly 7 million men under arms by 1917, exhausted by the Brusilov offensive's 1916 casualties.", roleInArc: "Mass desertion and the Petrograd garrison's refusal to fire on crowds ended the monarchy", defected: true },
    { actorType: "old-regime", name: "Nicholas II", description: "Tsar of Russia since 1894, commanded the army in person from 1915.", roleInArc: "Abdicated March 2, 1917 after generals withdrew their support", defected: false }
  ],
  tactics: [
    { tacticType: "general-strike", description: "Petrograd factory strikes beginning February 23, 1917 grew from 90,000 to over 300,000 workers within four days.", prominence: "primary, February phase" },
    { tacticType: "armed-insurgency", description: "Red Guards, sailors from Kronstadt, and Bolshevik-aligned soldiers occupied Petrograd's telegraph, bridges, and stations overnight on October 24-25.", prominence: "primary, October phase" },
    { tacticType: "parallel-institutions", description: "Bolsheviks won majorities in the Petrograd and Moscow soviets by September 1917 and used soviet structures to coordinate the October action.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "War and Famine", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "Three years of war losses and urban food shortages hollow out support for the monarchy.", keyEvents: ["1916 Brusilov offensive casualties exceed 500,000", "Petrograd bread rationing introduced late 1916"] },
    { phase: "the-spark", label: "February Days", tStart: 0.22, tEnd: 0.34, intensity: 60, reached: true, summary: "Petrograd strikes escalate into a five-day uprising; the Petrograd garrison mutinies rather than fire on crowds, and the Tsar abdicates within a week.", keyEvents: ["Strikes begin February 23, 1917", "Nicholas II abdicates March 2, 1917"] },
    { phase: "moderate-phase", label: "Dual Power", tStart: 0.34, tEnd: 0.48, intensity: 45, reached: true, summary: "The Provisional Government and the Petrograd Soviet govern in uneasy parallel while the war continues.", keyEvents: ["Lenin returns to Petrograd in the sealed train, April 1917", "July Days street violence in Petrograd"] },
    { phase: "dual-power", label: "Kornilov Affair to October Seizure", tStart: 0.48, tEnd: 0.60, intensity: 65, reached: true, summary: "General Kornilov's failed August coup arms the Bolshevik-aligned Red Guards, who occupy Petrograd's infrastructure and storm the Winter Palace in October with minimal resistance.", keyEvents: ["Kornilov affair, August 1917", "Bolsheviks win Petrograd Soviet majority, September 1917", "Winter Palace falls, October 25, 1917 (Julian calendar), fewer than ten deaths"] },
    { phase: "radical-phase", label: "Civil War", tStart: 0.60, tEnd: 0.72, intensity: 95, reached: true, summary: "Red, White, and foreign interventionist armies fight across the former empire.", keyEvents: ["Civil war fighting 1918-1921", "Execution of the Romanov family, July 1918", "Allied intervention forces land at Archangel and Vladivostok"] },
    { phase: "terror-virtue", label: "Red Terror and War Communism", tStart: 0.72, tEnd: 0.84, intensity: 85, reached: true, summary: "The Cheka conducts mass executions and the state seizes grain by force, provoking peasant uprisings the Red Army crushes in turn.", keyEvents: ["Red Terror declared, September 1918", "Kronstadt rebellion crushed, March 1921"] },
    { phase: "consolidation", label: "New Economic Policy and the USSR", tStart: 0.92, tEnd: 1.00, intensity: 50, reached: true, summary: "The Bolsheviks defeat the last White armies, retreat from forced requisitioning under the NEP, and formalize one-party rule under the new Soviet Union.", keyEvents: ["New Economic Policy adopted, 1921", "USSR formally established, December 1922"] }
  ],
  ateItsChildren: true,
  outcome: "consolidated-autocracy",
  peakParticipationPct: null,
  peakParticipationDisplay: "over 300,000 Petrograd strikers by February 26, 1917",
  crossedParticipationThreshold: null,
  militaryDefection: "full",
  foreignIntervention: "direct-military",
  durationDays: 2160,
  deathToll: "7 to 12 million dead in the ensuing civil war, including famine and disease deaths",
  deathTollLow: 7000000,
  deathTollHigh: 12000000,
  regimeBefore: "monarchy",
  regimeAfter: "one-party",
  democratizationDelta: -3,
  successFactors: [
    { factorKey: "military-defection", label: "Security force defection", framework: "chenoweth", status: "Petrograd garrison refused orders to fire on crowds in February 1917; full army collapse followed by autumn", direction: "favors-movement", baseRate: "Security force defection is the single strongest predictor of movement success across both nonviolent and armed campaigns", rationale: "The February uprising succeeded within days once garrison troops joined strikers rather than suppressing them; the October seizure met almost no armed resistance because loyal forces had evaporated.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "elite-fracture", label: "Elite and military fracture", framework: "skocpol", status: "Generals withdrew support from the Tsar in March 1917; the officer corps later split between Red and White armies", direction: "favors-movement", baseRate: "Skocpol identifies state breakdown via war strain and elite defection as a precondition for social revolution, distinct from ideology or leadership", rationale: "Skocpol's States and Social Revolutions uses 1917 Russia as a central case for revolution driven by international military pressure fracturing the state apparatus before any revolutionary organization could have engineered it alone.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "armed-campaign-rate", label: "Armed campaign base rate", framework: "chenoweth", status: "The October seizure and subsequent civil war were armed; nonviolent civil resistance was not the primary mechanism after February", direction: "indeterminate", baseRate: "Chenoweth and Stephan find armed campaigns succeed in roughly 26 percent of cases historically, versus about 53 percent for primarily nonviolent campaigns", rationale: "The Bolsheviks' success came less from mass civil resistance than from a small, disciplined party exploiting a state that had already collapsed via military defeat, complicating a clean armed-versus-nonviolent comparison.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] }
  ],
  keyFigures: [
    { name: "Vladimir Lenin", role: "Bolshevik Party leader, first head of the Soviet government", born: 1870, died: 1924, wikipedia: "https://en.wikipedia.org/wiki/Vladimir_Lenin" },
    { name: "Alexander Kerensky", role: "Provisional Government prime minister from July 1917", born: 1881, died: 1970, wikipedia: "https://en.wikipedia.org/wiki/Alexander_Kerensky" },
    { name: "Leon Trotsky", role: "Petrograd Soviet chairman, organizer of the October insurrection and the Red Army", born: 1879, died: 1940, wikipedia: "https://en.wikipedia.org/wiki/Leon_Trotsky" },
    { name: "Nicholas II", role: "Last Tsar of Russia, abdicated March 1917", born: 1868, died: 1918, wikipedia: "https://en.wikipedia.org/wiki/Nicholas_II_of_Russia" }
  ],
  legacyPoints: [
    "Established the Soviet Union, which endured as a global superpower until its 1991 dissolution.",
    "Provided the organizational template (vanguard party, soviets, armed insurrection) copied or adapted by later communist movements in China, Cuba, and Vietnam.",
    "Triggered the founding of the Third International in 1919, exporting Bolshevik organizing methods to Communist parties worldwide.",
    "The civil war's Red Terror and later Stalinist purges became the reference case for the 'revolution eats its own children' pattern of radical movements turning on their founders."
  ],
  perspectives: [
    {
      id: "bolshevik-revolutionary",
      viewpoint: "Bolshevik organizer",
      viewpointType: "revolutionary",
      regionOrigin: "europe",
      narrative: "To Bolshevik organizers, October was not a coup but the rescue of a revolution the Provisional Government had betrayed by continuing an unpopular war and stalling land reform. The soviets, not a self-appointed cabinet, represented the workers and soldiers who had actually overthrown the Tsar.",
      keyArguments: ["The Provisional Government lacked a popular mandate and kept fighting a war soldiers had already abandoned", "Soviet power represented direct working-class representation absent from the liberal cabinet"],
      emphasized: ["Land and peace as immediate popular demands", "The soviets as organic democratic bodies"],
      omitted: ["The Bolsheviks' own minority status in the Constituent Assembly election of November 1917, which they dissolved by force in January 1918"],
      notableQuotes: [{ text: "All power to the soviets", speaker: "Bolshevik slogan, 1917", context: "Central campaign slogan through the spring and summer of 1917" }]
    },
    {
      id: "academic-structural",
      viewpoint: "Structural historian",
      viewpointType: "academic",
      regionOrigin: "global",
      narrative: "Structural historians read 1917 as a case where total war broke the Russian state's capacity to govern before any organized opposition could take credit. The Bolsheviks did not cause the collapse; they were the best-organized faction positioned to exploit it once it happened.",
      keyArguments: ["State breakdown from military strain preceded and enabled the political vacuum both revolutions filled", "The Bolsheviks succeeded through organizational discipline in a fluid, disintegrating environment rather than mass popular consensus"],
      emphasized: ["Fiscal and military collapse of the Tsarist state", "The narrowness of the October vote of support relative to Russia's population"],
      omitted: ["The lived urgency of famine and casualties driving individual participants, which structural analysis tends to flatten"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "iranian-revolution", targetTitle: "The Iranian Revolution", type: "parallel", description: "Both replaced a monarchy with an ideologically disciplined minority movement that outmaneuvered broader, less organized coalitions during the transition." },
    { targetSlug: "arab-spring", targetTitle: "The Arab Spring", type: "counter-example", description: "Where 1917's Bolsheviks had a disciplined party ready to fill the power vacuum, most 2011 Arab Spring uprisings lacked an equivalent organized successor, producing different outcomes from a similar collapse of the old order." }
  ],
  media: [],
  relatedRevoltSlugs: ["iranian-revolution", "fall-of-communism-1989"],
  relatedHistorySlugs: ["russian-revolution"],
  published: true
},
{
  id: "iranian-revolution",
  slug: "iranian-revolution",
  title: "The Iranian Revolution",
  subtitle: "A monarch with the region's fifth-largest army fled without firing his forces",
  era: "people-power",
  region: "middle-east",
  country: "Iran",
  revoltType: "religious-theocratic",
  status: "concluded",
  dateDisplay: "January 1978 to April 1979",
  dateStart: 1978,
  dateEnd: 1979,
  summary: "A planted newspaper article insulting exiled cleric Ruhollah Khomeini in January 1978 set off a cycle of protest and mourning marches that repeated every 40 days under Shia mourning custom, each round larger than the last. By September 1978 over a million marched in Tehran. Strikes shut down the oil industry in December. The Shah left the country on January 16, 1979; Khomeini returned from exile on February 1 to a crowd estimated near 3 million and the monarchy's remaining army command declared neutrality within two weeks.",
  significance: "The only 20th-century revolution to replace a monarchy with a clerical theocracy, and the event that made political Islam an organizing template for opposition movements across the Muslim world.",
  analyticalOutlook: "A broad secular-religious coalition that overthrew the monarchy together, after which the best-organized faction, Khomeini's clergy, out-maneuvered its former allies within roughly two years.",
  grievances: [
    { kind: "Political repression", intensity: 85, evidence: "SAVAK, the Shah's secret police, was widely documented by Amnesty International in the 1970s for torture and the detention of thousands of political prisoners." },
    { kind: "Rapid Westernization and secularization", intensity: 75, evidence: "The Shah's White Revolution land reforms and 1976 replacement of the Islamic calendar with an imperial calendar angered both clergy and traditional bazaar merchants." },
    { kind: "Economic dislocation", intensity: 70, evidence: "Oil-boom inflation ran near 25 percent by 1977 while rural migrants crowded into Tehran shantytowns without matching wage growth." },
    { kind: "Perceived foreign domination", intensity: 65, evidence: "The 1953 Anglo-American-backed coup that restored the Shah after he fled Mossadegh's nationalist government remained a live grievance a quarter-century later." }
  ],
  actors: [
    { actorType: "religious-clergy", name: "Ayatollah Ruhollah Khomeini", description: "Shia cleric exiled since 1964, directing the movement from Najaf and then Paris via cassette-taped sermons smuggled into Iran.", roleInArc: "Became the unifying symbol and eventual leader of the post-revolutionary state", defected: false },
    { actorType: "old-regime", name: "Mohammad Reza Pahlavi", description: "Shah of Iran since 1941, commanded one of the largest militaries in the Middle East.", roleInArc: "Left Iran on January 16, 1979 and died in exile in 1980", defected: false },
    { actorType: "masses", name: "National Front and Islamic-secular coalition", description: "Liberal nationalist, leftist, and bazaar merchant groups that joined the anti-Shah marches alongside religious networks.", roleInArc: "Provided early organizational and street numbers before being marginalized after 1979", defected: false },
    { actorType: "military-defectors", name: "Imperial Iranian Army", description: "Roughly 400,000 strong, US-equipped, the Shah's primary instrument of control.", roleInArc: "Declared neutrality on February 11, 1979, ending the monarchy's last means of resistance", defected: true },
    { actorType: "religious-clergy", name: "Shia mosque and seminary network", description: "Existing religious infrastructure across Iran's cities used to organize mourning marches and distribute Khomeini's messages.", roleInArc: "Supplied the organizational backbone that outlasted the secular coalition", defected: false }
  ],
  tactics: [
    { tacticType: "mass-demonstration", description: "Marches every 40 days observing Shia mourning rites for prior protest deaths, each cycle drawing larger crowds through 1978.", prominence: "primary" },
    { tacticType: "general-strike", description: "Oil workers struck in October and December 1978, cutting production from 6 million to under 1 million barrels a day and crippling state revenue.", prominence: "primary" },
    { tacticType: "digital-mobilization", description: "Khomeini's speeches recorded on cassette tape in Paris were smuggled into Iran and copied for mosque distribution, bypassing state media.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "SAVAK Repression and Inflation", tStart: 0.00, tEnd: 0.12, intensity: 35, reached: true, summary: "Political repression and oil-boom inflation build resentment across secular and religious opposition alike.", keyEvents: ["SAVAK arrests documented by Amnesty International through the mid-1970s", "Inflation near 25 percent by 1977"] },
    { phase: "the-spark", label: "Qom Protests and the 40-Day Cycle", tStart: 0.22, tEnd: 0.34, intensity: 55, reached: true, summary: "A state-planted newspaper attack on Khomeini triggers protests in Qom; the 40-day Shia mourning cycle turns each crackdown into the next protest's cause.", keyEvents: ["Qom protests, January 1978", "Black Friday shootings in Tehran's Jaleh Square, September 8, 1978"] },
    { phase: "moderate-phase", label: "General Strikes", tStart: 0.34, tEnd: 0.48, intensity: 65, reached: true, summary: "Oil workers and civil servants strike nationwide, paralyzing the state's revenue and administration.", keyEvents: ["Oil worker strikes begin October 1978", "Oil production falls below 1 million barrels/day by December 1978"] },
    { phase: "dual-power", label: "The Shah Departs, Khomeini Returns", tStart: 0.48, tEnd: 0.60, intensity: 75, reached: true, summary: "The Shah appoints a caretaker government and leaves the country; Khomeini returns to a welcome of millions, and within two weeks the military high command declares neutrality.", keyEvents: ["Shah departs Iran, January 16, 1979", "Khomeini returns to Tehran, February 1, 1979", "Military declares neutrality, February 11, 1979"] },
    { phase: "radical-phase", label: "Consolidation of Clerical Rule", tStart: 0.60, tEnd: 0.72, intensity: 75, reached: true, summary: "Khomeini's faction sidelines secular and leftist former allies, culminating in a referendum establishing the Islamic Republic.", keyEvents: ["Islamic Republic referendum, March 30-31, 1979, reported 98 percent in favor", "New constitution establishing the Supreme Leader adopted December 1979"] }
  ],
  ateItsChildren: true,
  outcome: "consolidated-autocracy",
  peakParticipationPct: null,
  peakParticipationDisplay: "over 2 million marchers in Tehran on Ashura, December 10-11, 1978",
  crossedParticipationThreshold: true,
  militaryDefection: "partial",
  foreignIntervention: "diplomatic",
  durationDays: 455,
  deathToll: "estimates of deaths during the uprising itself range roughly 500 to 2,000; post-revolutionary tribunal executions add further thousands through 1979-1981",
  deathTollLow: 500,
  deathTollHigh: 2000,
  regimeBefore: "monarchy",
  regimeAfter: "theocracy",
  democratizationDelta: -1,
  successFactors: [
    { factorKey: "participation-threshold", label: "3.5 percent participation rule", framework: "chenoweth", status: "Tehran marches alone drew crowds estimated near 2 to 3 percent of Iran's roughly 37 million population on peak days in December 1978 and February 1979", direction: "favors-movement", baseRate: "Chenoweth's research finds no campaign that achieved active participation from 3.5 percent of a population has failed to achieve its aims", rationale: "The December 1978 Ashura marches and Khomeini's February 1979 return drew crowds in the low millions nationwide, plausibly crossing or approaching the 3.5 percent threshold when combined with the general strikes' broader participation.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "military-defection", label: "Security force defection", framework: "chenoweth", status: "The Imperial Army's high command declared neutrality on February 11, 1979 rather than defend the provisional government", direction: "favors-movement", baseRate: "Security force defection or non-cooperation is the strongest single predictor of movement success across the historical record", rationale: "The Shah's roughly 400,000-strong military did not mutiny outright, but its refusal to fire on crowds and its final neutrality declaration removed the regime's last coercive option within two weeks of the Shah's departure.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "elite-fracture", label: "Elite fracture and state breakdown", framework: "goldstone", status: "Oil revenue collapse from the December 1978 strikes broke the state's fiscal capacity within weeks", direction: "favors-movement", baseRate: "Goldstone's state-breakdown model identifies fiscal crisis combined with elite defection as the structural precondition that converts protest into revolution", rationale: "The strike wave did not just express grievance, it removed the state's ability to pay its own security forces and bureaucracy, a mechanism Goldstone identifies across early modern and 20th-century revolutions alike.", sources: ["Goldstone, Revolution and Rebellion in the Early Modern World (1991)"] }
  ],
  keyFigures: [
    { name: "Ruhollah Khomeini", role: "Exiled Shia cleric, became Supreme Leader of the Islamic Republic", born: 1902, died: 1989, wikipedia: "https://en.wikipedia.org/wiki/Ruhollah_Khomeini" },
    { name: "Mohammad Reza Pahlavi", role: "Shah of Iran, deposed 1979", born: 1919, died: 1980, wikipedia: "https://en.wikipedia.org/wiki/Mohammad_Reza_Pahlavi" },
    { name: "Mehdi Bazargan", role: "First prime minister of the Islamic Republic's provisional government, resigned November 1979", born: 1907, died: 1995, wikipedia: "https://en.wikipedia.org/wiki/Mehdi_Bazargan" }
  ],
  legacyPoints: [
    "Established the Islamic Republic of Iran, the first modern state to formally place clerical authority (velayat-e faqih) above elected government.",
    "The November 1979 US embassy hostage crisis that followed reshaped US-Iran relations for the subsequent four decades.",
    "Became a reference model for Islamist opposition movements across the Muslim world through the 1980s and beyond.",
    "The secular and leftist coalition partners who helped topple the Shah were largely purged or suppressed within two to three years, a widely cited case of revolutionary coalition fracture."
  ],
  perspectives: [
    {
      id: "clerical-revolutionary",
      viewpoint: "Revolutionary clergy",
      viewpointType: "revolutionary",
      regionOrigin: "middle-east",
      narrative: "To Khomeini's supporters, the revolution restored Islamic governance after decades of a foreign-installed monarchy that had suppressed religious life and sold Iran's resources to Western interests. The clergy's leadership reflected genuine popular consensus, confirmed by the March 1979 referendum.",
      keyArguments: ["The Shah's 1953 restoration by a foreign-backed coup delegitimized the monarchy from the outset", "Clerical networks were the only institutions with the reach and trust to organize a nationwide movement"],
      emphasized: ["SAVAK repression and the 1953 coup's lasting grievance", "The scale of the referendum result"],
      omitted: ["The extent of secular, leftist, and Marxist organizational contribution to the 1978 protests and strikes"],
      notableQuotes: [{ text: "We did not send our young people to the battlefronts to establish democracy", speaker: "Ruhollah Khomeini", context: "Widely cited remark reflecting the post-revolutionary marginalization of secular democratic demands" }]
    },
    {
      id: "secular-coalition-diaspora",
      viewpoint: "Secular and leftist coalition member",
      viewpointType: "diaspora",
      regionOrigin: "middle-east",
      narrative: "Many secular nationalists and leftists who marched against the Shah in 1978 later described the revolution as stolen from a broader coalition. They argue the anti-Shah movement had genuinely plural goals, constitutional government, land reform, free press, that clerical authorities abandoned once the monarchy fell.",
      keyArguments: ["The 1978 coalition included nationalist, leftist, and secular liberal currents with democratic rather than theocratic aims", "Post-1979 suppression of former allies, including the 1981 crackdown on the Mujahedin-e Khalq, reveals the theocratic outcome was not the coalition's shared goal"],
      emphasized: ["Bazaar merchant and student organizing prior to clerical dominance", "The narrowing of political space after 1979"],
      omitted: ["The comparative organizational weakness of secular factions relative to the mosque network by late 1978"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "russian-revolution", targetTitle: "The Russian Revolution", type: "parallel", description: "Both saw a broad anti-monarchist coalition splinter after victory, with the most disciplined ideological faction consolidating sole power within roughly two years." },
    { targetSlug: "iran-woman-life-freedom", targetTitle: "Iran: Woman, Life, Freedom", type: "provoked-backlash", description: "The 2022 uprising arose in direct opposition to enforcement mechanisms, including mandatory hijab law, established by the state this revolution created." }
  ],
  media: [],
  relatedRevoltSlugs: ["russian-revolution", "iran-woman-life-freedom"],
  relatedHistorySlugs: ["iranian-revolution"],
  published: true
},
{
  id: "haitian-revolution",
  slug: "haitian-revolution",
  title: "The Haitian Revolution",
  subtitle: "The only successful slave revolt in history to found a state",
  era: "atlantic",
  region: "americas",
  country: "Saint-Domingue (Haiti)",
  revoltType: "social",
  status: "concluded",
  dateDisplay: "August 1791 to January 1804",
  dateStart: 1791,
  dateEnd: 1804,
  summary: "On the night of August 22, 1791, enslaved organizers at a Vodou ceremony at Bois Caiman signaled a coordinated uprising across the Northern Plain of Saint-Domingue, France's most profitable colony and the source of nearly half of Europe's sugar and coffee. Within ten days roughly 1,000 plantations burned. Thirteen years of fighting followed, against French colonial forces, British and Spanish invasions, and finally an 1802 French expedition of over 40,000 troops sent by Napoleon to restore slavery. Jean-Jacques Dessalines declared independence on January 1, 1804, founding Haiti as the first nation in the Americas to abolish slavery and the first Black-led republic in the world.",
  significance: "The only slave uprising in world history to abolish slavery and establish an independent state, achieved against the era's dominant colonial and military power.",
  analyticalOutlook: "A movement whose armed campaign succeeded against overwhelming odds, then paid for independence through a French indemnity debt Haiti did not finish repaying until 1947.",
  grievances: [
    { kind: "Chattel slavery", intensity: 100, evidence: "Roughly 500,000 enslaved people worked Saint-Domingue's plantations by 1789, with mortality so high that planters calculated it was cheaper to work captives to death and import replacements than to sustain births." },
    { kind: "Racial caste exclusion", intensity: 80, evidence: "The colony's roughly 30,000 free people of color, many property-owning, were barred by the Code Noir and later restrictions from full civic and legal rights held by white colonists." },
    { kind: "Brutal plantation discipline", intensity: 95, evidence: "Firsthand accounts documented by historians included mutilation, branding, and burial alive as punishments used on Saint-Domingue's plantations." },
    { kind: "Revolutionary ideals withheld from the colony", intensity: 70, evidence: "The 1789 Declaration of the Rights of Man circulated in the colony while the National Assembly initially refused to extend citizenship to free people of color, let alone the enslaved." }
  ],
  actors: [
    { actorType: "vanguard", name: "Toussaint Louverture", description: "Formerly enslaved coachman turned military commander, rose to govern the colony as Governor-General by 1801.", roleInArc: "Unified rebel forces, negotiated with and fought against French, British, and Spanish forces before capture in 1802", defected: false },
    { actorType: "vanguard", name: "Jean-Jacques Dessalines", description: "Formerly enslaved general who took command after Louverture's 1802 capture and deportation to France.", roleInArc: "Led the final campaign against Napoleon's expedition and declared Haitian independence January 1, 1804", defected: false },
    { actorType: "old-regime", name: "France (colonial administration and Napoleon's expedition)", description: "Colonial government of Saint-Domingue, later an expeditionary force of over 40,000 troops under General Leclerc sent by Napoleon in 1802.", roleInArc: "Attempted to restore slavery after the 1794 abolition decree, was defeated by 1803", defected: false },
    { actorType: "masses", name: "Affranchis leadership", description: "Free, often property-owning people of mixed African and European descent, including early leader Vincent Oge.", roleInArc: "Initially fought for civil rights within the colonial system before joining the broader independence struggle", defected: false },
    { actorType: "foreign-intervener", name: "Britain and Spain", description: "Rival colonial powers that invaded Saint-Domingue during the 1790s to seize French territory amid revolutionary chaos.", roleInArc: "Both were ultimately repelled by rebel forces, with British losses alone estimated near 15,000 dead from combat and yellow fever by 1798", defected: false }
  ],
  tactics: [
    { tacticType: "urban-uprising", description: "The August 1791 rebellion burned roughly 1,000 plantations across the Northern Plain within the first ten days, organized through overseer and driver networks.", prominence: "primary, opening phase" },
    { tacticType: "armed-insurgency", description: "Rebel forces under Louverture and later Dessalines fought a thirteen-year campaign combining irregular warfare with organized troop formations against three European powers in turn.", prominence: "primary, throughout" },
    { tacticType: "guerrilla-warfare", description: "Rebel commanders retreated to the interior during the rainy season, letting yellow fever decimate the 1802 French expeditionary force, which lost an estimated 50,000 of its roughly 60,000 total deployed troops to combat and disease.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Plantation Slavery at Its Peak", tStart: 0.00, tEnd: 0.12, intensity: 60, reached: true, summary: "Saint-Domingue produces roughly 40 percent of Europe's sugar and 60 percent of its coffee under a brutal plantation system worked by roughly 500,000 enslaved people.", keyEvents: ["Colony reaches peak export production, late 1780s", "1789 Declaration of the Rights of Man circulates without extension to the colony"] },
    { phase: "the-spark", label: "Bois Caiman and the August Uprising", tStart: 0.22, tEnd: 0.34, intensity: 85, reached: true, summary: "A coordinated uprising begins the night of August 22, 1791, burning roughly 1,000 plantations within ten days.", keyEvents: ["Bois Caiman ceremony, August 22, 1791", "Northern Plain plantations burn, late August 1791"] },
    { phase: "moderate-phase", label: "Louverture's Rise and Abolition", tStart: 0.34, tEnd: 0.48, intensity: 65, reached: true, summary: "France abolishes slavery in its colonies in 1794 under pressure from the ongoing rebellion; Toussaint Louverture consolidates military and political leadership.", keyEvents: ["French National Convention abolishes slavery, February 1794", "Louverture named Governor-General, 1801"] },
    { phase: "radical-phase", label: "Napoleon's Expedition", tStart: 0.60, tEnd: 0.72, intensity: 100, reached: true, summary: "Napoleon dispatches over 40,000 troops in 1802 to restore French control and re-establish slavery; Louverture is captured and deported to France, where he dies in captivity in 1803.", keyEvents: ["Leclerc expedition lands, February 1802", "Louverture captured June 1802, dies at Fort de Joux, April 1803"] },
    { phase: "consolidation", label: "Independence Declared", tStart: 0.92, tEnd: 1.00, intensity: 70, reached: true, summary: "Rebel forces under Dessalines defeat the remaining French garrison at the Battle of Vertieres; independence is declared days later.", keyEvents: ["Battle of Vertieres, November 18, 1803", "Haiti declares independence, January 1, 1804"] }
  ],
  outcome: "independence",
  peakParticipationPct: null,
  peakParticipationDisplay: "roughly 100,000 combatants under arms at the movement's peak, drawn from a colony-wide enslaved population near 500,000",
  crossedParticipationThreshold: null,
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  durationDays: 4535,
  deathToll: "estimates range widely; roughly 350,000 to 500,000 total deaths across the thirteen-year conflict including combat, disease, and reprisal killings on all sides",
  deathTollLow: 350000,
  deathTollHigh: 500000,
  regimeBefore: "colonial",
  regimeAfter: "democracy",
  democratizationDelta: 2,
  successFactors: [
    { factorKey: "armed-campaign-rate", label: "Armed campaign base rate", framework: "chenoweth", status: "A fully armed thirteen-year campaign defeated France, Britain, and Spain in turn", direction: "favors-movement", baseRate: "Chenoweth and Stephan's dataset finds armed campaigns succeed in roughly 26 percent of cases historically, well below nonviolent campaigns' roughly 53 percent", rationale: "The Haitian Revolution sits among the rarer successful armed campaigns in the historical record, aided by disease attrition among European troops and the extreme, existential nature of the enslaved population's stake in the outcome.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-attrition", label: "Environmental and disease attrition of the intervening power", framework: "tilly", status: "Yellow fever killed an estimated 50,000 of the roughly 60,000 French troops deployed in the 1802 to 1803 campaign", direction: "favors-movement", baseRate: "Disease attrition of European expeditionary forces in the Caribbean is a widely documented factor across colonial military campaigns of the era, distinct from and additive to battlefield casualties", rationale: "Rebel commanders' strategy of retreating to the interior during the rainy season deliberately let disease do damage conventional battle could not, a documented factor historians credit as decisive alongside battlefield resistance.", sources: ["Girard, The Slaves Who Defeated Napoleon (2011)"] },
    { factorKey: "elite-fracture", label: "Colonial elite fracture", framework: "skocpol", status: "The French Revolution's own instability, competing revolutionary factions, and war with Britain and Spain divided colonial administrative authority throughout the 1790s", direction: "favors-movement", baseRate: "Skocpol's framework identifies a fractured or distracted central authority as a structural precondition enabling peripheral revolutions to succeed", rationale: "Saint-Domingue's rebellion unfolded while revolutionary France itself was consumed by internal political turnover and war with European rivals, leaving the colony's defense chronically under-resourced relative to the scale of the uprising it faced.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Toussaint Louverture", role: "Revolutionary general and Governor-General of Saint-Domingue", born: 1743, died: 1803, wikipedia: "https://en.wikipedia.org/wiki/Toussaint_Louverture" },
    { name: "Jean-Jacques Dessalines", role: "Revolutionary general, first ruler of independent Haiti", born: 1758, died: 1806, wikipedia: "https://en.wikipedia.org/wiki/Jean-Jacques_Dessalines" },
    { name: "Vincent Oge", role: "Free man of color who led an early 1790 uprising for civil rights, executed 1791", born: 1755, died: 1791, wikipedia: "https://en.wikipedia.org/wiki/Vincent_Og%C3%A9" },
    { name: "Napoleon Bonaparte", role: "First Consul of France, ordered the 1802 expedition to restore slavery", born: 1769, died: 1821, wikipedia: "https://en.wikipedia.org/wiki/Napoleon" }
  ],
  legacyPoints: [
    "Founded Haiti as the first independent nation in Latin America and the Caribbean and the first republic in the world founded by formerly enslaved people.",
    "France demanded a 150 million franc indemnity from Haiti in 1825 in exchange for diplomatic recognition, a debt Haiti finished repaying only in 1947, widely cited by economic historians as a drag on the country's subsequent development.",
    "The revolution ended slavery in the colony that had been France's single most profitable possession, and its news spread fear and inspiration through slaveholding societies across the Americas.",
    "Napoleon abandoned his broader plans for a North American empire partly as a consequence of the losses suffered in Saint-Domingue, a factor historians link to the 1803 Louisiana Purchase."
  ],
  perspectives: [
    {
      id: "revolutionary-formerly-enslaved",
      viewpoint: "Formerly enslaved combatant",
      viewpointType: "revolutionary",
      regionOrigin: "americas",
      narrative: "For the enslaved majority who rose up in August 1791, the revolution was an act of self-liberation against a system that worked people to death for profit. Freedom and independence were inseparable: no promise of gradual reform from a colonial or metropolitan authority could substitute for ending slavery outright and controlling their own state.",
      keyArguments: ["Only total abolition and independent Black governance could guarantee freedom would not be reversed, a fear later justified by Napoleon's 1802 attempt to restore slavery", "Armed resistance was a rational response given the brutality documented on Saint-Domingue's plantations"],
      emphasized: ["The scale and organization of the August 1791 uprising", "The thirteen-year duration and cost of defeating three European powers"],
      omitted: ["Internal divisions between formerly enslaved leaders and the free-colored elite over land and political structure after 1804"],
      notableQuotes: [{ text: "In overthrowing me, you have cut down in Saint-Domingue only the trunk of the tree of liberty. It will spring up again by the roots, for they are numerous and deep", speaker: "Toussaint Louverture", context: "Reported statement upon his 1802 capture and deportation to France" }]
    },
    {
      id: "french-colonial-administrator",
      viewpoint: "French colonial official",
      viewpointType: "counter-revolutionary",
      regionOrigin: "europe",
      narrative: "French colonial and later Napoleonic officials viewed the uprising as a catastrophic loss of the empire's most valuable possession and a precedent that risked destabilizing slavery across every other colonial holding in the Americas, justifying the scale of the 1802 military response.",
      keyArguments: ["Saint-Domingue represented an irreplaceable share of French colonial trade revenue that had to be defended by any means", "Allowing the rebellion to stand risked inspiring uprisings in other French and rival colonial possessions"],
      emphasized: ["The economic value of Saint-Domingue's sugar and coffee exports", "The scale of French military commitment to the 1802 expedition"],
      omitted: ["The brutality of plantation conditions that produced the uprising in the first place"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "french-revolution", targetTitle: "The French Revolution", type: "inspired", description: "The 1789 Declaration of the Rights of Man and revolutionary France's internal political chaos both catalyzed and enabled the Saint-Domingue uprising, though France itself resisted extending those rights to the colony." },
    { targetSlug: "american-revolution", targetTitle: "The American Revolution", type: "counter-example", description: "Where the American Revolution's new republic preserved and expanded chattel slavery for another eight decades, Haiti's revolution abolished it immediately and made abolition the founding condition of the state." }
  ],
  media: [],
  relatedRevoltSlugs: ["french-revolution", "american-revolution"],
  relatedHistorySlugs: ["haitian-revolution"],
  published: true
},
{
  id: "american-revolution",
  slug: "american-revolution",
  title: "The American Revolution",
  subtitle: "Thirteen colonies fought an eight-year war over taxation without representation",
  era: "atlantic",
  region: "americas",
  country: "United States (Thirteen Colonies)",
  revoltType: "political",
  status: "concluded",
  dateDisplay: "1765 to 1783",
  dateStart: 1765,
  dateEnd: 1783,
  summary: "Parliament's 1765 Stamp Act, the first direct tax levied on the American colonies, triggered a decade of escalating protest under the slogan 'no taxation without representation.' The Boston Tea Party of December 1773 and the punitive Coercive Acts that followed hardened positions on both sides. Fighting began at Lexington and Concord in April 1775; the Continental Congress declared independence on July 4, 1776. French military and naval support, formalized by treaty in 1778, proved decisive at the October 1781 siege of Yorktown, where a combined American and French force compelled the surrender of over 7,000 British troops under Cornwallis. The 1783 Treaty of Paris recognized American independence.",
  significance: "Established the first large-scale republic founded explicitly on Enlightenment principles of popular sovereignty and constitutional government, directly influencing the French Revolution six years later.",
  analyticalOutlook: "A political-rights movement that escalated into an eight-year war, won primarily through foreign military intervention rather than an internal collapse of British authority.",
  grievances: [
    { kind: "Taxation without representation", intensity: 85, evidence: "The 1765 Stamp Act and 1767 Townshend Acts imposed direct taxes on the colonies, which held no seats in the Parliament that levied them." },
    { kind: "Restriction of colonial self-governance", intensity: 75, evidence: "The 1774 Coercive Acts (Intolerable Acts) suspended Massachusetts's colonial charter and closed the port of Boston in response to the Tea Party." },
    { kind: "Standing army quartering", intensity: 55, evidence: "The Quartering Acts required colonies to house British troops, a grievance later written directly into the Declaration of Independence's list of charges against George III." },
    { kind: "Trade restriction", intensity: 60, evidence: "Navigation Acts restricted colonial trade to British ships and markets, angering merchants across New England and the Mid-Atlantic ports." }
  ],
  actors: [
    { actorType: "masses", name: "Continental Congress", description: "Delegate body representing the thirteen colonies, first convened 1774, issued the Declaration of Independence in 1776.", roleInArc: "Coordinated colonial resistance and formal independence, later governed under the Articles of Confederation", defected: false },
    { actorType: "vanguard", name: "Continental Army", description: "Colonial fighting force under George Washington's command, alongside state militias, numbering roughly 20,000 to 30,000 at various points.", roleInArc: "Fought the eight-year war against British regulars, ultimately forcing the Yorktown surrender", defected: false },
    { actorType: "old-regime", name: "Kingdom of Great Britain", description: "Governed the thirteen colonies through royal governors and Parliament; deployed roughly 50,000 troops to North America over the war's course.", roleInArc: "Suppressed early protest, then fought and ultimately lost the war, recognizing independence in 1783", defected: false },
    { actorType: "foreign-backer", name: "Kingdom of France", description: "Formal ally of the United States from the 1778 Treaty of Alliance, providing troops, a fleet, and financing.", roleInArc: "French naval blockade and roughly 8,000 French troops were decisive at the 1781 siege of Yorktown", defected: false },
    { actorType: "counter-revolutionaries", name: "American Loyalists", description: "An estimated 15 to 20 percent of the colonial population who remained loyal to the Crown; roughly 60,000 to 100,000 emigrated after the war.", roleInArc: "Fought alongside British forces and provided intelligence; largely resettled in Canada and Britain after 1783", defected: false }
  ],
  tactics: [
    { tacticType: "boycott-noncooperation", description: "Colonial merchants organized boycotts of British goods following the Stamp Act and Townshend Acts, coordinated through Committees of Correspondence.", prominence: "primary, pre-war phase" },
    { tacticType: "armed-insurgency", description: "The Continental Army and state militias fought a mix of set-piece battles (Saratoga, Yorktown) and irregular engagements (Lexington, Concord, the Southern partisan campaign) across an eight-year war.", prominence: "primary, war phase" },
    { tacticType: "parallel-institutions", description: "Benjamin Franklin's mission to Paris secured the 1778 Franco-American alliance, bringing French naval and land forces directly into the conflict.", prominence: "secondary, decisive at Yorktown" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Taxation Without Representation", tStart: 0.00, tEnd: 0.12, intensity: 30, reached: true, summary: "A decade of British taxation measures without colonial representation builds organized resistance from the Stamp Act onward.", keyEvents: ["Stamp Act, 1765", "Townshend Acts, 1767", "Boston Massacre, March 1770"] },
    { phase: "the-spark", label: "Tea Party and Coercive Acts", tStart: 0.22, tEnd: 0.34, intensity: 45, reached: true, summary: "The Boston Tea Party provokes Parliament's punitive Coercive Acts, uniting colonial opposition and prompting the First Continental Congress.", keyEvents: ["Boston Tea Party, December 1773", "Coercive Acts, 1774", "First Continental Congress convenes, September 1774"] },
    { phase: "moderate-phase", label: "Lexington to Declaration", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "Fighting breaks out at Lexington and Concord; the Continental Congress moves from petitioning the Crown to declaring independence.", keyEvents: ["Battles of Lexington and Concord, April 1775", "Declaration of Independence adopted, July 4, 1776"] },
    { phase: "radical-phase", label: "War and the French Alliance", tStart: 0.60, tEnd: 0.72, intensity: 80, reached: true, summary: "The war grinds through years of contested campaigns until the 1778 French alliance brings decisive naval and land support.", keyEvents: ["American victory at Saratoga, October 1777", "Treaty of Alliance with France, February 1778"] },
    { phase: "consolidation", label: "Yorktown and Peace", tStart: 0.92, tEnd: 1.00, intensity: 60, reached: true, summary: "A combined American and French force compels Cornwallis's surrender at Yorktown, and the Treaty of Paris formally ends the war.", keyEvents: ["Siege of Yorktown, September-October 1781, over 7,000 British troops surrender", "Treaty of Paris signed, September 1783"] }
  ],
  outcome: "independence",
  peakParticipationPct: null,
  peakParticipationDisplay: "roughly 200,000 total individuals served in the Continental Army and state militias over the course of the war",
  crossedParticipationThreshold: null,
  militaryDefection: "none",
  foreignIntervention: "direct-military",
  durationDays: 2922,
  deathToll: "an estimated 25,000 American deaths (combat and disease combined) out of a population near 2.5 million; British and allied losses added several thousand more",
  deathTollLow: 25000,
  deathTollHigh: 25000,
  regimeBefore: "colonial",
  regimeAfter: "democracy",
  democratizationDelta: 2,
  successFactors: [
    { factorKey: "foreign-intervention", label: "Direct foreign military intervention", framework: "tilly", status: "French troops, naval forces, and financing were decisive at the 1781 Yorktown siege that ended major combat operations", direction: "favors-movement", baseRate: "Comparative studies of independence wars find that direct foreign military intervention on the side of an insurgency substantially raises the odds of success relative to insurgencies fighting alone", rationale: "The Continental Army alone had not defeated British forces decisively in six years of fighting; the French fleet blocking Chesapeake Bay and roughly 8,000 French troops at Yorktown were what forced Cornwallis's surrender.", sources: ["Dull, A Diplomatic History of the American Revolution (1985)"] },
    { factorKey: "armed-campaign-rate", label: "Armed campaign base rate", framework: "chenoweth", status: "An eight-year armed campaign combining colonial forces with a foreign ally achieved independence", direction: "favors-movement", baseRate: "Chenoweth and Stephan find armed campaigns succeed in roughly 26 percent of cases historically, versus roughly 53 percent for primarily nonviolent campaigns", rationale: "The American case succeeded as an armed campaign in part because it secured a great-power ally rather than relying on domestic mobilization alone, a combination not present in most armed campaigns in the broader historical dataset.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "geographic-distance", label: "Distance and logistics burden on the imperial power", framework: "tilly", status: "Britain supplied and reinforced its army across roughly 3,000 miles of Atlantic Ocean for eight years", direction: "favors-movement", baseRate: "Historians of colonial and imperial warfare widely identify overextended supply lines as a recurring structural disadvantage for distant occupying powers fighting local or allied-supported insurgencies", rationale: "Troop and supply convoys took six to eight weeks to cross the Atlantic, delaying reinforcement and decision-making relative to the Continental Army and its French allies operating on or near home territory.", sources: ["Comparative colonial warfare historiography"] }
  ],
  keyFigures: [
    { name: "George Washington", role: "Commander-in-Chief of the Continental Army, later first US President", born: 1732, died: 1799, wikipedia: "https://en.wikipedia.org/wiki/George_Washington" },
    { name: "Thomas Jefferson", role: "Principal author of the Declaration of Independence", born: 1743, died: 1826, wikipedia: "https://en.wikipedia.org/wiki/Thomas_Jefferson" },
    { name: "Benjamin Franklin", role: "Diplomat who secured the 1778 French alliance", born: 1706, died: 1790, wikipedia: "https://en.wikipedia.org/wiki/Benjamin_Franklin" },
    { name: "King George III", role: "Monarch of Great Britain during the war", born: 1738, died: 1820, wikipedia: "https://en.wikipedia.org/wiki/George_III" }
  ],
  legacyPoints: [
    "Established the United States as an independent republic under a written constitution, ratified 1788, with a Bill of Rights added 1791.",
    "Directly inspired the French Revolution's own Declaration of the Rights of Man in 1789, with Lafayette drafting a version informed by his American service.",
    "Left slavery intact and expanding in the new republic even as the Declaration of Independence asserted that all men are created equal, a contradiction historians continue to examine.",
    "Established a template of written constitutionalism and codified individual rights that influenced independence and constitutional movements across the Americas in the following century."
  ],
  perspectives: [
    {
      id: "patriot-revolutionary",
      viewpoint: "Patriot colonist",
      viewpointType: "revolutionary",
      regionOrigin: "americas",
      narrative: "Patriots framed the conflict as a defense of English rights denied to colonial subjects, escalating from petition to boycott to arms only after Parliament repeatedly refused representation and imposed increasingly punitive measures like the 1774 Coercive Acts.",
      keyArguments: ["Parliament taxed the colonies without seating colonial representatives, violating a principle patriots traced to English constitutional tradition", "A decade of peaceful petition and boycott preceded the resort to arms in 1775"],
      emphasized: ["The escalating pattern of British punitive legislation from 1765 to 1774", "The colonies' prior record of self-governance through elected assemblies"],
      omitted: ["The continuation and expansion of chattel slavery under the new republic the Declaration's language of equality did not extend to"],
      notableQuotes: [{ text: "We hold these truths to be self-evident, that all men are created equal", speaker: "Declaration of Independence", context: "Adopted by the Continental Congress, July 4, 1776" }]
    },
    {
      id: "loyalist-counter",
      viewpoint: "British Loyalist",
      viewpointType: "counter-revolutionary",
      regionOrigin: "americas",
      narrative: "Loyalists, an estimated 15 to 20 percent of the colonial population, viewed the rebellion as an illegal armed insurrection against lawful Parliamentary authority, disruptive to trade and social order, and warned that independence would fracture the stability the empire provided.",
      keyArguments: ["Parliament held sovereign authority over the colonies as established by charter and precedent", "Armed rebellion against the Crown, not the underlying tax grievances, was the illegitimate escalation"],
      emphasized: ["Property and trade disruption caused by boycotts and mob actions", "The risks of political instability under an untested republican government"],
      omitted: ["The scale and duration of colonial petitioning that preceded the resort to boycott and eventually arms"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "french-revolution", targetTitle: "The French Revolution", type: "inspired", description: "American constitutional and rights-based language, along with the direct experience of French officers like Lafayette who served in the war, fed directly into French revolutionary thought in 1789." },
    { targetSlug: "haitian-revolution", targetTitle: "The Haitian Revolution", type: "counter-example", description: "The American republic's founding preserved and expanded slavery for another eight decades, in direct contrast to Haiti's revolution, which made abolition the condition of independence itself." }
  ],
  media: [],
  relatedRevoltSlugs: ["french-revolution", "haitian-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "fall-of-communism-1989",
  slug: "fall-of-communism-1989",
  title: "The Fall of Communism in Eastern Europe",
  subtitle: "Six governments fell in one year, most of them without a shot fired",
  era: "people-power",
  region: "europe",
  country: "Poland, East Germany, Czechoslovakia, Hungary, Bulgaria, Romania",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "June to December 1989",
  dateStart: 1989,
  dateEnd: 1989,
  summary: "Poland's Solidarity trade union, banned since 1981, won semi-free elections in June 1989 after roundtable talks with the communist government, taking every contested seat. Hungary began dismantling its border fence with Austria in May, opening a route east German vacationers used to flee west by the thousands. Weekly Leipzig demonstrations grew from a few hundred to over 300,000 by late October. On November 9, an East German spokesman's confused announcement of new travel rules sent crowds to the Berlin Wall, which border guards opened without orders that night. Czechoslovakia's Velvet Revolution replaced its government in eleven days of student-led protest and general strike. Romania's Ceausescu was the exception: his security forces fired on crowds, and he was captured fleeing the capital and executed on Christmas Day.",
  significance: "The fastest wave of regime collapse in modern history, ending Soviet-aligned communist rule across six countries within seven months and setting up German reunification and the Soviet Union's own 1991 dissolution.",
  analyticalOutlook: "A regional cascade in which each fallen government made the next one's collapse more likely, resolved almost entirely without large-scale violence outside Romania.",
  grievances: [
    { kind: "Economic stagnation", intensity: 80, evidence: "Poland's foreign debt reached roughly 40 billion dollars by 1989 with empty shop shelves and hyperinflation approaching 1,000 percent by year's end." },
    { kind: "Political repression and one-party rule", intensity: 75, evidence: "Solidarity, which had organized 10 million members in 1980-81, was banned under martial law from 1981 to 1989, with thousands interned." },
    { kind: "Restricted freedom of movement", intensity: 70, evidence: "East Germans were barred from traveling west without state permission; the Berlin Wall, standing since 1961, had killed over 100 people attempting to cross." },
    { kind: "Loss of Soviet backing for repression", intensity: 60, evidence: "Gorbachev's public renunciation of the Brezhnev Doctrine in 1988-89 signaled Moscow would not send tanks to save Warsaw Pact governments, as it had in Hungary 1956 and Czechoslovakia 1968." }
  ],
  actors: [
    { actorType: "organized-labor", name: "Solidarity (Solidarnosc)", description: "Polish independent trade union founded 1980, banned under martial law, legalized again in April 1989 roundtable talks.", roleInArc: "Won Poland's June 1989 semi-free elections, forming the first non-communist-led government in the Soviet bloc", defected: false },
    { actorType: "masses", name: "Leipzig Monday demonstrators", description: "East German protesters who gathered weekly at Leipzig's Nikolaikirche, growing from hundreds in September to over 300,000 by late October 1989.", roleInArc: "Pressured the East German government into the concessions that led to the Wall's opening", defected: false },
    { actorType: "foreign-backer", name: "Mikhail Gorbachev", description: "General Secretary of the Soviet Communist Party since 1985, pursued glasnost and perestroika reforms.", roleInArc: "Publicly signaled the USSR would not militarily intervene to save satellite governments, removing their ultimate backstop", defected: false },
    { actorType: "vanguard", name: "Civic Forum (Czechoslovakia)", description: "Umbrella opposition movement formed within days of the Velvet Revolution's start, led by playwright Vaclav Havel.", roleInArc: "Negotiated the peaceful transfer of power in eleven days, November 17-28, 1989", defected: false },
    { actorType: "old-regime", name: "Nicolae Ceausescu government", description: "Romania's communist leadership since 1965, ruling through the Securitate secret police.", roleInArc: "The only 1989 regime to order lethal force against protesters; Ceausescu was captured and executed December 25, 1989", defected: false }
  ],
  tactics: [
    { tacticType: "parallel-institutions", description: "Poland's government and Solidarity conducted roundtable talks from February to April 1989, agreeing to semi-free elections rather than continued confrontation.", prominence: "primary, Poland" },
    { tacticType: "mass-demonstration", description: "Leipzig's Monday demonstrations and similar gatherings across East Germany and Czechoslovakia built sustained, escalating public pressure without central organizing structures.", prominence: "primary, East Germany and Czechoslovakia" },
    { tacticType: "general-strike", description: "A two-hour general strike on November 27, 1989 in Czechoslovakia demonstrated near-total public backing for Civic Forum's demands, accelerating the government's collapse.", prominence: "secondary" }
  ],
  resistanceType: "nonviolent",
  phases: [
    { phase: "old-regime-crisis", label: "Debt and Stagnation", tStart: 0.00, tEnd: 0.12, intensity: 35, reached: true, summary: "Chronic shortages and foreign debt burden Poland and other Warsaw Pact economies through the late 1980s.", keyEvents: ["Polish foreign debt reaches roughly 40 billion dollars, late 1980s", "Gorbachev signals non-intervention in satellite states, 1988"] },
    { phase: "the-spark", label: "Roundtable and Border Opening", tStart: 0.22, tEnd: 0.34, intensity: 50, reached: true, summary: "Poland's roundtable talks and Hungary's border opening create the first cracks in the bloc's internal control.", keyEvents: ["Polish roundtable talks conclude, April 1989", "Hungary opens its Austrian border, May 1989"] },
    { phase: "moderate-phase", label: "Solidarity Wins, Leipzig Grows", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "Solidarity sweeps Poland's June elections while Leipzig's Monday protests swell week over week through the autumn.", keyEvents: ["Solidarity wins nearly every contested seat, June 4, 1989", "Leipzig protests exceed 300,000, late October 1989"] },
    { phase: "dual-power", label: "The Wall Falls", tStart: 0.48, tEnd: 0.60, intensity: 70, reached: true, summary: "A miscommunicated East German travel announcement sends crowds to the Berlin Wall, which guards open without orders.", keyEvents: ["Berlin Wall opens, November 9, 1989", "Velvet Revolution begins in Czechoslovakia, November 17, 1989"] },
    { phase: "radical-phase", label: "Velvet Revolution and Romanian Violence", tStart: 0.60, tEnd: 0.72, intensity: 65, reached: true, summary: "Czechoslovakia's transition completes peacefully within eleven days while Romania's government orders lethal force against protesters in Timisoara and Bucharest.", keyEvents: ["Czechoslovak general strike, November 27, 1989", "Romanian security forces fire on Timisoara protesters, December 17, 1989"] },
    { phase: "consolidation", label: "Governments Fall", tStart: 0.92, tEnd: 1.00, intensity: 55, reached: true, summary: "Communist governments fall across the region by year's end, with Ceausescu captured and executed on Christmas Day.", keyEvents: ["Havel elected Czechoslovak president, December 29, 1989", "Ceausescu executed, December 25, 1989"] }
  ],
  outcome: "consolidated-democracy",
  peakParticipationPct: null,
  peakParticipationDisplay: "over 300,000 at Leipzig's peak Monday demonstration, late October 1989",
  crossedParticipationThreshold: true,
  militaryDefection: "partial",
  foreignIntervention: "none",
  durationDays: 214,
  deathToll: "fewer than 100 across most of the six countries combined; Romania's crackdown alone killed over 1,000 in Timisoara and Bucharest in December 1989",
  deathTollLow: 1000,
  deathTollHigh: 1200,
  regimeBefore: "one-party",
  regimeAfter: "democracy",
  democratizationDelta: 3,
  successFactors: [
    { factorKey: "nonviolent-campaign-rate", label: "Nonviolent campaign base rate", framework: "chenoweth", status: "Five of six 1989 transitions (all but Romania) proceeded through negotiation, mass protest, and strikes without organized armed resistance", direction: "favors-movement", baseRate: "Chenoweth and Stephan find nonviolent campaigns succeed in roughly 53 percent of cases historically, roughly double the rate for armed campaigns", rationale: "Poland's roundtable, East Germany's Monday demonstrations, and Czechoslovakia's Velvet Revolution all achieved regime change through sustained nonviolent pressure rather than armed confrontation, consistent with the broader nonviolent success-rate literature.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "external-patron-withdrawal", label: "Withdrawal of external backing", framework: "skocpol", status: "Gorbachev's public renunciation of the Brezhnev Doctrine removed the threat of Soviet military intervention that had crushed 1956 Hungary and 1968 Czechoslovakia", direction: "favors-movement", baseRate: "Comparative historiography of the Soviet bloc identifies the credible withdrawal of a hegemon's guarantee of intervention as a necessary precondition distinguishing 1989's outcome from 1956 and 1968", rationale: "Absent Gorbachev's signal, protest movements of similar scale had been crushed by Warsaw Pact tanks twice before in the same region; the 1989 cascade required Moscow's non-intervention as much as domestic mobilization.", sources: ["Comparative Cold War historiography of 1956, 1968, and 1989"] },
    { factorKey: "regional-contagion", label: "Cross-border contagion effect", framework: "tilly", status: "Each government's collapse visibly lowered the perceived risk and raised the perceived odds of success for the next country's protesters within the same seven-month span", direction: "favors-movement", baseRate: "Diffusion and cascade models of protest find that geographically and politically proximate successful precedents measurably raise mobilization and reduce perceived risk in subsequent cases", rationale: "Poland's June election, Hungary's May border opening, and the November 9 Wall opening followed each other in rapid succession, with East German and Czechoslovak organizers explicitly citing the prior countries' events as evidence the old order could actually fall.", sources: ["Diffusion-of-protest literature applied to the 1989 cascade"] }
  ],
  keyFigures: [
    { name: "Lech Walesa", role: "Solidarity leader, later President of Poland", born: 1943, wikipedia: "https://en.wikipedia.org/wiki/Lech_Wa%C5%82%C4%99sa" },
    { name: "Mikhail Gorbachev", role: "Soviet General Secretary whose non-intervention policy enabled the cascade", born: 1931, died: 2022, wikipedia: "https://en.wikipedia.org/wiki/Mikhail_Gorbachev" },
    { name: "Vaclav Havel", role: "Playwright and dissident, led Civic Forum, became Czechoslovak president", born: 1936, died: 2011, wikipedia: "https://en.wikipedia.org/wiki/V%C3%A1clav_Havel" },
    { name: "Nicolae Ceausescu", role: "Romanian communist leader, executed December 25, 1989", born: 1918, died: 1989, wikipedia: "https://en.wikipedia.org/wiki/Nicolae_Ceau%C8%99escu" }
  ],
  legacyPoints: [
    "Ended Soviet-aligned communist rule across Poland, East Germany, Czechoslovakia, Hungary, Bulgaria, and Romania within a single calendar year.",
    "Directly enabled German reunification, completed October 3, 1990, less than a year after the Wall opened.",
    "Demonstrated the Chenoweth-cited historical case for nonviolent transition at scale, later studied as a model for other regional protest cascades.",
    "Set a precedent that contributed to the Soviet Union's own dissolution two years later, in December 1991."
  ],
  perspectives: [
    {
      id: "solidarity-movement-view",
      viewpoint: "Solidarity movement organizer",
      viewpointType: "movement",
      regionOrigin: "europe",
      narrative: "Solidarity organizers framed the 1980s struggle as a decade-long campaign, not a single 1989 event: nine years of underground organizing after the 1981 martial-law crackdown made the roundtable negotiations and June election possible the moment political space opened.",
      keyArguments: ["The 1989 election victory rested on organizational infrastructure Solidarity had maintained underground since the 1981 ban", "Negotiated roundtable transition, not confrontation, secured a durable and peaceful handover of power"],
      emphasized: ["The scale of Solidarity's original 10-million-member 1980-81 mobilization", "The discipline of the roundtable negotiating strategy"],
      omitted: ["The extent to which Gorbachev's external signal, not just internal organizing, made the 1989 opening possible where 1981's crackdown had succeeded"],
      notableQuotes: []
    },
    {
      id: "soviet-reformist-view",
      viewpoint: "Soviet reform-era official",
      viewpointType: "regime",
      regionOrigin: "europe",
      narrative: "Gorbachev-aligned Soviet officials described 1989 as a consequence of perestroika's internal logic: reform inside the USSR made continued military backing of unpopular satellite governments both impractical and inconsistent with the reformist program, not a decision to abandon socialism itself.",
      keyArguments: ["Renouncing the Brezhnev Doctrine was consistent with broader Soviet reform, not a deliberate plan to dissolve the Warsaw Pact", "Individual national governments, not Moscow, chose confrontation or negotiation with their own populations"],
      emphasized: ["The internal Soviet reform context of glasnost and perestroika", "Non-intervention as principled rather than merely a loss of capacity"],
      omitted: ["The Soviet economy's own strain, which limited Moscow's practical capacity for renewed large-scale military intervention regardless of stated principle"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "people-power-1986", targetTitle: "People Power (EDSA, Philippines)", type: "shared-repertoire", description: "Both movements demonstrated that mass nonviolent mobilization combined with security-force non-cooperation could remove entrenched governments without civil war, a template widely cited in 1989 organizing discussions." },
    { targetSlug: "iran-woman-life-freedom", targetTitle: "Iran: Woman, Life, Freedom", type: "counter-example", description: "Where 1989's cascade succeeded partly because the external hegemon withdrew backing for repression, the 2022 Iranian uprising faced a government willing and able to sustain lethal suppression without any comparable external constraint." }
  ],
  media: [],
  relatedRevoltSlugs: ["people-power-1986", "russian-revolution"],
  relatedHistorySlugs: ["fall-of-berlin-wall"],
  published: true
},
{
  id: "people-power-1986",
  slug: "people-power-1986",
  title: "People Power (EDSA Revolution)",
  subtitle: "Four days on one Manila highway ended a twenty-year dictatorship",
  era: "people-power",
  region: "southeast-asia",
  country: "Philippines",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "February 22-25, 1986",
  dateStart: 1986,
  dateEnd: 1986,
  summary: "Ferdinand Marcos claimed victory in a February 7, 1986 snap election widely documented as fraudulent, prompting opposition leader Corazon Aquino, widow of assassinated senator Benigno Aquino, to call for civil disobedience. When Defense Minister Juan Ponce Enrile and armed forces vice chief Fidel Ramos broke from Marcos on February 22 and barricaded themselves at two military camps on Epifanio de los Santos Avenue, Catholic Cardinal Jaime Sin broadcast a radio appeal for citizens to protect them. An estimated one to two million Filipinos filled EDSA over four days, offering food and rosaries to troops sent to disperse them. Marcos fled to Hawaii on a US Air Force flight on February 25, ending twenty years of rule including nine years of martial law.",
  significance: "Coined the term 'People Power' and became the reference case for mass nonviolent civilian protection of a military mutiny forcing a dictator's exit without civil war.",
  analyticalOutlook: "A near-textbook case of the security-force defection and mass-nonviolent-participation literature converging within a single four-day window.",
  grievances: [
    { kind: "Electoral fraud", intensity: 85, evidence: "The National Movement for Free Elections documented widespread ballot tampering in the February 7, 1986 snap election; the Marcos-controlled National Assembly declared him winner despite an independent count favoring Aquino." },
    { kind: "Political assassination and repression", intensity: 80, evidence: "Opposition leader Benigno Aquino Jr. was shot dead on the tarmac at Manila International Airport on August 21, 1983 upon returning from exile, an event that galvanized mass opposition organizing." },
    { kind: "Martial law legacy", intensity: 75, evidence: "Marcos ruled under martial law from 1972 to 1981, during which Amnesty International documented thousands of arbitrary arrests and hundreds of forced disappearances." },
    { kind: "Economic crisis and cronyism", intensity: 65, evidence: "The Philippine economy contracted by roughly 7 percent in 1984 amid an estimated 5 to 10 billion dollars in wealth accumulated by the Marcos family and associated cronies." }
  ],
  actors: [
    { actorType: "vanguard", name: "Corazon Aquino", description: "Widow of assassinated senator Benigno Aquino Jr., ran as opposition presidential candidate in the disputed 1986 election.", roleInArc: "Became the movement's civilian figurehead and was inaugurated president February 25, 1986", defected: false },
    { actorType: "military-defectors", name: "Juan Ponce Enrile and Fidel Ramos", description: "Marcos's Defense Minister and armed forces vice chief, who broke from the regime on February 22, 1986 and barricaded themselves at Camp Aguinaldo and Camp Crame.", roleInArc: "Their mutiny and the crowd that protected it became the pivot point of the four-day uprising", defected: true },
    { actorType: "religious-clergy", name: "Cardinal Jaime Sin", description: "Archbishop of Manila, broadcast a radio appeal via Radio Veritas asking citizens to bring food and support to the mutinous soldiers.", roleInArc: "His February 22 broadcast is widely credited with drawing the first large crowds to EDSA", defected: false },
    { actorType: "masses", name: "EDSA crowd", description: "An estimated one to two million Filipinos who filled Epifanio de los Santos Avenue over four days, unarmed, offering food, flowers, and rosaries to approaching troops.", roleInArc: "Physically blocked tank and troop movements against the mutinous camps without significant violence", defected: false },
    { actorType: "old-regime", name: "Ferdinand Marcos", description: "President of the Philippines since 1965, ruled under martial law 1972 to 1981.", roleInArc: "Fled to Hawaii via US Air Force evacuation on February 25, 1986, ending 20 years in power", defected: false }
  ],
  tactics: [
    { tacticType: "occupation", description: "Unarmed crowds physically blocked Marine tanks and troops from advancing on Camps Aguinaldo and Crame, offering food and prayer rather than confrontation.", prominence: "primary" },
    { tacticType: "digital-mobilization", description: "Radio Veritas, the Catholic station, broadcast Cardinal Sin's appeal and ongoing updates that drew and sustained the EDSA crowds after the government-controlled stations went dark.", prominence: "primary" },
    { tacticType: "civil-disobedience", description: "Aquino called for a boycott of Marcos-linked banks and businesses following the disputed election, part of a broader civil disobedience campaign preceding the military mutiny.", prominence: "secondary" }
  ],
  resistanceType: "nonviolent",
  phases: [
    { phase: "old-regime-crisis", label: "Martial Law Legacy and Assassination", tStart: 0.00, tEnd: 0.12, intensity: 45, reached: true, summary: "Nine years of martial law and the 1983 Aquino assassination build sustained opposition organizing through the mid-1980s.", keyEvents: ["Martial law period, 1972-1981", "Benigno Aquino Jr. assassinated, August 21, 1983"] },
    { phase: "the-spark", label: "Snap Election Fraud and Military Mutiny", tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: "Marcos claims victory in a widely documented fraudulent snap election; two weeks later Enrile and Ramos break from Marcos and barricade themselves inside two Manila military camps, and Cardinal Sin's radio appeal draws the first crowds.", keyEvents: ["Snap election held, February 7, 1986", "Enrile and Ramos mutiny, February 22, 1986", "Cardinal Sin's Radio Veritas appeal, evening of February 22"] },
    { phase: "dual-power", label: "EDSA Fills", tStart: 0.48, tEnd: 0.60, intensity: 80, reached: true, summary: "An estimated one to two million Filipinos occupy EDSA over three days, physically shielding the mutinous camps from Marcos loyalist troops.", keyEvents: ["Crowds swell to over a million, February 23-24, 1986", "Loyalist Marine units halt rather than fire on the crowd"] },
    { phase: "consolidation", label: "Marcos Departs", tStart: 0.92, tEnd: 1.00, intensity: 50, reached: true, summary: "Marcos is evacuated to Hawaii and Aquino is inaugurated the same day, ending twenty years of rule without a civil war.", keyEvents: ["Marcos flees to Hawaii, February 25, 1986", "Corazon Aquino inaugurated president, February 25, 1986"] }
  ],
  outcome: "consolidated-democracy",
  peakParticipationPct: null,
  peakParticipationDisplay: "one to two million on EDSA at peak, February 24-25, 1986",
  crossedParticipationThreshold: true,
  militaryDefection: "full",
  foreignIntervention: "diplomatic",
  durationDays: 4,
  deathToll: "widely reported as effectively bloodless; fewer than a handful of deaths documented directly at EDSA over the four days",
  deathTollLow: 0,
  deathTollHigh: 5,
  regimeBefore: "personalist",
  regimeAfter: "democracy",
  democratizationDelta: 3,
  successFactors: [
    { factorKey: "participation-threshold", label: "3.5 percent participation rule", framework: "chenoweth", status: "One to two million participants out of a national population near 56 million in 1986 is roughly 2 to 3.5 percent, among the more frequently cited near-threshold cases in the literature", direction: "favors-movement", baseRate: "Chenoweth's research finds no campaign that achieved active participation from 3.5 percent of a population has failed to achieve its aims", rationale: "EDSA sits close to or at the 3.5 percent line depending on which population and participation estimates are used, and is frequently cited alongside cases exceeding the threshold as evidence for the rule's predictive power.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "military-defection", label: "Security force defection", framework: "chenoweth", status: "Defense Minister Enrile and armed forces vice chief Ramos broke from Marcos on February 22, 1986, and loyalist units subsequently refused to fire on the EDSA crowd", direction: "favors-movement", baseRate: "Security force defection or refusal to suppress protesters is the single strongest predictor of nonviolent movement success across the historical record", rationale: "EDSA is a widely cited textbook case precisely because the defection came first, from the top of the military hierarchy, and the crowd's role was to protect that defection rather than to independently force capitulation.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "nonviolent-campaign-rate", label: "Nonviolent campaign base rate", framework: "chenoweth", status: "The entire four-day campaign proceeded without organized armed resistance from the opposition side", direction: "favors-movement", baseRate: "Chenoweth and Stephan find nonviolent campaigns succeed in roughly 53 percent of cases historically, roughly double the rate for armed campaigns", rationale: "EDSA achieved regime change in four days with a reported death toll in the single digits, an outcome the nonviolent-campaign literature associates with lower state repression capacity and higher public and international legitimacy relative to armed uprisings.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] }
  ],
  keyFigures: [
    { name: "Corazon Aquino", role: "Opposition leader, became President of the Philippines February 25, 1986", born: 1933, died: 2009, wikipedia: "https://en.wikipedia.org/wiki/Corazon_Aquino" },
    { name: "Ferdinand Marcos", role: "President of the Philippines 1965-1986", born: 1917, died: 1989, wikipedia: "https://en.wikipedia.org/wiki/Ferdinand_Marcos" },
    { name: "Fidel Ramos", role: "Armed forces vice chief who defected February 22, 1986, later President 1992-1998", born: 1928, died: 2022, wikipedia: "https://en.wikipedia.org/wiki/Fidel_V._Ramos" },
    { name: "Jaime Sin", role: "Cardinal Archbishop of Manila whose radio appeal mobilized the EDSA crowds", born: 1928, died: 2005, wikipedia: "https://en.wikipedia.org/wiki/Jaime_Sin" }
  ],
  legacyPoints: [
    "Coined the term 'People Power,' subsequently applied to nonviolent uprisings across the world.",
    "Ended twenty years of Marcos rule, including nine years of martial law, without descending into civil war.",
    "Restored competitive multiparty democracy under a new 1987 constitution drafted within a year of the uprising.",
    "Became a widely taught case study in the nonviolent-resistance literature for the combination of mass civilian mobilization and military defection."
  ],
  perspectives: [
    {
      id: "edsa-civilian-movement",
      viewpoint: "EDSA participant",
      viewpointType: "movement",
      regionOrigin: "southeast-asia",
      narrative: "Participants who filled EDSA over four days described a spontaneous civic response to Cardinal Sin's appeal, driven by years of accumulated anger over the 1983 Aquino assassination and the stolen 1986 election, expressed through prayer and food rather than weapons.",
      keyArguments: ["Mass unarmed presence, not organized armed force, was what physically prevented loyalist tanks from reaching the mutinous camps", "The movement's discipline in avoiding violence protected both the crowd and the defecting soldiers from a justification for a bloody crackdown"],
      emphasized: ["The religious and communal character of the crowd's tactics, including rosaries and shared food", "The rapid, four-day timeline from mutiny to Marcos's departure"],
      omitted: ["The extent to which the outcome depended on the prior elite-level defection by Enrile and Ramos rather than civilian action alone"],
      notableQuotes: []
    },
    {
      id: "military-defector-view",
      viewpoint: "Defecting military officer",
      viewpointType: "military",
      regionOrigin: "southeast-asia",
      narrative: "Enrile and Ramos later described their break from Marcos as driven by internal AFP factionalism and the perceived illegitimacy of the snap election result, framing their February 22 barricade less as a plan for civilian revolution and more as an attempted military reform that the EDSA crowd then made irreversible.",
      keyArguments: ["Their initial move was a narrow military mutiny against Marcos loyalists within the armed forces, not a call for the mass civilian mobilization that followed", "Cardinal Sin's broadcast and the resulting crowd transformed a contained military standoff into a decisive national event"],
      emphasized: ["Internal AFP reform grievances predating the snap election", "The tactical vulnerability of their position at Camps Aguinaldo and Crame absent civilian protection"],
      omitted: ["Their own prior service enforcing Marcos's martial-law-era policies before their 1986 break"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "fall-of-communism-1989", targetTitle: "The Fall of Communism in Eastern Europe", type: "provided-model", description: "EDSA's combination of mass nonviolent crowds and military non-cooperation was cited by organizers and observers of the 1989 Eastern European transitions as an example that entrenched governments could fall without civil war." },
    { targetSlug: "myanmar-spring-revolution", targetTitle: "The Myanmar Spring Revolution", type: "counter-example", description: "Where EDSA's military high command defected early and refused to fire on crowds, Myanmar's 2021 uprising faced a military that remained cohesive and used lethal force throughout, producing a starkly different trajectory." }
  ],
  media: [],
  relatedRevoltSlugs: ["fall-of-communism-1989", "myanmar-spring-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "arab-spring",
  slug: "arab-spring",
  title: "The Arab Spring",
  subtitle: "One street vendor's self-immolation set off uprisings in a dozen countries with a dozen different endings",
  era: "square-revolutions",
  region: "middle-east",
  country: "Tunisia, Egypt, Libya, Syria, Yemen, Bahrain (regional)",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "December 2010 to 2012 (initial wave)",
  dateStart: 2010,
  dateEnd: 2012,
  summary: "Street vendor Mohamed Bouazizi set himself on fire in Sidi Bouzid, Tunisia on December 17, 2010 after municipal officials confiscated his cart, a single act that detonated protests across a region where median age was under 25 and youth unemployment often exceeded 25 percent. Tunisia's Ben Ali fled within four weeks. Egypt's Hosni Mubarak resigned after eighteen days of Tahrir Square occupation in February 2011. From there national trajectories diverged sharply: Libya and Yemen's uprisings turned into prolonged armed conflict, Syria's protest movement became a civil war that by the 2020s had killed several hundred thousand people and displaced roughly half the country's pre-war population, Bahrain's uprising was suppressed with the direct military assistance of neighboring Gulf states, and Egypt's own democratic opening was reversed by a 2013 military coup.",
  significance: "The largest simultaneous wave of popular uprisings in the Arab world's modern history, and a widely studied case for how a single regional cascade can produce outcomes as divergent as Tunisia's fragile democracy and Syria's prolonged civil war from broadly similar starting grievances.",
  analyticalOutlook: "A regional cascade whose national branches diverged almost entirely on a single variable: whether the security apparatus fractured (Tunisia, Egypt) or held together and used force (Syria, Bahrain, Libya after early defections reversed into civil war).",
  grievances: [
    { kind: "Youth unemployment", intensity: 85, evidence: "Regional youth unemployment exceeded 25 percent in several countries in 2010, against a median population age under 25 across much of the Arab world." },
    { kind: "Authoritarian rule and corruption", intensity: 80, evidence: "Tunisia's Ben Ali and Egypt's Mubarak had each held power for roughly two and three decades respectively; WikiLeaks cables published in 2010 detailed documented Ben Ali family corruption that fueled early protest anger." },
    { kind: "Police brutality and state violence", intensity: 75, evidence: "Bouazizi's confrontation with a municipal inspector and subsequent self-immolation became a symbol of routine humiliation by local officials; Egypt's protests were partly catalyzed by the June 2010 police beating death of Khaled Said in Alexandria." },
    { kind: "Food price inflation", intensity: 65, evidence: "Global wheat prices roughly doubled between mid-2010 and early 2011 following a Russian export ban after a severe drought, sharply raising bread costs across food-importing Arab states." }
  ],
  actors: [
    { actorType: "masses", name: "Mohamed Bouazizi and the street protests", description: "Tunisian street vendor whose self-immolation on December 17, 2010 in Sidi Bouzid became the movement's founding act, and the mass protests that followed.", roleInArc: "His death on January 4, 2011 triggered protests that spread nationally within days", defected: false },
    { actorType: "students-youth", name: "Social-media-organized youth networks", description: "Loosely organized activist networks across Tunisia and Egypt, including Egypt's April 6 Youth Movement, that used social media to coordinate protests largely outside formal opposition parties.", roleInArc: "Provided early organizational capacity in Tunisia and Egypt's uprisings", defected: false },
    { actorType: "military-defectors", name: "Egyptian Armed Forces", description: "Egypt's military, a central economic and political institution under Mubarak.", roleInArc: "Declined to fire on Tahrir Square protesters and eased Mubarak out in February 2011, then led a 2013 coup against his elected successor", defected: true },
    { actorType: "old-regime", name: "Bashar al-Assad government", description: "Syria's ruling government since 2000, backed by Russia and Iran.", roleInArc: "Met protests with sustained lethal force starting in 2011, precipitating a civil war that continued for over a decade", defected: false },
    { actorType: "foreign-intervener", name: "Gulf Cooperation Council states", description: "Saudi Arabia and allied Gulf monarchies, which sent troops into Bahrain in March 2011 under a GCC mutual-defense framework.", roleInArc: "Directly suppressed Bahrain's uprising and backed counter-revolutionary outcomes elsewhere in the region", defected: false }
  ],
  tactics: [
    { tacticType: "occupation", description: "Sustained mass occupation of central public squares, most prominently Cairo's Tahrir Square for eighteen days in January-February 2011, became the movement's signature tactic and namesake.", prominence: "primary" },
    { tacticType: "digital-mobilization", description: "Facebook, Twitter, and YouTube were used to organize protests, document security force abuses, and spread footage internationally in real time, notably by Egypt's We Are All Khaled Said page.", prominence: "primary" },
    { tacticType: "general-strike", description: "Coordinated labor strikes, particularly in Egypt's Mahalla textile sector and Tunisia's UGTT-affiliated unions, added economic pressure alongside street protest.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "Youth Unemployment and Food Prices", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "High youth unemployment and a global wheat price spike build pressure across authoritarian Arab states through 2010.", keyEvents: ["Global wheat prices roughly double, mid-2010 to early 2011", "WikiLeaks Tunisia cables published, late 2010"] },
    { phase: "the-spark", label: "Bouazizi and the Tunisian Spark", tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: "Mohamed Bouazizi's self-immolation ignites protests that force Ben Ali to flee Tunisia within four weeks and spread the model regionally.", keyEvents: ["Bouazizi self-immolates, December 17, 2010; dies January 4, 2011", "Ben Ali flees Tunisia, January 14, 2011"] },
    { phase: "moderate-phase", label: "Tahrir Square", tStart: 0.34, tEnd: 0.48, intensity: 75, reached: true, summary: "Eighteen days of occupation in Cairo's Tahrir Square end with Mubarak's resignation, while protests spread to Libya, Yemen, Syria, and Bahrain.", keyEvents: ["Egyptian protests begin, January 25, 2011", "Mubarak resigns, February 11, 2011"] },
    { phase: "dual-power", label: "National Divergence", tStart: 0.48, tEnd: 0.60, intensity: 80, reached: true, summary: "National trajectories split sharply: Bahrain's uprising is crushed with GCC military assistance, Libya's escalates toward armed conflict, and Syria's protest movement meets sustained lethal repression.", keyEvents: ["GCC troops enter Bahrain, March 2011", "Syrian security forces fire on Deraa protesters, March 2011"] },
    { phase: "radical-phase", label: "Civil Wars Emerge", tStart: 0.60, tEnd: 0.72, intensity: 95, reached: true, summary: "Libya and Syria descend into prolonged civil war; Yemen's transition collapses into fragmented conflict over the following years.", keyEvents: ["Libyan civil war and NATO intervention, 2011", "Syrian conflict escalates into full civil war through 2012"] },
    { phase: "consolidation", label: "Divergent National Outcomes", tStart: 0.92, tEnd: 1.00, intensity: 60, reached: true, summary: "By 2012 to 2013, outcomes range from Tunisia's fragile new democracy to Egypt's 2013 military coup to ongoing war in Syria, Libya, and Yemen.", keyEvents: ["Egypt's Mohamed Morsi ousted by military coup, July 2013", "Syrian civil war continues past the initial uprising period"] }
  ],
  outcome: "ongoing-unresolved",
  peakParticipationPct: null,
  peakParticipationDisplay: "Cairo's Tahrir Square drew crowds estimated up to roughly 2 million on its largest single day, February 8, 2011",
  crossedParticipationThreshold: null,
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  durationDays: 730,
  deathToll: "varies enormously by country; Tunisia and Egypt's initial uprisings killed roughly 300 and 800 respectively, while the Syrian civil war alone had documented several hundred thousand deaths by the following decade",
  deathTollLow: 1000,
  deathTollHigh: 500000,
  regimeBefore: "personalist",
  regimeAfter: "unresolved",
  democratizationDelta: 0,
  successFactors: [
    { factorKey: "military-defection", label: "Security force defection as the branch point", framework: "chenoweth", status: "Tunisia's and Egypt's militaries declined to fire on protesters and eased their presidents out; Syria's, Bahrain's, and (initially) Libya's security forces did not fracture and used sustained force", direction: "indeterminate", baseRate: "Security force defection or non-cooperation is the strongest single predictor of movement success across the historical record, and its absence is equally predictive of prolonged violent conflict or suppression", rationale: "The Arab Spring is frequently cited as a natural experiment: near-identical protest repertoires and grievances produced opposite outcomes depending almost entirely on whether the military stayed loyal to the regime, cleanly separating Tunisia and Egypt's relatively fast transitions from Syria, Bahrain, and Libya's violent trajectories.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "external-intervention-divergence", label: "Divergent foreign intervention", framework: "skocpol", status: "Bahrain's uprising was suppressed by GCC troop intervention on the regime's side; Libya's saw NATO intervention on the opposition's side; Syria's saw Russian and Iranian intervention on the regime's side", direction: "indeterminate", baseRate: "Comparative studies of the 2011 uprisings identify the direction and presence of external military intervention as one of the clearest explanatory variables for why otherwise similar uprisings produced opposite outcomes", rationale: "Unlike 1989's relatively uniform external environment, the Arab Spring saw external powers intervene on both sides across different countries within the same regional wave, a key reason outcomes diverged so sharply from broadly similar starting conditions.", sources: ["Brownlee, Masoud and Reynolds, The Arab Spring (2015)"] },
    { factorKey: "participation-threshold", label: "3.5 percent participation rule", framework: "chenoweth", status: "Egypt's peak Tahrir crowds, estimated up to roughly 2 million against a population near 82 million in 2011, fall short of 3.5 percent nationally even though they proved sufficient given the concurrent military defection", direction: "indeterminate", baseRate: "Chenoweth's 3.5 percent finding is drawn primarily from national-level participation figures; sub-national concentrated mobilization, as in Tahrir Square, complicates direct application of the rule", rationale: "Egypt succeeded with concentrated capital-city mobilization well under the national 3.5 percent mark, illustrating that the threshold interacts with, rather than substitutes for, elite and security-force response.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] }
  ],
  keyFigures: [
    { name: "Mohamed Bouazizi", role: "Tunisian street vendor whose self-immolation catalyzed the regional uprisings", born: 1984, died: 2011, wikipedia: "https://en.wikipedia.org/wiki/Mohamed_Bouazizi" },
    { name: "Hosni Mubarak", role: "President of Egypt 1981-2011, resigned after eighteen days of protest", born: 1928, died: 2020, wikipedia: "https://en.wikipedia.org/wiki/Hosni_Mubarak" },
    { name: "Zine El Abidine Ben Ali", role: "President of Tunisia 1987-2011, fled the country January 14, 2011", born: 1936, died: 2019, wikipedia: "https://en.wikipedia.org/wiki/Zine_El_Abidine_Ben_Ali" },
    { name: "Bashar al-Assad", role: "President of Syria since 2000, whose government's crackdown produced the Syrian civil war", born: 1965, wikipedia: "https://en.wikipedia.org/wiki/Bashar_al-Assad" }
  ],
  legacyPoints: [
    "Tunisia produced the wave's one durable democratic transition, adopting a new constitution in 2014, though a 2021 presidential self-coup later concentrated power again.",
    "Syria's uprising became one of the 21st century's deadliest civil wars, with the UN documenting several hundred thousand deaths and roughly half the pre-war population displaced internally or abroad by the following decade.",
    "Egypt's initial democratic opening was reversed by a July 2013 military coup that removed elected president Mohamed Morsi, restoring military-linked rule.",
    "Demonstrated to subsequent movements worldwide, including Sudan's 2018-2019 uprising, both the mobilizing power of social media and the decisive importance of security-force behavior in determining outcomes."
  ],
  perspectives: [
    {
      id: "tunisian-democratic-activist",
      viewpoint: "Tunisian pro-democracy activist",
      viewpointType: "movement",
      regionOrigin: "middle-east",
      narrative: "Tunisian activists who organized after Bouazizi's death describe a genuine, broad-based democratic aspiration rooted in specific, documented grievances, unemployment, corruption, and police abuse, that succeeded because Tunisia's military, unlike Syria's or Bahrain's, declined to fire on its own citizens.",
      keyArguments: ["Tunisia's relatively professional, less politically entrenched military made the crucial difference between its outcome and the region's other uprisings", "The UGTT labor union's institutional weight gave Tunisia's transition an organizing backbone many other countries' uprisings lacked"],
      emphasized: ["The specific, documented corruption detailed in the 2010 WikiLeaks cables", "The 2014 constitution as a concrete democratic achievement"],
      omitted: ["The fragility of the 2014 settlement, later undone in part by the 2021 presidential self-coup"],
      notableQuotes: [{ text: "The people want the fall of the regime", speaker: "Regional protest chant, 2011", context: "Used across Tunisia, Egypt, Libya, Syria, Yemen, and Bahrain" }]
    },
    {
      id: "syrian-civil-war-displaced",
      viewpoint: "Displaced Syrian civilian",
      viewpointType: "diaspora",
      regionOrigin: "middle-east",
      narrative: "For Syrians displaced by the ensuing civil war, the 2011 protests are remembered as a peaceful movement for basic reforms that a government willing to use sustained lethal force, backed by Russian and Iranian intervention, turned into over a decade of war and displacement rather than the fast transitions seen in Tunisia or Egypt.",
      keyArguments: ["The initial 2011 protests in Deraa and elsewhere were peaceful and locally specific before the government's crackdown escalated the conflict", "External military backing for the Assad government, absent in Tunisia's case, prevented the kind of negotiated or forced exit seen elsewhere in the region"],
      emphasized: ["The peaceful character of the movement's first months", "The scale of civilian displacement and casualties over the following decade"],
      omitted: ["The subsequent fragmentation of the Syrian opposition into competing armed factions, including groups later designated as extremist by multiple governments"],
      notableQuotes: []
    }
  ],
  connections: [
    { targetSlug: "sudan-civil-war", targetTitle: "Sudan: The Captured Revolution", type: "inspired", description: "Sudan's 2018-2019 protest movement against Omar al-Bashir explicitly drew on Arab Spring tactics and framing, including sustained square occupation, before its own post-transition trajectory fractured into conflict." },
    { targetSlug: "fall-of-communism-1989", targetTitle: "The Fall of Communism in Eastern Europe", type: "parallel", description: "Both were regional cascades triggered by a single catalytic event spreading rapidly across neighboring states, though 1989's outcomes converged toward democracy while the Arab Spring's diverged sharply by country." }
  ],
  media: [],
  relatedRevoltSlugs: ["sudan-civil-war", "fall-of-communism-1989"],
  relatedHistorySlugs: ["arab-spring"],
  published: true
},
];
