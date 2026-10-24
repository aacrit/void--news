# Void News: Voice

Last updated: 2026-09-21 (rev 2). Rev 1 described six synthetic hosts on a
multi-run, multi-edition schedule; none of that has run since June. The
pipeline runs once a day, publishes one edition, and Kokoro reads every
programme. Kokoro is a reader, not an author: the voice on this page is the
writer's, checked at write time by the gates in section X. Where this document
and CLAUDE.md disagree, CLAUDE.md wins.

---

## I. Philosophy

Void News exists because the news is broken in three specific ways:

1. **Sensationalism.** Outlets optimize for clicks, not clarity. The loudest framing wins.
2. **Factual sloppiness.** Assertions without attribution; "experts say" without naming the expert.
3. **Bias as default.** A partisan lens presented as neutral reality; inconvenient facts omitted.

Void News is the answer. Not by being bloodless or robotic, but by being
*better*: more precise, more honest, more respectful of the reader's intelligence.

**The Void voice is what happens when deeply informed people discuss the news
without performing for a camera.**

## II. Cardinal Rules

### Show, Don't Tell
Never assert significance. Place two facts next to each other and let the
reader see the pattern.

**No:** "Tensions are rising significantly between the two nations."
**Yes:** "Both countries recalled their ambassadors within 48 hours. Neither
has done that since 1979."

### Evidence Before Interpretation
Every claim must be load-bearing. If you remove a sentence and the piece still
works, the sentence was scaffolding. Cut it.

### Attribute or Abstain
Name the source, cite the number, quote the official. If you can't, don't make
the claim. "The Pentagon confirmed" is reporting. "Experts say" is abdication.

### No Scaffolding
Never announce what you're about to say. The sentence "This isn't just about
trade" contains zero information. Start with the fact: "The tariff targets the
three provinces that voted against the ruling coalition."

### No Sensationalism
Confidence, not hype. The story's weight comes from what happened, not from
adjectives stapled onto it.

### No Em Dashes
Banned in every written surface; rewrite as two sentences, or use a comma,
semicolon, colon or parentheses. Audio scripts alone keep them, as breath marks.

## VII. Anti-Patterns: The Kill List

These are not only prohibited phrases. They are *symptoms* of a voice failure.
If the copy contains any of these, the voice has drifted from the brand.

### Scaffolding (Announcing What You're About To Say)
> "This isn't just about trade." / "Here's the thing." / "The bigger picture is..." /
> "What makes this interesting is..." / "The reality is..." / "The question now is..." / "This matters because..."

Clearing your throat in print. If a sentence survives deletion of its first clause, the first clause was scaffolding.

### Significance Assertion (Telling Instead of Showing)
> "significant" / "notable" / "importantly" / "interestingly" / "crucially" / "it should be noted" / "it is worth mentioning"

These words *claim* importance without *demonstrating* it. Replace with the fact that makes it important.

### AI Slop (LLM Default Voice)
> "delve" / "navigate" / "underscores" / "multifaceted" / "robust" / "pivotal" / "tapestry" / "nuanced" /
> "game-changing" / "paves the way" / "sends a clear message" / "a testament to" / "sheds light on"

Stock photos in prose. They sound like a machine wrote them because machines write them constantly.

### Vox Scaffolding (Explanatory Performer Voice)
> "So here's what's happening." / "Let me explain." / "Here's what you need to know." /
> "Think of it this way." / "Zoom out for a second." / "The short version is..."

Performing understanding for an audience. Void's writers *have* it, and show it by explaining the mechanism.

### False Intimacy (Podcast Voice)
> "I mean..." (as filler) / "Right?" (seeking agreement) / "Look..." (demanding attention) / "So basically..." (oversimplifying)

On Air's two voices are equals briefing each other, not performers seeking the listener's approval.

The machine-readable form of this list is `PROHIBITED_TERMS` in
`pipeline/utils/prohibited_terms.py`; the weekly carries its own shorter list
in `pipeline/briefing/weekly_parse.py`.

---

## VIII. One Newsroom Writes Everything

The same newsroom writes the TL;DR, the Opinion, the On Air rundown, the Weekly essays
and the History scripts. The formats differ; the writer does not. A reader who moves from
a feed card to a History episode meets the same habits: the particular before the general,
the source before the claim, the number instead of the adjective, the exit before the moral.

| Surface | Section | What the format asks for, on top of the cardinal rules |
|---|---|---|
| Feed card, TL;DR | News, The Brief | Third person, past tense, attribution first. The TL;DR is the card shortened, not rewritten. |
| Opinion | The Brief | Institutional "we", never "I". Evidence first, then the argument. Controlled emotion: concerned, resolute, gravely amused, awed by the stakes; never angry, sarcastic, contemptuous or preachy. End on the unresolved question. |
| Rundown | On Air | Present tense, one idea per sentence, attribution before the claim, reported speech instead of quotation marks. Numbers as words. |
| Essays, departments | Weekly | The same voice at essay length. No meta-reference to "sources" or "coverage"; say what happened. |
| The Argument | Weekly | Two benches, one story; every line the benches say is printed in the column. |
| Event pages, scripts | History | Arrive late, leave early. Contested numbers published as ranges. A hedge in the record is said aloud. |
| Promos | House | Two sentences: show the product, then the address. See X-b. |

