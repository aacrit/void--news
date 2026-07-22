/* ===========================================================================
   void --revolt — Mock data
   Ships the section without a database (data.ts falls back to this on a 5s
   Supabase race) AND serves as the static-export slug registry (REVOLT_SLUGS
   feeds every [param]/generateStaticParams so a loaded revolution never 404s).
   =========================================================================== */

import type { Revolution } from './types';
import { MOCK_HISTORICAL_EXTRA } from './mockHistoricalExtra';

/* ── The French Revolution — the type anchor (ported from the YAML canary) ── */
const FRENCH_REVOLUTION: Revolution = {
  id: 'french-revolution',
  slug: 'french-revolution',
  title: 'The French Revolution',
  subtitle: 'A bankrupt monarchy, a hungry city, and the invention of modern politics',
  era: 'atlantic',
  region: 'europe',
  country: 'France',
  revoltType: 'social',
  status: 'concluded',
  dateDisplay: '1789 to 1799',
  dateStart: 1789,
  dateEnd: 1799,
  summary:
    "In the spring of 1789 the French crown could not pay its debts. A king who ruled by divine right summoned an assembly he had not called in 175 years, hoping to tax his way out of ruin. The Third Estate refused to be counted as one vote against two. Within weeks a locksmith king was a prisoner of the nation, feudalism was abolished in a single night, and a document declared that men are born free and equal in rights. Within five years the same revolution was guillotining its own founders at a rate of one every hour.",
  significance:
    "The French Revolution set the template every later revolution would argue with. It proved a determined urban crowd could topple Europe's oldest monarchy, and it proved that a revolution devours the people who make it. The words liberty, the nation, the left and the right, terror as a policy: all entered modern politics here.",
  grievances: [
    { kind: 'fiscal', intensity: 95, evidence: "State debt consumed roughly half of annual revenue; the 1788 harvest failed and bread reached 88 percent of a laborer's wage." },
    { kind: 'political', intensity: 80, evidence: 'An absolute monarchy with no representative check; the Estates-General had not met since 1614.' },
    { kind: 'inequality', intensity: 85, evidence: 'The clergy and nobility, two percent of the population, held most land and paid almost no direct tax.' },
    { kind: 'subsistence', intensity: 90, evidence: 'A cold winter and grain speculation left Paris hungry; bread riots preceded every political turn.' },
  ],
  structuralPressures: {
    'Fiscal crisis': { score: 3, note: 'Near-total state insolvency after backing the American Revolution.' },
    'Elite fracture': { score: 3, note: 'Liberal nobles and clergy defected at the Tennis Court Oath.' },
    'Mass immiseration': { score: 3, note: 'Harvest failure and bread prices at famine levels.' },
    'Repression': { score: 2, note: 'Royal troops massed at Versailles but the Paris garrison would not fire.' },
    'External shock': { score: 1, note: 'War debt from aiding the American colonies against Britain.' },
    'Legitimacy collapse': { score: 3, note: 'Divine-right monarchy could not survive needing permission to tax.' },
  },
  repressionLevel: 'moderate',
  actors: [
    { actorType: 'masses', name: 'The Paris sans-culottes', description: 'Artisans, shopkeepers and wage workers who supplied the crowd power and, later, the radical edge.', roleInArc: 'Stormed the Bastille, marched on Versailles, pushed the revolution leftward.', defected: false },
    { actorType: 'vanguard', name: 'The Jacobin Club', description: 'A network of clubs that moved from constitutional reform to revolutionary dictatorship.', roleInArc: 'Organized the radical phase and administered the Terror.', defected: false },
    { actorType: 'military-defectors', name: 'The Gardes Francaises', description: 'Royal guardsmen in Paris who refused to fire on the crowd and joined it.', roleInArc: 'Their defection made the storming of the Bastille possible.', defected: true },
    { actorType: 'old-regime', name: 'Louis XVI and the court', description: 'A monarch who conceded slowly, plotted escape, and was executed as Citizen Capet.', roleInArc: 'The target; his failed flight to Varennes destroyed the case for a constitutional monarchy.', defected: false },
    { actorType: 'foreign-intervener', name: 'The First Coalition', description: 'Austria, Prussia, Britain and allies who invaded to restore the monarchy.', roleInArc: 'External war radicalized the revolution and justified emergency government.', defected: false },
  ],
  tactics: [
    { tacticType: 'urban-uprising', description: 'The storming of the Bastille and the insurrections of August 1792 and 1793.', prominence: 'high' },
    { tacticType: 'mass-demonstration', description: "The Women's March on Versailles that brought the king back to Paris.", prominence: 'high' },
    { tacticType: 'parallel-institutions', description: 'The National Assembly, the Commune, and the network of Jacobin clubs.', prominence: 'high' },
    { tacticType: 'armed-insurgency', description: 'Revolutionary armies and the levee en masse that mobilized the nation for war.', prominence: 'medium' },
  ],
  resistanceType: 'hybrid',
  phases: [
    { phase: 'old-regime-crisis', label: 'The crown runs out of money', dateStart: '1788-08', tStart: 0.00, tEnd: 0.10, intensity: 30, reached: true, summary: 'Insolvency forces the king to summon the Estates-General for the first time since 1614.', keyEvents: ['Harvest failure of 1788', 'Convocation of the Estates-General'] },
    { phase: 'intellectual-desertion', label: 'The Third Estate refuses to be outvoted', dateStart: '1789-06', tStart: 0.12, tEnd: 0.22, intensity: 45, reached: true, summary: 'The commons declare themselves the National Assembly and swear the Tennis Court Oath.', keyEvents: ['Tennis Court Oath', 'Formation of the National Assembly'] },
    { phase: 'the-spark', label: 'The Bastille falls', dateStart: '1789-07-14', tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: 'A crowd storms the fortress-prison. Royal troops will not fire. The king has lost his capital.', keyEvents: ['Storming of the Bastille', 'Great Fear in the countryside'] },
    { phase: 'moderate-phase', label: 'A constitutional monarchy is tried', dateStart: '1789-08', tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: 'Feudalism abolished overnight; the Declaration of the Rights of Man proclaimed.', keyEvents: ['Abolition of feudalism', 'Declaration of the Rights of Man'] },
    { phase: 'dual-power', label: 'The king flees and is caught', dateStart: '1791-06', tStart: 0.48, tEnd: 0.60, intensity: 60, reached: true, summary: 'The flight to Varennes exposes the monarch as an enemy of the revolution. War with Austria begins.', keyEvents: ['Flight to Varennes', 'War of the First Coalition begins'] },
    { phase: 'radical-phase', label: 'The monarchy is overthrown', dateStart: '1792-08', tStart: 0.60, tEnd: 0.72, intensity: 80, reached: true, summary: 'The Tuileries is stormed, the First Republic proclaimed. Louis XVI is executed in January 1793.', keyEvents: ['Insurrection of 10 August 1792', 'Execution of Louis XVI'] },
    { phase: 'terror-virtue', label: 'The Terror', dateStart: '1793-09', tStart: 0.72, tEnd: 0.84, intensity: 100, reached: true, summary: 'The Committee of Public Safety governs by guillotine. Roughly 17000 are formally executed.', keyEvents: ['Committee of Public Safety', 'Law of Suspects'] },
    { phase: 'thermidor', label: 'The revolution eats Robespierre', dateStart: '1794-07', tStart: 0.84, tEnd: 0.92, intensity: 70, reached: true, summary: 'Robespierre is guillotined by colleagues who fear they are next. The Terror ends.', keyEvents: ['Fall of Robespierre', 'The Directory'] },
    { phase: 'consolidation', label: 'A general takes the republic', dateStart: '1799-11', tStart: 0.92, tEnd: 1.00, intensity: 60, reached: true, summary: 'Napoleon seizes power in the coup of 18 Brumaire. The revolution as a popular force is over.', keyEvents: ['Coup of 18 Brumaire', 'The Consulate'] },
  ],
  ateItsChildren: true,
  outcome: 'consolidated-autocracy',
  peakParticipationPct: null,
  peakParticipationDisplay: 'Tens of thousands at the decisive journees; participation was urban and intense rather than a measured national share.',
  crossedParticipationThreshold: null,
  militaryDefection: 'partial',
  foreignIntervention: 'direct-military',
  durationDays: 3765,
  deathToll: 'Roughly 17000 formally executed in the Terror; total deaths including the Vendee and the revolutionary wars run far higher.',
  deathTollLow: 17000,
  deathTollHigh: 40000,
  regimeBefore: 'monarchy',
  regimeAfter: 'personalist',
  democratizationDelta: 0,
  successFactors: [
    { factorKey: 'resistance_method', label: 'Method of struggle', framework: 'chenoweth', status: 'Hybrid. Mass urban uprising fused with armed revolutionary war.', direction: 'indeterminate', baseRate: 'Across 1900 to 2006, nonviolent campaigns succeeded about 53 percent of the time versus about 26 percent for armed ones.', rationale: 'The case predates the dataset, but its slide into armed terror illustrates why violence correlates with harder consolidation.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '1799', confidence: 'n/a' },
    { factorKey: 'security_defection', label: 'Did the security forces defect', framework: 'chenoweth', status: 'Partial. The Paris garrison would not fire in July 1789; the wider army stayed contested.', direction: 'favors-movement', baseRate: 'Security-force defection is the single strongest predictor of campaign success.', rationale: 'The refusal of royal troops to fire on the Bastille crowd removed the monarchy’s last coercive advantage in its capital.', sources: ['Nepstad, Nonviolent Revolutions (2011)'], asOf: '1789', confidence: 'high' },
    { factorKey: 'elite_fracture', label: 'Did the ruling elite split', framework: 'goldstone', status: 'Yes. Liberal nobles and parish clergy joined the Third Estate.', direction: 'favors-movement', baseRate: 'Elite defection is a core precondition of state breakdown in structural theories of revolution.', rationale: 'The Tennis Court Oath only held because a bloc of the privileged orders crossed over.', sources: ['Skocpol, States and Social Revolutions (1979)'], asOf: '1789', confidence: 'high' },
  ],
  keyFigures: [
    { name: 'Maximilien Robespierre', role: 'Jacobin leader and architect of the Terror, later its victim', born: 1758, died: 1794, wikipedia: 'https://en.wikipedia.org/wiki/Maximilien_Robespierre' },
    { name: 'Louis XVI', role: 'King of France, executed as Citizen Louis Capet', born: 1754, died: 1793, wikipedia: 'https://en.wikipedia.org/wiki/Louis_XVI' },
    { name: 'Georges Danton', role: 'Revolutionary orator, guillotined by his former allies', born: 1759, died: 1794, wikipedia: 'https://en.wikipedia.org/wiki/Georges_Danton' },
    { name: 'Napoleon Bonaparte', role: 'General who ended the revolution in the coup of 18 Brumaire', born: 1769, died: 1821, wikipedia: 'https://en.wikipedia.org/wiki/Napoleon' },
  ],
  legacyPoints: [
    'The left and the right are named for where deputies sat in the National Assembly.',
    'The metric system, civil marriage and the abolition of feudal dues outlived the republic.',
    'Terror as deliberate state policy entered the modern political vocabulary here.',
    'Every later revolution measured itself against 1789, in hope or in warning.',
  ],
  perspectives: [
    { id: 'fr-jacobin', viewpoint: 'The Jacobin republican', viewpointType: 'revolutionary', regionOrigin: 'Paris', narrative: 'The revolution had enemies within and armies without. A republic fighting for its life could not extend the rights of man to those plotting its destruction. The guillotine was the republic defending itself.', keyArguments: ['The Terror was a wartime emergency, not a program.', 'Invasion and revolt forced centralized power.'], emphasized: ['Foreign invasion', 'Royalist plots'], omitted: ['The scale of executions without trial'], notableQuotes: [{ text: 'Terror is nothing other than justice, prompt, severe, inflexible.', speaker: 'Maximilien Robespierre', context: 'On the Principles of Political Morality, 1794' }] },
    { id: 'fr-liberal', viewpoint: 'The liberal constitutionalist', viewpointType: 'moderate', regionOrigin: 'France', narrative: '1789 was the achievement: a constitution, a limited monarch, the rights of man. What followed was the betrayal. The radicals mistook the crowd for the nation and the guillotine for justice.', keyArguments: ['The moderate phase was the revolution’s real gift.', 'Radicalization was a choice, not a necessity.'], emphasized: ['The Declaration of Rights', 'Rule of law'], omitted: ['Why the constitutional monarchy failed to hold'], notableQuotes: [{ text: 'They have made a desert and called it liberty.', speaker: 'A Girondin, before the scaffold', context: 'The purge of the moderates, 1793' }] },
  ],
  connections: [
    { targetSlug: 'haitian-revolution', targetTitle: 'The Haitian Revolution', type: 'inspired', description: 'The Declaration of the Rights of Man was read in Saint-Domingue and turned against the slaveholders who wrote it.' },
    { targetSlug: 'russian-revolution', targetTitle: 'The Russian Revolution', type: 'provided-model', description: 'The Bolsheviks studied 1789 closely, casting themselves as Jacobins who would not stop at Thermidor.' },
  ],
  media: [
    { id: 'fr-bastille', type: 'painting', url: 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Prise_de_la_Bastille.jpg', caption: "Jean-Pierre Houel's contemporary watercolor of 14 July 1789.", attribution: 'Jean-Pierre Houel, 1789, Bibliotheque nationale de France', year: '1789' },
  ],
  heroImage: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/Prise_de_la_Bastille.jpg/1280px-Prise_de_la_Bastille.jpg',
  heroAttribution: 'Jean-Pierre Houel, Storming of the Bastille (1789), public domain.',
  relatedRevoltSlugs: ['haitian-revolution', 'russian-revolution'],
  relatedHistorySlugs: ['french-revolution'],
  published: true,
};

/* ── Active revolutions (curated; augmented at runtime with live news cards) ── */

const MYANMAR: Revolution = {
  id: 'myanmar-spring-revolution',
  slug: 'myanmar-spring-revolution',
  title: 'The Myanmar Spring Revolution',
  subtitle: 'A stolen election answered with rifles',
  era: 'square-revolutions',
  region: 'southeast-asia',
  country: 'Myanmar',
  revoltType: 'democratic-uprising',
  status: 'active',
  dateDisplay: '2021 to present',
  dateStart: 2021,
  summary:
    "On 1 February 2021 the Myanmar military annulled an election it had lost in a landslide and jailed the civilian leadership. Nonviolent strikes filled the streets for weeks. When the army answered with live fire, much of the movement took up arms. A parallel National Unity Government and a patchwork of People's Defence Forces now hold ground the junta cannot retake.",
  significance:
    'Myanmar is a live test of the hardest question in the study of revolution: what a movement does when nonviolent resistance is met with mass killing. It began nonviolent and became one of the largest armed uprisings of the century.',
  analyticalOutlook:
    'The junta has lost control of much of the country’s periphery but holds the core cities. The historical record on armed insurgencies against an entrenched military is mixed, and foreign patrons on both sides prolong the stalemate. Placement on the arc: a contested dual-power phase with no thermidor in sight.',
  grievances: [
    { kind: 'political', intensity: 90, evidence: 'The military voided the November 2020 election, which the National League for Democracy won with about 80 percent of contested seats.' },
    { kind: 'repression', intensity: 88, evidence: 'Security forces killed more than 1500 people in the first year and detained thousands.' },
    { kind: 'ethnic', intensity: 75, evidence: 'Decades of conflict with ethnic armed organizations gave the new resistance ready-made allies and training.' },
  ],
  repressionLevel: 'severe',
  actors: [
    { actorType: 'masses', name: 'The Civil Disobedience Movement', description: 'Doctors, teachers and civil servants who walked off the job to deny the junta a functioning state.', roleInArc: 'Opened the revolution nonviolently and paralyzed public administration.', defected: false },
    { actorType: 'vanguard', name: 'The National Unity Government', description: 'A parallel government formed by ousted lawmakers and ethnic representatives.', roleInArc: 'Claims legitimate authority and coordinates the armed resistance.', defected: false },
    { actorType: 'military-defectors', name: 'Defecting soldiers and police', description: 'Members of the security forces who crossed to the resistance.', roleInArc: 'A steady but partial trickle of defections rather than a decisive break.', defected: true },
    { actorType: 'security-forces', name: 'The Tatmadaw', description: 'The Myanmar armed forces under Min Aung Hlaing.', roleInArc: 'Holds the cities and air power; has lost much of the countryside.', defected: false },
  ],
  tactics: [
    { tacticType: 'general-strike', description: 'The Civil Disobedience Movement shut down hospitals, banks and railways.', prominence: 'high' },
    { tacticType: 'armed-insurgency', description: "People's Defence Forces and allied ethnic armies contest territory.", prominence: 'high' },
    { tacticType: 'parallel-institutions', description: 'The National Unity Government runs courts, schools and taxation in liberated areas.', prominence: 'medium' },
  ],
  resistanceType: 'hybrid',
  phases: [
    { phase: 'old-regime-crisis', label: 'A managed transition curdles', dateStart: '2020-11', tStart: 0.00, tEnd: 0.12, intensity: 35, reached: true, summary: 'The military loses an election it expected to control and refuses the result.', keyEvents: ['NLD landslide', 'Fraud claims rejected by the election commission'] },
    { phase: 'the-spark', label: 'The coup', dateStart: '2021-02-01', tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: 'The army detains the civilian leadership and declares a state of emergency. Mass protest follows within days.', keyEvents: ['1 February coup', 'Civil Disobedience Movement begins'] },
    { phase: 'radical-phase', label: 'From strikes to rifles', dateStart: '2021-05', tStart: 0.60, tEnd: 0.72, intensity: 85, reached: true, summary: 'After mass killings of protesters, the movement forms armed defence forces. The revolution becomes a war.', keyEvents: ['Formation of the PDFs', 'Alliance with ethnic armies'] },
    { phase: 'dual-power', label: 'Two governments, one country', dateStart: '2023-10', tStart: 0.48, tEnd: 0.60, intensity: 75, reached: true, summary: 'A coordinated offensive takes towns and border posts. Neither side can dislodge the other from its base.', keyEvents: ['Operation 1027', 'NUG administration expands'] },
    { phase: 'terror-virtue', label: 'Radicalization and reprisal', tStart: 0.72, tEnd: 0.84, intensity: 0, reached: false, summary: 'Not reached.', keyEvents: [] },
    { phase: 'consolidation', label: 'A settled order', tStart: 0.92, tEnd: 1.00, intensity: 0, reached: false, summary: 'Not reached.', keyEvents: [] },
  ],
  outcome: 'ongoing-unresolved',
  militaryDefection: 'partial',
  foreignIntervention: 'material',
  peakParticipationDisplay: 'Millions joined the early strikes; the armed phase involves tens of thousands under arms.',
  crossedParticipationThreshold: true,
  regimeBefore: 'military',
  regimeAfter: 'unresolved',
  successFactors: [
    { factorKey: 'resistance_method', label: 'Method of struggle', framework: 'chenoweth', status: 'Now primarily armed after beginning nonviolent.', direction: 'favors-regime', baseRate: 'About 53 percent of nonviolent campaigns from 1900 to 2006 succeeded, versus about 26 percent of armed ones.', rationale: 'The shift to arms was forced by mass killing, but the base rate for armed campaigns is markedly lower.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2024', confidence: 'medium' },
    { factorKey: 'security_defection', label: 'Did the security forces defect', framework: 'chenoweth', status: 'Partial. A steady trickle of defectors, but no unit-level break.', direction: 'indeterminate', baseRate: 'Defection of the security forces is the single strongest predictor of a campaign’s success.', rationale: 'The Tatmadaw’s cohesion, built on economic self-interest and isolation, has largely held.', sources: ['Nepstad, Nonviolent Revolutions (2011)'], asOf: '2024', confidence: 'medium' },
    { factorKey: 'external_support', label: 'Foreign backing', framework: 'chenoweth', status: 'Both sides receive material foreign support.', direction: 'favors-regime', baseRate: 'Foreign sponsorship correlates with lower, not higher, long-run campaign success.', rationale: 'Arms flows to the junta from major neighbors help it outlast a fragmented resistance.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2024', confidence: 'low' },
    { factorKey: 'coalition_breadth', label: 'Breadth of the coalition', framework: 'goldstone', status: 'Broad. Bamar majority pro-democracy forces allied with ethnic armed organizations.', direction: 'favors-movement', baseRate: 'Revolutions rarely succeed until a broad cross-class, cross-region coalition forms against the ruler.', rationale: 'The 2021 uprising bridged a historic divide between the majority and the ethnic peripheries.', sources: ['Goldstone, Revolution and Rebellion in the Early Modern World (1991)'], asOf: '2024', confidence: 'medium' },
  ],
  keyFigures: [
    { name: 'Min Aung Hlaing', role: 'Commander-in-chief who led the coup', wikipedia: 'https://en.wikipedia.org/wiki/Min_Aung_Hlaing' },
    { name: 'Aung San Suu Kyi', role: 'Ousted civilian leader, imprisoned since the coup', wikipedia: 'https://en.wikipedia.org/wiki/Aung_San_Suu_Kyi' },
  ],
  legacyPoints: [
    'The revolution began nonviolent and turned armed only after mass killings of protesters.',
    'A parallel government administers territory the junta no longer controls.',
    'It fused the Bamar democracy movement with long-standing ethnic insurgencies for the first time.',
  ],
  perspectives: [
    { id: 'mm-movement', viewpoint: 'The resistance', viewpointType: 'movement', regionOrigin: 'Myanmar', narrative: 'We tried the streets and they answered with bullets. Taking up arms was not a choice we wanted. It was the only door the generals left open.', keyArguments: ['The turn to arms was defensive.', 'The NUG, not the junta, holds legitimate authority.'], emphasized: ['The stolen election', 'The scale of killings'], omitted: ['Civilian harm from resistance operations'], notableQuotes: [] },
    { id: 'mm-academic', viewpoint: 'The analyst', viewpointType: 'academic', regionOrigin: 'Global', narrative: 'Myanmar shows why the nonviolent advantage is not a law of nature. A regime willing to kill at scale can force even a broad movement into a war it is statistically less likely to win, then wait it out with foreign arms.', keyArguments: ['Regime brutality can invert the resistance advantage.', 'Fragmentation is the resistance’s central weakness.'], emphasized: ['Base rates', 'Security-force cohesion'], omitted: [], notableQuotes: [] },
  ],
  connections: [],
  media: [],
  relatedRevoltSlugs: ['arab-spring'],
  relatedHistorySlugs: [],
  liveQuery: {
    strong: ['Min Aung Hlaing', 'National Unity Government', "People's Defence Force", 'Tatmadaw', 'Arakan Army', 'Operation 1027'],
    context: ['Myanmar', 'Burma', 'Naypyidaw', 'Rakhine', 'Rohingya'],
    exclude: [],
  },
  analysisReviewedAt: '2026-07-01',
  predictionConfidence: 'low',
  published: true,
};

const IRAN_WLF: Revolution = {
  id: 'iran-woman-life-freedom',
  slug: 'iran-woman-life-freedom',
  title: 'Woman, Life, Freedom',
  subtitle: 'A death in custody and the largest challenge to the Islamic Republic in a generation',
  era: 'square-revolutions',
  region: 'middle-east',
  country: 'Iran',
  revoltType: 'democratic-uprising',
  status: 'dormant',
  dateDisplay: '2022 to present',
  dateStart: 2022,
  summary:
    'In September 2022 a 22-year-old woman, Mahsa Jina Amini, died in the custody of Iran’s morality police after being detained over her headscarf. Protests led by young women spread to every province under three words: Woman, Life, Freedom. The state answered with mass arrests, hundreds of deaths and executions. Open protest has receded, but the defiance of the mandatory hijab has not.',
  significance:
    'This was the first Iranian uprising organized around gender and everyday autonomy rather than economics or a single leader. It has no headquarters to arrest, which is both its resilience and its limit.',
  analyticalOutlook:
    'The movement is currently dormant rather than defeated: street mobilization has fallen, but everyday noncompliance persists and the security forces have not fractured. History suggests leaderless movements are hard to crush and hard to convert into a transfer of power. Placement on the arc: a spark that reached a radical challenge and then receded without dual power.',
  grievances: [
    { kind: 'rights', intensity: 88, evidence: 'Enforcement of the mandatory hijab by a morality police empowered to detain women on sight.' },
    { kind: 'political', intensity: 80, evidence: 'A clerical system that vets candidates and reserves ultimate power to an unelected Supreme Leader.' },
    { kind: 'economic', intensity: 70, evidence: 'Sanctions, inflation and youth unemployment among a large, educated under-30 population.' },
  ],
  repressionLevel: 'severe',
  actors: [
    { actorType: 'students-youth', name: 'Young women and students', description: 'Schoolgirls and university students who led the marches and removed their headscarves in public.', roleInArc: 'The movement’s face and front line.', defected: false },
    { actorType: 'masses', name: 'Cross-class urban protesters', description: 'Bazaar merchants, ethnic minorities and workers who joined the wave.', roleInArc: 'Broadened the protests beyond the capital.', defected: false },
    { actorType: 'security-forces', name: 'The Basij and the Revolutionary Guard', description: 'The paramilitary and elite security apparatus of the Islamic Republic.', roleInArc: 'Suppressed the protests without visible defection.', defected: false },
    { actorType: 'diaspora', name: 'The Iranian diaspora', description: 'Exiles who amplified the movement abroad and pressed for sanctions.', roleInArc: 'Kept the movement visible internationally; contested over leadership claims.', defected: false },
  ],
  tactics: [
    { tacticType: 'mass-demonstration', description: 'Street protests across more than 150 cities and towns.', prominence: 'high' },
    { tacticType: 'civil-disobedience', description: 'Public removal and burning of the mandatory hijab.', prominence: 'high' },
    { tacticType: 'digital-mobilization', description: 'Encrypted apps and diaspora media coordinated protest despite internet shutdowns.', prominence: 'medium' },
  ],
  resistanceType: 'nonviolent',
  phases: [
    { phase: 'old-regime-crisis', label: 'A brittle system', dateStart: '2022-09', tStart: 0.00, tEnd: 0.12, intensity: 30, reached: true, summary: 'Economic pain and social control meet a young, connected population.', keyEvents: ['Sanctions and inflation', 'Rising defiance of dress codes'] },
    { phase: 'the-spark', label: 'A death in custody', dateStart: '2022-09-16', tStart: 0.22, tEnd: 0.34, intensity: 75, reached: true, summary: 'Mahsa Jina Amini dies after detention over her headscarf. Protests spread nationwide within days.', keyEvents: ['Death of Mahsa Amini', 'Woman, Life, Freedom spreads'] },
    { phase: 'radical-phase', label: 'A nationwide challenge', dateStart: '2022-10', tStart: 0.60, tEnd: 0.72, intensity: 80, reached: true, summary: 'Protests demand not reform but the end of the Islamic Republic. The state responds with lethal force and executions.', keyEvents: ['Nationwide protests', 'Executions of protesters'] },
    { phase: 'dual-power', label: 'A rival authority', tStart: 0.48, tEnd: 0.60, intensity: 0, reached: false, summary: 'Not reached. The movement produced no governing alternative on the ground.', keyEvents: [] },
    { phase: 'consolidation', label: 'A settled order', tStart: 0.92, tEnd: 1.00, intensity: 0, reached: false, summary: 'Not reached.', keyEvents: [] },
  ],
  outcome: 'ongoing-unresolved',
  militaryDefection: 'none',
  foreignIntervention: 'none',
  peakParticipationDisplay: 'Protests in more than 150 cities; sustained peak participation stayed below the level that has historically forced change.',
  crossedParticipationThreshold: false,
  regimeBefore: 'theocracy',
  regimeAfter: 'unresolved',
  successFactors: [
    { factorKey: 'resistance_method', label: 'Method of struggle', framework: 'chenoweth', status: 'Nonviolent and civic.', direction: 'favors-movement', baseRate: 'About 53 percent of nonviolent campaigns from 1900 to 2006 succeeded, versus about 26 percent of armed ones.', rationale: 'The movement’s discipline keeps the higher base rate available to it.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2026', confidence: 'medium' },
    { factorKey: 'peak_participation', label: 'Peak participation', framework: 'chenoweth', status: 'Broad but below the threshold; sustained turnout fell after the crackdown.', direction: 'favors-regime', baseRate: 'No campaign that mobilized at least 3.5 percent of the population at its peak has failed.', rationale: 'The movement did not sustain the mass turnout the record associates with success.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2026', confidence: 'medium' },
    { factorKey: 'security_defection', label: 'Did the security forces defect', framework: 'chenoweth', status: 'No visible defection.', direction: 'favors-regime', baseRate: 'Defection of the security forces is the single strongest predictor of a campaign’s success.', rationale: 'The Revolutionary Guard and Basij are bound to the system by ideology and privilege.', sources: ['Nepstad, Nonviolent Revolutions (2011)'], asOf: '2026', confidence: 'high' },
    { factorKey: 'leadership_structure', label: 'Leadership', framework: 'tilly', status: 'Leaderless and horizontal.', direction: 'indeterminate', baseRate: 'Leaderless movements resist decapitation but struggle to negotiate a transfer of power.', rationale: 'No headquarters to arrest, but also no body that could accept a regime’s surrender.', sources: ['Tufekci, Twitter and Tear Gas (2017)'], asOf: '2026', confidence: 'medium' },
  ],
  keyFigures: [
    { name: 'Mahsa Jina Amini', role: 'Whose death in custody sparked the movement', born: 2000, died: 2022, wikipedia: 'https://en.wikipedia.org/wiki/Death_of_Mahsa_Amini' },
  ],
  legacyPoints: [
    'The first Iranian uprising centered on women and bodily autonomy rather than economics.',
    'Everyday defiance of the mandatory hijab has outlasted the street protests.',
    'A leaderless structure made the movement hard to behead and hard to bargain with.',
  ],
  perspectives: [
    { id: 'ir-movement', viewpoint: 'The protesters', viewpointType: 'movement', regionOrigin: 'Iran', narrative: 'We are not asking for a softer version of this system. A woman detained and dead over a piece of cloth is the whole system in one image. Woman, Life, Freedom is not a slogan about clothes. It is about who owns a life.', keyArguments: ['The demand is the end of the system, not reform.', 'Everyday defiance continues even when the streets are quiet.'], emphasized: ['Gender and autonomy', 'The scale of repression'], omitted: [], notableQuotes: [] },
    { id: 'ir-academic', viewpoint: 'The analyst', viewpointType: 'academic', regionOrigin: 'Global', narrative: 'The movement has the method the record rewards and lacks the two things it also rewards: a security-force fracture and sustained mass turnout. Leaderlessness protects it from decapitation and denies it a negotiating table.', keyArguments: ['Method favorable, structure unfavorable.', 'Dormant is not the same as defeated.'], emphasized: ['Base rates', 'Movement structure'], omitted: [], notableQuotes: [] },
  ],
  connections: [],
  media: [],
  relatedRevoltSlugs: ['iranian-revolution'],
  relatedHistorySlugs: ['iranian-revolution'],
  liveQuery: {
    strong: ['Mahsa Amini', 'Woman Life Freedom', 'Woman, Life, Freedom', 'morality police', 'Jina Amini'],
    context: ['Iran', 'Tehran', 'Iranian'],
    exclude: ['nuclear deal', 'nuclear talks', 'JCPOA', 'uranium enrichment', 'nuclear program'],
  },
  analysisReviewedAt: '2026-07-01',
  predictionConfidence: 'medium',
  published: true,
};

const SUDAN: Revolution = {
  id: 'sudan-civil-war',
  slug: 'sudan-civil-war',
  title: 'Sudan: The Captured Revolution',
  subtitle: 'A democracy overthrown by the two generals meant to protect it',
  era: 'square-revolutions',
  region: 'africa',
  country: 'Sudan',
  revoltType: 'political',
  status: 'active',
  dateDisplay: '2019 to present',
  dateStart: 2019,
  summary:
    'In 2019 a nonviolent uprising toppled Omar al-Bashir after thirty years in power. A civilian-military transition followed. In 2021 the generals seized full control in a coup. In April 2023 the two men who led that coup, the head of the army and the head of the Rapid Support Forces, turned their arsenals on each other. A revolution that began with chants for civilian rule became one of the world’s largest displacement crises.',
  significance:
    'Sudan is the case of a successful nonviolent overthrow that was captured before it could consolidate. It shows that removing a dictator is not the same as ending the system that produced him.',
  analyticalOutlook:
    'The civilian movement that won in 2019 has been sidelined by a war between two armed factions. The historical record is clear that revolutions are most vulnerable in the transition, when the old coercive institutions survive the ruler. Placement on the arc: a spark and moderate phase that collapsed back into a factional civil war rather than reaching consolidation.',
  grievances: [
    { kind: 'economic', intensity: 85, evidence: 'A tripling of bread prices in December 2018 lit the initial protests.' },
    { kind: 'political', intensity: 88, evidence: 'Thirty years of one-man rule under Omar al-Bashir, wanted by the International Criminal Court.' },
    { kind: 'security', intensity: 82, evidence: 'A paramilitary force, the Rapid Support Forces, grown powerful enough to rival the national army.' },
  ],
  repressionLevel: 'severe',
  actors: [
    { actorType: 'organized-labor', name: 'The Sudanese Professionals Association', description: 'A coalition of doctors, lawyers and teachers that organized the 2019 uprising.', roleInArc: 'Provided the civilian leadership and the sit-in that forced Bashir out.', defected: false },
    { actorType: 'masses', name: 'The neighborhood resistance committees', description: 'Grassroots bodies that sustained protest and now run local aid.', roleInArc: 'Kept the civilian revolution alive after the coup.', defected: false },
    { actorType: 'security-forces', name: 'The Sudanese Armed Forces', description: 'The national army under General Abdel Fattah al-Burhan.', roleInArc: 'Co-led the coup, then fought its former partner.', defected: false },
    { actorType: 'counter-revolutionaries', name: 'The Rapid Support Forces', description: 'A paramilitary force under Mohamed Hamdan Dagalo, known as Hemedti, rooted in the Darfur Janjaweed.', roleInArc: 'Co-led the coup, then turned on the army; accused of atrocities in Darfur.', defected: false },
  ],
  tactics: [
    { tacticType: 'general-strike', description: 'A general strike and a mass sit-in outside army headquarters forced Bashir out in 2019.', prominence: 'high' },
    { tacticType: 'occupation', description: 'The Khartoum sit-in became the symbol of the civilian revolution.', prominence: 'high' },
    { tacticType: 'parallel-institutions', description: 'Resistance committees organized services and documentation through the war.', prominence: 'medium' },
  ],
  resistanceType: 'nonviolent',
  phases: [
    { phase: 'old-regime-crisis', label: 'Bread and thirty years', dateStart: '2018-12', tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: 'A currency crisis and a price shock ignite protests against a long dictatorship.', keyEvents: ['Bread price protests', 'Nationwide demonstrations'] },
    { phase: 'the-spark', label: 'The sit-in topples Bashir', dateStart: '2019-04', tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: 'A mass sit-in outside army headquarters forces the military to remove Bashir.', keyEvents: ['Fall of al-Bashir', 'The Khartoum sit-in'] },
    { phase: 'moderate-phase', label: 'A shared transition', dateStart: '2019-08', tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: 'A civilian-military council is meant to lead to elections. The generals never intend to leave.', keyEvents: ['Transitional government', 'Massacre of the sit-in'] },
    { phase: 'dual-power', label: 'The coup and the split', dateStart: '2021-10', tStart: 0.48, tEnd: 0.60, intensity: 78, reached: true, summary: 'The generals seize full power, then fall out. In April 2023 army and paramilitary go to war.', keyEvents: ['2021 coup', 'April 2023 war begins'] },
    { phase: 'radical-phase', label: 'The radicals win', tStart: 0.60, tEnd: 0.72, intensity: 0, reached: false, summary: 'Not reached. Power was captured by armed factions, not a revolutionary vanguard.', keyEvents: [] },
    { phase: 'consolidation', label: 'A settled order', tStart: 0.92, tEnd: 1.00, intensity: 0, reached: false, summary: 'Not reached.', keyEvents: [] },
  ],
  outcome: 'civil-war',
  militaryDefection: 'none',
  foreignIntervention: 'material',
  peakParticipationDisplay: 'The 2019 uprising drew mass nationwide participation; the current war is fought by two armed factions, not the civilian movement.',
  crossedParticipationThreshold: true,
  regimeBefore: 'personalist',
  regimeAfter: 'unresolved',
  successFactors: [
    { factorKey: 'resistance_method', label: 'Method of the 2019 uprising', framework: 'chenoweth', status: 'Nonviolent, and it succeeded in removing the dictator.', direction: 'favors-movement', baseRate: 'About 53 percent of nonviolent campaigns from 1900 to 2006 succeeded, versus about 26 percent of armed ones.', rationale: 'The civilian movement achieved the higher-probability outcome: it toppled the ruler without a war.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2019', confidence: 'high' },
    { factorKey: 'transition_capture', label: 'Surviving the transition', framework: 'skocpol', status: 'Failed. The old coercive institutions outlived the ruler and seized power.', direction: 'favors-regime', baseRate: 'Revolutions are most fragile in the transition, when the old state’s security apparatus survives the leader.', rationale: 'The army and the Rapid Support Forces were never dismantled and later took the state by force.', sources: ['Skocpol, States and Social Revolutions (1979)'], asOf: '2023', confidence: 'high' },
    { factorKey: 'security_defection', label: 'Did the security forces defect', framework: 'chenoweth', status: 'The army removed Bashir but kept power for itself.', direction: 'indeterminate', baseRate: 'Defection of the security forces is the single strongest predictor of a campaign’s success.', rationale: 'A defection that installs the generals rather than the movement is a partial and dangerous kind of victory.', sources: ['Nepstad, Nonviolent Revolutions (2011)'], asOf: '2021', confidence: 'medium' },
  ],
  keyFigures: [
    { name: 'Abdel Fattah al-Burhan', role: 'Head of the Sudanese Armed Forces', wikipedia: 'https://en.wikipedia.org/wiki/Abdel_Fattah_al-Burhan' },
    { name: 'Mohamed Hamdan Dagalo (Hemedti)', role: 'Head of the Rapid Support Forces', wikipedia: 'https://en.wikipedia.org/wiki/Hemedti' },
  ],
  legacyPoints: [
    'A nonviolent movement removed a thirty-year dictator in 2019.',
    'The revolution was captured in the transition by the very forces meant to guard it.',
    'The 2023 war became one of the world’s largest displacement crises.',
  ],
  perspectives: [
    { id: 'sd-movement', viewpoint: 'The resistance committees', viewpointType: 'movement', regionOrigin: 'Sudan', narrative: 'We won in 2019 and were robbed in the years after. Neither general speaks for the revolution. Our demand has not changed since the sit-in: a full civilian government and no army in politics.', keyArguments: ['Neither warring faction represents the revolution.', 'The demand remains civilian rule.'], emphasized: ['The 2019 victory', 'The betrayal of the transition'], omitted: [], notableQuotes: [] },
    { id: 'sd-academic', viewpoint: 'The analyst', viewpointType: 'academic', regionOrigin: 'Global', narrative: 'Sudan is the textbook warning that toppling a dictator is the easy half. When the old security institutions survive intact, they can wait out the crowd and then divide the state between them.', keyArguments: ['The danger is the transition, not the overthrow.', 'Unreformed coercive institutions capture revolutions.'], emphasized: ['Institutional survival'], omitted: [], notableQuotes: [] },
  ],
  connections: [],
  media: [],
  relatedRevoltSlugs: ['arab-spring'],
  relatedHistorySlugs: [],
  liveQuery: {
    strong: ['Rapid Support Forces', 'Hemedti', 'Burhan', 'Sudanese Armed Forces', 'Dagalo'],
    context: ['Sudan', 'Khartoum', 'Darfur', 'Sudanese'],
    exclude: ['South Sudan', 'Juba'],
  },
  analysisReviewedAt: '2026-07-01',
  predictionConfidence: 'low',
  published: true,
};

const VENEZUELA: Revolution = {
  id: 'venezuela',
  slug: 'venezuela',
  title: 'Venezuela: The Ballot-Box Standoff',
  subtitle: 'An opposition that keeps winning votes it is not allowed to count',
  era: 'square-revolutions',
  region: 'americas',
  country: 'Venezuela',
  revoltType: 'democratic-uprising',
  status: 'dormant',
  dateDisplay: '2014 to present',
  dateStart: 2014,
  summary:
    'Venezuela holds the largest oil reserves on earth and a population that has watched its economy collapse and roughly a quarter of its people leave. Waves of protest in 2014, 2017 and 2019 failed to dislodge the government. In 2024 the opposition says it won the presidential election by a wide margin and published the tallies to prove it. The government declared itself the winner without releasing the count.',
  significance:
    'Venezuela is a case of a movement with majorities and mobilization that still cannot cross the last step, because the state controls the courts, the count and the guns. It tests whether elections can end an autocracy that has learned to survive them.',
  analyticalOutlook:
    'The opposition has repeatedly won public support without winning power, because the security forces and the electoral authority remain loyal to the government. The record on removing entrenched autocracies through contested elections alone, without an elite or military fracture, is poor. Placement on the arc: a recurring spark that has not produced dual power or a security-force break.',
  grievances: [
    { kind: 'economic', intensity: 90, evidence: 'Years of hyperinflation and shortages; an estimated seven to eight million people have emigrated.' },
    { kind: 'political', intensity: 85, evidence: 'Courts, the electoral council and the legislature packed to favor the ruling party.' },
    { kind: 'electoral', intensity: 88, evidence: 'A 2024 presidential result declared without publishing polling-station tallies.' },
  ],
  repressionLevel: 'high',
  actors: [
    { actorType: 'masses', name: 'The opposition electorate', description: 'A cross-class majority that has repeatedly voted against the government.', roleInArc: 'Provides the votes and the crowds, but not the leverage.', defected: false },
    { actorType: 'vanguard', name: 'The opposition leadership', description: 'Figures including Maria Corina Machado and Edmundo Gonzalez around the 2024 campaign.', roleInArc: 'Organized the electoral challenge and documented the tallies.', defected: false },
    { actorType: 'security-forces', name: 'The armed forces and colectivos', description: 'A military tied to the government by patronage and pro-government armed groups.', roleInArc: 'The decisive bloc that has not defected.', defected: false },
  ],
  tactics: [
    { tacticType: 'mass-demonstration', description: 'Repeated waves of street protest in 2014, 2017 and 2019.', prominence: 'high' },
    { tacticType: 'parallel-institutions', description: 'The opposition documented and published its own vote tallies in 2024.', prominence: 'medium' },
    { tacticType: 'boycott-noncooperation', description: 'International non-recognition and sanctions pressure.', prominence: 'medium' },
  ],
  resistanceType: 'nonviolent',
  phases: [
    { phase: 'old-regime-crisis', label: 'An oil economy collapses', dateStart: '2014', tStart: 0.00, tEnd: 0.12, intensity: 45, reached: true, summary: 'Falling oil prices and mismanagement trigger shortages, inflation and the first protest wave.', keyEvents: ['2014 protests', 'Economic collapse'] },
    { phase: 'the-spark', label: 'Recurring uprisings', dateStart: '2017', tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: 'Mass protests in 2017 and a rival presidency in 2019 challenge the government and fail to move it.', keyEvents: ['2017 protests', 'The 2019 presidential standoff'] },
    { phase: 'moderate-phase', label: 'The electoral route', dateStart: '2024', tStart: 0.34, tEnd: 0.48, intensity: 60, reached: true, summary: 'The opposition contests the 2024 election, claims a wide win and publishes tallies. The result is declared against it.', keyEvents: ['2024 election', 'Disputed result'] },
    { phase: 'dual-power', label: 'A rival authority', tStart: 0.48, tEnd: 0.60, intensity: 0, reached: false, summary: 'Not durably reached. The 2019 rival presidency never controlled the state.', keyEvents: [] },
    { phase: 'consolidation', label: 'A settled order', tStart: 0.92, tEnd: 1.00, intensity: 0, reached: false, summary: 'Not reached.', keyEvents: [] },
  ],
  outcome: 'ongoing-unresolved',
  militaryDefection: 'none',
  foreignIntervention: 'diplomatic',
  peakParticipationDisplay: 'Large repeated protest waves and a decisive electoral majority in 2024, without the security-force break that turns votes into power.',
  crossedParticipationThreshold: false,
  regimeBefore: 'personalist',
  regimeAfter: 'unresolved',
  successFactors: [
    { factorKey: 'resistance_method', label: 'Method of struggle', framework: 'chenoweth', status: 'Nonviolent and electoral.', direction: 'favors-movement', baseRate: 'About 53 percent of nonviolent campaigns from 1900 to 2006 succeeded, versus about 26 percent of armed ones.', rationale: 'Method keeps the favorable base rate available, but method alone has not sufficed here.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2026', confidence: 'medium' },
    { factorKey: 'security_defection', label: 'Did the security forces defect', framework: 'chenoweth', status: 'No. The military remains bound to the government by patronage.', direction: 'favors-regime', baseRate: 'Defection of the security forces is the single strongest predictor of a campaign’s success.', rationale: 'Every Venezuelan protest wave has broken against an intact military.', sources: ['Nepstad, Nonviolent Revolutions (2011)'], asOf: '2026', confidence: 'high' },
    { factorKey: 'elite_fracture', label: 'Did the ruling elite split', framework: 'goldstone', status: 'No durable split within the governing bloc.', direction: 'favors-regime', baseRate: 'Revolutions rarely succeed until the ruling elite fractures.', rationale: 'Oil patronage and the fear of prosecution have kept the elite together.', sources: ['Goldstone, Revolution and Rebellion in the Early Modern World (1991)'], asOf: '2026', confidence: 'high' },
    { factorKey: 'peak_participation', label: 'Peak participation', framework: 'chenoweth', status: 'Large but episodic; sustained mobilization has faded between waves.', direction: 'indeterminate', baseRate: 'No campaign that mobilized at least 3.5 percent of the population at its peak has failed.', rationale: 'Emigration and exhaustion have thinned each successive wave.', sources: ['Chenoweth and Stephan, Why Civil Resistance Works (2011)'], asOf: '2026', confidence: 'medium' },
  ],
  keyFigures: [
    { name: 'Maria Corina Machado', role: 'Opposition leader behind the 2024 campaign', wikipedia: 'https://en.wikipedia.org/wiki/Mar%C3%ADa_Corina_Machado' },
    { name: 'Nicolas Maduro', role: 'President since 2013', wikipedia: 'https://en.wikipedia.org/wiki/Nicol%C3%A1s_Maduro' },
  ],
  legacyPoints: [
    'A movement that has won public majorities without winning power.',
    'Roughly a quarter of the population has emigrated during the crisis.',
    'The 2024 dispute turned on published vote tallies the government would not release.',
  ],
  perspectives: [
    { id: 've-movement', viewpoint: 'The opposition', viewpointType: 'movement', regionOrigin: 'Venezuela', narrative: 'We do not need to seize anything. We won the vote and we can prove it, receipt by receipt. What stands between the count and the country is not the people. It is a government that will not let the numbers be read aloud.', keyArguments: ['The 2024 tallies show a decisive opposition win.', 'The obstacle is state control of the count and the guns.'], emphasized: ['The published tallies', 'The scale of emigration'], omitted: [], notableQuotes: [] },
    { id: 've-academic', viewpoint: 'The analyst', viewpointType: 'academic', regionOrigin: 'Global', narrative: 'Venezuela is a standing lesson that majorities do not equal leverage. Without a fracture in the military or the elite, an autocracy that controls the count can lose every honest tally and keep every office.', keyArguments: ['Votes without a security-force break rarely move an autocracy.', 'Elite cohesion is the government’s core asset.'], emphasized: ['Security-force loyalty', 'Elite cohesion'], omitted: [], notableQuotes: [] },
  ],
  connections: [],
  media: [],
  relatedRevoltSlugs: [],
  relatedHistorySlugs: [],
  liveQuery: {
    strong: ['Maduro', 'Machado', 'Gonzalez', 'Guaido', 'Chavismo'],
    context: ['Venezuela', 'Caracas', 'Venezuelan'],
    exclude: [],
  },
  analysisReviewedAt: '2026-07-01',
  predictionConfidence: 'medium',
  published: true,
};

export const MOCK_HISTORICAL: Revolution[] = [
  FRENCH_REVOLUTION,
  ...MOCK_HISTORICAL_EXTRA,
];

export const MOCK_ACTIVE: Revolution[] = [
  MYANMAR,
  IRAN_WLF,
  SUDAN,
  VENEZUELA,
];

export const MOCK_REVOLUTIONS: Revolution[] = [...MOCK_HISTORICAL, ...MOCK_ACTIVE];

/** Build-time slug registry for generateStaticParams (static export). */
export const REVOLT_SLUGS: string[] = MOCK_REVOLUTIONS.map((r) => r.slug);
