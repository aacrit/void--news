# History data audit, 2026-09-21

The scheduled-error pass. `docs/audits/BRAND-AUDIT-2026-09-21.md` Appendix C,
findings F-05 and F-15: the History catalogue carried 81 claims measured from
the moment somebody reads the page, and four places where a hedge noun stood
where a name belonged.

The three 2026-09-20 audits looked for facts that were wrong. This one looks
for facts that are right today and become wrong on their own, which is the
class CLAUDE.md Rule 1 names outright: "A number that goes stale is a future
error. Do not publish a count that changes with time ('ten presidents',
'sixty-five years on') when a durable formulation exists." The catalogue
carried the rule's own example, in `cuban-revolution.yaml`.

Same shape as the 09-20 files, and for the same reason: what was changed, and
what was deliberately not changed, are both only reusable if the evidence sits
next to them.

---

## What was gated

`tests/test_history_copy.py` grew two gates, so this class cannot regrow
silently. Both run over `summary`, `subtitle`, `significance`,
`legacy_points[]` and `perspectives[].narrative`, with quotations exempt for
the reason the dash gate exempts them: the words are as the source printed
them.

| Gate | Fails on |
|---|---|
| time-relative | `in / as of / since <2024-2039>`; `to this day`; `still open / governs / leads / stands / in force / the`; `remains / persists` followed in the same sentence by `in force / today / the most / the largest / the only / the world's`; `<n> years on / ago / later` not followed by `in <year>`; `in the 2020s`; `currently`; `today` |
| prose attribution | `analysts / experts / critics / observers / some / many / sources` + `say / argue / believe / note` (and past and third-person forms) unless the same sentence names a person, a work or an institution |

Two carve-outs, both false positives the rule produced on its first run and
both recorded in the test's docstring:

- **an inflation conversion.** "$1.5 billion in 2025 dollars" is pinned to its
  base year forever. Three entries carry one: `cyrus-cylinder`
  perspectives[2], `hiroshima-nagasaki` perspectives[0],
  `indian-independence-movement` perspectives[2]. Untouched.
- **"years on" as a preposition.** `apartheid` perspectives[0]: "Walter Sisulu
  ... served alongside him for 25 years on the island". The idiom "thirty years
  on" always closes a clause, so the rule requires punctuation after it.

## The allowed rewrite

Three forms, in order of preference, and the third is not a failure:

1. **Anchor to a dated observation**, with the date attached to the
   measurement rather than to the reader. "By 2024, 34 countries had formally
   recognized the genocide." "A 2024 Gini coefficient of 0.63 made South Africa
   the most unequal country on earth." "A 2003 genetic study estimated that 16
   million men then alive carried Y-chromosomal lineages." `By <year>` and a
   year used adjectivally are spared on purpose: they read as a fixed
   observation, where `in / as of / since <the year of writing>` reads as now.
2. **Use the absolute date the record already carries.** "Four years later he
   launched the Cultural Revolution" became "In 1966 he launched the Cultural
   Revolution", which `great-leap-forward.yaml` states twice elsewhere. Every
   substitution of this kind in the table below was checked against the same
   file, never against model knowledge.
3. **Drop the clause.** Where neither the YAML nor the event's own `sources`
   carried a durable form, the claim was cut rather than dated. Rule 1:
   silence beats a plausible reconstruction.

## Dropped rather than dated

Eleven claims went out instead of being anchored. Each is listed so the next
writer does not reinstate it from memory.