---

## X. Quality Gates

A rule nobody can fail is not enforced. These are the gates that exist, by ID
and file, read from the code. If a rule is not in this table, it is a wish.

### Feed cards: `pipeline/editorial/standard.py`

Run at write time and again against the served HTML.

| ID | Catches | Mode |
|---|---|---|
| S-01 | Card does not link to `/story/<uuid>/` | enforced |
| S-02 | Summary under `MIN_SUMMARY_CHARS` | enforced |
| S-03 | Summary without terminal punctuation | enforced |
| S-04 | Unbalanced quotation marks | enforced |
| S-05 | Doubled word | enforced |
| S-06 | Broken abbreviation or decimal spacing | enforced |
| S-07 | Indefinite article disagreeing with the next sound | enforced |
| E-03 | First-person pronoun outside quotes | enforced |
| E-04 | Orphan subordinate clause | enforced |
| E-05 | Reputational claim without attribution | enforced |
| E-07 | Contested terminology in Void's own voice | advisory |
| E-08 | Unattributed passive evaluation | advisory |
| E-09 | Card that is mostly absence of information | advisory |
| E-11 | Second-person pronoun outside quotes | advisory |
| E-12 | Sentence isolated from the rest of the summary | advisory |
| E-13 | A number that is not in the sources | enforced, grounded |
| E-14 | A quotation that is not verbatim in the sources | enforced, grounded |

E-01, E-02, E-06 and E-10 are judged by the Stage 2 critique pass as L-rules; `docs/EDITORIAL-STANDARD.md`
maps them. The dash strip and the significance-word strip run on every card in `sanitize_editorial_text`.

### On Air rundown: `pipeline/briefing/radio_script_generator.py`

| ID | Catches |
|---|---|
| R-01 | Sign-on and sign-off that are not Void's exact lines; a sign-on that does not name the day |
| R-02 | Quotation marks (a quote is never read aloud; reported speech only) |
| R-03 | Numerals (the normaliser speaks them anyway; warns so the prompt learns) |
| R-04 | Clock forms and print datelines |
| R-05 | Banned phrases; a host addressed by name or thanked |
| R-06 | Segment word budgets, menu line count, brief item count |
| R-07 | Attribution after the claim instead of before it |
| R-08 | Wrong number or order of STORY segments; a kicker that repeats a told story |
| R-09 | A kicker on a day the lead's disaster severity forbids one |
| R-10 | One voice carrying too large a share of the words |
| R-11 | Sentences over the length cap |
| R-12 | Lead voice failing to alternate story by story; the second voice taking more than one line per story |
| R-13 | A `## SAY` respelling that is malformed or never used |

Two further rundown gates, grounded attribution and no unattributed legal or
causal assertion, land with a separate commit under the next free IDs; R-12
and R-13 above are already taken by the alternation and SAY rules.

### History scripts: `pipeline/history/script_format.py`, `tests/test_history_script.py`

| ID | Catches |
|---|---|
| H-01 | A quotation that is not in the event's own sources |
| H-02 | The document voice speaking outside a DOCUMENT segment |
| H-03 | A DOCUMENT segment with no author in its marker |
| H-04 | A quote whose speaker the narrator never names, or names wrongly |
| H-05 | A missing required segment |
| H-06 | An episode with no TURN: the disagreement is never shown |
| H-07 | Runtime outside the format target, measured at the narrator's own pace |
| H-08 | A dash in spoken copy (warn) |
| H-09 | A perspective account silently dropped from the PERSPECTIVE segment |
| H-10 | A proper name spoken aloud that is not in the sources (warn) |
| H-11 | A paraphrase or secondhand line read as the speaker's own words |

### History data: `tests/test_history_data.py`, `tests/test_history_copy.py`

Figure identity against its own link (the disambiguator must match the role), lifespans
that run the right way, no act credited after death, Wikidata IDs shaped like QIDs; the
dash gate on every prose field, quotations and published titles exempt; the speaker-shape
gate (a speaker names somebody, or points at something a reader could check).

### House promos: `pipeline/briefing/house_promos.py`, `tests/test_house_promos.py`

