# History data audit, 2026-09-20, part 2 of 3

One of three parallel audits comparing every event's `data/history/events/*.yaml`
against its validated documentary script in `data/history/scripts/`. The scripts
are gate-checked and sourced, so where the two disagree the YAML is the likelier
error, and the page renders the YAML.

Moved here from a session scratchpad, which does not survive the session. The
evidence is the point: several findings in these tables were REFUTED on checking,
and a refutation is only reusable if the evidence behind the original claim
survives alongside it.

Findings acted on, and findings refuted, are recorded in the git history of
`data/history/events/` and in `docs/OPEN-ITEMS.md`.

---

# History Data Audit — Slice 2 (alphabetical, second third)

Events audited (24): fall-of-berlin-wall, fall-of-constantinople, fall-of-rome, fall-of-tenochtitlan,
french-revolution, global-financial-crisis-2008, great-depression, great-leap-forward,
gutenberg-printing-press, haitian-revolution, hiroshima-nagasaki, holodomor, inca-conquest-peru,
indian-independence-movement, industrial-revolution, iran-iraq-war, iranian-revolution,
kingdom-of-kongo, korean-war, mali-empire-mansa-musa, meiji-restoration, mongol-conquest-baghdad,
mongol-empire, mughal-empire.

Method: for each event, read the full YAML (all top-level fields, every perspective's narrative and
notable_quotes) and the paired script, cross-checked all dates/figures against each other and against
the YAML's own internal statements, and traced how `notable_quotes`/`primary_source_excerpts` actually
render on the page (`frontend/app/history/data.ts` maps a perspective's `notable_quotes[].speaker` →
`author` and `.context` → `work`, then `PrimarySourceBlock`/`PerspectiveFrame` render them as
blockquoted citations — so the `context` disclosure text DOES reach the page, and `primarySources[0]`
is the one quote featured prominently in the swipeable "PerspectiveFrame" reel).

## Findings