| slug | field | what went, and why |
|---|---|---|
| `algerian-war` | `significance` | "that still governs France". The Fifth Republic's founding is in the file; its present tenure is not. |
| `algerian-war` | `significance` | "and his party leads French elections in the 2020s". No dated election result anywhere in the event or its sources. |
| `ashoka-maurya-empire` | `significance` | "where it remains the majority religion in the 2020s". No dated census in the record. |
| `chernobyl-disaster` | `perspectives[4].narrative` | "even counting Chernobyl and Fukushima, nuclear power has caused far fewer deaths per unit of energy than coal, and ... the retreat from nuclear after 1986 locked in decades of fossil-fuel emissions". The perspective cites INSAG-7 (1992), Higginbotham (2019) and the World Nuclear Association's RBMK appendix (2021). None of the three carries a deaths-per-unit-energy comparison. Both an F-15 hedge and an unsourced claim. |
| `congo-wars` | `summary` | "As of 2026, eastern Congo has over 120 active armed groups." |
| `congo-wars` | `perspectives[1].narrative` | "Eastern Congo in 2026 has over 120 active armed groups." The figure appears three times in the file and is dated nowhere, and none of the event's sources is an armed-group census. The sentence after it, "The war that officially ended in 2003 has not ended", carries the point without the count. |
| `great-depression` | `significance` | "much of which still governs finance in the 2020s". Glass-Steagall's repeal in 1999 makes the continuity claim unsafe as well as stale, and the file does not carry the distinction. |
| `great-depression` | `legacy_points[1]` | "still in force today", for the same reason. |
| `iran-iraq-war` | `perspectives[4].narrative` | "many analysts argue". The paragraph names Narges Bajoghli and Dina Rizk Khoury two sentences earlier for a different claim; neither is cited for the nuclear-hedging one. |
| `mongol-conquest-baghdad` | `summary` | "Some sources say he was forced to watch his sons killed first." The file cites Juvayni, Rashid al-Din, Ibn al-Athir and Ibn Kathir by name and attaches none of them to this detail. Rule 1: a claim that cannot be sourced is cut, not softened. |
| `sykes-picot-agreement` | `legacy_points[3]` | "that persists today". |

## Left standing

- `data/history/scripts/mongol-conquest-baghdad.txt:39` still carries "Some
  sources say he was made to watch his sons killed first", the sentence now
  removed from the YAML for want of a named chronicle. Scripts are governed by
  H-01..H-11 and were outside this pass, so the record and the episode now
  disagree on that one line. It is the same defect in the same words and needs
  the same cut.
- Counts that decay but carry no time-relative wording are invisible to this
  gate, because nothing in the sentence says "now". `bandung-conference`
  `significance` ("grew from 25 to 120 member states by 2026"),
  `inca-conquest-peru` `significance` ("now draws 50,000 annual visitors") and
  every bare population figure are of this kind. A gate for them would have to
  read meaning, not shape, which is the line the speaker gate already refuses
  to cross.