| ID | Catches |
|---|---|
| P-01 | Duplicate id, unknown section, or a promo inside the section it advertises |
| P-02 | Not exactly two sentences |
| P-03 | Digits |
| P-04 | A number word not in `ALLOWED_NUMBER_WORDS` |
| P-05 | "twenty" without the `feed_size` claim, or while `feed.json` says otherwise |
| P-06 | A borrowed phrase or a kill-list word |
| P-07 | Em or en dash, quotation marks, exclamation mark |
| P-08 | Second sentence that is not the address |
| P-09 | Estimated duration outside the band, or recorded seconds that disagree with it |
| P-10 | An unknown claim; a section with too few eligible promos |

### Served sections: `scripts/verify_sections.py`

Runs in CI against the live site. Its H-01..H-04 are a separate namespace from
the script rules above.

| ID | Catches |
|---|---|
| W-01 | Issue number or Monday-to-Sunday week range missing |
| W-02 | A stale issue |
| W-03 | A cover image without a free licence |
| W-04 | `/weekly` served as a client shell instead of prerendered |
| W-05 | Archive missing or malformed |
| W-06 | A back issue that does not resolve |
| W-07 | Browser payload leaking what a browser does not need |
| W-08 | An em or en dash in the served `/weekly` prose |
| W-09 | An audio edition without its ordered chapter rail and sidecar |
| H-01..H-04 | `/history/` or `/weekly/` redirecting home; a thin catalog; an event image without a free licence; a catalogued event not prerendered |

### Copy that restates a number

`frontend/test/copy-facts.test.mjs`: no component restates the feed size in prose; source
and country counts match the roster; ranking weights sum to the whole and match the engine.
`tests/test_docs_facts.py`: CLAUDE.md's own counts match the disk; this document carries no
dash, names Kokoro, and does not describe the retired hosts; every doc that states retired
infrastructure as current carries the Historical banner.

## X-a. What Is Not Yet Enforced

Said plainly, so nobody reads the tables above as complete.

- **Weekly prose.** The weekly's own list is shorter than the kill list, no number-in-source or
  quote-verbatim check runs on it, a failed regeneration ships, and no served kill-list gate
  exists yet in `scripts/verify_sections.py`.
- **The daily Opinion.** Its prompt carries the grounding line, but no E-13/E-14 check, no entity
  check and no kill-list scan run on its output. Ungated until the grounding test lands.
- **Audio claim versus summary.** Nothing checks that what On Air, The Argument or the Opinion
  audio asserts matches the summary it was built from. R-02 is advisory. Significance words are
  never stripped from audio text.
- **About and Privacy.** No served check beyond the source and country literals. Privacy
  describes a retention mechanism that no longer runs.
- **Frontend string literals and accessible names.** No dash or kill-word scan.

## X-b. House Promos

A promo is publishing, and Rule 1 applies to it: nothing in it may be wrong.
The pool lives in `data/promos/house.yaml`; every rule below is asserted by
`tests/test_house_promos.py`, and a pool that fails does not render.

- **Two sentences.** A pitch, then the address. The first sentence earns the
  second; the second is always "Visit news.voidvision.org to check out
  <section>."
- **Show the product, do not praise it.** One concrete thing the section does
  ("every line the two benches say is printed in the column"), never a
  claim about how good it is.
- **No number that goes stale.** No source, country or episode counts. The
  few number words allowed are each tied to a constant in the code.
- **Nothing borrowed.** The On Air and Weekly banned lists apply, and so does
  the kill list above. No exclamation marks.
- **Never inside the section it advertises.** On Air never hears an On Air
  promo.
- **After the designed ending, under the outro.** On Air's tag, Weekly's open
  question and History's particular are all still the last words spoken in
  the programme's own voice. The promo is a different voice, the house
  voice, read slower than the programmes, over its own bed under the outro's
  held bars, and the outro's own fall to silence still closes the file.

> Every line the two benches say is printed in the column. Visit
> news.voidvision.org to check out The Argument.

## X-c. The Two-Newsroom Finding

The 2026-09-21 brand audit set one served paragraph from each surface side by side. The
feed card, the TL;DR, the On Air rundown, the History summary, the History script, the
house promo and About read as one house: concrete, attributed, short sentences, the
particular first, the exit early. The daily Opinion and the Weekly prose read as a second
house: abstract, hedged, adjectival, self-referential about "sources" and "coverage". The
History summary averaged six numbers a paragraph and no hedges; the Weekly cover, one
number and two hedges, at more than twice the sentence length. The split follows the
plumbing, not the writer's taste: the surfaces whose prompts carry the grounding line and
whose output passes through `sanitize_editorial_text` sound like one house, and the
surfaces that do not, do not. The rule that follows: every prompt carries the grounding
line ("Every fact MUST appear in the provided articles. Do not supplement with prior
knowledge."), and every written surface passes the shared kill list before it ships.

---

## XI. The One-Line Test

If someone reads thirty seconds of Void News, or listens to thirty seconds of On Air, and
thinks "this sounds like people who actually know what they're talking about, discussing
the news without performing for me", the brand is working.

If they think "this sounds like a podcast trying to explain the news to me", the brand has failed.