| slug | field | severity | what is wrong | evidence (quote both sides) | suggested fix |
|---|---|---|---|---|---|
| hiroshima-nagasaki | `death_toll` (top-level) | **P0** | The headline death-toll range's low end is arithmetically impossible given the event's own summary. | `death_toll`: "110,000-210,000 by end of 1945". But `summary` states Hiroshima alone reached "an estimated 140,000" by December 1945, and Nagasaki "Between 40,000 and 70,000 people died by the end of 1945." 140,000 + 40,000 = 180,000 minimum — the stated floor of 110,000 is ~70,000 below what the article's own body text requires. | Change the range's floor to ~180,000 (or explicitly source the 110,000 figure and reconcile it with the per-city numbers already in the summary). |
| iranian-revolution | `duration` (top-level) + script CLOSE | **P0** | The date given for "Islamic Republic established" is wrong, and contradicts the event's own perspective narrative. | `duration`: "Revolutionary phase: January 9, 1978 ... to February 11, 1979 (Islamic Republic established)". But the "Islamic Republican" perspective's own narrative says: "On April 1, 1979, a national referendum on the Islamic Republic received 98.2% approval on a turnout of 90%." Feb 11, 1979 is when the Supreme Military Council declared neutrality and the monarchy fell — not when the Islamic Republic was established. The error propagates into `scripts/iranian-revolution.txt` CLOSE line: "The Islamic Republic declared on the eleventh of February nineteen seventy nine is still governing Iran," and the referendum is never mentioned in the script at all. | Change `duration`'s parenthetical to "monarchy falls / Pahlavi dynasty ends" for Feb 11, and cite April 1, 1979 as the Islamic Republic's actual founding date; fix the script's closing line to match. |
| fall-of-constantinople | `significance`, `legacy_points` + script | **P0** | A specific, falsifiable arithmetic claim is wrong for 2 of the 4 examples given. | `significance`: "Within 40 years: Bartolomeu Dias rounded the Cape of Good Hope (1488), Columbus crossed the Atlantic (1492), Vasco da Gama reached Calicut (1498), and John Cabot ... reached North America (1497)." 1453+40=1493. Da Gama's 1498 voyage is **45** years after 1453; Cabot's 1497 is **44** years after. Only Dias (35 yrs) and Columbus (39 yrs) are actually "within 40 years." The same wrong framing is repeated in `legacy_points` ("within 40 years, Dias, Columbus, da Gama, and Cabot reached four new maritime routes") and voiced in `scripts/fall-of-constantinople.txt`: "Within forty years Bartolomeu Dias rounded the Cape of Good Hope, and Vasco da Gama reached Calicut..." | Change "within 40 years" to "within 45 years" (or split the claim: Dias/Columbus within 40, da Gama/Cabot within 45). |
| haitian-revolution | perspective narrative (Economic Aftermath / French Indemnity) | **P1** | Mislabels which bicentennial a 2003 event marked; contradicted by the document's own quote metadata two sentences later. | Narrative text: "In 2003, on the bicentennial of Haitian independence, President Jean-Bertrand Aristide demanded restitution from France." Haitian independence was declared January 1, 1804 — its bicentennial is 2004, not 2003. The very next `notable_quotes` entry, quoting Aristide's same restitution demand, correctly dates it: "context": "Restitution demand, April 7, 2003 — the 200th anniversary of Toussaint's death" (Toussaint Louverture died April 7, 1803). The narrative sentence and the quote's own context disagree with each other about what April 2003 was the bicentennial *of*. | Change "on the bicentennial of Haitian independence" to "on the bicentennial of Toussaint Louverture's death." |
| iran-iraq-war | perspective `notable_quotes` (multiple) | **P1** | Several "quotes" are not quotes at all — the `speaker` field holds an analytical description rather than any real person or document, yet the text renders in a blockquote under a "Primary sources" heading. | Four entries: speaker "Iraqi state framing of the September 1980 casus belli" for text "The Shatt al-Arab must return to Arab and Iraqi sovereignty..."; speaker "Summary of the US Navy inquiry into Iran Air Flight 655" for text "The system worked. The men operating it did not."; speaker "Scholarly consensus on the war's outcome" for text "Both sides declared victory over a war that returned them to the border where it began." (this is `primarySources[0]` for its perspective, i.e. the one quote featured in the swipeable reel view); speaker "Analytic framing in later scholarship" for text "The road from Halabja runs to the nuclear question." None of these are attributed to an identifiable speaker or document — they are the site's own analysis dressed as quotation marks. Tellingly, `scripts/iran-iraq-war.txt` uses none of these four as spoken `## DOCUMENT` lines — only the four genuinely-attributed quotes (Khomeini, UN Resolution 598, Reagan, al-Majid) are voiced. | Move these four out of `notable_quotes` into the narrative prose (they read as ordinary analytical sentences), or clearly re-label them (e.g. drop the quotation marks and blockquote treatment) since they are not primary sources. |
| great-leap-forward | `death_toll` (top-level) vs `significance` | **P1** | The headline range excludes a figure the document itself cites as a legitimate scholarly estimate. | `death_toll`: "15-45 million (disputed; Beijing ~15 million, Yang Jisheng ~36 million, Dikotter ~45 million)." But `significance` states: "A revisionist current (Utsa Patnaik, Joseph Ball, Sun Jingxian) argues ... the true excess is far lower, near 11.5 million." 11.5 million is below the stated floor of 15 million. The script explicitly flags "The lowest estimate on record is eleven point five million," which is *outside* the range given in the death_toll card. | Widen the top-level range to "11.5-45 million" or otherwise note the low-end outlier explicitly in the death_toll field. |
| french-revolution | `subtitle` | **P1** | The subtitle's compressed phrasing implies the two events happened in the same year; the sourced facts (in the same document and its script) show they are 18 months apart, spanning two different years. | `subtitle`: "They beheaded the king in January. By July they were beheading the men who had beheaded the king." Louis XVI was executed January 21, **1793**; Robespierre was executed July 28, **1794** — the script itself states the gap explicitly: "Eighteen months after that they were executing the men who had voted to execute the king." A reader taking the subtitle's "January... by July" at face value would assume one calendar year. | Add the years to the subtitle, or rephrase to make the 18-month/two-year gap explicit (e.g., "...By the next July..."). |
| mughal-empire | `subtitle` vs `summary` | P2 | Subtitle rounds up a cited figure. | `subtitle`: "his empire held 25% of world GDP." `summary`: "Angus Maddison's OECD data estimates Mughal India at approximately 24.4% of world GDP in 1700." 24.4% is closer to 24% than 25%. | Change subtitle to "~24% of world GDP" or "a quarter of world GDP" (looser wording is defensible; "25%" as a specific figure is not what the cited source says). |
| mali-empire-mansa-musa | `subtitle` vs `summary` (x2) + script | P2 | Subtitle understates a figure repeated three times elsewhere in the same document. | `subtitle`: "crashed the Egyptian economy for a **decade**." `summary` states twice that Musa's hajj "depressed the price of gold in Egypt for **12 years**" / "gold lost 10-25% of its value... interviewed eyewitnesses who still remembered the economic disruption" after "12 years." `scripts/mali-empire-mansa-musa.txt` CLOSE line: "for twelve years after a man came through on his way to Mecca, the price of gold was wrong." Every other instance of this fact in the document says 12 years, not 10. | Change subtitle to "for twelve years" or "over a decade." |
| fall-of-rome | `death_toll` (top-level) vs perspective narrative | P2 | Two different population figures for the same empire appear in the same document without reconciliation. | `death_toll`: "an estimated 55 million (2nd century CE)" for the Western Empire's population. The "Late Roman / Imperial" perspective's narrative separately states: "The Forum, once the administrative center of an empire governing **60 million** people, became a cattle pasture." Both purport to describe the empire near its height; the two figures don't match. | Reconcile to one figure, or specify that the 60 million figure is for the whole (East+West) empire versus the West alone. |
| mughal-empire | `duration` vs `significance` | P2 (low confidence) | A one-year mismatch between the "331 years" figure and the exile year given elsewhere. | `significance`: "The Mughal Empire governed the Indian subcontinent for 331 years" (1526-1857). `duration`: "last Mughal emperor exiled: **1858**." 1858-1526 = 332, not 331. This may be intentional (1857 = uprising/dethronement, 1858 = formal exile), so confidence is lower than the other findings, but a careful reader doing the arithmetic on the `duration` card's own numbers gets 332, not the "331" quoted in `significance`. | Either state "332 years" in significance, or use 1857 consistently as the end-marker in duration's own phrasing. |