- `key_arguments[]`, `emphasized[]` and `omitted[]` are not gated. At least one
  carries the same shape (`chernobyl-disaster` key_arguments[3], "Pro-nuclear
  analysts argue ..."). They are perspective scaffolding rather than rendered
  prose, and widening the gate to them was not in this pass's remit.

## Every change

149 edits across 128 fields in 60 files: 51 in `perspectives[].narrative`, 29
in `significance`, 26 in `legacy_points[]`, 19 in `summary`, 3 in `subtitle`.
The audit predicted 81 (summary 21, significance 40, legacy 20); the difference
is `perspectives[].narrative`, `today`, `currently` and `in the 2020s`, which
the audit's own count did not cover.

Each row was applied by exact-substring replacement on the raw YAML and then
verified by re-parsing the file and comparing every other field against the
parse taken before the edit, so no row here changed anything it does not name.

| slug | field | before | after |
|---|---|---|---|
| `alexanders-conquests` | `perspectives[4].narrative` | that shaped Arrian's account 2,300 years ago. | that shaped Arrian's account. |
| `algerian-war` | `significance` | and produced the Fifth Republic that still governs France. | and produced the Fifth Republic. |
| `algerian-war` | `significance` | built the National Front on pied-noir and anti-immigrant grievance, and his party leads French elections in the 2020s. | built the National Front on pied-noir and anti-immigrant grievance. |
| `angkor-khmer-empire` | `perspectives[1].narrative` | created the archaeological park that tourists visit today. | created the archaeological park that tourists visit. |
| `angkor-khmer-empire` | `significance` | Angkor Wat remains the largest religious monument on Earth at 162.6 hectares. | Angkor Wat is the largest religious monument on Earth at 162.6 hectares. |
| `angkor-khmer-empire` | `summary` | Today, Angkor Wat appears on the Cambodian flag | Angkor Wat appears on the Cambodian flag |
| `apartheid` | `legacy_points[3]` | Post-apartheid South Africa remains the world's most unequal country by Gini coefficient (0.63) | A 2024 Gini coefficient of 0.63 made post-apartheid South Africa the most unequal country on earth by income distribution |
| `apartheid` | `significance` | The Gini coefficient, 0.63 in 2024, makes South Africa the most unequal country on earth by income distribution. | A 2024 Gini coefficient of 0.63 made South Africa the most unequal country on earth by income distribution. |
| `apartheid` | `significance` | unemployment among black South Africans exceeded 40% in 2024, compared to 8% among white South Africans. | 2024 unemployment among black South Africans exceeded 40%, against 8% among white South Africans. |
| `apollo-11-moon-landing` | `perspectives[3].narrative` | opened one such container in 2019, fifty years on. | opened one such container in 2019, fifty years after the landing. |
| `armenian-genocide` | `legacy_points[1]` | 34 countries have formally recognized the genocide as of 2024 | 34 countries had formally recognized the genocide by 2024 |
| `armenian-genocide` | `perspectives[4].narrative` | The United States did not ratify it until 1988 (forty years later) partly because | The United States did not ratify it until 1988, forty years after its adoption, partly because |
| `armenian-genocide` | `perspectives[4].narrative` | As of 2024, 34 countries formally recognize the Armenian Genocide. | By 2024, 34 countries had formally recognized the Armenian Genocide. |
| `armenian-genocide` | `significance` | As of 2024, 34 countries have formally recognized the Armenian Genocide; | By 2024, 34 countries had formally recognized the Armenian Genocide; |
| `ashoka-maurya-empire` | `perspectives[2].narrative` | That tree (or its descendant) still stands in Anuradhapura, making it one of the oldest historically documented trees in the world. | That tree (or its descendant) grows in Anuradhapura, one of the oldest historically documented trees in the world. |
| `ashoka-maurya-empire` | `perspectives[2].narrative` | was enlarged over the next 400 years into the monumental form that survives today. | was enlarged over the next 400 years into the monumental form that survives. |
| `ashoka-maurya-empire` | `significance` | established Theravada Buddhism on the island, where it remains the majority religion in the 2020s. | established Theravada Buddhism on the island. |
| `ashoka-maurya-empire` | `summary` | became, 2,200 years later, the national emblem of the Republic of India. | became the national emblem of the Republic of India. |
| `bandung-conference` | `perspectives[3].narrative` | remained the currency of fourteen African nations in 2026) | was the currency of fourteen African nations) |
| `bandung-conference` | `perspectives[3].narrative` | The question Nkrumah posed in 1965 remains unanswered in 2026: | The question Nkrumah posed in 1965 was never answered: |
| `bandung-conference` | `significance` | Its framework of sovereign equality and non-interference shapes the BRICS grouping, the G-77, and Global South solidarity in 2026, institutions that trace | Its framework of sovereign equality and non-interference shaped the BRICS grouping, the G-77, and Global South solidarity, institutions that trace |
| `chernobyl-disaster` | `legacy_points[3]` | the 2,600 sq km exclusion zone persists in 2026 | the 2,600 sq km exclusion zone was never lifted |
| `chernobyl-disaster` | `perspectives[4].narrative` | Six years later, the IAEA's own advisory group revisited that verdict in the report INSAG-7 | In 1992 the IAEA's own advisory group revisited that verdict in the report INSAG-7 |
| `chernobyl-disaster` | `perspectives[4].narrative` | were held to be categorically safer, though critics noted the industry had strong incentives to draw that line firmly. | were held to be categorically safer, a line the industry had strong incentives to draw firmly. |
| `chernobyl-disaster` | `perspectives[4].narrative` | That fear is itself contested: pro-nuclear analysts argue that even counting Chernobyl and Fukushima, nuclear power has caused far fewer deaths per unit of energy than coal, and that the retreat from nuclear after 1986 locked in decades of fossil-fuel emissions. In this framing Chernobyl is | That fear is itself contested. In this framing Chernobyl is |
| `chernobyl-disaster` | `summary` | The exclusion zone drawn around the plant, 2,600 square kilometers, remains largely uninhabited in 2026. | The exclusion zone drawn around the plant, 2,600 square kilometers, was never reopened to resettlement. |
| `chinese-civil-war` | `legacy_points[2]` | question that remains the most dangerous flashpoint between nuclear powers | question, the most dangerous flashpoint between nuclear powers |
| `chinese-civil-war` | `perspectives[0].narrative` | to the flag raised over Tiananmen 22 years later, | to the flag raised over Tiananmen in 1949, |
| `chinese-civil-war` | `perspectives[1].narrative` | and why Taipei's status is contested to this day. | and why Taipei's status was never settled. |
| `chinese-civil-war` | `significance` | has governed without interruption for more than 75 years, longer than | has governed without interruption since 1949, longer than |
| `chinese-civil-war` | `significance` | a split sovereignty that in the 2020s is the single most dangerous flashpoint between nuclear-armed states. | a split sovereignty that became the single most dangerous flashpoint between nuclear-armed states. |
| `chinese-civil-war` | `significance` | The line drawn across 110 miles of the Taiwan Strait remains the most consequential unfinished border of the twentieth century. | The line drawn across 110 miles of the Taiwan Strait is the twentieth century's most consequential unfinished border. |
| `chinese-civil-war` | `summary` | crossing the strait to Taiwan, where the Republic of China survives to this day. | crossing the strait to Taiwan, where the Republic of China moved its capital to Taipei that December. |
| `chinese-civil-war` | `summary` | One question left open in 1949 is still open in 2026. | The question left open in 1949 was never settled. |
| `chinese-cultural-revolution` | `perspectives[1].narrative` | His children did not learn of his death until years later. | His children did not learn of his death for years. |
| `columbian-exchange` | `perspectives[2].narrative` | Maize, domesticated from teosinte in central Mexico 9,000 years ago, reached West Africa by the 1550s | Maize, domesticated from teosinte in central Mexico around 7000 BCE, reached West Africa by the 1550s |
| `columbian-exchange` | `perspectives[2].narrative` | The Italian cuisine that the world recognizes today (marinara, pizza, bolognese) | The Italian cuisine that the world recognizes (marinara, pizza, bolognese) |
| `congo-free-state` | `legacy_points[4]` | and echo in cobalt mining conditions today | and echo in cobalt mining conditions |
| `congo-wars` | `perspectives[1].narrative` | It has never been the beneficiary of its own mineral wealth. Eastern Congo in 2026 has over 120 active armed groups. The M23 movement, | It has never been the beneficiary of its own mineral wealth. The M23 movement, |
| `congo-wars` | `perspectives[1].narrative` | What happened between 1996 and 2003, and what continues in 2026, was an invasion disguised as liberation, | What happened between 1996 and 2003, and what has not stopped since, was an invasion disguised as liberation, |
| `congo-wars` | `summary` | and returned in 2022. As of 2026, eastern Congo has over 120 active armed groups. The war that officially ended in 2003 has not ended. | and returned in 2022. The war that officially ended in 2003 has not ended. |
| `cuban-revolution` | `perspectives[4].narrative` | the more than 1,000 political prisoners counted by independent monitors in 2025 are treated as established | the more than 1,000 political prisoners in the 2025 count by independent monitors are treated as established |
| `cuban-revolution` | `perspectives[4].narrative` | The open historiographic question, sixty-five years on, is whether | The open historiographic question is whether |
| `cuban-revolution` | `significance` | remains the most contested balance sheet in Latin American history. | is the most contested balance sheet in Latin American history. |
| `cuban-revolution` | `summary` | imposed a trade embargo that remains in force in 2026. | imposed a trade embargo that was never lifted. |
| `cuban-revolution` | `summary` | Sixty-five years on, the question of whether January 1, 1959 was a liberation or a takeover has never been settled | The question of whether January 1, 1959 was a liberation or a takeover has never been settled |
| `cyrus-cylinder` | `perspectives[1].narrative` | Twenty-five hundred years later, it was repurposed as a propaganda text by a modern autocrat. | In 1971 it was repurposed as a propaganda text by a modern autocrat. |
| `fall-of-berlin-wall` | `perspectives[1].narrative` | Surveys in the 2020s show that a majority of East Germans feel they are treated as second-class citizens within unified Germany. | Surveys have found a majority of East Germans feeling treated as second-class citizens within unified Germany. |
| `fall-of-berlin-wall` | `perspectives[4].narrative` | preserved the racial distribution of wealth: in 2024, white South Africans | preserved the racial distribution of wealth: by 2024, white South Africans |
| `fall-of-rome` | `perspectives[1].narrative` | Her mausoleum in Ravenna, with its midnight-blue mosaics of gold stars, still stands. | Her mausoleum in Ravenna keeps its midnight-blue mosaics of gold stars. |
| `fall-of-rome` | `perspectives[2].narrative` | The real fall, the one that ended the Roman state, happened 977 years later. | The real fall, the one that ended the Roman state, came in 1453. |
| `fall-of-tenochtitlan` | `perspectives[0].narrative` | a foot soldier who participated in the conquest and wrote his account 40 years later, | a foot soldier who participated in the conquest and wrote his account forty years after the siege, |
| `great-depression` | `legacy_points[1]` | Established deposit insurance, securities regulation, and Social Security through the New Deal, still in force today | Established deposit insurance, securities regulation, and Social Security through the New Deal |
| `great-depression` | `significance` | through the New Deal's Social Security, deposit insurance, and securities regulation, much of which still governs finance in the 2020s. | through the New Deal's Social Security, deposit insurance, and securities regulation. |
| `great-depression` | `significance` | still divides economists and shapes how governments respond to recessions today. | still divides economists and shapes how governments respond to recessions. |
| `great-depression` | `subtitle` | In 1929 America had never been richer. Four years later one in four workers had no job and nobody could agree why. | In 1929 America had never been richer. By 1933 one in four workers had no job and nobody could agree why. |
| `great-leap-forward` | `summary` | Four years later he launched the Cultural Revolution. | In 1966 he launched the Cultural Revolution. |
| `hiroshima-nagasaki` | `perspectives[1].narrative` | It sold out immediately and remains in print 80 years later. | It sold out immediately and stayed in print. |
| `hiroshima-nagasaki` | `perspectives[4].narrative` | As of 2024, approximately 1,700 Korean hibakusha were still alive in South Korea, | By 2024, approximately 1,700 Korean hibakusha were still alive in South Korea, |
| `hiroshima-nagasaki` | `summary` | As of 2024, approximately 106,000 hibakusha were still alive, | By 2024, approximately 106,000 hibakusha were still alive, |
| `holodomor` | `significance` | As of 2024, 34 countries and the European Parliament have recognized the Holodomor as a genocide. | By 2024, 34 countries and the European Parliament had recognized the Holodomor as a genocide. |
| `inca-conquest-peru` | `legacy_points[2]` | 10 million Quechua speakers today, the most widely spoken indigenous language in the Americas | 10 million Quechua speakers, the most widely spoken indigenous language in the Americas |
| `inca-conquest-peru` | `perspectives[4].narrative` | Ten million people speak Quechua today. | Ten million people speak Quechua. |
| `inca-conquest-peru` | `significance` | Ten million people still speak Quechua today, making it the most widely spoken indigenous language in the Americas. | Ten million people speak Quechua, the most widely spoken indigenous language in the Americas. |
| `inca-conquest-peru` | `summary` | The potato, domesticated in the Andes 8,000 years ago and cultivated by Inca farmers | The potato, domesticated in the Andes around 6000 BCE and cultivated by Inca farmers |
| `indian-independence-movement` | `legacy_points[2]` | Salt March (1930) remains the most iconic act of civil disobedience in modern history | Salt March (1930), the most iconic act of civil disobedience in modern history |
| `indian-independence-movement` | `perspectives[3].narrative` | was not officially outlawed until 1993 and continues today. | was not officially outlawed until 1993 and did not stop. |
| `indian-independence-movement` | `significance` | The Salt March remains the most widely cited example of nonviolent resistance in human history. | The Salt March is the most widely cited example of nonviolent resistance in human history. |
| `industrial-revolution` | `legacy_points[1]` | a structure that governs most human work in 2026 | a structure that governs most human work |
| `industrial-revolution` | `significance` | in the 1780s remains in the atmosphere in 2026. | in the 1780s has not left the atmosphere. |
| `iran-iraq-war` | `perspectives[0].narrative` | The lesson the Islamic Republic drew, and teaches to this day through the state media and the war museums studied by scholars such as Narges Bajoghli, is that | The lesson the Islamic Republic drew, and goes on teaching through the state media and the war museums studied by Narges Bajoghli, is that |
| `iran-iraq-war` | `perspectives[4].narrative` | became the permanent justification for a missile program and, many analysts argue, for the nuclear hedging that defines the standoff of the 2020s. | became the permanent justification for a missile program and for the nuclear hedging that followed. |
| `iran-iraq-war` | `significance` | two years later Saddam invaded Kuwait to erase the debt, | in 1990 Saddam invaded Kuwait to erase the debt, |
| `iran-iraq-war` | `significance` | are all, in 2026, still being negotiated in the language this war wrote. | were all left to be negotiated in the language this war wrote. |
| `iranian-revolution` | `legacy_points[0]` | ended Jimmy Carter's presidency and inaugurated 47 years of US-Iran confrontation that continues in 2026 | ended Jimmy Carter's presidency and opened a US-Iran confrontation that was never resolved |
| `iranian-revolution` | `legacy_points[5]` | the standoff that defines the region's security architecture in 2026 | the standoff that defines the region's security architecture |
| `iranian-revolution` | `perspectives[3].narrative` | Before 1979, Iran had 4 universities with international rankings. In 2026, none rank in the global top 200. | Before 1979, Iran had 4 universities with international rankings. None has since entered the global top 200. |
| `korean-war` | `legacy_points[0]` | No peace treaty has been signed as of 2026, 73 years after the armistice. The Korean War is technically still ongoing. | No peace treaty has ever been signed. The Korean War is technically still ongoing. |
| `korean-war` | `legacy_points[4]` | North Korea's GDP per capita in 2024: estimated at $640. | North Korea's 2024 GDP per capita: estimated at $640. |
| `korean-war` | `perspectives[0].narrative` | Five years later, 36,574 Americans would die defending that line. | From 1950, 36,574 Americans would die defending that line. |
| `korean-war` | `perspectives[1].narrative` | The Sinchon Museum of American War Atrocities remains the most visited museum in North Korea. | The Sinchon Museum of American War Atrocities is the most visited museum in North Korea. |
| `korean-war` | `subtitle` | Three years later, 3 million were dead. | By 1953, 3 million were dead. |
| `mali-empire-mansa-musa` | `perspectives[2].narrative` | who collected eyewitness accounts in Cairo 12 years later, | who collected eyewitness accounts in Cairo in 1336, |
| `mali-empire-mansa-musa` | `significance` | constitute the largest body of pre-colonial African written scholarship and survive today in the Ahmed Baba Institute | constitute the largest body of pre-colonial African written scholarship and survive in the Ahmed Baba Institute |
| `mali-empire-mansa-musa` | `summary` | an Arab historian who visited Cairo 12 years later, | an Arab historian who visited Cairo in 1336, |
| `meiji-restoration` | `perspectives[4].narrative` | The issue remains unresolved between Japan and South Korea in the 2020s, with survivors demanding | The issue was never resolved between Japan and South Korea, with survivors demanding |
| `meiji-restoration` | `significance` | in 77 years remains the most compressed arc of industrialization, conquest, and catastrophe in modern history. | in 77 years is the most compressed arc of industrialization, conquest, and catastrophe in modern history. |
| `meiji-restoration` | `subtitle` | Thirty years later, it had a constitution, a conscript army, and a rail network | By 1889 it had a constitution, a conscript army, and a rail network |
| `mongol-conquest-baghdad` | `legacy_points[2]` | produced astronomical work that influenced Copernicus 285 years later | produced astronomical work that influenced Copernicus |
| `mongol-conquest-baghdad` | `perspectives[4].narrative` | preeminent center of learning, a position it holds in the 2020s. | preeminent center of learning, a position it never lost. |
| `mongol-conquest-baghdad` | `summary` | trampled by horses. Some sources say he was forced to watch his sons killed first. The Mongol principle was | trampled by horses. The Mongol principle was |
| `mongol-conquest-baghdad` | `summary` | numeral system into the "Arabic numerals" used worldwide today. | numeral system into the "Arabic numerals" in use worldwide. |
| `mongol-empire` | `legacy_points[3]` | 16 million men alive today carry Y-chromosomal lineages attributable to Genghis Khan's male line | A 2003 study estimated 16 million men then alive carried Y-chromosomal lineages attributable to Genghis Khan's male line |
| `mongol-empire` | `significance` | A 2003 genetic study estimated that 16 million men alive today carry Y-chromosomal lineages attributable to Genghis Khan or his close male relatives. | A 2003 genetic study estimated that 16 million men then alive carried Y-chromosomal lineages attributable to Genghis Khan or his close male relatives. |
| `mughal-empire` | `legacy_points[0]` | by 20,000 workers, remains the most visited monument in India | by 20,000 workers, is the most visited monument in India |
| `mughal-empire` | `legacy_points[4]` | replaced by Ram Mandir in 2024) is the contemporary political echo | replaced by the 2024 Ram Mandir) is the contemporary political echo |
| `mughal-empire` | `perspectives[1].narrative` | dominates contemporary Indian political discourse and shapes state policy in the 2020s. | dominates contemporary Indian political discourse and shapes state policy. |
| `mughal-empire` | `perspectives[1].narrative` | In the 2020s, BJP-governed states have renamed cities: | BJP-governed states have renamed cities: |
| `mughal-empire` | `significance` | The political legacy remains contested in the 2020s. | The political legacy was never settled. |
| `nanjing-massacre` | `significance` | the reason the two countries have never fully reconciled almost 90 years later. | the reason the two countries have never fully reconciled. |
| `ottoman-empire` | `legacy_points[0]` | Those borders remain in the 2020s | Those borders were never redrawn |
| `ottoman-empire` | `perspectives[0].narrative` | Two years later, in March 1924, the assembly abolished the caliphate itself. | In March 1924 the assembly abolished the caliphate itself. |
| `ottoman-empire` | `perspectives[1].narrative` | in Beirut's central square (today Martyrs' Square) | in Beirut's central square (later Martyrs' Square) |
| `ottoman-empire` | `significance` | A Turkish university student in the 2020s cannot read the text of Suleiman's Kanunname | A Turkish university student cannot read the text of Suleiman's Kanunname |
| `partition-of-india` | `significance` | locked in four wars (1947, 1965, 1971, 1999), and still contesting Kashmir in the 2020s. | locked in four wars (1947, 1965, 1971, 1999), and contesting a Kashmir neither has conceded. |
| `peloponnesian-war` | `perspectives[3].narrative` | void --history operates on the same principle, 2,400 years later. | void --history operates on the same principle. |
| `rise-of-islam` | `legacy_points[2]` | the defining sectarian division for 1.9 billion Muslims today | the defining sectarian division for 1.9 billion Muslims |
| `rise-of-islam` | `perspectives[2].narrative` | He returned it to Jerusalem in 630 in a ceremony of triumph. Two years later, he lost the Levant permanently. | He returned it to Jerusalem in 630 in a ceremony of triumph. He lost the Levant permanently within the decade. |
| `rwandan-genocide` | `perspectives[1].narrative` | The church still stands, its walls marked with machete strikes and grenade fragments. | The church was left standing, its walls marked with machete strikes and grenade fragments. |
| `scramble-for-africa` | `significance` | infrastructure oriented toward ports rather than internal trade) persist: Africa contains 30% of the world's mineral reserves but processes less than 3% domestically, | infrastructure oriented toward ports rather than internal trade) outlived the colonies: Africa holds 30% of global mineral reserves but processes less than 3% domestically, |
| `september-11-attacks` | `perspectives[0].narrative` | Twenty years later, it remained the legal basis for military operations in at least seven countries. | By 2021 it remained the legal basis for military operations in at least seven countries. |
| `september-11-attacks` | `summary` | held 780 detainees; as of 2025, it still holds 15. | held 780 detainees; by 2025 the number held was 15. |
| `silk-road` | `perspectives[2].narrative` | His translations of the Lotus Sutra and the Heart Sutra remain the standard Chinese versions today, 1,600 years later. | His translations of the Lotus Sutra and the Heart Sutra became the standard Chinese versions and were never displaced. |
| `silk-road` | `perspectives[2].narrative` | from this Greco-Buddhist synthesis in a valley that is today part of Pakistan's Khyber Pakhtunkhwa province. | from this Greco-Buddhist synthesis in a valley later taken into Pakistan's Khyber Pakhtunkhwa province. |
| `six-day-war` | `legacy_points[0]` | under a military occupation that in 2026 has lasted 59 years | under a military occupation that began in June 1967 and was never ended |
| `six-day-war` | `perspectives[1].narrative` | a broken man who died three years later. | a broken man who died in 1970. |
| `six-day-war` | `perspectives[2].narrative` | a status their grandchildren still hold in 2026. | a status inherited by their grandchildren. |
| `six-day-war` | `summary` | That occupation was given no end date. In 2026 it is 59 years old. | That occupation was given no end date, and none has been set since. |
| `soviet-union-collapse` | `perspectives[0].narrative` | Two years later it was gone. | In 1989 it was gone. |
| `spanish-civil-war` | `legacy_points[3]` | an estimated 114,000 remain in unmarked mass graves, | an estimated 114,000 lie in unmarked mass graves, |
| `spanish-civil-war` | `significance` | An estimated 114,000 people remain in unmarked mass graves, | An estimated 114,000 people lie in unmarked mass graves, |
| `spanish-flu-1918` | `perspectives[3].narrative` | New Zealand formally apologized to Samoa for the epidemic in 2002, eighty-four years later. | New Zealand formally apologized to Samoa for the epidemic in 2002. |
| `srebrenica-genocide` | `legacy_points[4]` | In 2024 the UN General Assembly designated July 11 | A 2024 UN General Assembly vote designated July 11 |
| `srebrenica-genocide` | `significance` | Forty-seven years later, 8,000 men and boys died inside a United Nations safe area in Europe. | In 1995, 8,000 men and boys died inside a United Nations safe area in Europe. |
| `srebrenica-genocide` | `significance` | Thirty years on, the president of Republika Srpska denies the genocide occurred, and in 2024 the UN General Assembly established July 11 as a day of commemoration over the objections of Serbia. | The president of Republika Srpska denies the genocide occurred; a 2024 UN General Assembly vote established July 11 as a day of commemoration over the objections of Serbia. |
| `suez-crisis` | `perspectives[4].narrative` | Some argue that Eisenhower's financial coercion needlessly humiliated allies and taught France a lesson in self-reliance that led straight to the force de frappe and a generation of Atlantic friction. Others credit Eisenhower with preventing a catastrophe that would have driven the Arab world into Soviet arms. | One reading holds that Eisenhower's financial coercion needlessly humiliated allies and taught France a lesson in self-reliance that led straight to the force de frappe and a generation of Atlantic friction. A second credits Eisenhower with preventing a catastrophe that would have driven the Arab world into Soviet arms. |
| `suez-crisis` | `significance` | That wave broke eleven years later in the Six-Day War. | That wave broke in 1967 in the Six-Day War. |
| `sykes-picot-agreement` | `legacy_points[3]` | Paired with the Balfour Declaration to frame the Israeli-Palestinian conflict that persists today | Paired with the Balfour Declaration to frame the Israeli-Palestinian conflict |
| `sykes-picot-agreement` | `summary` | The borders that emerged from that decade still run through the region today. | The borders that emerged from that decade were never redrawn. |
| `taiping-rebellion` | `summary` | until the Mahdists killed him at Khartoum 21 years later. | until the Mahdists killed him at Khartoum in 1885. |
| `the-crusades` | `perspectives[2].narrative` | the theological and political division that the sack of Constantinople entrenched persists in the 2020s. | the theological and political division that the sack of Constantinople entrenched was never closed. |
| `the-crusades` | `perspectives[4].narrative` | still lists the names of the dead 900 years later. | lists the names of the dead. |
| `the-crusades` | `significance` | (the Hospitallers, as the Sovereign Military Order of Malta, still hold observer status at the UN in the 2020s) | (the Hospitallers survive as the Sovereign Military Order of Malta, a permanent observer at the UN) |
| `the-crusades` | `summary` | Four years later, on July 15, 1099, the armies of the First Crusade breached the walls of Jerusalem. | On July 15, 1099, the armies of the First Crusade breached the walls of Jerusalem. |
| `the-reformation` | `legacy_points[3]` | worlds; today more than 900 million Protestants | worlds; more than 900 million Protestants |
| `the-reformation` | `perspectives[3].narrative` | is the seed of the nation-state system that governs the world today. | is the seed of the nation-state system that governs the world. |
| `the-reformation` | `significance` | Western Christianity never reunified. Today there are more than 900 million Protestants across tens of thousands of denominations. | Western Christianity never reunified. More than 900 million Protestants are spread across tens of thousands of denominations. |
| `tiananmen-square` | `perspectives[0].narrative` | Young Chinese surveyed in the 2020s overwhelmingly either do not know | Young Chinese who have been surveyed overwhelmingly either do not know |
| `tiananmen-square` | `summary` | have documented 202 deaths by name as of 2024, | had documented 202 deaths by name by 2024, |
| `trail-of-tears` | `perspectives[3].narrative` | where their descendants, the Seminole Tribe of Florida, live today. | where their descendants formed the Seminole Tribe of Florida. |
| `trail-of-tears` | `significance` | (Worcester v. Georgia) that remain operative law in the 2020s, even though they were ignored at the time. | (Worcester v. Georgia) that were never overturned, even though they were ignored at the time. |
| `trail-of-tears` | `significance` | The Cherokee Nation today is the largest tribal government in the United States, | The Cherokee Nation is the largest tribal government in the United States, |
| `transatlantic-slave-trade` | `perspectives[2].narrative` | show lower levels of trust and social cohesion today, a direct statistical link | showed lower levels of trust and social cohesion, a direct statistical link |
| `vietnam-war` | `legacy_points[1]` | Agent Orange contamination persists in Vietnamese soil in 2026; | Agent Orange contamination was never cleared from Vietnamese soil; |
| `watergate` | `significance` | set a near-absolute bar against prior restraint that still governs press-versus-state conflicts. | set a near-absolute bar against prior restraint in press-versus-state conflicts. |
| `womens-suffrage` | `perspectives[0].narrative` | as the 19th Amendment forty-two years later. | as the 19th Amendment in 1920. |
| `womens-suffrage` | `summary` | Forty-five years later and eight thousand miles away, Kate Sheppard delivered a petition to the New Zealand Parliament. | In 1893, eight thousand miles away, Kate Sheppard delivered a petition to the New Zealand Parliament. |
| `world-war-i` | `legacy_points[2]` | borders still contested today | borders contested ever since |
| `world-war-i` | `summary` | Twenty years later he was proved right. | In 1939 he was proved right. |
