/* ===========================================================================
   void --history — Shared Hooks & CTAs
   Story-specific, "Arrive Late, Leave Early" copy.
   Imported by both HistoryLanding (timeline cards) and EventDetail (Stage 2).
   =========================================================================== */

/* ── Hooks — the "crack" for each event ── */
export const HOOKS: Record<string, string> = {
  "partition-of-india":
    "A lawyer who\u2019d never been to India drew the border in five weeks. 15 million crossed it.",
  "hiroshima-nagasaki":
    "66,000 dead in 8.5 seconds. Seven of eight five-star American generals said it wasn\u2019t necessary.",
  "rwandan-genocide":
    "The UN had a fax warning them. They reduced their force from 2,500 to 270. 800,000 died in 100 days.",
  "scramble-for-africa":
    "Fourteen nations met in a Berlin conference room in 1884. Not one African was invited. By 1914, Europeans controlled 90% of the continent.",
  "opium-wars":
    "Britain went to war because China burned 20,000 chests of opium. The peace treaty ceded Hong Kong for 156 years.",
  "french-revolution":
    "A Parisian laborer spent 88% of his wages on bread. On July 14, the crowd took 30,000 muskets. The Bastille fell by dinner.",
  "creation-of-israel-nakba":
    "On May 14, 1948, one people declared independence. On May 15, 750,000 of another people became refugees. Same land.",
  "trail-of-tears":
    "The Supreme Court ruled in their favor. The president ignored the ruling. 60,000 walked. 4,000 never arrived.",
  "fall-of-berlin-wall":
    "At 6:53 p.m. on November 9, 1989, a spokesman misread a memo on live television. The Wall fell by midnight.",
  "transatlantic-slave-trade":
    "12.5 million embarked. 10.7 million survived the crossing. The database lists 36,000 individual voyages.",
  "armenian-genocide":
    "The American ambassador cabled Washington: \u2018Race extermination.\u2019 Raphael Lemkin later coined a word for it \u2014 \u2018genocide.\u2019",
  "holodomor":
    "Gareth Jones walked through Ukrainian villages counting bodies. Walter Duranty won a Pulitzer for saying there was no famine.",
  "congo-free-state":
    "Leopold II never visited the Congo. His agents collected severed hands as proof of productivity. The population fell by 10 million.",
  "cambodian-genocide":
    "Tuol Sleng processed 17,000 prisoners. Seven survived. The guards photographed every face before killing them.",
  "tiananmen-square":
    "On June 5, 1989, a man with two shopping bags stopped a column of tanks. No one knows his name. China erased the photograph.",
  "peloponnesian-war":
    "Athens told the island of Melos: submit or die. Melos chose neutrality. Athens killed every man and enslaved the women and children.",
  "mongol-conquest-baghdad":
    "The Tigris ran black with ink from a million manuscripts. Then Hulagu built the world\u2019s finest observatory with the looted books.",
  "haitian-revolution":
    "Dessalines tore the white from the French tricolor. The flag that remained was the first made by formerly enslaved people who\u2019d defeated a European army.",
  "meiji-restoration":
    "Japan watched China lose two wars to Britain. In 30 years, a feudal archipelago built railways, a constitution, and a navy that sank the Russian fleet.",
  "treaty-of-waitangi":
    "The English text said \u2018sovereignty.\u2019 The Maori text said \u2018governance.\u2019 Hone Heke cut down the British flagpole four times to make the point.",
  "bolivarian-revolutions":
    "Bol\u00edvar sailed to Haiti after his defeat. P\u00e9tion gave him ships and soldiers in exchange for one promise: free the enslaved. Bol\u00edvar partially broke it.",
  "ashoka-maurya-empire":
    "He carved the body count into rock for everyone to read: 100,000 killed, 150,000 deported. Then, on the same stone, he said he regretted it.",
  "fall-of-rome":
    "The last emperor was sixteen. The general who deposed him didn\u2019t kill him \u2014 he gave him a pension and mailed the crown to Constantinople.",
  "mali-empire-mansa-musa":
    "Mansa Musa carried 18 tons of gold to Mecca. His charity crashed Egypt\u2019s gold market for twelve years.",
  "the-crusades":
    "The Fourth Crusade never reached Jerusalem. It sacked Constantinople \u2014 the largest Christian city on earth \u2014 instead.",
};

/* ── CTAs — story-specific calls to action ── */
export const CTAS: Record<string, string> = {
  "partition-of-india": "See how 4 nations remember August 15, 1947",
  "hiroshima-nagasaki":
    "Compare what Washington said vs. what survivors remember",
  "rwandan-genocide":
    "Read what the world chose not to see for 100 days",
  "scramble-for-africa":
    "See what the colonizers wrote vs. what the kingdoms remember",
  "opium-wars":
    "Compare the British free-trade argument with the Qing court\u2019s response",
  "french-revolution":
    "Read the revolution from Paris, Versailles, and Haiti",
  "creation-of-israel-nakba":
    "Same day, same land \u2014 read both declarations side by side",
  "trail-of-tears":
    "The court said no. The president said yes. Read both arguments",
  "fall-of-berlin-wall":
    "Compare what East and West saw on the same night",
  "transatlantic-slave-trade":
    "Ledger entries vs. survivor testimony \u2014 two records of the same voyage",
  "armenian-genocide":
    "The ambassador\u2019s cables vs. the government\u2019s denials",
  "holodomor":
    "One journalist told the truth. Another won a Pulitzer for lying. Read both",
  "congo-free-state":
    "Leopold\u2019s civilizing mission vs. the photographs of severed hands",
  "cambodian-genocide":
    "The regime\u2019s ideology vs. the faces in the S-21 photographs",
  "tiananmen-square":
    "The party\u2019s version vs. what the cameras recorded before the signal cut",
  "peloponnesian-war":
    "Thucydides put words in both mouths. Read what Athens said to Melos",
  "mongol-conquest-baghdad":
    "Destroyer or globalizer? Two accounts of what happened to the library",
  "haitian-revolution":
    "The enslaved who defeated Napoleon \u2014 told by 4 sides",
  "meiji-restoration":
    "How Japan avoided China\u2019s fate \u2014 reformers vs. the last samurai",
  "treaty-of-waitangi":
    "Two texts, two languages, two meanings. Read both treaties",
  "bolivarian-revolutions":
    "The liberator\u2019s promise to Haiti vs. what he actually delivered",
  "ashoka-maurya-empire":
    "The conqueror\u2019s own confession vs. the modern nation that put his symbol on its flag",
  "fall-of-rome":
    "Did it fall or transform? The debate that shaped how the West thinks about collapse",
  "mali-empire-mansa-musa":
    "European maps vs. oral tradition \u2014 two records of Africa\u2019s wealthiest empire",
  "the-crusades":
    "Jerusalem 1099 vs. Jerusalem 1187 \u2014 the massacre and the mercy, side by side",
};