## Clean events (no findings)

- **fall-of-berlin-wall** — read in full (all 4 perspectives + script); dates, figures (140 deaths at the
  Wall, 28y/88d duration, 41-day Panama gap, etc.) all check out and match the script.
- **global-financial-crisis-2008** — all figures (Lehman's $639B/$619B, TARP $700B, Iceland, ADB $9.6T,
  China's ¥4T stimulus) are consistent between YAML and script.
- **great-depression** — unemployment/vote/GDP figures all check out and match across summary,
  perspectives, and script.
- **gutenberg-printing-press** — this is one of the two "known cases" named in the brief; checked
  specifically for how attributed/paraphrased quotes render. All of them ("Attributed to various
  16th-century clergy," "Attributed to the Vicar of Croydon," the Trent friar quote) are disclosed in
  the `context`/`work` field, which *does* render on the page via `PrimarySourceBlock`, and the script
  independently flags them as "a line attributed to..." No undisclosed-paraphrase problem found.
- **fall-of-tenochtitlan** — figures, dates and the "500 Spaniards / thousands of Tlaxcalans" numbers
  are internally consistent and match the script.
- **industrial-revolution** — figures check out (Enclosure Acts, Peterloo, Luddites, coal output).
- **inca-conquest-peru** — dates/figures check out. One soft note: the "Andean Continuity" perspective's
  featured quote is from Rigoberta Menchú, who is Guatemalan/K'iche' Maya, not Quechua/Aymara/Andean —
  but both the YAML's `context` ("cited across indigenous movements in the Americas") and the script
  ("cited across indigenous movements far beyond her own country") already disclose this, so it is not
  presented as an Andean voice. Not counted as a finding.
- **indian-independence-movement** — duration math (90 years, 1857-1947) and death tolls check out.
- **holodomor** — death toll, dates, and the "13% of Ukraine's population" figure are consistent once
  you note the 13% is calculated against total Ukrainian population (~30-31M), not the `affected_population`
  field's narrower "rural population, 23 million" — a different but equally correct denominator, not a
  contradiction.
- **kingdom-of-kongo** — dates and figures (275-year duration, Battle of Mbwila math, Dona Beatriz's age)
  check out.
- **korean-war** — extensively cross-checked (five perspectives + script); duration math (3y1m2d) is
  exact; the two different American death figures (36,574 KIA vs. 54,246 total war-era dead) are both
  real, standard, distinct official statistics, not a contradiction.
- **meiji-restoration** — dates and figures (Boshin War casualties, Ganghwa Treaty 22 years after Perry,
  77-year arc to Hiroshima) check out exactly.
- **mongol-conquest-baghdad** — siege length, death toll range, and House of Wisdom material all check
  out and match the script.
- **mongol-empire** — dates and figures (1206 founding, 1279 peak, 162-year duration, 16M Y-chromosome
  study) check out.

## Summary

Audited all 24 assigned events (read every YAML field and paired script). 14 came back clean. Of the
10 findings: **3 are P0** (reach the page and are factually wrong), **4 are P1** (reach the page and are
misleading or malformed), and **3 are P2** (internal inconsistencies a casual reader is less likely to
catch, lower confidence on one of them).

The single worst finding is the **iranian-revolution** `duration` field's claim that the Islamic Republic
was "established" on February 11, 1979 — that date is the fall of the monarchy, not the founding of the
Islamic Republic (which the document's own text correctly places at the April 1, 1979 referendum). This
is a specific, dated, checkable claim that is simply wrong, it renders on the event page's duration card,
and the error was carried verbatim into the audio script's closing line, so it reaches the listener too.
It's the clearest case in this slice of a "wrong number live on the page," matching the `arab-spring`
pattern described in the brief.
