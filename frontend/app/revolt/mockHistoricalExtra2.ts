/* void --revolt: additional historical mock entries (full bench, batch 2). */
import type { Revolution } from './types';

export const MOCK_HISTORICAL_EXTRA_2: Revolution[] = [
{
  id: "glorious-revolution-1688",
  slug: "glorious-revolution-1688",
  title: "The Glorious Revolution",
  subtitle: "A king invites his own overthrow and calls it an invitation",
  era: "atlantic",
  region: "europe",
  country: "England",
  revoltType: "velvet-negotiated",
  status: "concluded",
  dateDisplay: "1688-1689",
  dateStart: 1688,
  dateEnd: 1689,
  summary: "James II's Catholic heir, born June 10, 1688, turned a tolerable succession into an intolerable one. Seven English peers invited his Dutch son-in-law William of Orange to intervene; William landed with 463 ships and 15,000 men, James's army deserted around him, and Parliament crowned William and Mary jointly in February 1689.",
  significance: "Settled, without a major battle, the same question the Civil War had settled forty years earlier with an axe: that a king rules within law, not above it. The Bill of Rights it produced became a direct source text for the American framers.",
  grievances: [
    { kind: "Religious succession crisis", intensity: 88, evidence: "James Francis Edward, born Catholic on June 10, 1688, displaced his Protestant daughter Mary as heir, raising the prospect of a permanent Catholic dynasty." },
    { kind: "Abuse of royal prerogative", intensity: 75, evidence: "The 1687 Declaration of Indulgence suspended penal laws against Catholics and Dissenters by royal fiat, bypassing Parliament entirely." },
    { kind: "Politicization of the army and universities", intensity: 62, evidence: "James commissioned Catholic officers in violation of the Test Act and installed a Catholic president at Magdalen College, Oxford, in 1687." }
  ],
  actors: [
    { actorType: "foreign-intervener", name: "William of Orange", description: "Stadtholder of the Dutch Republic and husband of James's daughter Mary.", roleInArc: "Landed at Torbay on November 5, 1688, and marched on London largely unopposed.", defected: false },
    { actorType: "vanguard", name: "The Immortal Seven", description: "Six peers and a bishop who signed the June 1688 invitation letter asking William to intervene.", roleInArc: "Supplied the domestic legal cover for what would otherwise have been a foreign invasion.", defected: false },
    { actorType: "military-defectors", name: "John Churchill", description: "Senior army officer under James II, later Duke of Marlborough.", roleInArc: "Defected to William's camp on November 24, 1688, triggering a cascade of officer desertions.", defected: true },
    { actorType: "old-regime", name: "James II", description: "King of England, Scotland, and Ireland since 1685.", roleInArc: "Fled London in December 1688 after his army dissolved; captured, then deliberately permitted to escape to France.", defected: false },
    { actorType: "vanguard", name: "The Convention Parliament", description: "An extralegal assembly summoned after James's flight to resolve the succession.", roleInArc: "Declared the throne vacant and offered it jointly to William and Mary in February 1689, conditioned on the Bill of Rights.", defected: false }
  ],
  tactics: [
    { tacticType: "defection-fraternization", description: "James's officer corps deserted piecemeal once Churchill broke first, leaving the king no force able to resist William's advance.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "The Convention Parliament asserted authority over the succession the moment James fled, filling the vacuum before any rival body could.", prominence: "primary" },
    { tacticType: "elite-negotiation", description: "The Immortal Seven's invitation turned an invasion into a rescue in the eyes of the political class.", prominence: "secondary" }
  ],
  resistanceType: "nonviolent",
  phases: [
    { phase: "old-regime-crisis", label: "The Catholic heir", dateStart: "1688-06-10", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "The birth of a Catholic prince converts a tolerable irritant into an intolerable one: a Catholic dynasty.", keyEvents: ["Birth of Prince James Francis Edward, June 10, 1688", "Seven bishops acquitted of seditious libel, June 30, 1688"] },
    { phase: "the-spark", label: "The invitation and the landing", dateStart: "1688-11-05", tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: "William's fleet lands at Torbay in November, and James's army begins to dissolve around him.", keyEvents: ["Immortal Seven invitation letter dispatched, June 30, 1688", "William lands at Torbay, November 5, 1688", "John Churchill defects, November 24, 1688"] },
    { phase: "moderate-phase", label: "Flight and vacancy", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "James flees London, is briefly detained by fishermen at Faversham, and is deliberately allowed to escape rather than be made a martyr.", keyEvents: ["James II flees London, December 11, 1688", "James detained then released, escapes to France, December 23, 1688"] },
    { phase: "consolidation", label: "The Convention settlement", dateStart: "1689-02-13", tStart: 0.92, tEnd: 1.00, intensity: 45, reached: true, summary: "The Convention Parliament declares the throne vacant, crowns William and Mary jointly, and pairs the crown with a Bill of Rights ending the sovereign's claim to suspend law unilaterally.", keyEvents: ["Convention Parliament declares the throne vacant, February 1689", "William and Mary crowned jointly, February 13, 1689", "Bill of Rights enacted, December 1689"] }
  ],
  outcome: "consolidated-democracy",
  militaryDefection: "full",
  foreignIntervention: "direct-military",
  durationDays: 100,
  deathToll: "Fewer than a few dozen killed in scattered skirmishes; the campaign that toppled a king cost less blood than a single minor battle of the Civil War forty years earlier.",
  deathTollLow: 10,
  deathTollHigh: 50,
  regimeBefore: "monarchy",
  regimeAfter: "monarchy",
  democratizationDelta: 1,
  successFactors: [
    { factorKey: "nonviolent-success-rate", label: "Low-violence campaigns succeed more often than armed ones", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Nonviolent campaigns succeed roughly 53% of the time historically, versus about 26% for armed campaigns (Chenoweth and Stephan)", rationale: "The crown changed hands through mass desertion and elite realignment rather than battle, matching the pattern that low-violence transitions succeed more often.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "security-force-defection", label: "Security force defection is the strongest single predictor", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Movements that achieve security force defection succeed at markedly higher rates than those that do not, across the cross-national record", rationale: "Churchill's defection on November 24 triggered a collapse of James's officer corps within days; the king had no army left to give battle with.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "elite-fracture", label: "Elite fracture precedes regime collapse", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's structural account identifies a split within the ruling elite, not mass mobilization alone, as the precondition for rapid state collapse", rationale: "The Immortal Seven were peers and a bishop acting against their own king; the crisis was resolved inside the political class before it reached the street.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "William III", role: "Stadtholder of the Dutch Republic, later King of England", born: 1650, died: 1702 },
    { name: "Mary II", role: "Daughter of James II, joint monarch with William", born: 1662, died: 1694 },
    { name: "James II", role: "Deposed King of England, Scotland, and Ireland", born: 1633, died: 1701 },
    { name: "John Churchill", role: "Defecting general, later Duke of Marlborough", born: 1650, died: 1722 }
  ],
  legacyPoints: [
    "The 1689 Bill of Rights barred the crown from suspending laws or raising taxes without Parliament, language later cited directly by the American framers.",
    "It fixed the principle that Parliament could determine the succession, invoked again in the 1701 Act of Settlement.",
    "England avoided the prolonged civil war it had fought only forty years earlier, cementing 'bloodless' as the revolution's defining, if contested, brand.",
    "Whig historians spent two centuries treating 1688 as the template for orderly, elite-led constitutional change, a framing later scholarship complicated by pointing to William's very real invasion force."
  ],
  perspectives: [
    { id: "whig-constitutionalist", viewpoint: "Whig constitutionalist tradition", viewpointType: "moderate", regionOrigin: "England", narrative: "A king violated the ancient constitution and a united political nation corrected course without bloodshed, restoring rather than overturning England's fundamental law.", keyArguments: ["James II broke settled law by ruling through prerogative alone", "The Convention Parliament acted to restore, not invent, constitutional balance", "The near-absence of violence proves the nation's underlying consensus"], emphasized: ["the Bill of Rights", "the bloodless transfer of power"], omitted: ["the scale of William's invasion force", "the coercive pressure the landing placed on undecided elites"], notableQuotes: [{ text: "This nation is happily rescued from popery and slavery.", speaker: "Convention Parliament address to William, 1689", context: "Resolution accompanying the crown offer" }] },
    { id: "revisionist-invasion", viewpoint: "Revisionist reading as a foreign-backed coup", viewpointType: "academic", regionOrigin: "England", narrative: "William's fleet dwarfed the Spanish Armada a century earlier, and the outcome depended on a foreign prince's army, not domestic consensus; the label 'Glorious' was itself Whig branding applied after the fact.", keyArguments: ["William's force was larger and better organized than any domestic faction could field", "James's own miscalculations, not a spontaneous national uprising, opened the door", "the 'bloodless' framing understates the violence in Ireland and Scotland that followed within months"], emphasized: ["the military scale of the Dutch landing", "the Irish and Scottish aftermath"], omitted: ["the elite consensus that legitimized William's claim", "the durability of the constitutional settlement that followed"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "english-civil-war", targetTitle: "The English Civil War", type: "parallel", description: "Both crises pitted crown against Parliament over the same unresolved question of prerogative power, the first settled by war and regicide, the second by a negotiated succession forty years later." },
    { targetSlug: "american-revolution", targetTitle: "The American Revolution", type: "provided-model", description: "The 1689 Bill of Rights supplied language, no taxation without consent, no standing army without Parliament's consent, that reappears nearly verbatim in colonial grievances a century later." }
  ],
  media: [],
  relatedRevoltSlugs: ["english-civil-war", "american-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "english-civil-war",
  slug: "english-civil-war",
  title: "The English Civil War",
  subtitle: "Parliament tries a king for treason against his own kingdom",
  era: "atlantic",
  region: "europe",
  country: "England",
  revoltType: "political",
  status: "concluded",
  dateDisplay: "1642-1651",
  dateStart: 1642,
  dateEnd: 1651,
  summary: "Three linked wars between Charles I and Parliament ended in regicide, an eleven-year republic under Cromwell, and then a restoration in 1660 that put Charles's son back on the same throne the war had been fought to constrain.",
  significance: "The first time an English king was tried and publicly executed by his own subjects. The monarchy returned within a generation, but it returned changed: never again would a king rule for eleven years without Parliament.",
  grievances: [
    { kind: "Unilateral taxation without Parliament", intensity: 80, evidence: "Charles ruled for eleven years, 1629 to 1640, without summoning Parliament, funding his government through expedients like ship money extended to inland counties that had never paid it before." },
    { kind: "Religious imposition", intensity: 72, evidence: "Archbishop Laud's 1637 attempt to impose a new prayer book on Scotland triggered the Bishops' Wars, forcing Charles to recall Parliament to raise funds." },
    { kind: "Attempted arrest of sitting MPs", intensity: 85, evidence: "On January 4, 1642, Charles entered the House of Commons with armed men to arrest five members, finding they had already fled; the breach of parliamentary privilege made compromise nearly impossible." }
  ],
  actors: [
    { actorType: "old-regime", name: "Charles I", description: "King of England, Scotland, and Ireland since 1625.", roleInArc: "Raised his standard at Nottingham in August 1642, was defeated in two wars, tried, and executed in January 1649.", defected: false },
    { actorType: "vanguard", name: "Oliver Cromwell", description: "Member of Parliament turned cavalry commander, then Lord Protector.", roleInArc: "Built the New Model Army's disciplined cavalry, pushed the regicide through, and ruled as Protector from 1653 until his death in 1658.", defected: false },
    { actorType: "military-defectors", name: "The New Model Army", description: "Parliament's reorganized 1645 fighting force, recruited and promoted on merit rather than aristocratic rank.", roleInArc: "Won the war for Parliament, then turned on Parliament itself, purging it in 1648 to clear the way for the king's trial.", defected: false },
    { actorType: "counter-revolutionaries", name: "Levellers", description: "A radical faction within the army and London demanding wider suffrage and legal equality.", roleInArc: "Pushed the revolution further than its own leadership wanted; suppressed by Cromwell at Burford in 1649.", defected: false },
    { actorType: "old-regime", name: "Charles II", description: "Son of Charles I, exiled after his father's execution.", roleInArc: "Restored to the throne in 1660 after the Protectorate collapsed under his cousin Richard Cromwell.", defected: false }
  ],
  tactics: [
    { tacticType: "armed-insurgency", description: "Set-piece battles across three linked wars, Edgehill, Marston Moor, Naseby, decided the conflict on the battlefield rather than through negotiation.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "Parliament raised its own taxes, army, and administration in direct competition with the king's court, functioning as a rival government years before the war ended.", prominence: "primary" },
    { tacticType: "mass-demonstration", description: "London crowds and petitions, including the 1641 Root and Branch petition against bishops, pressured Parliament toward confrontation before fighting began.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  ateItsChildren: true,
  phases: [
    { phase: "old-regime-crisis", label: "Eleven years without Parliament", tStart: 0.00, tEnd: 0.12, intensity: 45, reached: true, summary: "Charles governs without Parliament from 1629, funding the crown through prerogative revenue until the Bishops' Wars force him to recall it in 1640.", keyEvents: ["Personal Rule begins, 1629", "Bishops' Wars begin, 1639", "Long Parliament summoned, November 1640"] },
    { phase: "the-spark", label: "The five members", dateStart: "1642-01-04", tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: "Charles's failed attempt to arrest five MPs in the Commons chamber destroys any remaining trust between crown and Parliament.", keyEvents: ["Charles attempts to arrest five MPs, January 4, 1642", "Charles raises his standard at Nottingham, August 22, 1642"] },
    { phase: "moderate-phase", label: "The first civil war", tStart: 0.34, tEnd: 0.48, intensity: 70, reached: true, summary: "Parliament fights to force concessions from the king rather than to remove him outright, forming the New Model Army to professionalize the effort.", keyEvents: ["Battle of Marston Moor, July 1644", "New Model Army formed, 1645", "Battle of Naseby, June 1645"] },
    { phase: "dual-power", label: "King in captivity, army in the streets", tStart: 0.48, tEnd: 0.60, intensity: 60, reached: true, summary: "Charles, defeated but still king, negotiates simultaneously with Parliament, the army, and the Scots, while the New Model Army grows radicalized and unpaid.", keyEvents: ["Charles surrenders to the Scots, 1646", "Charles handed to Parliament, 1647", "Second Civil War, 1648"] },
    { phase: "radical-phase", label: "Pride's Purge and the trial", dateStart: "1648-12-06", tStart: 0.60, tEnd: 0.72, intensity: 90, reached: true, summary: "Colonel Pride's soldiers physically bar MPs unwilling to try the king from entering Parliament, and the remaining Rump tries and executes Charles weeks later.", keyEvents: ["Pride's Purge, December 6, 1648", "Charles I tried, January 1649", "Charles I executed, January 30, 1649"] },
    { phase: "thermidor", label: "Protectorate to Restoration", tStart: 0.84, tEnd: 0.92, intensity: 55, reached: true, summary: "Cromwell's Commonwealth hardens into a personal Protectorate that looks increasingly like the monarchy it replaced, and collapses within two years of his death.", keyEvents: ["Cromwell becomes Lord Protector, 1653", "Cromwell dies, 1658", "Charles II restored, May 1660"] }
  ],
  outcome: "restored-old-regime",
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  durationDays: 3305,
  deathToll: "Estimated 200,000 dead across England, Scotland, and Ireland once disease and famine are counted, a higher proportional death toll than World War One inflicted on England alone.",
  deathTollLow: 190000,
  deathTollHigh: 250000,
  regimeBefore: "monarchy",
  regimeAfter: "monarchy",
  democratizationDelta: 0,
  successFactors: [
    { factorKey: "armed-campaign-base-rate", label: "Armed campaigns win at lower and less durable rates", framework: "chenoweth", status: "partial", direction: "indeterminate", baseRate: "Armed campaigns succeed in imposing lasting change in roughly 26% of historical cases, well under nonviolent campaigns' 53%", rationale: "Parliament's army won every battle that mattered, yet the republic it produced lasted barely a decade before the monarchy it fought to constrain returned largely intact.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "revolution-consumes-radicals", label: "Revolutionary coalitions purge their own radical wing", framework: "brinton", status: "confirmed", direction: "favors-regime", baseRate: "Crane Brinton's comparative model identifies a recurring terror-and-virtue phase in which a revolution turns on its own extremists before a Thermidorian reaction restores order", rationale: "Cromwell suppressed the Levellers at Burford in 1649, the same year he helped execute the king, and the Protectorate he then built drifted back toward one-man rule.", sources: ["Brinton, The Anatomy of Revolution (1938)"] },
    { factorKey: "elite-fracture", label: "Elite fracture opens the crisis, elite reunification closes it", framework: "skocpol", status: "confirmed", direction: "indeterminate", baseRate: "Skocpol's structural model treats a split ruling class as the trigger for state breakdown and its reunification as the marker of consolidation, in either direction", rationale: "The gentry and merchant class that split from the crown in 1642 was largely the same class that invited Charles II home in 1660, having concluded a republic without a king was less stable than a king with limits.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Charles I", role: "Executed King of England, Scotland, and Ireland", born: 1600, died: 1649 },
    { name: "Oliver Cromwell", role: "Parliamentary general, later Lord Protector", born: 1599, died: 1658 },
    { name: "Thomas Fairfax", role: "Commander in chief of the New Model Army", born: 1612, died: 1671 },
    { name: "Charles II", role: "Restored King of England, Scotland, and Ireland", born: 1630, died: 1685 }
  ],
  legacyPoints: [
    "Charles I's trial and execution established, for the first time in English history, that a king could be held legally accountable to his own subjects, a precedent the Restoration could not fully erase.",
    "The New Model Army's promotion-by-merit model influenced military organization well beyond England.",
    "The 1660 Restoration settlement quietly preserved Parliament's wartime gains, including control over taxation, leaving the argument 1688 would settle more permanently already half won.",
    "Republican and regicide arguments circulated by Leveller pamphleteers resurfaced over a century later in French and American revolutionary rhetoric."
  ],
  perspectives: [
    { id: "parliamentary-whig", viewpoint: "Parliamentary constitutionalist", viewpointType: "revolutionary", regionOrigin: "England", narrative: "Charles's claim to rule by divine right without Parliament's consent was itself the illegal act; the war and the trial enforced a law the king had already broken.", keyArguments: ["Eleven years of taxation without consent violated ancient parliamentary privilege", "The king's attempted arrest of MPs in their own chamber was the true rupture", "Trying the king held the crown accountable to law for the first time"], emphasized: ["ship money and prerogative taxation", "the five members"], omitted: ["the scale of civilian death from disease and requisition", "Leveller demands the Parliamentary leadership itself suppressed"], notableQuotes: [{ text: "I am a martyr of the people.", speaker: "Charles I", context: "Reported final words on the scaffold, January 30, 1649" }] },
    { id: "royalist-traditionalist", viewpoint: "Royalist and later Restoration apologist", viewpointType: "counter-revolutionary", regionOrigin: "England", narrative: "The war destroyed a functioning constitutional balance and replaced it with a decade of military rule under Cromwell no more accountable than the king it deposed, vindicating the 1660 return to monarchy.", keyArguments: ["Regicide was an unprecedented and unlawful act regardless of Charles's failings", "The Protectorate's rule by major-generals was itself a military dictatorship", "Popular relief at the Restoration shows the republic had lost its own legitimacy"], emphasized: ["the disorder and taxation of the Protectorate years", "the popular welcome given Charles II in 1660"], omitted: ["Charles I's own record of ruling without Parliament for eleven years", "the durable gains Parliament kept even after 1660"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "glorious-revolution-1688", targetTitle: "The Glorious Revolution", type: "provided-model", description: "The unresolved argument over prerogative power that started the civil war was finally settled, this time without a war, by the Bill of Rights forty years later." },
    { targetSlug: "french-revolution", targetTitle: "The French Revolution", type: "parallel", description: "Both revolutions moved from limiting a monarch to trying and executing him, then cycled through a radical phase before a reaction restored a more conservative order." }
  ],
  media: [],
  relatedRevoltSlugs: ["glorious-revolution-1688", "french-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "springtime-of-nations-1848",
  slug: "springtime-of-nations-1848",
  title: "The Springtime of Nations",
  subtitle: "A continent rises in a single season and is put down within a year",
  era: "springtime",
  region: "europe",
  country: "France, the German and Italian states, and the Austrian Empire",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "1848-1849",
  dateStart: 1848,
  dateEnd: 1849,
  summary: "Bread riots in Paris toppled a king in three days in February 1848, and within weeks Berlin, Vienna, Milan, and Budapest had their own barricades. Liberal parliaments met, constitutions were promised, and by the summer of 1849 nearly every gain had been reversed by force, often with foreign troops doing the reversing.",
  significance: "The first genuinely continental revolutionary wave, spreading from capital to capital by newspaper and rail faster than any government could contain it, and the clearest historical case of a revolution succeeding everywhere at first and surviving almost nowhere.",
  grievances: [
    { kind: "Economic crisis and food prices", intensity: 78, evidence: "The 1845-46 potato blight and a poor 1846-47 grain harvest doubled bread prices across much of Europe, driving urban unemployment before a single barricade went up." },
    { kind: "Absence of constitutional representation", intensity: 82, evidence: "Louis Philippe's France, the Austrian Empire, and most German states in 1848 had no elected national parliament with real budgetary power over the monarch." },
    { kind: "Suppressed national aspiration", intensity: 74, evidence: "Germans, Italians, Hungarians, and Czechs each lived divided across multiple dynastic states or under Habsburg rule with no unified national government of their own." }
  ],
  actors: [
    { actorType: "students-youth", name: "Parisian and Berlin students", description: "University students who organized early banquets and demonstrations before the crowds turned into workers and shopkeepers.", roleInArc: "Provided the first street confrontations that forced Louis Philippe's abdication and the Prussian king's initial concessions.", defected: false },
    { actorType: "organized-labor", name: "Parisian workers", description: "Skilled and unskilled laborers hit hardest by the 1846-47 economic downturn.", roleInArc: "Drove the June Days uprising in Paris after the new republic closed the National Workshops jobs program, and were crushed by the army in four days of street fighting.", defected: false },
    { actorType: "old-regime", name: "Klemens von Metternich", description: "Austrian chancellor and chief architect of the post-1815 conservative order.", roleInArc: "Fled Vienna in disguise on March 13, 1848, ending 38 years running the continental system built to prevent exactly this kind of upheaval.", defected: false },
    { actorType: "vanguard", name: "The Frankfurt Parliament", description: "An elected all-German assembly that met in 1848 to draft a liberal constitution for a unified Germany.", roleInArc: "Debated for a year, offered the imperial crown to the Prussian king in 1849, and was refused and then dispersed by troops.", defected: false },
    { actorType: "military-defectors", name: "Piedmont-Sardinia's army", description: "The one Italian state whose king backed the 1848 revolts with force against Austria.", roleInArc: "Declared war on Austria to support Milan's uprising, was defeated at Custoza in July 1848 and again at Novara in March 1849.", defected: false }
  ],
  tactics: [
    { tacticType: "mass-demonstration", description: "The February 1848 Paris banquet campaign and street crowds forced Louis Philippe's abdication within three days.", prominence: "primary" },
    { tacticType: "urban-uprising", description: "Barricade fighting in Berlin, Vienna, and Milan in March 1848 forced immediate concessions from monarchs unwilling to risk prolonged street war.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "The Frankfurt Parliament assembled as a rival national authority to the German princes, though it never controlled an army of its own.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "Famine and stagnation", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "Potato blight and grain shortfalls compound years of political stagnation across the German and Italian states and the Austrian Empire.", keyEvents: ["Potato blight reaches continental Europe, 1845", "Poor grain harvest, 1846-47"] },
    { phase: "the-spark", label: "Paris falls in three days", dateStart: "1848-02-22", tStart: 0.22, tEnd: 0.34, intensity: 85, reached: true, summary: "A banned reform banquet triggers street fighting in Paris; Louis Philippe abdicates within three days and the news reaches Vienna and Berlin within weeks.", keyEvents: ["February Revolution begins in Paris, February 22, 1848", "Louis Philippe abdicates, February 24, 1848", "Metternich flees Vienna, March 13, 1848"] },
    { phase: "moderate-phase", label: "Constitutions promised", tStart: 0.34, tEnd: 0.48, intensity: 65, reached: true, summary: "Frightened monarchs across the German states grant liberal constitutions and the Frankfurt Parliament convenes to draft a unified German charter.", keyEvents: ["Frankfurt Parliament convenes, May 1848", "Austrian Emperor Ferdinand grants a constitution, April 1848"] },
    { phase: "dual-power", label: "Parliaments without armies", tStart: 0.48, tEnd: 0.60, intensity: 55, reached: true, summary: "Elected liberal assemblies claim national authority while the old monarchies quietly retain command of the armies that will eventually be turned against them.", keyEvents: ["Piedmont declares war on Austria, March 1848", "Prague uprising suppressed by Windischgratz, June 1848"] },
    { phase: "radical-phase", label: "June Days", dateStart: "1848-06-23", tStart: 0.60, tEnd: 0.72, intensity: 80, reached: true, summary: "Paris workers, radicalized by the closure of the National Workshops jobs program, rise against the new republic itself and are crushed by General Cavaignac's army.", keyEvents: ["National Workshops closed, June 21, 1848", "June Days uprising crushed, June 23-26, 1848"] },
    { phase: "thermidor", label: "The reaction", tStart: 0.84, tEnd: 0.92, intensity: 60, reached: true, summary: "Austrian and allied forces retake Vienna, Prague, Milan, and finally Hungary, the last holdout, with direct Russian military intervention in 1849.", keyEvents: ["Vienna retaken by imperial troops, October 1848", "Battle of Novara, March 1849", "Russian intervention crushes Hungary, August 1849"] }
  ],
  outcome: "failed-suppressed",
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  peakParticipationPct: null,
  peakParticipationDisplay: "Tens of thousands in the street crowds of Paris, Berlin, and Vienna at peak in March 1848, though no reliable continental total exists",
  crossedParticipationThreshold: null,
  durationDays: 540,
  deathToll: "Several thousand killed across the combined uprisings and their suppression, with Hungary's 1849 defeat alone costing an estimated 50,000 lives in the fighting and reprisals that followed.",
  deathTollLow: 10000,
  deathTollHigh: 60000,
  regimeBefore: "monarchy",
  regimeAfter: "monarchy",
  democratizationDelta: -1,
  successFactors: [
    { factorKey: "no-security-defection", label: "Without security force defection, street victories do not hold", framework: "chenoweth", status: "contradicted", direction: "favors-regime", baseRate: "Movements that fail to secure defection from the army or police see their initial gains reversed at far higher rates than those that do", rationale: "Austrian, Prussian, and Russian armies stayed loyal to their monarchs throughout; every liberal parliament that lacked its own army was eventually dispersed by one that had never changed sides.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-counter-intervention", label: "Foreign intervention against a movement reverses its gains", framework: "chenoweth", status: "confirmed", direction: "favors-regime", baseRate: "Direct foreign military intervention on behalf of an incumbent regime correlates with reversal of an otherwise successful uprising", rationale: "Russia's 1849 invasion crushed the Hungarian revolution after it had defeated Austria's own forces in the field, a case study in how a neighboring power's army can undo a domestic victory.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] },
    { factorKey: "elite-fracture-absent", label: "Without elite fracture, monarchies can wait out a revolutionary wave", framework: "skocpol", status: "confirmed", direction: "favors-regime", baseRate: "Skocpol's model finds regime survival likely where the aristocracy, officer corps, and monarchy remain aligned even under mass pressure", rationale: "Unlike 1688 or 1789, the officer corps of Austria, Prussia, and Russia never split from their monarchs, giving each regime a coercive instrument the revolutions never captured.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Louis Philippe", role: "Deposed King of the French" },
    { name: "Klemens von Metternich", role: "Austrian chancellor, fled Vienna March 1848", born: 1773, died: 1859 },
    { name: "Lajos Kossuth", role: "Leader of the Hungarian revolutionary government", born: 1802, died: 1894 },
    { name: "Giuseppe Mazzini", role: "Italian nationalist, head of the short-lived Roman Republic", born: 1805, died: 1872 }
  ],
  legacyPoints: [
    "Nearly every constitutional gain of 1848 was formally revoked within eighteen months, yet the ideas of national unification and constitutional rule did not disappear with the barricades.",
    "Karl Marx and Friedrich Engels published the Communist Manifesto in February 1848, days before the Paris uprising, linking the revolutions permanently to socialist thought.",
    "German and Italian unification came within a generation, but under conservative architects, Bismarck and Cavour, rather than the liberal parliaments of 1848.",
    "A generation of failed 1848 revolutionaries emigrated to Britain and the United States, carrying constitutional and nationalist ideas into new political movements abroad."
  ],
  perspectives: [
    { id: "liberal-nationalist", viewpoint: "Liberal nationalist retrospective", viewpointType: "revolutionary", regionOrigin: "central Europe", narrative: "1848 was the moment Europe's peoples first tried to govern themselves by written constitution and national self-determination rather than dynastic inheritance, and its defeat only delayed rather than disproved the idea.", keyArguments: ["The Frankfurt Parliament's draft constitution anticipated rights later written into German and Austrian law", "National unification eventually happened, proving the underlying demand was real", "Popular participation across dozens of cities in a single year had no earlier precedent in Europe"], emphasized: ["the speed and breadth of the 1848 uprisings", "the constitutional texts the parliaments produced"], omitted: ["the June Days massacre of Parisian workers by the same republic the revolution created", "the movement's failure to secure any army of its own"], notableQuotes: [] },
    { id: "conservative-monarchist", viewpoint: "Conservative monarchist view", viewpointType: "counter-revolutionary", regionOrigin: "Austria", narrative: "The uprisings were a dangerous but ultimately manageable disorder; restraint and, where necessary, allied military force restored the legitimate order that alone could guarantee stability across such a diverse empire.", keyArguments: ["The Habsburg monarchy held together despite simultaneous revolts in Vienna, Prague, Milan, and Budapest", "Russian intervention in Hungary prevented a wider collapse of the European balance", "Constitutions granted under street pressure lacked lasting legitimacy and were reasonably withdrawn once order returned"], emphasized: ["the empire's survival", "the restoration of order by 1849"], omitted: ["the scale of the death toll in Hungary's suppression", "the economic grievances that triggered the uprisings in the first place"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "french-revolution", targetTitle: "The French Revolution", type: "inspired", description: "1848's Parisian rising consciously invoked 1789's language and symbols, even naming its new government the Second Republic." },
    { targetSlug: "arab-spring", targetTitle: "The Arab Spring", type: "parallel", description: "Both were continent-scale contagion waves that toppled or shook multiple regimes within months, and both saw most individual uprisings reversed rather than consolidated into lasting democracies." }
  ],
  media: [],
  relatedRevoltSlugs: ["french-revolution", "arab-spring"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "meiji-restoration",
  slug: "meiji-restoration",
  title: "The Meiji Restoration",
  subtitle: "Provincial samurai overthrow a shogunate to modernize it out of existence",
  era: "modern-nationalist",
  region: "east-asia",
  country: "Japan",
  revoltType: "coup-from-above",
  status: "concluded",
  dateDisplay: "1868-1869",
  dateStart: 1868,
  dateEnd: 1869,
  summary: "Commodore Perry's 1853 warships exposed the Tokugawa shogunate's weakness against foreign power. Fifteen years later, samurai from the Satsuma and Choshu domains forced the last shogun to resign, fought the Boshin War against his loyalists, and installed the teenage Emperor Meiji as the figurehead of a rapid, top-down industrial transformation.",
  significance: "One of the few revolutions where the challengers explicitly organized around restoring an ancient monarch, then used that restored authority to abolish the very feudal class, the samurai, that had carried out the restoration.",
  grievances: [
    { kind: "Humiliation by foreign powers", intensity: 85, evidence: "Commodore Perry's 1853 fleet forced the shogunate to sign unequal treaties opening Japanese ports and surrendering tariff control, treaties Japan could not renegotiate for decades." },
    { kind: "Samurai economic decline", intensity: 65, evidence: "Rice-stipend samurai incomes had stagnated for generations under Tokugawa rule while merchant wealth grew, leaving lower-ranking samurai in the Satsuma and Choshu domains with status but shrinking income." },
    { kind: "Domain exclusion from national power", intensity: 60, evidence: "The Satsuma and Choshu domains, among Japan's largest, had been excluded from senior shogunate posts since their defeat at the 1600 Battle of Sekigahara." },
    { kind: "Repeated foreign bombardment", intensity: 55, evidence: "British warships shelled Kagoshima in 1863 and an allied Western fleet bombarded Shimonoseki in 1864, demonstrating the shogunate could not protect its own domains from foreign navies." }
  ],
  actors: [
    { actorType: "vanguard", name: "Satsuma-Choshu alliance", description: "A secret 1866 pact between two rival domains united against the shogunate.", roleInArc: "Provided the troops, funding, and political strategy behind the restoration and the Boshin War that followed.", defected: false },
    { actorType: "old-regime", name: "Tokugawa Yoshinobu", description: "The fifteenth and last Tokugawa shogun.", roleInArc: "Resigned civil authority to the emperor in November 1867, then fought and lost the Boshin War before formally submitting in 1869.", defected: false },
    { actorType: "military-defectors", name: "Domain lords who switched allegiance", description: "Regional daimyo who abandoned the shogunate once its military weakness became clear.", roleInArc: "Their defections after the shogunate's 1868 defeat at Toba-Fushimi accelerated the Boshin War's rapid conclusion.", defected: true },
    { actorType: "foreign-backer", name: "British and French arms traders", description: "European powers who sold modern rifles and warships to both the pro-restoration and shogunate sides.", roleInArc: "British merchants favored the Satsuma-Choshu alliance while France backed the shogunate, indirectly shaping the war's military balance.", defected: false },
    { actorType: "vanguard", name: "Emperor Meiji", description: "Enthroned in 1867 at age fourteen.", roleInArc: "Served as the symbolic center of authority the restoration invoked, then as the figurehead of the modernization program carried out largely by his former samurai backers.", defected: false }
  ],
  tactics: [
    { tacticType: "armed-insurgency", description: "The Boshin War's set-piece battles, Toba-Fushimi and the fall of Edo, decided the shogunate's fate within eighteen months.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "The Satsuma-Choshu alliance built a shadow imperial court and military command structure around the young emperor before openly challenging the shogunate.", prominence: "primary" },
    { tacticType: "defection-fraternization", description: "Domain after domain abandoned the shogunate once Toba-Fushimi showed which side could win, sparing much of Japan a prolonged war.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "The unequal treaties", tStart: 0.00, tEnd: 0.12, intensity: 50, reached: true, summary: "Perry's 1853 fleet and the treaties that followed expose the shogunate's inability to defend Japanese sovereignty, discrediting it in the eyes of ambitious domains.", keyEvents: ["Perry's fleet arrives, 1853", "Unequal treaties signed, 1858", "Bombardment of Kagoshima, 1863"] },
    { phase: "the-spark", label: "The shogun resigns", dateStart: "1867-11-09", tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: "Tokugawa Yoshinobu resigns civil authority to the emperor in an attempt to preserve influence within a new order, a bid the Satsuma-Choshu alliance moves to preempt.", keyEvents: ["Satsuma-Choshu secret alliance formed, 1866", "Yoshinobu resigns to the emperor, November 9, 1867"] },
    { phase: "radical-phase", label: "The Boshin War", dateStart: "1868-01-27", tStart: 0.60, tEnd: 0.72, intensity: 88, reached: true, summary: "Pro-restoration forces defeat shogunate loyalists at Toba-Fushimi, triggering a cascade of domain defections and the fall of Edo without a prolonged siege.", keyEvents: ["Battle of Toba-Fushimi, January 27, 1868", "Edo surrenders without major battle, May 1868"] },
    { phase: "consolidation", label: "Restoration proclaimed", dateStart: "1869-06-27", tStart: 0.92, tEnd: 1.00, intensity: 55, reached: true, summary: "The last shogunate holdouts surrender at Hakodate in June 1869, and the new imperial government begins dismantling the feudal domain system that had just carried it to power.", keyEvents: ["Battle of Hakodate ends resistance, June 1869", "Charter Oath sets reform direction, 1868"] }
  ],
  outcome: "consolidated-autocracy",
  militaryDefection: "partial",
  foreignIntervention: "material",
  durationDays: 500,
  deathToll: "An estimated 8,000 to 10,000 killed in the Boshin War, a fraction of the toll from contemporaneous revolutions elsewhere, reflecting the speed of domain defections once the shogunate's weakness was proven.",
  deathTollLow: 8000,
  deathTollHigh: 12000,
  regimeBefore: "military",
  regimeAfter: "monarchy",
  democratizationDelta: -1,
  successFactors: [
    { factorKey: "elite-fracture", label: "Elite fracture between rival power centers, not mass mobilization, drove the outcome", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's model applies most cleanly to elite-driven cases like this one: a split between the shogunate and excluded regional elites, not a popular uprising, produced the state collapse", rationale: "The restoration was organized by samurai from two domains, not by peasants or urban crowds; ordinary Japanese participation in the actual fighting was minimal.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "participation-threshold-inapplicable", label: "The 3.5 percent mass-participation rule does not apply to elite coups", framework: "chenoweth", status: "atypical", direction: "indeterminate", baseRate: "Chenoweth's participation threshold research concerns mass civil resistance campaigns and offers no predictive claim about narrowly elite-led restorations", rationale: "The Meiji Restoration succeeded with a coalition of a few domains' samurai forces rather than broad popular mobilization, a structurally different mechanism than the mass movements the 3.5 percent finding describes.", sources: ["Chenoweth, Civil Resistance: What Everyone Needs to Know (2021)"] },
    { factorKey: "foreign-material-limited", label: "Indirect foreign arms sales shaped, but did not decide, the military balance", framework: "goldstone", status: "partial", direction: "favors-movement", baseRate: "Goldstone's comparative work finds foreign material support a secondary factor next to domestic elite alignment in determining a challenger's success", rationale: "British arms sales to Satsuma and Choshu improved their forces, but domain defections after Toba-Fushimi, not superior weaponry, decided the war's outcome.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Emperor Meiji", role: "Restored emperor, figurehead of the modernization program", born: 1852, died: 1912 },
    { name: "Saigo Takamori", role: "Satsuma military leader of the restoration, later led the 1877 Satsuma Rebellion against it", born: 1828, died: 1877 },
    { name: "Tokugawa Yoshinobu", role: "Last Tokugawa shogun", born: 1837, died: 1913 },
    { name: "Okubo Toshimichi", role: "Chief architect of the new Meiji government's centralizing reforms", born: 1830, died: 1878 }
  ],
  legacyPoints: [
    "The new government abolished the samurai class and the feudal domain system within a few years of the restoration that samurai themselves had carried out.",
    "Japan industrialized fast enough to defeat Qing China in 1895 and Russia in 1905, within two generations of Perry's warships.",
    "The 1889 Meiji Constitution established a parliament, though one that left the emperor and military largely outside civilian control.",
    "The centralized, militarized state the restoration built later drove Japan's expansionism through the 1930s and into the Second World War."
  ],
  perspectives: [
    { id: "restoration-nationalist", viewpoint: "Meiji nationalist and modernizer view", viewpointType: "revolutionary", regionOrigin: "Japan", narrative: "The restoration was a necessary act of national survival: without rapid centralization and industrial catch-up, Japan risked colonization like much of the rest of Asia.", keyArguments: ["Unequal treaties proved the shogunate could not defend Japanese sovereignty", "Rapid modernization required a unified national government the domain system could not provide", "Within a single generation Japan avoided the colonization that befell its neighbors"], emphasized: ["the speed of industrial and military modernization", "the treaty humiliations that preceded the restoration"], omitted: ["the loss of status and livelihood imposed on lower-ranking samurai", "the militarist trajectory the centralized state later took"], notableQuotes: [] },
    { id: "samurai-traditionalist", viewpoint: "Displaced samurai retrospective", viewpointType: "counter-revolutionary", regionOrigin: "Japan", narrative: "Many of the very samurai who fought for the restoration found their class abolished within a decade, a betrayal significant enough to trigger armed rebellion against the government they had helped install.", keyArguments: ["Saigo Takamori, a restoration hero, led the 1877 Satsuma Rebellion against the government he helped create", "Stipend abolition and conscription reform stripped samurai of both income and social function", "The restoration's rhetoric of honoring the emperor obscured how thoroughly it dismantled the old order"], emphasized: ["the 1877 Satsuma Rebellion", "stipend and status losses among lower samurai"], omitted: ["the economic stagnation samurai already faced before the restoration", "the industrial gains that followed for the wider population"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "chinese-revolution-1949", targetTitle: "The Chinese Revolution", type: "counter-example", description: "Japan's elite-led, top-down transformation avoided the prolonged mass civil war China endured eight decades later to reach a comparably centralized state." },
    { targetSlug: "french-revolution", targetTitle: "The French Revolution", type: "parallel", description: "Both revolutions dismantled a feudal privileged class, the French nobility, the Japanese samurai, in the name of a more centralized national state." }
  ],
  media: [],
  relatedRevoltSlugs: ["chinese-revolution-1949", "french-revolution"],
  relatedHistorySlugs: ["meiji-restoration"],
  published: true
},
{
  id: "mexican-revolution",
  slug: "mexican-revolution",
  title: "The Mexican Revolution",
  subtitle: "Ten years of war leave a constitution, a ruling party, and a million dead",
  era: "modern-nationalist",
  region: "americas",
  country: "Mexico",
  revoltType: "social",
  status: "concluded",
  dateDisplay: "1910-1920",
  dateStart: 1910,
  dateEnd: 1920,
  summary: "Porfirio Diaz's rigged 1910 re-election set off a decade of shifting armed coalitions, Madero's liberal reformers, Zapata's landless peasants, Villa's northern cavalry, Carranza's constitutionalists, that toppled Diaz, then fought each other for control of what came after him.",
  significance: "Produced Latin America's first great social revolution of the twentieth century and a constitution, 1917, whose land reform and labor provisions still shape Mexican law, even as the revolutionary coalition's own factions spent years killing each other over what the revolution meant.",
  grievances: [
    { kind: "Land concentration under the Porfiriato", intensity: 90, evidence: "By 1910, roughly 90 percent of Mexico's rural population owned no land at all, while haciendas belonging to a small elite controlled the majority of arable territory." },
    { kind: "Fraudulent 1910 re-election", intensity: 75, evidence: "Porfirio Diaz jailed his opposition candidate Francisco Madero before the 1910 election and declared himself the winner for an eighth term after 34 years in power." },
    { kind: "Foreign ownership of Mexican industry", intensity: 60, evidence: "American and British companies controlled the majority of Mexico's oil production and much of its mining by 1910, with profits flowing largely out of the country." }
  ],
  actors: [
    { actorType: "vanguard", name: "Francisco Madero", description: "Wealthy landowner turned liberal reformer, jailed then exiled by Diaz before the 1910 election.", roleInArc: "Issued the Plan of San Luis Potosi calling for revolt, became president in 1911, and was overthrown and killed in Huerta's 1913 coup.", defected: false },
    { actorType: "masses", name: "Emiliano Zapata", description: "Leader of the Ejercito Libertador del Sur, the peasant army of Morelos state.", roleInArc: "Fought for land redistribution under the slogan Tierra y Libertad through every shift in national leadership, and was assassinated by Carranza's forces in 1919.", defected: false },
    { actorType: "military-defectors", name: "Pancho Villa", description: "Former bandit turned commander of the Division del Norte cavalry.", roleInArc: "Won major battles against Huerta and later against Carranza, then was marginalized after his coalition's defeat at Celaya in 1915.", defected: false },
    { actorType: "old-regime", name: "Porfirio Diaz", description: "President of Mexico for 34 of the previous 35 years.", roleInArc: "Resigned and went into exile in France in May 1911 after Madero's forces took Ciudad Juarez.", defected: false },
    { actorType: "counter-revolutionaries", name: "Victoriano Huerta", description: "General who led the coup against Madero.", roleInArc: "Seized the presidency in February 1913 after Madero's assassination, and was driven from power by the Constitutionalist coalition in 1914.", defected: false }
  ],
  tactics: [
    { tacticType: "armed-insurgency", description: "Successive campaigns, Ciudad Juarez, Torreon, Celaya, moved the front lines across most of Mexico's territory over ten years.", prominence: "primary" },
    { tacticType: "guerrilla-warfare", description: "Zapata's Ejercito Libertador fought a sustained irregular campaign in Morelos, retreating to the hills whenever a national government's army advanced.", prominence: "primary" },
    { tacticType: "sabotage", description: "Villa's forces repeatedly cut rail lines to isolate federal garrisons and disrupt troop movements across the north.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "The Porfiriato's stagnation", tStart: 0.00, tEnd: 0.12, intensity: 45, reached: true, summary: "Three decades of Diaz rule concentrate land and political power while leaving most Mexicans landless and unrepresented.", keyEvents: ["Diaz jails Madero before the 1910 election", "Diaz declared winner of an eighth term, 1910"] },
    { phase: "the-spark", label: "The Plan of San Luis Potosi", dateStart: "1910-11-20", tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: "Madero calls for armed revolt from exile in Texas, and fighting spreads across northern Mexico within weeks.", keyEvents: ["Plan of San Luis Potosi issued, October 1910", "Armed revolt begins, November 20, 1910"] },
    { phase: "moderate-phase", label: "Madero's presidency", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "Diaz resigns and Madero takes office promising gradual reform, disappointing Zapata's peasant base, which resumes fighting almost immediately.", keyEvents: ["Diaz resigns, May 1911", "Madero inaugurated, November 1911", "Zapata's Plan of Ayala rejects Madero, November 1911"] },
    { phase: "radical-phase", label: "Huerta's coup and the Constitutionalist war", dateStart: "1913-02-22", tStart: 0.60, tEnd: 0.72, intensity: 85, reached: true, summary: "Huerta's coup and Madero's assassination unite Villa, Zapata, and Carranza in a war against the new dictatorship, which collapses within eighteen months.", keyEvents: ["Madero assassinated, February 22, 1913", "Huerta driven from power, July 1914"] },
    { phase: "terror-virtue", label: "War among the winners", tStart: 0.72, tEnd: 0.84, intensity: 80, reached: true, summary: "The victorious revolutionary coalition splits; Villa and Zapata fight Carranza's constitutionalists in a war as bloody as the one against Huerta.", keyEvents: ["Convention of Aguascalientes fails to unify factions, October 1914", "Villa defeated at Celaya, April 1915"] },
    { phase: "thermidor", label: "Carranza consolidates", tStart: 0.84, tEnd: 0.92, intensity: 60, reached: true, summary: "Carranza secures national power and moves against his former allies, having Zapata ambushed and killed in 1919.", keyEvents: ["Zapata assassinated, April 10, 1919", "Carranza's government recognized internationally, 1915-1917"] },
    { phase: "consolidation", label: "The 1917 Constitution", dateStart: "1917-02-05", tStart: 0.92, tEnd: 1.00, intensity: 50, reached: true, summary: "Mexico ratifies a new constitution enshrining land reform and labor rights, and Alvaro Obregon's 1920 accession ends the decade of open civil war.", keyEvents: ["1917 Constitution ratified, February 5, 1917", "Obregon becomes president, 1920"] }
  ],
  outcome: "consolidated-autocracy",
  militaryDefection: "partial",
  foreignIntervention: "material",
  durationDays: 3650,
  deathToll: "Estimated at close to one million dead across the decade of fighting, disease, and displacement, roughly one in fifteen of Mexico's 1910 population.",
  deathTollLow: 900000,
  deathTollHigh: 1000000,
  regimeBefore: "personalist",
  regimeAfter: "one-party",
  democratizationDelta: 1,
  successFactors: [
    { factorKey: "armed-duration-cost", label: "Prolonged armed campaigns are costlier and less predictable than short ones", framework: "chenoweth", status: "confirmed", direction: "indeterminate", baseRate: "Armed campaigns succeed in roughly 26% of historical cases and tend to produce more durable authoritarian aftermaths than nonviolent transitions when they do succeed", rationale: "A full decade of shifting armed coalitions eventually toppled Diaz and Huerta, but produced a one-party state, the PRI's predecessor coalitions, rather than the pluralist democracy Madero had originally sought.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "coalition-fracture", label: "Revolutionary coalitions that win together often fracture immediately after victory", framework: "skocpol", status: "confirmed", direction: "favors-regime", baseRate: "Skocpol's comparative cases find post-victory elite fracture among a revolution's own factions a common cause of prolonged instability", rationale: "Villa, Zapata, and Carranza fought together against Huerta in 1914, then fought each other for the next three years, with Carranza's faction eventually prevailing.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "agrarian-mobilization", label: "Peasant-army mobilization can outlast urban elite coalitions", framework: "goldstone", status: "confirmed", direction: "favors-movement", baseRate: "Goldstone's comparative work identifies sustained agrarian mobilization as a structural advantage over narrowly elite-led movements in protracted conflicts", rationale: "Zapata's peasant base in Morelos kept fighting through every change of national government from 1911 until his 1919 assassination, outlasting three separate national administrations.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Francisco Madero", role: "Reformist president, 1911-1913", born: 1873, died: 1913 },
    { name: "Emiliano Zapata", role: "Leader of the peasant Ejercito Libertador del Sur", born: 1879, died: 1919 },
    { name: "Pancho Villa", role: "Commander of the Division del Norte", born: 1878, died: 1923 },
    { name: "Venustiano Carranza", role: "Constitutionalist leader, president 1917-1920", born: 1859, died: 1920 }
  ],
  legacyPoints: [
    "The 1917 Constitution's Article 27 authorized land redistribution and Article 123 guaranteed labor rights, both still cited in Mexican legal and political debate today.",
    "The revolutionary coalition's surviving generals founded the party that would rule Mexico continuously for 71 years, later renamed the PRI.",
    "Zapata's slogan Tierra y Libertad became a rallying cry for agrarian movements far beyond Mexico's borders.",
    "The decade of war and its near million deaths reshaped Mexico's population distribution and drove significant emigration to the United States."
  ],
  perspectives: [
    { id: "zapatista-agrarian", viewpoint: "Zapatista agrarian view", viewpointType: "movement", regionOrigin: "Morelos, Mexico", narrative: "The revolution's true promise was land for the people who worked it; every national government from Madero to Carranza betrayed that promise in turn, and Zapata's assassination confirmed the betrayal was deliberate.", keyArguments: ["The Plan of Ayala explicitly demanded land redistribution Madero refused to deliver", "Carranza's forces hunted and killed Zapata rather than negotiate land reform", "Genuine land reform waited until Cardenas's presidency in the 1930s, over a decade after the fighting ended"], emphasized: ["the Plan de Ayala", "Zapata's assassination"], omitted: ["the administrative difficulty of redistributing land nationally during ongoing civil war", "gains urban labor secured under the 1917 Constitution"], notableQuotes: [{ text: "It is better to die on your feet than to live on your knees.", speaker: "Emiliano Zapata", context: "Widely attributed statement of the Zapatista movement's stance" }] },
    { id: "institutional-constitutionalist", viewpoint: "Constitutionalist institution-building view", viewpointType: "moderate", regionOrigin: "Mexico City", narrative: "Ending a decade of factional war required a single dominant coalition capable of writing and enforcing a national constitution, even at the cost of marginalizing rival revolutionary leaders like Villa and Zapata.", keyArguments: ["The 1917 Constitution's reforms could not be implemented while rival armies still contested the countryside", "Carranza's consolidation, however costly, ended open civil war faster than a continued three-way conflict would have", "The resulting one-party system provided decades of political stability after ten years of war"], emphasized: ["the 1917 Constitution's durability", "the end of open civil war by 1920"], omitted: ["the human cost of suppressing Villa's and Zapata's factions", "the decades of one-party rule the consolidation entrenched"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "cuban-revolution", targetTitle: "The Cuban Revolution", type: "parallel", description: "Both revolutions were fought substantially over land concentration and produced sweeping agrarian reform once the fighting ended." },
    { targetSlug: "chinese-revolution-1949", targetTitle: "The Chinese Revolution", type: "parallel", description: "Both mobilized a landless peasant base as a decisive military and political force against an urban-elite-backed government." }
  ],
  media: [],
  relatedRevoltSlugs: ["cuban-revolution", "chinese-revolution-1949"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "chinese-revolution-1949",
  slug: "chinese-revolution-1949",
  title: "The Chinese Communist Revolution",
  subtitle: "Twenty-two years of civil war end with a proclamation in Tiananmen Square",
  era: "anticolonial",
  region: "east-asia",
  country: "China",
  revoltType: "communist",
  status: "concluded",
  dateDisplay: "1927-1949",
  dateStart: 1927,
  dateEnd: 1949,
  summary: "Chiang Kai-shek's 1927 purge of his communist allies in Shanghai forced the Chinese Communist Party into rural exile, where it built peasant support through land reform and outlasted both a Nationalist encirclement and a Japanese occupation before defeating the Kuomintang in a final four-year civil war.",
  significance: "The largest communist revolution to succeed anywhere, founding the world's most populous state under one-party rule and permanently dividing China from the Nationalist government that fled to Taiwan.",
  grievances: [
    { kind: "Landlord exploitation of tenant farmers", intensity: 80, evidence: "Tenant farmers across much of China paid rents as high as 50 percent of their harvest to landlords, leaving many families without enough grain to survive a poor season." },
    { kind: "Kuomintang corruption and warlordism", intensity: 65, evidence: "The 1927 Shanghai massacre killed thousands of communists and allied labor organizers as Chiang Kai-shek consolidated Nationalist power through allied warlord militias." },
    { kind: "Japanese occupation devastation", intensity: 75, evidence: "Japan's occupation from 1931 to 1945 killed an estimated 15 to 20 million Chinese and devastated the industrial base the Kuomintang depended on for its army." },
    { kind: "Hyperinflation collapse", intensity: 70, evidence: "Kuomintang currency lost most of its value between 1947 and 1949, wiping out urban middle-class savings and eroding support for Chiang's government in its final years." }
  ],
  actors: [
    { actorType: "vanguard", name: "Mao Zedong", description: "Chairman of the Chinese Communist Party from the 1930s.", roleInArc: "Led the Long March retreat in 1934-35, built the Yan'an base area, and proclaimed the People's Republic of China on October 1, 1949.", defected: false },
    { actorType: "masses", name: "The Red Army and peasant base", description: "Communist military forces recruited heavily from landless and land-poor peasants who benefited from CCP land redistribution in liberated zones.", roleInArc: "Provided the manpower that outlasted Kuomintang encirclement campaigns and eventually overwhelmed Nationalist forces in the 1948-49 civil war offensives.", defected: false },
    { actorType: "old-regime", name: "Chiang Kai-shek", description: "Leader of the Kuomintang Nationalist government.", roleInArc: "Purged communist allies in 1927, fought the Japanese occupation, then lost the renewed civil war and retreated to Taiwan in December 1949.", defected: false },
    { actorType: "foreign-intervener", name: "Imperial Japan", description: "Occupying power in northern and eastern China from 1931 to 1945.", roleInArc: "Devastated Kuomintang-held territory and industry, indirectly weakening the Nationalist government's postwar capacity relative to the communists.", defected: false }
  ],
  tactics: [
    { tacticType: "guerrilla-warfare", description: "The Long March retreat and Yan'an base-area strategy preserved CCP forces through Kuomintang encirclement campaigns in the early 1930s.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "Land redistribution and local governance in CCP-controlled liberated zones built peasant loyalty years before the final military victory.", prominence: "primary" },
    { tacticType: "armed-insurgency", description: "Conventional battles in the 1946-1949 civil war, including the Huaihai and Liaoshen campaigns, destroyed the bulk of Nationalist field armies.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "The Shanghai massacre", dateStart: "1927-04-12", tStart: 0.00, tEnd: 0.12, intensity: 60, reached: true, summary: "Chiang Kai-shek turns on his communist allies, killing thousands and forcing the CCP into rural exile and armed self-defense.", keyEvents: ["Shanghai massacre, April 12, 1927", "CCP forced into rural base areas, 1927-1930"] },
    { phase: "the-spark", label: "The Long March", dateStart: "1934-10-16", tStart: 0.22, tEnd: 0.34, intensity: 65, reached: true, summary: "Encircled by Nationalist forces, roughly 86,000 communist troops begin a year-long retreat that becomes the CCP's founding legend and cements Mao's leadership.", keyEvents: ["Long March begins, October 1934", "Long March ends at Yan'an, October 1935"] },
    { phase: "moderate-phase", label: "United front against Japan", tStart: 0.34, tEnd: 0.48, intensity: 45, reached: true, summary: "The CCP and Kuomintang form a wartime alliance against Japanese occupation, giving the communists breathing room to expand base areas across northern China.", keyEvents: ["Second United Front formed, 1937", "Japanese surrender, August 1945"] },
    { phase: "dual-power", label: "Liberated zones expand", tStart: 0.48, tEnd: 0.60, intensity: 55, reached: true, summary: "CCP-administered rural zones with redistributed land coexist alongside shrinking Kuomintang-controlled territory as the wartime truce breaks down.", keyEvents: ["Full-scale civil war resumes, 1946", "Land reform campaigns expand in CCP zones, 1946-47"] },
    { phase: "radical-phase", label: "The civil war's decisive campaigns", tStart: 0.60, tEnd: 0.72, intensity: 85, reached: true, summary: "The Liaoshen, Huaihai, and Pingjin campaigns of 1948-49 destroy the core of the Nationalist army within months.", keyEvents: ["Liaoshen campaign, September-November 1948", "Huaihai campaign, November 1948-January 1949"] },
    { phase: "consolidation", label: "The People's Republic proclaimed", dateStart: "1949-10-01", tStart: 0.92, tEnd: 1.00, intensity: 50, reached: true, summary: "Communist forces take Beijing and Nanjing, Chiang Kai-shek retreats to Taiwan, and Mao proclaims the People's Republic of China in Tiananmen Square.", keyEvents: ["Beijing falls, January 1949", "Chiang retreats to Taiwan, December 1949", "People's Republic proclaimed, October 1, 1949"] }
  ],
  outcome: "consolidated-autocracy",
  militaryDefection: "partial",
  foreignIntervention: "material",
  durationDays: 8035,
  deathToll: "Estimates for the full 1927-1949 conflict, including the Japanese occupation years, range into the tens of millions when war, famine, and reprisal deaths are combined; the final 1946-1949 civil war phase alone is estimated at several million military and civilian deaths.",
  deathTollLow: 3000000,
  deathTollHigh: 6000000,
  regimeBefore: "military",
  regimeAfter: "one-party",
  democratizationDelta: -2,
  successFactors: [
    { factorKey: "protracted-base-strategy", label: "Protracted base-area guerrilla strategy can outlast the standard armed-campaign timeline", framework: "tilly", status: "confirmed", direction: "favors-movement", baseRate: "Tilly's mobilization framework identifies durable base-area control and repeated resource extraction cycles as a mechanism by which weaker challengers outlast stronger incumbents over long timeframes", rationale: "The CCP survived nearly a decade of Nationalist encirclement and a further eight years of Japanese occupation before its final, comparatively short, 1946-1949 offensive.", sources: ["Tilly, From Mobilization to Revolution (1978)"] },
    { factorKey: "occupation-weakens-incumbent", label: "Foreign occupation of the incumbent's territory can erode its coercive capacity", framework: "goldstone", status: "confirmed", direction: "favors-movement", baseRate: "Goldstone's comparative cases find that a foreign occupation absorbing an incumbent regime's military resources often benefits an internal challenger indirectly, distinct from foreign backing given directly to the challenger", rationale: "Japan's occupation devastated Kuomintang-held industrial and agricultural regions far more than CCP base areas, leaving Chiang's postwar army poorly supplied relative to the CCP's.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] },
    { factorKey: "agrarian-mass-mobilization", label: "Land redistribution mobilized a peasant base beyond narrow elite politics", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's account of the Chinese case specifically identifies peasant mobilization through land reform in liberated zones as decisive to the CCP's eventual military manpower advantage", rationale: "CCP-controlled areas redistributed land to tenant farmers years before national victory, generating both recruits and logistical support that a purely urban movement could not have matched.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Mao Zedong", role: "CCP Chairman, founding leader of the People's Republic", born: 1893, died: 1976 },
    { name: "Chiang Kai-shek", role: "Kuomintang leader, president of the Republic of China", born: 1887, died: 1975 },
    { name: "Zhou Enlai", role: "CCP negotiator and later premier", born: 1898, died: 1976 },
    { name: "Lin Biao", role: "Communist military commander of the Liaoshen and Pingjin campaigns", born: 1907, died: 1971 }
  ],
  legacyPoints: [
    "The People's Republic of China, proclaimed October 1, 1949, remains the world's most populous state under continuous one-party rule.",
    "Land reform redistributed holdings from landlords to an estimated 300 million peasants in the years immediately following the revolution.",
    "Chiang Kai-shek's retreat to Taiwan created the cross-strait political divide that continues to shape East Asian geopolitics today.",
    "The CCP is now among the longest continuously governing parties to have taken power through revolutionary armed struggle anywhere in the world."
  ],
  perspectives: [
    { id: "ccp-official", viewpoint: "CCP official historiography", viewpointType: "regime", regionOrigin: "China", narrative: "The revolution liberated China from a century of foreign imperialism, warlordism, and landlord exploitation, uniting a fractured country under a government finally answerable to its peasant majority.", keyArguments: ["Land reform ended centuries of landlord exploitation for hundreds of millions of tenant farmers", "The revolution ended a century of foreign concessions and unequal treaties dating to the Opium Wars", "National unification ended decades of warlordism and civil fragmentation"], emphasized: ["land reform's scale", "the end of foreign concessions"], omitted: ["the death toll of the civil war and subsequent political campaigns", "the loss of political pluralism under one-party rule"], notableQuotes: [{ text: "The Chinese people have stood up.", speaker: "Mao Zedong", context: "Widely cited framing of the October 1, 1949 proclamation" }] },
    { id: "kmt-exile", viewpoint: "Kuomintang and Taiwan exile view", viewpointType: "diaspora", regionOrigin: "Taiwan", narrative: "The communist victory was a national tragedy that ended the Republic of China's project of modernizing democracy on the mainland, driving millions into exile and dividing families across the strait for generations.", keyArguments: ["The Republic of China had already begun constitutional reforms before the civil war interrupted them", "Communist land reform in later decades produced its own severe famines and violence", "Millions of mainlanders fled to Taiwan rather than live under the new government"], emphasized: ["the disruption of the Republic's constitutional project", "the scale of postwar displacement to Taiwan"], omitted: ["Kuomintang corruption and hyperinflation in the war's final years", "the Kuomintang's own record of political repression before 1949"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "cuban-revolution", targetTitle: "The Cuban Revolution", type: "inspired", description: "Che Guevara and other Cuban revolutionaries studied Mao's protracted guerrilla and base-area doctrine directly when planning their own campaign." },
    { targetSlug: "chinese-cultural-revolution", targetTitle: "The Chinese Cultural Revolution", type: "parallel", description: "The same party and leader who won the 1949 revolution would, seventeen years later, turn a mass campaign against much of its own governing structure." }
  ],
  media: [],
  relatedRevoltSlugs: ["cuban-revolution", "chinese-cultural-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "chinese-cultural-revolution",
  slug: "chinese-cultural-revolution",
  title: "The Chinese Cultural Revolution",
  subtitle: "A chairman mobilizes the young against his own party to reclaim it",
  era: "anticolonial",
  region: "east-asia",
  country: "China",
  revoltType: "communist",
  status: "concluded",
  dateDisplay: "1966-1976",
  dateStart: 1966,
  dateEnd: 1976,
  summary: "Weakened politically after the Great Leap Forward's famine, Mao Zedong called on students to attack his own party's bureaucracy as insufficiently revolutionary. Red Guards denounced, imprisoned, and in many cases killed officials, teachers, and each other in factional violence for a decade, until Mao's death and the arrest of the Gang of Four ended the campaign in 1976.",
  significance: "A rare case of a revolution turned inward: the ruling party of an already-consolidated communist state used mass mobilization against its own institutions, at a human cost historians and the CCP's own 1981 party resolution both count in the millions.",
  grievances: [
    { kind: "Mao's diminished political authority", intensity: 85, evidence: "The Great Leap Forward's 1959-1961 famine, estimated to have killed between 15 and 45 million people, left Mao politically sidelined within the party leadership by the mid-1960s." },
    { kind: "Perceived bourgeois restoration within the party", intensity: 75, evidence: "Mao and his allies accused senior officials including Liu Shaoqi of reintroducing material incentives and easing collectivization after the famine, framing this as a retreat from revolutionary principle." },
    { kind: "Generational resentment of entrenched officials", intensity: 60, evidence: "Urban students facing limited advancement under an increasingly bureaucratic party structure responded readily to Mao's call to challenge officials as insufficiently revolutionary." }
  ],
  actors: [
    { actorType: "vanguard", name: "Mao Zedong", description: "CCP Chairman, initiator of the campaign.", roleInArc: "Issued the May 1966 circular launching the campaign and used mass youth mobilization to sideline rivals within the party leadership.", defected: false },
    { actorType: "students-youth", name: "Red Guards", description: "Student and youth militants organized into factions across Chinese cities.", roleInArc: "Denounced, humiliated, and in many cases physically attacked officials, teachers, and rival Red Guard factions between 1966 and 1968.", defected: false },
    { actorType: "old-regime", name: "Liu Shaoqi", description: "President of China and senior party official.", roleInArc: "Denounced as a 'capitalist roader,' stripped of position, and died in custody in 1969 without medical treatment.", defected: false },
    { actorType: "security-forces", name: "The People's Liberation Army under Lin Biao", description: "The military, which Mao relied on to eventually restore order after factional Red Guard violence spiraled.", roleInArc: "Enforced the 1968 'Down to the Countryside' campaign that dispersed millions of urban youth to rural labor, then Lin Biao himself fell from power and died in 1971.", defected: false },
    { actorType: "vanguard", name: "The Gang of Four", description: "Jiang Qing, Mao's wife, and three allied officials who directed much of the campaign's later ideological enforcement.", roleInArc: "Arrested within a month of Mao's death in 1976, formally ending the Cultural Revolution.", defected: false }
  ],
  tactics: [
    { tacticType: "mass-demonstration", description: "Red Guard rallies in Tiananmen Square drew crowds estimated near a million at their August 1966 peak.", prominence: "primary" },
    { tacticType: "sabotage", description: "The campaign against the 'Four Olds' destroyed temples, historical sites, books, and artifacts judged insufficiently revolutionary.", prominence: "primary" },
    { tacticType: "urban-uprising", description: "Rival Red Guard factions fought each other in city streets through 1967 and 1968, at times with seized weapons, before the army intervened.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  ateItsChildren: true,
  phases: [
    { phase: "old-regime-crisis", label: "Post-famine political weakness", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "The Great Leap Forward's famine leaves Mao politically vulnerable within his own party, setting the stage for a campaign to reassert his authority.", keyEvents: ["Great Leap Forward famine, 1959-1961", "Party leadership shifts toward pragmatist policies, 1962-1965"] },
    { phase: "the-spark", label: "The May circular", dateStart: "1966-05-16", tStart: 0.22, tEnd: 0.34, intensity: 60, reached: true, summary: "Mao's May 1966 Politburo circular and the first big-character poster at Peking University launch open attacks on party officials as insufficiently revolutionary.", keyEvents: ["May 16 circular issued, 1966", "First big-character poster at Peking University, May 1966"] },
    { phase: "radical-phase", label: "Red Guard mobilization", tStart: 0.60, tEnd: 0.72, intensity: 90, reached: true, summary: "Red Guard rallies fill Tiananmen Square, officials including Liu Shaoqi are purged, and denunciation campaigns spread through schools, factories, and government offices nationwide.", keyEvents: ["Million-strong Red Guard rally, August 1966", "Liu Shaoqi purged, 1968"] },
    { phase: "terror-virtue", label: "Factional violence and rustication", tStart: 0.72, tEnd: 0.84, intensity: 85, reached: true, summary: "Rival Red Guard factions turn on each other in city streets, and the government responds by sending millions of urban youth to rural labor under the Down to the Countryside campaign.", keyEvents: ["Factional Red Guard violence peaks, 1967-1968", "Down to the Countryside campaign begins, 1968"] },
    { phase: "thermidor", label: "Lin Biao's fall", dateStart: "1971-09-13", tStart: 0.84, tEnd: 0.92, intensity: 55, reached: true, summary: "Lin Biao, Mao's designated successor and the army leader who had helped restore order, dies fleeing China after an alleged coup plot, and the campaign's intensity gradually recedes.", keyEvents: ["Lin Biao dies in a plane crash fleeing China, September 13, 1971"] },
    { phase: "consolidation", label: "Mao's death and the Gang's arrest", dateStart: "1976-10-06", tStart: 0.92, tEnd: 1.00, intensity: 45, reached: true, summary: "Mao dies in September 1976; within a month the Gang of Four are arrested, formally ending a decade of campaign-driven upheaval.", keyEvents: ["Mao Zedong dies, September 9, 1976", "Gang of Four arrested, October 6, 1976"] }
  ],
  outcome: "intra-regime-purge",
  militaryDefection: "partial",
  foreignIntervention: "none",
  durationDays: 3650,
  deathToll: "Estimates for direct deaths from violence, persecution, and forced-labor conditions range from roughly 1.5 to 2 million, with tens of millions more affected by denunciation, imprisonment, or rural exile; the CCP's own 1981 party resolution called the decade a catastrophe.",
  deathTollLow: 1500000,
  deathTollHigh: 2000000,
  regimeBefore: "one-party",
  regimeAfter: "one-party",
  democratizationDelta: -1,
  successFactors: [
    { factorKey: "leader-mobilizes-against-elite", label: "A leader can mobilize mass campaigns to bypass institutional rivals within his own regime", framework: "skocpol", status: "atypical", direction: "favors-regime", baseRate: "Skocpol's framework generally treats elite fracture as a challenge to regime survival, but China's case shows a ruling figure can also engineer mass mobilization to defeat internal elite rivals while leaving the regime nominally intact", rationale: "Mao used Red Guard mobilization to remove Liu Shaoqi and other party rivals without ever ceding the CCP's monopoly on power, an intra-regime purge rather than a regime-versus-challenger contest.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "revolution-consumes-its-agents", label: "Movements that mobilize radical youth cadres often discard them once their purpose is served", framework: "brinton", status: "confirmed", direction: "favors-regime", baseRate: "Brinton's comparative model finds revolutionary regimes repeatedly mobilize and then abandon or suppress their most radical enforcers once the leadership's position is secure", rationale: "Red Guards who denounced officials on Mao's behalf in 1966-67 were themselves dispersed to rural labor by 1968 once their usefulness to the center had passed.", sources: ["Brinton, The Anatomy of Revolution (1938)"] },
    { factorKey: "elite-fracture-within-party", label: "Elite fracture inside a single ruling party can substitute for fracture between regime and opposition", framework: "goldstone", status: "confirmed", direction: "indeterminate", baseRate: "Goldstone's framework notes that state crises can originate from fracture within a ruling coalition, not only from external challengers, with outcomes ranging from purge to regime collapse depending on how the fracture resolves", rationale: "The Lin Biao affair in 1971, a fracture between Mao and his own designated successor, shows the instability could have widened into a broader regime crisis had it not been contained within the top leadership.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Mao Zedong", role: "CCP Chairman, initiator of the campaign", born: 1893, died: 1976 },
    { name: "Liu Shaoqi", role: "President of China, purged 1968, died in custody 1969", born: 1898, died: 1969 },
    { name: "Lin Biao", role: "Defense minister and Mao's designated successor until his 1971 fall", born: 1907, died: 1971 },
    { name: "Jiang Qing", role: "Mao's wife, leading member of the Gang of Four", born: 1914, died: 1991 }
  ],
  legacyPoints: [
    "An estimated 1.5 to 2 million deaths and tens of millions of disrupted lives resulted from a decade of denunciation, imprisonment, and rural exile.",
    "An entire cohort of Chinese youth lost formal schooling during the Down to the Countryside years, later termed China's 'lost generation.'",
    "The CCP's 1981 Resolution on Party History officially labeled the decade a catastrophe caused 'chiefly' by Mao, while preserving his broader legacy within party doctrine.",
    "Deng Xiaoping's post-1978 economic reforms were framed explicitly against Cultural Revolution excess, prioritizing stability and material development over ideological campaigns."
  ],
  perspectives: [
    { id: "ccp-post-1981", viewpoint: "CCP post-1981 official assessment", viewpointType: "regime", regionOrigin: "China", narrative: "The party's own 1981 resolution acknowledges the decade as a grave error driven chiefly by Mao's misjudgment, while crediting the party's capacity for self-correction under Deng Xiaoping's subsequent reforms.", keyArguments: ["The 1981 resolution assigns chief responsibility to Mao while preserving his broader historical standing", "The campaign's chaos and economic disruption justified the post-1978 turn toward stability and reform", "The party's ability to reverse course is presented as evidence of institutional resilience"], emphasized: ["the 1981 resolution's formal verdict", "the subsequent reform era's economic gains"], omitted: ["the scale of individual suffering during denunciation campaigns", "the party's own role in organizing and directing Red Guard violence"], notableQuotes: [] },
    { id: "red-guard-retrospective", viewpoint: "Former Red Guard participant retrospective", viewpointType: "diaspora", regionOrigin: "China", narrative: "Many who joined as teenagers describe genuine revolutionary idealism mixed with the ordinary pressures of youth conformity, followed by disillusionment once they themselves were sent to rural labor and their leaders discarded them.", keyArguments: ["Participation often blended sincere ideological belief with fear of being labeled insufficiently revolutionary", "The 1968 rustication campaign abruptly ended many participants' education and urban lives", "Retrospective accounts frequently describe both agency in denouncing others and later victimization by the same system"], emphasized: ["personal accounts of rustication", "the gap between initial idealism and later disillusionment"], omitted: ["systematic tallies of the campaign's total death toll", "top-level factional politics driving the campaign's timing"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "chinese-revolution-1949", targetTitle: "The Chinese Communist Revolution", type: "parallel", description: "The same party that mobilized peasants against landlords in 1949 mobilized students against its own officials seventeen years later, using a comparable mass-campaign method turned inward." },
    { targetSlug: "cuban-revolution", targetTitle: "The Cuban Revolution", type: "counter-example", description: "Cuba's one-party consolidation under Castro avoided a comparably destructive internal purge of its own revolutionary cadres." }
  ],
  media: [],
  relatedRevoltSlugs: ["chinese-revolution-1949", "cuban-revolution"],
  relatedHistorySlugs: ["chinese-cultural-revolution"],
  published: true
},
{
  id: "cuban-revolution",
  slug: "cuban-revolution",
  title: "The Cuban Revolution",
  subtitle: "Eighty-two guerrillas land in a rowboat and topple a dictator in six years",
  era: "anticolonial",
  region: "americas",
  country: "Cuba",
  revoltType: "communist",
  status: "concluded",
  dateDisplay: "1953-1959",
  dateStart: 1953,
  dateEnd: 1959,
  summary: "Fidel Castro's failed 1953 attack on the Moncada Barracks became the founding date of a movement that regrouped in Mexico, landed 82 fighters from the yacht Granma in 1956, and fought a guerrilla campaign from the Sierra Maestra mountains that combined with an urban underground and a collapsing army to drive Batista from power in six years.",
  significance: "Established the first Marxist-Leninist government in the Western Hemisphere, ninety miles from the United States, and made the Sierra Maestra guerrilla model a template studied and imitated across Latin America and Africa for decades.",
  grievances: [
    { kind: "Batista's 1952 coup", intensity: 80, evidence: "Fulgencio Batista seized power in a March 1952 coup that canceled scheduled elections he was expected to lose, ending any near-term path to change at the ballot box." },
    { kind: "Foreign ownership of the sugar economy", intensity: 65, evidence: "US-based companies owned an estimated 40 percent of Cuba's sugar-producing land by the early 1950s, concentrating the island's main export industry in foreign hands." },
    { kind: "Police repression under Batista", intensity: 75, evidence: "Batista's secret police, the SIM, tortured and killed an estimated several thousand suspected opponents over the course of his rule, radicalizing broad sections of Cuban society against him." }
  ],
  actors: [
    { actorType: "vanguard", name: "Fidel Castro", description: "Lawyer and leader of the 26th of July Movement.", roleInArc: "Led the failed 1953 Moncada attack, organized the 1956 Granma landing, and commanded the Sierra Maestra guerrilla campaign to victory.", defected: false },
    { actorType: "military-defectors", name: "Che Guevara", description: "Argentine physician who joined Castro's movement in Mexico.", roleInArc: "Commanded rebel columns including the decisive Battle of Santa Clara in December 1958 that cut the island in two.", defected: false },
    { actorType: "old-regime", name: "Fulgencio Batista", description: "President of Cuba after his 1952 coup.", roleInArc: "Fled Cuba by plane on January 1, 1959, as rebel forces and mass army desertions closed in on Havana.", defected: false },
    { actorType: "organized-labor", name: "The urban underground", description: "26th of July Movement cells operating in Havana and Santiago de Cuba.", roleInArc: "Carried out sabotage and organized a partially successful April 1958 general strike, complementing the rural guerrilla campaign.", defected: false },
    { actorType: "security-forces", name: "Batista's conscript army", description: "Cuba's roughly 40,000-strong military.", roleInArc: "Suffered mass desertions in the final weeks of 1958 after repeated defeats, collapsing the regime's last coercive instrument.", defected: true }
  ],
  tactics: [
    { tacticType: "guerrilla-warfare", description: "The Sierra Maestra campaign built rebel-controlled rural territory from a landing force of just a dozen survivors in late 1956.", prominence: "primary" },
    { tacticType: "sabotage", description: "Urban underground cells in Havana and Santiago carried out bombings and arson against Batista-aligned infrastructure and businesses.", prominence: "primary" },
    { tacticType: "general-strike", description: "An April 1958 general strike call achieved only partial participation, exposing the limits of the urban wing relative to the rural guerrilla campaign.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Batista's coup", dateStart: "1952-03-10", tStart: 0.00, tEnd: 0.12, intensity: 50, reached: true, summary: "Batista's coup cancels scheduled elections, closing off legal paths to change and pushing opposition figures like Castro toward armed resistance.", keyEvents: ["Batista's coup, March 10, 1952"] },
    { phase: "the-spark", label: "Moncada", dateStart: "1953-07-26", tStart: 0.22, tEnd: 0.34, intensity: 55, reached: true, summary: "Castro's attack on the Moncada Barracks fails militarily but gives the movement its name and its founding date.", keyEvents: ["Moncada Barracks attack, July 26, 1953", "Castro imprisoned then amnestied, 1953-1955"] },
    { phase: "moderate-phase", label: "Exile and the Granma landing", dateStart: "1956-12-02", tStart: 0.34, tEnd: 0.48, intensity: 50, reached: true, summary: "Castro's movement regroups in Mexico and lands 82 fighters from the yacht Granma; most are killed or captured within days, leaving a small surviving nucleus in the mountains.", keyEvents: ["Granma landing, December 2, 1956"] },
    { phase: "dual-power", label: "Sierra Maestra versus the cities", tStart: 0.48, tEnd: 0.60, intensity: 60, reached: true, summary: "Rebel-controlled rural zones in the Sierra Maestra expand while Batista's government still controls Havana and the major cities.", keyEvents: ["Rebel radio broadcasts begin from the Sierra Maestra, 1958", "April 1958 general strike only partially succeeds"] },
    { phase: "radical-phase", label: "The final offensive", dateStart: "1958-12-28", tStart: 0.60, tEnd: 0.72, intensity: 85, reached: true, summary: "Rebel columns under Guevara and Camilo Cienfuegos advance from the mountains, culminating in the Battle of Santa Clara that severs the island.", keyEvents: ["Battle of Santa Clara, December 28-31, 1958"] },
    { phase: "consolidation", label: "Batista flees", dateStart: "1959-01-01", tStart: 0.92, tEnd: 1.00, intensity: 55, reached: true, summary: "Batista flees Cuba by plane and Castro's forces enter Havana within days, installing a new revolutionary government.", keyEvents: ["Batista flees Cuba, January 1, 1959", "Castro's forces enter Havana, January 8, 1959"] }
  ],
  outcome: "consolidated-autocracy",
  militaryDefection: "full",
  foreignIntervention: "material",
  durationDays: 2200,
  deathToll: "Estimates for the insurgency itself range from roughly 5,000 to 20,000 killed, including combatants and civilian victims of Batista's repression.",
  deathTollLow: 5000,
  deathTollHigh: 20000,
  regimeBefore: "personalist",
  regimeAfter: "one-party",
  democratizationDelta: -1,
  successFactors: [
    { factorKey: "hybrid-tactics", label: "Combining guerrilla and urban sabotage tactics can outperform either alone", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Armed campaigns succeed in roughly 26% of historical cases; hybrid campaigns pairing rural guerrilla war with urban sabotage networks fracture regime morale on multiple fronts at once", rationale: "The Sierra Maestra guerrilla campaign alone controlled only rural territory, but combined with the Havana and Santiago underground, it steadily eroded Batista's urban support base as well.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "security-force-defection", label: "Security force defection is the strongest single predictor of rapid collapse", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Movements that achieve late-stage defection among an incumbent's own conscript forces succeed at markedly higher rates than those facing a fully loyal military", rationale: "Batista's 40,000-strong army suffered mass desertions in December 1958 after repeated battlefield defeats, leaving him with no force willing to defend Havana.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-backing-withdrawal", label: "Withdrawal of foreign backing from an incumbent can weaken it as much as backing a challenger", framework: "goldstone", status: "atypical", direction: "favors-movement", baseRate: "The literature more often finds that foreign material backing GIVEN to a challenger correlates with weaker post-victory institutions; Cuba's case instead shows withdrawal of backing FROM the incumbent accelerating its collapse", rationale: "A US arms embargo imposed on Batista in March 1958 reduced his government's coercive capacity in the campaign's final, decisive months.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Fidel Castro", role: "Leader of the 26th of July Movement, later Cuban head of state", born: 1926, died: 2016 },
    { name: "Che Guevara", role: "Rebel commander, later government minister", born: 1928, died: 1967 },
    { name: "Fulgencio Batista", role: "Deposed president of Cuba", born: 1901, died: 1973 },
    { name: "Camilo Cienfuegos", role: "Rebel column commander in the final offensive", born: 1932, died: 1959 }
  ],
  legacyPoints: [
    "Nationalization of US-owned sugar and utility companies within two years of victory triggered the US trade embargo still in force today.",
    "Cuba became the first Marxist-Leninist government in the Western Hemisphere, a status it retains more than six decades later.",
    "A 1961 national literacy campaign raised Cuba's literacy rate from roughly 60 to over 96 percent within a single year.",
    "The Sierra Maestra guerrilla model became a template studied and adapted by revolutionary movements across Latin America and Africa for decades afterward."
  ],
  perspectives: [
    { id: "revolutionary-official", viewpoint: "Cuban revolutionary official view", viewpointType: "regime", regionOrigin: "Cuba", narrative: "The revolution ended a corrupt dictatorship propped up by foreign capital and delivered literacy, healthcare, and national sovereignty to a population long treated as a dependent economy of the United States.", keyArguments: ["Batista's government was a dictatorship maintained through torture and canceled elections", "US corporate ownership of Cuban sugar land represented a loss of national economic sovereignty", "Post-revolution literacy and healthcare gains are measurable and durable"], emphasized: ["the literacy campaign", "US corporate landholding before 1959"], omitted: ["the one-party political system installed after 1959", "the scale of political imprisonment under the new government"], notableQuotes: [] },
    { id: "exile-diaspora", viewpoint: "Cuban exile diaspora view", viewpointType: "diaspora", regionOrigin: "Miami, United States", narrative: "A revolution that promised a return to Cuba's 1940 constitution and free elections instead consolidated into a one-party state, driving hundreds of thousands into exile and nationalizing private property without compensation.", keyArguments: ["Castro postponed and then abandoned the promised elections of the 26th of July Movement's original platform", "Nationalization without compensation devastated the Cuban middle class and professional sectors", "Ongoing one-party rule and political imprisonment contradict the revolution's original democratic rhetoric"], emphasized: ["the abandoned 1940 constitution promise", "mass emigration after 1959"], omitted: ["the scale of Batista-era repression that preceded the revolution", "material gains among Cuba's rural poor after 1959"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "chinese-revolution-1949", targetTitle: "The Chinese Communist Revolution", type: "inspired", description: "Guevara and other Cuban revolutionaries studied Mao's protracted guerrilla and base-area doctrine while planning the Sierra Maestra campaign." },
    { targetSlug: "sandinista-revolution", targetTitle: "The Sandinista Revolution", type: "provided-model", description: "Cuba supplied material aid, training, and an ideological template that directly shaped the Sandinista Front's own guerrilla campaign two decades later." }
  ],
  media: [],
  relatedRevoltSlugs: ["chinese-revolution-1949", "sandinista-revolution"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "algerian-revolution",
  slug: "algerian-revolution",
  title: "The Algerian War of Independence",
  subtitle: "A settler colony of one million loses a war fought mostly out of sight",
  era: "anticolonial",
  region: "africa",
  country: "Algeria",
  revoltType: "anticolonial",
  status: "concluded",
  dateDisplay: "1954-1962",
  dateStart: 1954,
  dateEnd: 1962,
  summary: "The FLN's coordinated attacks on All Saints' Day 1954 opened an eight-year war against French rule that killed hundreds of thousands, brought down France's own Fourth Republic, and ended with nearly a million pied-noir settlers leaving within months of Algerian independence.",
  significance: "One of the defining anticolonial wars of the twentieth century, it demonstrated that a colonial power with overwhelming military superiority could still be exhausted into withdrawal by a protracted guerrilla and urban campaign paired with its own domestic political fracture.",
  grievances: [
    { kind: "Settler control of land and political power", intensity: 85, evidence: "Pied-noir settlers, roughly 10 percent of Algeria's population, controlled the majority of the colony's arable farmland and nearly all senior administrative posts through the mid-1950s." },
    { kind: "Denial of political rights", intensity: 80, evidence: "The 1947 Algerian Statute created a second electoral college so that roughly 1 million European settlers held equal representation with roughly 9 million Muslim Algerians." },
    { kind: "The Setif massacre", intensity: 90, evidence: "French forces and settler militias killed an estimated several thousand to over ten thousand Algerians in reprisals after independence demonstrations on May 8, 1945, a date Algerians remember as the war's true origin." }
  ],
  actors: [
    { actorType: "vanguard", name: "The FLN", description: "The National Liberation Front, formed in 1954 to unify Algeria's fractured nationalist movements.", roleInArc: "Coordinated the All Saints' Day attacks and led the political and military campaign through to the 1962 Evian Accords.", defected: false },
    { actorType: "masses", name: "The ALN", description: "The FLN's guerrilla army, operating from rural bases and cross-border sanctuaries.", roleInArc: "Fought a sustained rural and mountain guerrilla campaign against French forces for the length of the war.", defected: false },
    { actorType: "old-regime", name: "The French colonial administration", description: "France's civil and military government of Algeria, then legally three departments of metropolitan France.", roleInArc: "Deployed up to 500,000 troops and interned hundreds of thousands of Algerians in an escalating counterinsurgency campaign.", defected: false },
    { actorType: "counter-revolutionaries", name: "The OAS", description: "A settler and dissident-military organization formed in 1961 to keep Algeria French by force.", roleInArc: "Carried out bombings and assassinations against both Algerian civilians and French officials negotiating independence, including an assassination attempt on de Gaulle.", defected: false },
    { actorType: "foreign-backer", name: "Tunisia and Morocco", description: "Newly independent neighboring states that hosted FLN sanctuary bases and training camps.", roleInArc: "Provided cross-border refuge that sustained ALN operations even as the French army built fortified lines to seal the borders.", defected: false }
  ],
  tactics: [
    { tacticType: "guerrilla-warfare", description: "ALN units operated from rural and mountain bases, avoiding direct engagement with superior French firepower.", prominence: "primary" },
    { tacticType: "urban-uprising", description: "The 1956-57 Battle of Algiers brought bombing and assassination campaigns into the capital itself, provoking a brutal French counter-campaign of mass arrest and torture.", prominence: "primary" },
    { tacticType: "sabotage", description: "Attacks on settler farms, infrastructure, and the colonial economy pressured the settler population's willingness to remain.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Setif and stalled reform", tStart: 0.00, tEnd: 0.12, intensity: 55, reached: true, summary: "Post-1945 repression and failed reform proposals leave Algerian nationalists convinced legal channels are closed.", keyEvents: ["Setif massacre, May 8, 1945", "1947 Algerian Statute creates unequal electoral colleges"] },
    { phase: "the-spark", label: "Toussaint Rouge", dateStart: "1954-11-01", tStart: 0.22, tEnd: 0.34, intensity: 70, reached: true, summary: "The FLN coordinates roughly 30 attacks across Algeria on All Saints' Day, announcing the war's start.", keyEvents: ["All Saints' Day attacks, November 1, 1954", "FLN founding proclamation broadcast"] },
    { phase: "moderate-phase", label: "The Soummam Congress", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "FLN delegates meet in the Soummam valley in 1956 to unify military and political command under a single structure.", keyEvents: ["Soummam Congress, August 1956"] },
    { phase: "radical-phase", label: "The Battle of Algiers", dateStart: "1956-09-30", tStart: 0.60, tEnd: 0.72, intensity: 85, reached: true, summary: "An FLN bombing campaign in Algiers is met by a French paratrooper mass arrest, interrogation, and torture campaign that dismantles the urban FLN network within months.", keyEvents: ["Battle of Algiers begins, September 1956", "French forces claim the urban network dismantled, 1957"] },
    { phase: "terror-virtue", label: "Internment and reprisal", tStart: 0.72, tEnd: 0.84, intensity: 80, reached: true, summary: "French forces intern an estimated two million rural Algerians in regroupment camps while FLN reprisals target harkis and rival nationalist factions.", keyEvents: ["Regroupment camp policy expands, 1957-1960", "FLN purges the rival MNA faction"] },
    { phase: "thermidor", label: "The generals' putsch", dateStart: "1961-04-21", tStart: 0.84, tEnd: 0.92, intensity: 65, reached: true, summary: "Dissident French generals seize Algiers in a failed putsch against de Gaulle's negotiations, splitting the French military and accelerating a negotiated exit.", keyEvents: ["Algiers putsch, April 1961", "OAS terror campaign intensifies, 1961-62"] },
    { phase: "consolidation", label: "Evian and independence", dateStart: "1962-03-18", tStart: 0.92, tEnd: 1.00, intensity: 55, reached: true, summary: "The Evian Accords end the war, and a July 1962 referendum delivers overwhelming support for independence.", keyEvents: ["Evian Accords signed, March 18, 1962", "Independence referendum, July 1, 1962", "Independence declared, July 5, 1962"] }
  ],
  outcome: "independence",
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  durationDays: 2804,
  deathToll: "French and Algerian estimates diverge sharply: French figures put Algerian deaths near 350,000, while the Algerian government has cited a figure near 1 million; both sides broadly agree on around 25,000 French military deaths.",
  deathTollLow: 350000,
  deathTollHigh: 1000000,
  regimeBefore: "colonial",
  regimeAfter: "one-party",
  democratizationDelta: 1,
  successFactors: [
    { factorKey: "armed-campaign-attrition", label: "Protracted armed campaigns can win by exhausting the incumbent's will more than by defeating its army", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Armed campaigns succeed in roughly 26% of historical cases; protracted wars exceeding a decade more often succeed through attrition of the incumbent's domestic political will than through outright military victory", rationale: "Eight years of war and over a million rotated French conscripts wore down metropolitan political support for the war faster than the French army broke the ALN's rural sanctuary network.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-sanctuary-support", label: "Cross-border sanctuary sustains protracted challenger campaigns", framework: "goldstone", status: "confirmed", direction: "favors-movement", baseRate: "Foreign material and sanctuary support correlates with sustaining protracted challenger campaigns, though the wider literature also finds it often correlates with weaker post-victory institutions", rationale: "Tunisian and Moroccan sanctuary kept ALN cross-border operations alive even as France built the fortified Morice Line to try to seal the border.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] },
    { factorKey: "elite-fracture", label: "Elite fracture within the incumbent power often precedes a negotiated exit", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's model finds a split within the incumbent's own governing and military elite a frequent precursor to negotiated withdrawal rather than continued suppression", rationale: "The April 1961 generals' putsch against de Gaulle exposed exactly this fracture within the French military and accelerated the Evian negotiations that followed within a year.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Ahmed Ben Bella", role: "FLN leader, first president of independent Algeria", born: 1918, died: 2012 },
    { name: "Ferhat Abbas", role: "Nationalist leader, first president of the FLN's provisional government", born: 1899, died: 1985 },
    { name: "Charles de Gaulle", role: "President of France, negotiated the Evian Accords", born: 1890, died: 1970 },
    { name: "Larbi Ben M'hidi", role: "FLN military leader in the Battle of Algiers", born: 1923, died: 1957 }
  ],
  legacyPoints: [
    "French and Algerian death toll estimates still diverge by hundreds of thousands, a gap that continues to shape memory politics on both sides of the Mediterranean today.",
    "Roughly 900,000 pied-noir settlers left Algeria within months of independence in 1962, one of the fastest mass departures of a settler population in modern history.",
    "The war's political fallout ended France's Fourth Republic and brought Charles de Gaulle back to power in 1958.",
    "The FLN's one-party rule after 1962 shaped Algerian governance for decades, a direct continuation of the wartime political structure."
  ],
  perspectives: [
    { id: "fln-nationalist", viewpoint: "FLN nationalist view", viewpointType: "revolutionary", regionOrigin: "Algeria", narrative: "Armed struggle became the only remaining avenue after a decade of failed legal reform, and eight years of sustained sacrifice, not French goodwill, produced independence.", keyArguments: ["The Setif massacre of 1945 proved peaceful demonstration would be met with reprisal killing", "The unequal electoral college made legislative change structurally impossible", "Independence came only after sustained armed and political pressure, not through French reform"], emphasized: ["the Setif massacre", "the scale of wartime sacrifice"], omitted: ["the FLN's own purges of rival nationalist factions", "the treatment of harkis after independence"], notableQuotes: [] },
    { id: "pied-noir-retrospective", viewpoint: "French veteran and pied-noir retrospective view", viewpointType: "diaspora", regionOrigin: "France", narrative: "A community whose roots in Algeria spanned generations lost its homes within months, and the brutality both sides inflicted during the war is often flattened into a single-sided colonial narrative.", keyArguments: ["Multi-generational settler communities are frequently erased from independence-era narratives", "The FLN's own violence against harkis and rival Algerians remains undercounted in most accounts", "French conscripts, many of them reluctant nineteen-year-olds, also paid a heavy cost in the war"], emphasized: ["settler displacement", "harki reprisals after independence"], omitted: ["settler-era land and political inequality", "the 1945 Setif reprisal killings"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "cuban-revolution", targetTitle: "The Cuban Revolution", type: "parallel", description: "Both were contemporaneous anticolonial and anti-dictatorial guerrilla wars fought and won within roughly the same decade." },
    { targetSlug: "latin-american-independence", targetTitle: "The Spanish American Wars of Independence", type: "parallel", description: "Both pitted a colonized population against a settler-linked metropolitan power, though separated by more than a century." }
  ],
  media: [],
  relatedRevoltSlugs: ["cuban-revolution", "latin-american-independence"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "carnation-revolution",
  slug: "carnation-revolution",
  title: "The Carnation Revolution",
  subtitle: "An army coup ends a dictatorship before breakfast, and a nation answers with flowers",
  era: "people-power",
  region: "europe",
  country: "Portugal",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "April 1974",
  dateStart: 1974,
  dateEnd: 1974,
  summary: "Junior army officers exhausted by thirteen years of colonial war in Angola, Mozambique, and Guinea-Bissau seized Lisbon's key installations before dawn on April 25, 1974. Civilians filled the streets within hours, putting carnations into soldiers' rifle barrels, and the forty-eight-year-old Estado Novo dictatorship collapsed by nightfall with fewer than five deaths.",
  significance: "One of the fastest and least violent authoritarian collapses of the twentieth century, driven almost entirely by the military itself rather than by prior mass civilian mobilization, and a direct trigger for the rapid decolonization of Portugal's African territories.",
  grievances: [
    { kind: "Colonial war exhaustion", intensity: 88, evidence: "Portugal had fought simultaneous colonial wars in Angola, Mozambique, and Guinea-Bissau since 1961, consuming an estimated 40 percent of the state budget by the early 1970s." },
    { kind: "Officer promotion grievance", intensity: 60, evidence: "A 1973 decree allowed conscript militia officers to gain seniority over career officers with equivalent combat service, angering the professional officer corps that would form the Armed Forces Movement." },
    { kind: "Decades of political repression", intensity: 65, evidence: "The Estado Novo's secret police, the PIDE, had operated since the 1930s, suppressing opposition parties and a free press for longer than most Portuguese citizens had been alive." }
  ],
  actors: [
    { actorType: "military-defectors", name: "The Armed Forces Movement", description: "A clandestine network of junior and mid-ranking officers frustrated by the colonial wars and promotion policy.", roleInArc: "Planned and executed the coup, seizing radio stations, the airport, and government buildings within hours on April 25, 1974.", defected: true },
    { actorType: "masses", name: "Lisbon civilians", description: "Residents who filled the streets once word of the coup spread on the morning of April 25.", roleInArc: "Placed carnations in soldiers' rifle barrels and uniforms, giving the revolution its name and helping deter any violent response.", defected: false },
    { actorType: "old-regime", name: "Marcelo Caetano", description: "Prime Minister and head of the Estado Novo government since 1968.", roleInArc: "Surrendered to Armed Forces Movement units at the Carmo barracks on the evening of April 25 and was flown into exile.", defected: false },
    { actorType: "security-forces", name: "PIDE secret police", description: "The regime's political police force.", roleInArc: "Fired the coup's only fatal shots from its Lisbon headquarters, killing four civilians before surrendering.", defected: false }
  ],
  tactics: [
    { tacticType: "defection-fraternization", description: "The coup was carried out by serving army units themselves refusing to defend the regime, the decisive act rather than a supporting one.", prominence: "primary" },
    { tacticType: "occupation", description: "Armed Forces Movement units seized the national radio and television stations, the airport, and government ministries within hours of the coup's start.", prominence: "primary" },
    { tacticType: "mass-demonstration", description: "Spontaneous crowds filled central Lisbon within hours, physically surrounding army vehicles in celebration rather than confrontation.", prominence: "secondary" }
  ],
  resistanceType: "nonviolent",
  phases: [
    { phase: "old-regime-crisis", label: "Thirteen years of colonial war", tStart: 0.00, tEnd: 0.12, intensity: 55, reached: true, summary: "Portugal's wars in Angola, Mozambique, and Guinea-Bissau drain the treasury and exhaust the officer corps by the early 1970s.", keyEvents: ["Colonial wars begin, 1961", "1973 officer seniority decree angers career officers"] },
    { phase: "the-spark", label: "Two songs and a coup", dateStart: "1974-04-25", tStart: 0.22, tEnd: 0.34, intensity: 90, reached: true, summary: "A pair of coded radio broadcasts signal Armed Forces Movement units to move at dawn, and Lisbon's key installations fall within hours.", keyEvents: ["E depois do adeus broadcast as first signal", "Grandola Vila Morena broadcast as second signal", "Armed Forces Movement units seize Lisbon, April 25, 1974"] },
    { phase: "radical-phase", label: "PREC", tStart: 0.60, tEnd: 0.72, intensity: 65, reached: true, summary: "The Processo Revolucionario Em Curso sees factional struggle between moderates and a more radical left through 1975, including an attempted leftist countercoup.", keyEvents: ["Nationalization wave, 1974-75", "Attempted leftist coup, November 25, 1975"] },
    { phase: "consolidation", label: "The 1976 constitution", tStart: 0.92, tEnd: 1.00, intensity: 45, reached: true, summary: "Portugal holds its first free elections in April 1975 and adopts a democratic constitution in 1976.", keyEvents: ["First free elections, April 1975", "1976 constitution adopted"] }
  ],
  outcome: "consolidated-democracy",
  militaryDefection: "full",
  foreignIntervention: "none",
  peakParticipationPct: null,
  peakParticipationDisplay: "Hundreds of thousands of Lisbon residents filled the streets within hours of the coup, though the decisive action was the army's own defection rather than prior mass mobilization",
  crossedParticipationThreshold: null,
  durationDays: 1,
  deathToll: "Four civilians killed by PIDE gunfire at its Lisbon headquarters; otherwise close to bloodless.",
  deathTollLow: 4,
  deathTollHigh: 4,
  regimeBefore: "personalist",
  regimeAfter: "democracy",
  democratizationDelta: 4,
  successFactors: [
    { factorKey: "security-force-defection", label: "Security force defection is the single strongest predictor of rapid regime collapse", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Movements that achieve security force defection succeed at markedly higher rates than those that do not, across the cross-national record", rationale: "The coup succeeded because it was carried out by the military itself, not because the military had to be persuaded to abandon a regime it still defended.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "nonviolent-success-rate", label: "Low-violence campaigns succeed more often than armed ones", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Nonviolent campaigns succeed roughly 53% of the time historically, versus about 26% for armed campaigns", rationale: "A near-bloodless outcome, four deaths, matches the historical pattern that low-violence transitions succeed at markedly higher rates.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "incumbent-coercive-exhaustion", label: "Prolonged external conflict can exhaust an incumbent's coercive apparatus before a challenger even appears", framework: "goldstone", status: "confirmed", direction: "favors-movement", baseRate: "An incumbent regime whose coercive apparatus is exhausted by prolonged external conflict is structurally vulnerable to even a small, well-organized internal challenge", rationale: "Thirteen years of colonial war had already broken the officer corps' loyalty to the regime before a single carnation was placed in a rifle.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Marcelo Caetano", role: "Deposed Prime Minister of the Estado Novo", born: 1906, died: 1980 },
    { name: "Otelo Saraiva de Carvalho", role: "Chief military planner of the coup", born: 1936, died: 2009 },
    { name: "Mario Soares", role: "Opposition leader, later prime minister and president", born: 1924, died: 2017 },
    { name: "Antonio de Spinola", role: "General and first post-coup president", born: 1910, died: 1996 }
  ],
  legacyPoints: [
    "The revolution's name comes from carnations placed in soldiers' rifle barrels by Celeste Caeiro and other Lisbon civilians on the morning of April 25, 1974.",
    "Portugal granted independence to Angola, Mozambique, Guinea-Bissau, Cape Verde, and Sao Tome and Principe within eighteen months of the coup.",
    "Portugal joined the European Community in 1986, cementing its democratic consolidation within little more than a decade of the coup.",
    "April 25 is now a national holiday, Freedom Day, marked across Portugal every year."
  ],
  perspectives: [
    { id: "mfa-officer", viewpoint: "Armed Forces Movement officer view", viewpointType: "military", regionOrigin: "Portugal", narrative: "The war in Africa could not be won militarily and the regime could not be reformed from within, leaving the army itself as the only institution capable of ending both at once.", keyArguments: ["Colonial war casualties and budget strain had become unsustainable by 1973", "Officers who had served multiple African tours concluded no military victory was achievable", "Reform attempts within the Estado Novo's own structures had repeatedly failed"], emphasized: ["colonial war exhaustion", "officer testimony from multiple African tours"], omitted: ["the retornado settler displacement that followed decolonization", "PREC-era political instability"], notableQuotes: [] },
    { id: "retornado-settler", viewpoint: "Retornado settler view", viewpointType: "diaspora", regionOrigin: "Portugal, Angola, and Mozambique", narrative: "Over half a million settlers were displaced from Angola and Mozambique within months of the coup, a rupture rarely centered in the celebratory national memory of April 25.", keyArguments: ["Decolonization's speed left little time for an orderly settler transition", "Many retornados arrived in Portugal with only what they could carry", "Their displacement is often treated as a footnote to the coup's domestic celebration"], emphasized: ["the speed of the settler exodus", "economic hardship on arrival in Portugal"], omitted: ["the colonial war's cost to Angolan and Mozambican populations", "the democratic gains that followed in Portugal itself"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "euromaidan", targetTitle: "Euromaidan", type: "parallel", description: "Both revolutions turned on the same hinge: a security apparatus refusing, at the decisive moment, to defend the regime it served." },
    { targetSlug: "anti-apartheid", targetTitle: "The Anti-Apartheid Struggle", type: "parallel", description: "Both produced negotiated rather than violently contested transitions, though Portugal's took a single day and South Africa's took decades." }
  ],
  media: [],
  relatedRevoltSlugs: ["euromaidan", "anti-apartheid"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "sandinista-revolution",
  slug: "sandinista-revolution",
  title: "The Sandinista Revolution",
  subtitle: "A forty-three-year dynasty falls in eighteen months, then loses the ballot a decade later",
  era: "people-power",
  region: "americas",
  country: "Nicaragua",
  revoltType: "social",
  status: "concluded",
  dateDisplay: "1961-1990",
  dateStart: 1961,
  dateEnd: 1990,
  summary: "The Sandinista National Liberation Front, founded in 1961 against the Somoza family dynasty, fought an on-and-off guerrilla war for eighteen years before a broad coalition of guerrillas, striking businesses, and outraged citizens finally drove Anastasio Somoza Debayle from power in 1979. The Sandinistas then governed through a decade of Contra war before losing Nicaragua's 1990 election at the ballot box.",
  significance: "A rare case of an armed revolutionary movement that won power by force and then, a decade later, peacefully relinquished it after losing a free election, though its founding generation would return to government by ballot years afterward.",
  grievances: [
    { kind: "Dynastic rule", intensity: 82, evidence: "The Somoza family had governed Nicaragua for 43 years by 1979, with Anastasio Somoza Debayle the third family member to hold the presidency since his father seized power in 1936." },
    { kind: "Earthquake relief corruption", intensity: 78, evidence: "The National Guard diverted a substantial share of international relief aid following the 1972 Managua earthquake, which killed an estimated 10,000 people, deepening public anger even among the business elite." },
    { kind: "Assassination of a leading dissident journalist", intensity: 80, evidence: "The January 1978 assassination of newspaper editor Pedro Joaquin Chamorro, a prominent Somoza critic, triggered nationwide strikes and riots that widened the opposition far beyond the FSLN's guerrilla base." }
  ],
  actors: [
    { actorType: "vanguard", name: "The FSLN", description: "The Sandinista National Liberation Front, founded in 1961 by Carlos Fonseca and allies.", roleInArc: "Fought an intermittent guerrilla campaign for eighteen years before leading the final 1978-79 insurrection.", defected: false },
    { actorType: "old-regime", name: "Anastasio Somoza Debayle", description: "President of Nicaragua and commander of the National Guard.", roleInArc: "Fled Nicaragua in July 1979 as FSLN forces and allied insurgents closed in on Managua.", defected: false },
    { actorType: "religious-clergy", name: "Liberation theology clergy", description: "Catholic priests and lay organizers influenced by liberation theology.", roleInArc: "Provided organizing networks and moral legitimacy to the anti-Somoza movement in rural and poor urban communities.", defected: false },
    { actorType: "foreign-backer", name: "Cuba", description: "Cuba's government, which trained and armed FSLN fighters from the 1960s onward.", roleInArc: "Supplied material and ideological support that sustained FSLN operations through repeated setbacks.", defected: false },
    { actorType: "old-regime", name: "The National Guard", description: "Nicaragua's US-trained security force and the Somoza family's chief instrument of control.", roleInArc: "Remained loyal to Somoza almost to the very end, but collapsed once conscript morale broke in the final weeks of the 1979 offensive.", defected: true }
  ],
  tactics: [
    { tacticType: "guerrilla-warfare", description: "FSLN columns fought an intermittent rural and mountain campaign from the early 1960s, absorbing repeated defeats before building a sustainable base by the mid-1970s.", prominence: "primary" },
    { tacticType: "general-strike", description: "Business-sector strikes following Chamorro's 1978 assassination brought even Somoza's former commercial allies into open opposition.", prominence: "primary" },
    { tacticType: "urban-uprising", description: "Coordinated insurrections in Managua, Leon, and Esteli during the 1979 final offensive stretched the National Guard's forces past their breaking point.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Dynasty and earthquake corruption", tStart: 0.00, tEnd: 0.12, intensity: 50, reached: true, summary: "Four decades of Somoza rule and the diversion of 1972 earthquake relief funds erode support across Nicaraguan society, including the business elite.", keyEvents: ["FSLN founded, 1961", "Managua earthquake and relief corruption, 1972"] },
    { phase: "the-spark", label: "Chamorro's assassination", dateStart: "1978-01-10", tStart: 0.22, tEnd: 0.34, intensity: 75, reached: true, summary: "The assassination of newspaper editor Pedro Joaquin Chamorro triggers nationwide strikes and riots that widen anti-Somoza opposition far beyond the FSLN's existing base.", keyEvents: ["Chamorro assassinated, January 10, 1978", "Nationwide strikes and riots follow"] },
    { phase: "moderate-phase", label: "A broad coalition forms", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "Business associations, clergy, and opposition parties join the FSLN in a broad anti-Somoza front through 1978.", keyEvents: ["Business-sector strikes, 1978", "Broad opposition front forms"] },
    { phase: "dual-power", label: "Liberated zones expand", tStart: 0.48, tEnd: 0.60, intensity: 60, reached: true, summary: "FSLN-controlled territory expands through late 1978 and early 1979 even as Somoza's National Guard still holds Managua and the major cities.", keyEvents: ["FSLN territorial gains expand, 1978-79"] },
    { phase: "radical-phase", label: "The final offensive", dateStart: "1979-06-01", tStart: 0.60, tEnd: 0.72, intensity: 88, reached: true, summary: "A coordinated final offensive combines urban insurrection with FSLN's rural columns, and Somoza flees the country weeks later.", keyEvents: ["Final offensive begins, June 1979", "Somoza flees, July 17, 1979"] },
    { phase: "thermidor", label: "Coalition fractures and the Contra war", tStart: 0.84, tEnd: 0.92, intensity: 65, reached: true, summary: "The broad coalition that toppled Somoza splits over land, press, and economic policy through the 1980s, while US-backed Contra forces wage a decade-long insurgency against the new government.", keyEvents: ["Contra war begins, 1981", "Mixed-economy and press-policy disputes intensify through the 1980s"] }
  ],
  outcome: "ongoing-unresolved",
  militaryDefection: "partial",
  foreignIntervention: "material",
  durationDays: null,
  deathToll: "An estimated 30,000 to 50,000 killed in the 1978-79 insurrection alone; the subsequent 1980s Contra war killed a further estimated 30,000.",
  deathTollLow: 30000,
  deathTollHigh: 50000,
  regimeBefore: "personalist",
  regimeAfter: "unresolved",
  democratizationDelta: 1,
  successFactors: [
    { factorKey: "hybrid-tactics", label: "Combining guerrilla warfare with general strikes can outperform either alone", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Armed campaigns succeed in roughly 26% of historical cases versus 53% for nonviolent ones; hybrid campaigns pairing armed struggle with mass economic pressure can outperform either tactic alone", rationale: "Business-sector strikes after Chamorro's assassination brought pressure on Somoza from a constituency the FSLN's guerrilla campaign alone could never have reached.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-backing-tradeoff", label: "Heavy foreign backing to a challenger correlates with weaker post-victory consolidation", framework: "goldstone", status: "atypical", direction: "indeterminate", baseRate: "Heavy foreign material backing to a challenger correlates in the comparative literature with weaker post-victory democratic consolidation", rationale: "Cuban backing sustained FSLN operations through the 1960s and 70s, and the pattern arguably bears out in the 1990 electoral defeat and the later Ortega-era consolidation of power the new government underwent.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] },
    { factorKey: "broad-coalition-mobilization", label: "Uniting normally opposed social classes against a common target increases the odds of rapid collapse", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's comparative work finds that coalitions spanning class lines, not narrow single-class movements, more often produce rapid regime collapse", rationale: "The 1978 strikes brought commercial and professional Nicaraguans who had never supported the FSLN into the same anti-Somoza front as its guerrilla fighters.", sources: ["Skocpol, States and Social Revolutions (1979)"] }
  ],
  keyFigures: [
    { name: "Anastasio Somoza Debayle", role: "Deposed President of Nicaragua", born: 1925, died: 1980 },
    { name: "Carlos Fonseca", role: "Founder of the FSLN", born: 1936, died: 1976 },
    { name: "Daniel Ortega", role: "FSLN commander, later President of Nicaragua", born: 1945 },
    { name: "Violeta Chamorro", role: "Opposition candidate, won the 1990 presidential election", born: 1929 }
  ],
  legacyPoints: [
    "The FSLN's 1979 victory ended a Somoza family dynasty that had ruled Nicaragua for 43 years.",
    "The 1980s Contra war, backed by covert US funding, killed an estimated 30,000 Nicaraguans on top of the insurrection's own death toll.",
    "Violeta Chamorro's 1990 election victory marked one of the few instances of a revolutionary armed movement peacefully ceding power at the ballot box.",
    "Daniel Ortega's later return to the presidency through elections revived debate over how much of the original revolution's democratic promise survived its own founding generation's later consolidation of power."
  ],
  perspectives: [
    { id: "sandinista-founding", viewpoint: "Sandinista founding-generation view", viewpointType: "revolutionary", regionOrigin: "Nicaragua", narrative: "A popular armed movement ended dynastic dictatorship and delivered land and literacy gains to a population long excluded from both, even if its own later leadership drew criticism for consolidating power.", keyArguments: ["The FSLN united guerrilla fighters, clergy, and business elites against a common dynastic enemy", "Land reform and a 1980 literacy campaign reached millions of rural Nicaraguans within two years of victory", "The 1990 election loss demonstrated the movement's own willingness to accept a democratic verdict"], emphasized: ["the literacy campaign", "the 1990 peaceful transfer of power"], omitted: ["internal FSLN dissent over the Contra war's economic toll", "later criticism of Ortega-era power consolidation"], notableQuotes: [] },
    { id: "opposition-chamorro-era", viewpoint: "Opposition and Chamorro-era view", viewpointType: "moderate", regionOrigin: "Nicaragua", narrative: "The FSLN's economic mismanagement and a drawn-out Contra war exhausted a population that voted decisively for change in 1990, rejecting continued armed conflict and centralized economic control.", keyArguments: ["Hyperinflation and war exhaustion had devastated household incomes by the late 1980s", "The FSLN's own land expropriations alienated segments of its founding coalition", "Chamorro's 1990 victory reflected a broad desire to end both the war and one-party dominance"], emphasized: ["1980s economic collapse", "war fatigue among the electorate"], omitted: ["the scale of Somoza-era repression the revolution originally responded to", "the Sandinistas' later return to power via subsequent elections"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "cuban-revolution", targetTitle: "The Cuban Revolution", type: "inspired", description: "Cuban training, arms, and ideological example directly shaped the FSLN's guerrilla strategy from the 1960s onward." },
    { targetSlug: "chinese-revolution-1949", targetTitle: "The Chinese Communist Revolution", type: "parallel", description: "Both mobilized a rural guerrilla base against a personalist regime over a protracted, multi-decade campaign before final victory." }
  ],
  media: [],
  relatedRevoltSlugs: ["cuban-revolution", "chinese-revolution-1949"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "anti-apartheid",
  slug: "anti-apartheid",
  title: "The Anti-Apartheid Struggle",
  subtitle: "Forty-six years, and the vote finally reaches everyone",
  era: "people-power",
  region: "africa",
  country: "South Africa",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "1948-1994",
  dateStart: 1948,
  dateEnd: 1994,
  summary: "The National Party legislated apartheid into law in 1948. Decades of banned organizations, township uprisings, international sanctions, and a security-state crackdown followed before President F.W. de Klerk unbanned the ANC and released Nelson Mandela in 1990, opening four years of negotiation that produced South Africa's first fully multiracial election in 1994.",
  significance: "One of the longest sustained mass movements against institutionalized minority rule in modern history, and one of relatively few such struggles resolved through negotiated transition rather than civil war or the incumbent's outright military defeat.",
  grievances: [
    { kind: "Legislated racial segregation", intensity: 92, evidence: "The National Party's 1948 election victory began four decades of apartheid legislation classifying every South African by race and restricting where each group could live, work, and vote." },
    { kind: "Forced removals", intensity: 78, evidence: "The Group Areas Act and related laws forcibly relocated an estimated 3.5 million Black South Africans between 1960 and 1983 to racially designated townships and homelands." },
    { kind: "State violence against protest", intensity: 88, evidence: "Police killed 69 people at a peaceful pass-law protest in Sharpeville on March 21, 1960, and killed hundreds more, many of them students, during the June 1976 Soweto uprising." }
  ],
  actors: [
    { actorType: "vanguard", name: "The African National Congress", description: "South Africa's oldest liberation movement, founded in 1912, banned by the government from 1960 to 1990.", roleInArc: "Led the political campaign against apartheid from underground and exile for three decades before returning to legal politics in 1990.", defected: false },
    { actorType: "military-defectors", name: "Umkhonto we Sizwe", description: "The ANC's armed wing, founded in 1961 after the Sharpeville massacre closed off purely nonviolent avenues.", roleInArc: "Carried out a limited sabotage campaign against infrastructure targets, deliberately avoiding civilian casualties in its early years.", defected: false },
    { actorType: "organized-labor", name: "COSATU-aligned unions", description: "The Congress of South African Trade Unions, formed in 1985.", roleInArc: "Organized major stayaway strikes through the 1980s that combined with township unrest to raise the economic cost of continued apartheid rule.", defected: false },
    { actorType: "students-youth", name: "Soweto students", description: "Secondary school students who protested a 1976 policy mandating Afrikaans as a language of instruction.", roleInArc: "Their June 16, 1976 march, met with police gunfire, radicalized a new generation and drew international attention to apartheid's violence.", defected: false },
    { actorType: "old-regime", name: "The National Party government", description: "South Africa's ruling party from 1948 to 1994.", roleInArc: "Under F.W. de Klerk, unbanned the ANC and other liberation movements in February 1990 and negotiated a four-year transition to majority rule.", defected: false }
  ],
  tactics: [
    { tacticType: "boycott-noncooperation", description: "An international sanctions and divestment campaign, building from the 1960s and accelerating through the 1980s, pressured the South African economy and its foreign investors.", prominence: "primary" },
    { tacticType: "mass-demonstration", description: "The 1952 Defiance Campaign and the 1983-founded United Democratic Front organized mass civil disobedience and township protest through the 1980s.", prominence: "primary" },
    { tacticType: "armed-insurgency", description: "Umkhonto we Sizwe's sabotage campaign, beginning in 1961, targeted infrastructure rather than civilians, remaining limited in scale relative to the mass civil resistance campaign.", prominence: "secondary" },
    { tacticType: "general-strike", description: "Coordinated stayaways organized by UDF-aligned unions through the 1980s repeatedly shut down major industrial centers.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "Apartheid legislated", tStart: 0.00, tEnd: 0.12, intensity: 45, reached: true, summary: "The National Party's 1948 victory begins four decades of racial legislation as the ANC organizes underground resistance.", keyEvents: ["National Party wins the 1948 election", "Population Registration Act, 1950"] },
    { phase: "the-spark", label: "Sharpeville", dateStart: "1960-03-21", tStart: 0.22, tEnd: 0.34, intensity: 80, reached: true, summary: "Police kill 69 peaceful protesters at Sharpeville, and the government bans the ANC and PAC within weeks, closing off legal political opposition.", keyEvents: ["Sharpeville massacre, March 21, 1960", "ANC and PAC banned, April 1960"] },
    { phase: "moderate-phase", label: "Underground reorganization", tStart: 0.34, tEnd: 0.48, intensity: 50, reached: true, summary: "The ANC reorganizes underground and in exile, and Umkhonto we Sizwe begins a limited sabotage campaign against infrastructure targets.", keyEvents: ["Umkhonto we Sizwe founded, 1961", "Rivonia Trial sentences Mandela to life imprisonment, 1964"] },
    { phase: "dual-power", label: "Township uprisings and sanctions", tStart: 0.48, tEnd: 0.60, intensity: 65, reached: true, summary: "The 1976 Soweto uprising and the 1983-founded United Democratic Front build sustained township resistance as an international sanctions campaign gathers pace.", keyEvents: ["Soweto uprising, June 1976", "United Democratic Front founded, 1983", "International sanctions expand through the 1980s"] },
    { phase: "radical-phase", label: "States of emergency", tStart: 0.60, tEnd: 0.72, intensity: 78, reached: true, summary: "The government declares repeated states of emergency between 1985 and 1989 as township unrest, strikes, and security force killings escalate together.", keyEvents: ["National state of emergency declared, 1986", "Township unrest and security crackdowns intensify, 1985-89"] },
    { phase: "thermidor", label: "Unbanning and release", dateStart: "1990-02-02", tStart: 0.84, tEnd: 0.92, intensity: 55, reached: true, summary: "President de Klerk unbans the ANC and other liberation movements and releases Nelson Mandela after 27 years, opening formal negotiations.", keyEvents: ["ANC unbanned, February 2, 1990", "Mandela released, February 11, 1990"] },
    { phase: "consolidation", label: "The 1994 election", dateStart: "1994-04-27", tStart: 0.92, tEnd: 1.00, intensity: 50, reached: true, summary: "South Africa holds its first fully multiracial election, and Nelson Mandela becomes president.", keyEvents: ["First multiracial election, April 27, 1994", "Mandela inaugurated, May 10, 1994"] }
  ],
  outcome: "consolidated-democracy",
  militaryDefection: "none",
  foreignIntervention: "material",
  peakParticipationPct: null,
  peakParticipationDisplay: "Hundreds of thousands joined 1980s township stayaways and United Democratic Front protests at the campaign's peak, sustained over years rather than concentrated in a single mobilization",
  crossedParticipationThreshold: null,
  durationDays: null,
  deathToll: "Precise figures remain contested and incomplete; well-documented single incidents include Sharpeville's 69 dead in 1960 and Soweto's estimated 176 to over 700 dead in 1976, with security force killings continuing through the 1980s state-of-emergency years.",
  deathTollLow: 5000,
  deathTollHigh: 21000,
  regimeBefore: "other",
  regimeAfter: "democracy",
  democratizationDelta: 3,
  successFactors: [
    { factorKey: "hybrid-pressure", label: "Combining international boycott pressure with domestic mass mobilization outperforms either channel alone", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Hybrid campaigns combining international economic pressure with domestic mass mobilization succeed more often than either channel alone in cross-national comparative work", rationale: "The 1980s combination of township stayaways, UDF organizing, and international divestment applied pressure the government could not resolve by force alone.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "elite-fracture", label: "A split within the ruling party's reform-minded faction typically precedes negotiation over suppression", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Skocpol's model finds a split within the ruling elite's reform-minded faction a frequent precondition for negotiated, rather than violently suppressed, transition", rationale: "De Klerk's own National Party concluded by 1990 that the security-state approach could not be sustained indefinitely, opening formal negotiations rather than escalating repression further.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "sanctions-pressure-on-incumbent", label: "Sustained international pressure aimed at an incumbent can push it toward negotiated exit", framework: "goldstone", status: "confirmed", direction: "favors-movement", baseRate: "Sustained international material pressure aimed at an incumbent regime, rather than backing given to an armed challenger, correlates with pushing entrenched minority-rule regimes toward negotiated exit", rationale: "Divestment and trade sanctions through the 1980s raised the economic cost of continued apartheid rule enough to shift calculations inside the National Party itself.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Nelson Mandela", role: "ANC leader, first president of democratic South Africa", born: 1918, died: 2013 },
    { name: "Desmond Tutu", role: "Anglican archbishop and anti-apartheid campaigner", born: 1931, died: 2021 },
    { name: "F.W. de Klerk", role: "Last National Party president, negotiated the transition", born: 1936, died: 2021 },
    { name: "Steve Biko", role: "Black Consciousness Movement leader, died in police custody", born: 1946, died: 1977 }
  ],
  legacyPoints: [
    "The April 1994 election drew over 19 million voters in South Africa's first fully multiracial ballot.",
    "The Truth and Reconciliation Commission, convened in 1996, became a widely studied model for post-conflict accountability processes elsewhere.",
    "Apartheid-era legislation was dismantled through four years of negotiated transition beginning in 1990 rather than through civil war.",
    "South Africa's post-1994 constitution is frequently cited among the most rights-expansive in the world."
  ],
  perspectives: [
    { id: "anc-liberation", viewpoint: "ANC liberation movement view", viewpointType: "revolutionary", regionOrigin: "South Africa", narrative: "Decades of mass and international struggle finally dismantled institutionalized racial rule that legal channels alone could never have reached.", keyArguments: ["Legal opposition was closed off entirely once the ANC was banned in 1960", "Sustained township organizing through the 1980s made the country increasingly difficult to govern under apartheid law", "International sanctions pressure combined with domestic resistance to bring the National Party to the negotiating table"], emphasized: ["the scale and duration of the mass movement", "international solidarity"], omitted: ["internal ANC debate over the pace and scope of the armed struggle", "tensions within the broader liberation movement itself"], notableQuotes: [{ text: "It always seems impossible until it is done.", speaker: "Nelson Mandela", context: "Widely cited reflection on the anti-apartheid struggle" }] },
    { id: "afrikaner-nationalist-retrospective", viewpoint: "Afrikaner nationalist retrospective view", viewpointType: "counter-revolutionary", regionOrigin: "South Africa", narrative: "A negotiated relinquishing of power shaped by concerns about majority rule's economic and security consequences, a process some who backed reform still view with ambivalence decades later.", keyArguments: ["De Klerk's government chose negotiation while it still held substantial security and economic leverage, not after total collapse", "The negotiated settlement included constitutional protections its framers saw as essential trade-offs", "The transition's relative peacefulness reflected a deliberate, contested choice by reform-minded Afrikaner leadership"], emphasized: ["the negotiated, non-collapse nature of the transition"], omitted: ["the decades of violence and legal repression that preceded the 1990 negotiations", "township death tolls under state-of-emergency rule"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "carnation-revolution", targetTitle: "The Carnation Revolution", type: "parallel", description: "Both produced negotiated rather than violently contested transitions, though Portugal's took a single day and South Africa's took decades." },
    { targetSlug: "people-power-1986", targetTitle: "People Power 1986", type: "parallel", description: "Both combined international pressure with sustained domestic mass mobilization to force a negotiated exit from entrenched rule." }
  ],
  media: [],
  relatedRevoltSlugs: ["carnation-revolution", "people-power-1986"],
  relatedHistorySlugs: ["apartheid"],
  published: true
},
{
  id: "euromaidan",
  slug: "euromaidan",
  title: "Euromaidan",
  subtitle: "Three months on the square end a presidency and open a war",
  era: "square-revolutions",
  region: "europe",
  country: "Ukraine",
  revoltType: "democratic-uprising",
  status: "concluded",
  dateDisplay: "November 2013 - February 2014",
  dateStart: 2013,
  dateEnd: 2014,
  summary: "President Viktor Yanukovych's last-minute refusal to sign a long-negotiated EU association agreement brought students onto Kyiv's central square on November 21, 2013. A violent police crackdown nine days later turned a policy protest into a mass occupation that lasted three months, ending in February 2014 with roughly 100 dead in the square's final days and Yanukovych's flight to Russia.",
  significance: "A rapid, security-force-defection-driven collapse of an elected government that nonetheless failed to produce a stable, uncontested outcome: Russia annexed Crimea within weeks and backed a separatist war in the Donbas that same spring.",
  grievances: [
    { kind: "Reversal of the EU association agreement", intensity: 80, evidence: "Yanukovych announced on November 21, 2013 that Ukraine would not sign the EU Association Agreement after months of negotiation, days before it was due to be signed in Vilnius." },
    { kind: "Violent crackdown on student protesters", intensity: 85, evidence: "Berkut riot police beat student demonstrators camped on Maidan Nezalezhnosti before dawn on November 30, 2013, injuring dozens and dramatically widening the protest movement." },
    { kind: "Entrenched high-level corruption", intensity: 70, evidence: "Yanukovych's private Mezhyhirya estate, revealed in detail after his flight, was valued by investigators in the hundreds of millions of dollars, a stark contrast to his stated presidential salary." },
    { kind: "Anti-protest legislation", intensity: 65, evidence: "A package of laws passed on January 16, 2014 criminalized many forms of protest activity, sharply escalating tensions rather than deterring the demonstrations." }
  ],
  actors: [
    { actorType: "students-youth", name: "The first Maidan protesters", description: "Students and young professionals who gathered on Kyiv's Independence Square the night of November 21, 2013.", roleInArc: "Initiated the protest movement in response to Yanukovych's EU agreement reversal, before the November 30 crackdown widened it into a mass movement.", defected: false },
    { actorType: "masses", name: "The Maidan encampment", description: "A self-organized protest camp on Independence Square that grew to an estimated 500,000 to 800,000 at its December 2013 peak.", roleInArc: "Sustained a three-month occupation with its own medical, security, and supply structures functioning alongside a paralyzed state authority.", defected: false },
    { actorType: "security-forces", name: "Berkut riot police", description: "Ukraine's special police force, later disbanded after the revolution.", roleInArc: "Carried out repeated violent clearance attempts, including the fatal shootings of February 18-20, 2014, before the unit was dissolved.", defected: false },
    { actorType: "old-regime", name: "Viktor Yanukovych", description: "President of Ukraine since 2010.", roleInArc: "Fled Kyiv on February 22, 2014, as police and security units began refusing orders to use lethal force, and was removed by parliamentary vote the same day.", defected: false },
    { actorType: "foreign-intervener", name: "Russia", description: "Ukraine's neighboring power and Yanukovych's chief external backer.", roleInArc: "Annexed Crimea within weeks of Yanukovych's fall and backed separatist forces in the Donbas that same spring.", defected: false }
  ],
  tactics: [
    { tacticType: "occupation", description: "The Maidan encampment held central Kyiv for three months, building its own barricades, kitchens, and medical stations.", prominence: "primary" },
    { tacticType: "mass-demonstration", description: "Crowds estimated between 500,000 and 800,000 filled Independence Square at the movement's December 2013 peak.", prominence: "primary" },
    { tacticType: "civil-disobedience", description: "Protesters built barricades and organized self-defense units to resist repeated riot police clearance attempts through January and February 2014.", prominence: "secondary" }
  ],
  resistanceType: "hybrid",
  phases: [
    { phase: "old-regime-crisis", label: "The EU deal stalls", tStart: 0.00, tEnd: 0.12, intensity: 40, reached: true, summary: "Months of negotiation over the EU Association Agreement culminate in Yanukovych's abrupt reversal, straining a policy path his government had pursued for years.", keyEvents: ["EU Association Agreement negotiations near completion, 2013", "Yanukovych signals reversal, November 2013"] },
    { phase: "the-spark", label: "The first protests", dateStart: "2013-11-21", tStart: 0.22, tEnd: 0.34, intensity: 60, reached: true, summary: "Yanukovych's announcement that Ukraine will not sign the EU agreement draws students onto Independence Square the same night.", keyEvents: ["Yanukovych announces the EU agreement will not be signed, November 21, 2013", "First Maidan protests begin that night"] },
    { phase: "moderate-phase", label: "Peaceful encampment", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "The protest camp grows through December into a sustained, largely peaceful occupation following the November 30 police crackdown that widened public outrage.", keyEvents: ["Berkut crackdown on protesters, November 30, 2013", "Crowds swell to peak size, December 2013"] },
    { phase: "dual-power", label: "Self-organization amid paralysis", tStart: 0.48, tEnd: 0.60, intensity: 60, reached: true, summary: "Maidan's own security, medical, and supply structures function alongside an increasingly paralyzed state authority through January 2014.", keyEvents: ["Anti-protest laws passed, January 16, 2014", "Maidan self-defense units organize"] },
    { phase: "radical-phase", label: "The Heavenly Hundred", dateStart: "2014-02-18", tStart: 0.60, tEnd: 0.72, intensity: 95, reached: true, summary: "Clashes between February 18 and 20, 2014 leave roughly 100 protesters and police dead in the square, the deadliest days of the entire occupation.", keyEvents: ["Violent clashes begin, February 18, 2014", "Roughly 100 killed over three days, February 18-20, 2014"] },
    { phase: "consolidation", label: "Yanukovych flees", dateStart: "2014-02-22", tStart: 0.92, tEnd: 1.00, intensity: 60, reached: true, summary: "Yanukovych flees Kyiv on February 22, 2014, and parliament votes to remove him from office the same day, installing an interim government.", keyEvents: ["Yanukovych flees Kyiv, February 22, 2014", "Parliament votes to remove Yanukovych, February 22, 2014"] }
  ],
  outcome: "ongoing-unresolved",
  militaryDefection: "partial",
  foreignIntervention: "direct-military",
  peakParticipationPct: 1.8,
  peakParticipationDisplay: "An estimated 500,000 to 800,000 gathered in Kyiv's Independence Square at peak in December 2013, roughly 1 to 2 percent of Ukraine's population on a single day",
  crossedParticipationThreshold: null,
  durationDays: 93,
  deathToll: "Roughly 100 protesters, along with a smaller number of police, were killed in Kyiv between November 2013 and February 2014, the great majority in the final three days of clashes.",
  deathTollLow: 100,
  deathTollHigh: 130,
  regimeBefore: "democracy",
  regimeAfter: "unresolved",
  democratizationDelta: null,
  successFactors: [
    { factorKey: "security-force-fracture", label: "Security force refusal to fire is the strongest single predictor of rapid collapse", framework: "chenoweth", status: "confirmed", direction: "favors-movement", baseRate: "Security force defection or refusal to fire remains the single strongest predictor of rapid regime collapse across the comparative record", rationale: "Police and some military units refused orders to use lethal force against protesters in the final days, removing Yanukovych's last coercive option and precipitating his flight within hours.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "nonviolent-then-violent-escalation", label: "A mostly peaceful campaign that escalates late can still remove an incumbent without settling the outcome", framework: "chenoweth", status: "partial", direction: "indeterminate", baseRate: "Nonviolent-leaning campaigns succeed roughly twice as often as armed ones, 53 percent versus 26 percent, though the finding concerns durable outcomes, not merely toppling an incumbent", rationale: "Euromaidan stayed overwhelmingly peaceful for three months before a violent final escalation, and while it succeeded in removing Yanukovych within days of that escalation, the post-victory outcome was immediately contested rather than settled.", sources: ["Chenoweth and Stephan, Why Civil Resistance Works (2011)"] },
    { factorKey: "foreign-counter-intervention", label: "Foreign military intervention against a successful uprising can reverse or freeze its gains", framework: "goldstone", status: "confirmed", direction: "favors-regime", baseRate: "Direct foreign military intervention against a successful uprising's outcome can reverse or freeze its gains even after the incumbent has already fallen", rationale: "Russia's annexation of Crimea within weeks and its backing of separatist war in the Donbas the same spring prevented the post-Yanukovych government from consolidating control over the whole country.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] }
  ],
  keyFigures: [
    { name: "Viktor Yanukovych", role: "Deposed President of Ukraine", born: 1950 },
    { name: "Petro Poroshenko", role: "Businessman, later President of Ukraine", born: 1965 },
    { name: "Vitali Klitschko", role: "Opposition leader, later Mayor of Kyiv", born: 1971 },
    { name: "The Heavenly Hundred", role: "Collective name for the protesters killed in the square's final days" }
  ],
  legacyPoints: [
    "Roughly 100 protesters and a smaller number of police died in central Kyiv between February 18 and 20, 2014, remembered in Ukraine as the Heavenly Hundred.",
    "The crackdown accelerated rather than deterred Yanukovych's collapse, which came within 72 hours of the square's deadliest violence.",
    "Russia annexed Crimea within weeks and backed separatist war in the Donbas that same spring, opening a conflict that continued for years afterward.",
    "The events reoriented Ukrainian national identity and policy decisively toward European and NATO integration, a trajectory still shaping the region years later."
  ],
  perspectives: [
    { id: "pro-european-civic", viewpoint: "Pro-European civic view", viewpointType: "movement", regionOrigin: "Ukraine", narrative: "A democratic reassertion of national sovereignty and European orientation against a corrupt, increasingly authoritarian government.", keyArguments: ["Yanukovych's reversal on the EU agreement followed months of apparent negotiation, reading as a last-minute capitulation to external pressure", "The Mezhyhirya estate's scale symbolized entrenched corruption at the top of government", "The movement's self-organized, largely peaceful character over three months reflected broad civic rather than narrow factional support"], emphasized: ["the EU agreement reversal", "the Mezhyhirya revelations"], omitted: ["divisions within Ukraine over EU versus Russia orientation in eastern and southern regions", "the composition of far-right groups within the broader protest movement"], notableQuotes: [] },
    { id: "russian-state-aligned", viewpoint: "Russian state-aligned view", viewpointType: "regime", regionOrigin: "Russia", narrative: "Frames the events as an externally encouraged, unconstitutional removal of an elected president, the basis Moscow cited for its subsequent actions in Crimea and the Donbas.", keyArguments: ["Yanukovych was removed by a parliamentary vote taken under street pressure rather than through a constitutional process like impeachment", "Western governments' public support for the protest movement is presented as direct interference in Ukrainian internal politics", "The rapid change of government is portrayed as illegitimate given the circumstances of Yanukovych's removal"], emphasized: ["the manner of Yanukovych's removal from office", "Western statements of support for the protesters"], omitted: ["the scale of the killings in the square's final days", "Yanukovych's own reversal of a long-negotiated agreement that triggered the protests"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "people-power-1986", targetTitle: "People Power 1986", type: "parallel", description: "Both toppled an incumbent through a sustained mass occupation of a central public space rather than through elections or armed conquest." },
    { targetSlug: "fall-of-communism-1989", targetTitle: "The Fall of Communism", type: "shared-repertoire", description: "Both relied on mass peaceful occupation of central squares as the core tactic, even where outcomes ultimately diverged." }
  ],
  media: [],
  relatedRevoltSlugs: ["people-power-1986", "fall-of-communism-1989"],
  relatedHistorySlugs: [],
  published: true
},
{
  id: "latin-american-independence",
  slug: "latin-american-independence",
  title: "The Spanish American Wars of Independence",
  subtitle: "Napoleon topples a king in Madrid, and a continent stops asking Spain's permission",
  era: "atlantic",
  region: "americas",
  country: "Spanish America (Venezuela, Colombia, Ecuador, Peru, Bolivia, Argentina, Chile, Mexico, and beyond)",
  revoltType: "anticolonial",
  status: "concluded",
  dateDisplay: "1808-1826",
  dateStart: 1808,
  dateEnd: 1826,
  summary: "Napoleon's 1808 invasion of Spain and imposition of his brother Joseph Bonaparte as king stripped Madrid of the authority its American colonies had always answered to. Creole-led juntas formed across the viceroyalties claiming to rule in the exiled king's name, then declared outright independence, and two decades of campaigning under Simon Bolivar and Jose de San Martin produced more than a dozen new republics by 1826.",
  significance: "The dismantling, within a single generation, of nearly the entire Spanish American empire, a process driven as much by Spain's own metropolitan collapse as by any single military campaign, and one that left the new republics with independence but, in most cases, decades of subsequent civil conflict.",
  grievances: [
    { kind: "Loss of Spanish royal legitimacy", intensity: 75, evidence: "Napoleon's 1808 invasion of Spain and the forced abdication of Ferdinand VII in favor of Joseph Bonaparte left the American colonies without a legitimate king to answer to, opening the legal argument for local self-rule." },
    { kind: "Exclusion of creole elites from senior office", intensity: 68, evidence: "Colonial administrative and church posts above a certain rank were reserved by policy for peninsulares born in Spain, regardless of a creole candidate's wealth or education." },
    { kind: "Bourbon trade restrictions", intensity: 60, evidence: "Colonial trade was legally restricted to Spain alone for most of the eighteenth century, and Bourbon-era tax increases in the decades before 1808 had already generated repeated local unrest." },
    { kind: "Caste-based legal hierarchy", intensity: 55, evidence: "The casta system assigned differentiated legal rights by racial classification, constraining the political and economic standing of mixed-race, indigenous, and enslaved populations throughout the viceroyalties." }
  ],
  actors: [
    { actorType: "vanguard", name: "Simon Bolivar", description: "Venezuelan-born creole officer and political leader.", roleInArc: "Led campaigns across present-day Venezuela, Colombia, Ecuador, Peru, and Bolivia, and envisioned a unified Gran Colombia that did not outlast his own lifetime.", defected: false },
    { actorType: "vanguard", name: "Jose de San Martin", description: "Argentine-born officer trained in the Spanish army before joining the independence cause.", roleInArc: "Led the crossing of the Andes and the liberation campaigns in Argentina, Chile, and Peru before ceding leadership of the Peruvian campaign to Bolivar in 1822.", defected: false },
    { actorType: "old-regime", name: "Royalist Spanish forces", description: "Troops loyal to the Spanish crown, reinforced from Spain after Ferdinand VII's 1814 restoration.", roleInArc: "Fought a prolonged and often brutal counterinsurgency, particularly in Venezuela and Peru, before the final defeats at Ayacucho in 1824 and Callao in 1826.", defected: false },
    { actorType: "masses", name: "Llanero cavalry and mixed-race soldiers", description: "Plains horsemen and soldiers of mixed racial background who formed the bulk of Bolivar's fighting force in Venezuela.", roleInArc: "Provided the decisive manpower for Bolivar's Venezuelan and Colombian campaigns, often under promises of legal equality only partially honored after independence.", defected: false },
    { actorType: "foreign-backer", name: "British volunteers and merchants", description: "British Legion volunteers and arms merchants who supported the independence campaigns.", roleInArc: "Supplied weapons, loans, and several thousand volunteer soldiers who fought alongside Bolivar's armies.", defected: false }
  ],
  tactics: [
    { tacticType: "armed-insurgency", description: "Continental campaigns and set-piece battles, including Boyaca in 1819 and Ayacucho in 1824, decided control of entire viceroyalties.", prominence: "primary" },
    { tacticType: "guerrilla-warfare", description: "Llanero irregular cavalry raids sustained the Venezuelan independence campaign through years when conventional forces could not hold territory.", prominence: "primary" },
    { tacticType: "parallel-institutions", description: "Creole-led juntas formed in Caracas, Buenos Aires, and Bogota in 1810, initially claiming to govern in the exiled king's name before moving to outright independence.", prominence: "secondary" }
  ],
  resistanceType: "armed",
  phases: [
    { phase: "old-regime-crisis", label: "Madrid falls", dateStart: "1808-05-02", tStart: 0.00, tEnd: 0.12, intensity: 55, reached: true, summary: "Napoleon's invasion of Spain and the forced abdication of Ferdinand VII strip the American colonies of a legitimate king to answer to.", keyEvents: ["Napoleon invades Spain, 1808", "Joseph Bonaparte installed as king, 1808"] },
    { phase: "the-spark", label: "The juntas form", dateStart: "1810-04-19", tStart: 0.22, tEnd: 0.34, intensity: 60, reached: true, summary: "Creole-led juntas form across the viceroyalties in 1810, claiming authority in the exiled king's name while local governance slips from Madrid's control.", keyEvents: ["Caracas junta formed, April 19, 1810", "Buenos Aires and Bogota juntas formed, 1810"] },
    { phase: "moderate-phase", label: "Governing in the king's name", tStart: 0.34, tEnd: 0.48, intensity: 55, reached: true, summary: "The juntas govern nominally in Ferdinand VII's name through 1810 and 1811, a legal fiction that thins as fighting with royalist forces spreads.", keyEvents: ["Venezuela's first declaration of independence, July 5, 1811"] },
    { phase: "radical-phase", label: "The Admirable Campaign", tStart: 0.60, tEnd: 0.72, intensity: 80, reached: true, summary: "Formal independence declarations and years of campaign warfare follow, including Bolivar's 1813 Admirable Campaign into Venezuela.", keyEvents: ["Bolivar's Admirable Campaign, 1813", "War to the Death decree issued, 1813"] },
    { phase: "terror-virtue", label: "Restoration and reconquest", tStart: 0.72, tEnd: 0.84, intensity: 75, reached: true, summary: "Ferdinand VII's 1814 restoration to the Spanish throne brings a reinforced royalist reconquest and brutal reprisals on both sides through the following years.", keyEvents: ["Ferdinand VII restored, 1814", "Royalist reconquest of Venezuela and New Granada, 1815-16"] },
    { phase: "consolidation", label: "Ayacucho and independence", dateStart: "1824-12-09", tStart: 0.92, tEnd: 1.00, intensity: 60, reached: true, summary: "Bolivar and San Martin's converging campaigns culminate at Ayacucho in December 1824, and the last royalist stronghold at Callao surrenders in 1826.", keyEvents: ["Battle of Ayacucho, December 9, 1824", "Callao surrenders, January 1826"] }
  ],
  outcome: "independence",
  militaryDefection: "partial",
  foreignIntervention: "material",
  durationDays: 6300,
  deathToll: "Estimates run into the hundreds of thousands across two decades of campaigning and reprisal, though comprehensive figures remain imprecise given the number of separate theaters involved.",
  deathTollLow: 200000,
  deathTollHigh: 600000,
  regimeBefore: "colonial",
  regimeAfter: "democracy",
  democratizationDelta: 2,
  successFactors: [
    { factorKey: "incumbent-metropolitan-crisis", label: "Collapse of the incumbent's metropolitan capacity, not challenger tactics alone, decided the outcome", framework: "skocpol", status: "confirmed", direction: "favors-movement", baseRate: "Incumbent state capacity collapse at the metropole is frequently the decisive variable in colonial independence outcomes", rationale: "Spain's own occupation by Napoleon and later civil conflict between liberals and absolutists left it with dwindling capacity to reinforce or resupply its American armies for most of the two decades of fighting.", sources: ["Skocpol, States and Social Revolutions (1979)"] },
    { factorKey: "foreign-material-support", label: "Foreign material and financial backing correlates with independence success but not reliably with stable institutions after", framework: "goldstone", status: "partial", direction: "indeterminate", baseRate: "Foreign material and financial backing correlates with independence success though not reliably with stable post-victory institutions", rationale: "British arms sales, loans, and volunteer legions materially aided Bolivar's campaigns, yet most of the resulting republics endured decades of civil war and caudillo rule after 1826 rather than immediate stability.", sources: ["Goldstone, Revolutions: A Very Short Introduction (2014)"] },
    { factorKey: "broad-multiclass-mobilization", label: "Mobilization spanning multiple social classes expands a challenger's available manpower", framework: "tilly", status: "confirmed", direction: "favors-movement", baseRate: "Mobilization spanning multiple social classes, not narrow elite-led rebellion alone, expands a challenger's available manpower and resource base", rationale: "Bolivar's Venezuelan campaigns depended heavily on llanero cavalry and mixed-race soldiers, a far broader coalition than the creole elite alone could have fielded.", sources: ["Tilly, From Mobilization to Revolution (1978)"] }
  ],
  keyFigures: [
    { name: "Simon Bolivar", role: "Leader of the northern independence campaigns", born: 1783, died: 1830 },
    { name: "Jose de San Martin", role: "Leader of the southern independence campaigns", born: 1778, died: 1850 },
    { name: "Miguel Hidalgo", role: "Priest who launched Mexico's independence movement", born: 1753, died: 1811 },
    { name: "Bernardo O'Higgins", role: "Leader of Chile's independence movement", born: 1778, died: 1842 }
  ],
  legacyPoints: [
    "The wars produced more than a dozen new republics across the hemisphere within two decades, ending three centuries of Spanish colonial rule outside Cuba and Puerto Rico.",
    "Bolivar's vision of a unified Gran Colombia collapsed into separate Venezuela, Colombia, and Ecuador by 1830, within a decade of independence.",
    "Most new states adopted republican constitutions while retaining much of the old casta-era racial hierarchy in practice for generations afterward.",
    "The wars cemented caudillo militarism as the dominant post-independence political pattern across much of the region for most of the nineteenth century."
  ],
  perspectives: [
    { id: "bolivarian-liberationist", viewpoint: "Bolivarian liberationist view", viewpointType: "revolutionary", regionOrigin: "Venezuela and Colombia", narrative: "A continental project of unified American self-rule, cut short by regional rivalry and the same elite fragmentation that had once served the independence cause.", keyArguments: ["Bolivar's writings explicitly argued for continental unity as a defense against renewed European intervention", "The rapid collapse of Gran Colombia after 1830 vindicated his own warnings about regional factionalism", "Broad participation by llanero and mixed-race soldiers reflected a genuinely popular, not merely elite, independence movement"], emphasized: ["Bolivar's unity project", "broad military participation"], omitted: ["the limited practical extension of legal equality to non-white soldiers after victory", "the civil wars that followed independence in nearly every new republic"], notableQuotes: [] },
    { id: "royalist-loyalist-retrospective", viewpoint: "Royalist and loyalist retrospective view", viewpointType: "counter-revolutionary", regionOrigin: "Spain", narrative: "The wars fractured a functioning, if imperfect, multi-ethnic imperial order into a series of unstable and often authoritarian successor states that took generations to approach the administrative capacity Spanish rule had provided.", keyArguments: ["The viceroyalties had functioning administrative and legal institutions that many successor states struggled to replicate for decades", "Independence-era warfare and subsequent caudillo conflicts caused substantial loss of life and economic disruption", "Several new republics experienced political instability lasting through most of the nineteenth century"], emphasized: ["post-independence civil conflict", "administrative disruption"], omitted: ["the exclusion of creole elites and the caste system's constraints under colonial rule", "the extended decline of Spain's own capacity that made reconquest impossible regardless of local administration"], notableQuotes: [] }
  ],
  connections: [
    { targetSlug: "haitian-revolution", targetTitle: "The Haitian Revolution", type: "inspired", description: "Haiti's 1804 independence, achieved years earlier through slave revolt against a European power, unsettled and inspired Spanish American elites in different measure." },
    { targetSlug: "american-revolution", targetTitle: "The American Revolution", type: "provided-model", description: "Republican constitutional templates and revolutionary rhetoric from the United States circulated widely among Spanish American independence leaders." }
  ],
  media: [],
  relatedRevoltSlugs: ["haitian-revolution", "american-revolution"],
  relatedHistorySlugs: ["bolivarian-revolutions"],
  published: true
}
];
