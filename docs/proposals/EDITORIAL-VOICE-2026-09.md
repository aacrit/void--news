# Quotes, attribution and framing: proposals

Four defect families the CEO flagged on the 2026-09-06 feed keep recurring
across reviews. This document reports the current logic for each, shows what it
does on the live text, and puts options. Nothing here is implemented. The
detection side of 5b, 5c and 5d already ships as advisory validators
(`docs/EDITORIAL-STANDARD.md`, rules E-05, E-07, E-08, E-09); what needs a
decision is what the pipeline should DO about a finding, and the one rule that
requires deleting working code (5a).

---

## 5a. The pronoun scrubber is corrupting quotations

### What it does now

`pipeline/summarizer/cluster_summarizer.py` carries a substitution table,
`_FIRST_PERSON_SUBS`: `we` becomes `they`, `our` becomes `their`, `us` becomes
`them`, `my` becomes `their`. There is no rule for `I`, `me`, `mine`, `you`,
`your` or `yours`. `_convert_first_person_outside_quotes` runs it as the last
step of the hygiene chain, on the LLM path and on the summary floor, and it
tracks straight and curly DOUBLE quotes only. Single quotes are not tracked;
nesting is not handled. The system prompt prescribes the same mapping.

### What it produced

Three live examples, all of them unquoted indirect speech, so the scrubber
operated on every one:

> She also told investigators she had never smoked a cigarette in **their** life.

> Gary Moss, who is blind, experienced the Cybercab in Austin, noting its
> automatic doors and describing it as a glimpse of regaining **their**
> independence.

> Vance also told El-Sayed to keep **their** wife's name the hell out of
> **your** mouth.

The first two swap person without fixing number: a singular antecedent takes a
plural possessive. The third is the clearest: the original is "keep **my**
wife's name the hell out of **your** mouth". `my` was rewritten, `your` had no
rule and survived, and the result has Void addressing the reader. The served
gate cannot see any of them, because it only detects the UNCONVERTED forms.

### Proposal

**Delete `_FIRST_PERSON_SUBS` and stop rewriting pronouns.** A quotation is
verbatim, and a pronoun inside any quotation span (double, single, curly,
nested) is never touched. Outside quotations, no substitution at all: converting
indirect speech to the third person means rewriting the sentence, which is a
generation task, not a regex.

The layers that replace it already exist:

* the prompt keeps the third-person instruction, minus the lossy `my` becomes
  `their` example;
* E-03 flags a first-person pronoun outside quotes and E-11 flags a
  second-person one, both live today;
* the critique pass (Block 2) regenerates the sentence properly, so
  "she had never smoked a cigarette in my life" becomes "in her life", not
  "in their life".

Cost: for one run, between deleting the scrubber and the critique pass landing,
a first-person pronoun could reach a card instead of being silently mangled.
That is the better failure: it is visible, the gate catches it, and it does not
put words in a named person's mouth.

Fixtures: the three strings above.

---

## 5b. Unattributed reputational claims

### What it does now

`_strip_unattributed_reputational_claims` drops a SENTENCE that makes a
reputational or criminal claim with no attribution cue and no quotation. Nine
regexes back it, mirrored in `summaryHygiene.ts` as a render-time guard. Four
rules fire: a verification assertion on a reputational claim, a reputational
claim about a relative, an unattributed verb-led claim, and an association term
without an identifiable subject.

### What it let through

The 09-06 Mamdani card, 9 sources, labelled Far Right. Every sentence survived.
Traced against the compiled regexes:

| sentence | why it survived |
|---|---|
| "...the 25th anniversary of the 9/11 Islamic terror attacks." | the negative-association list arms the relative and verification rules but cannot drop a sentence on its own |
| "Kassem previously represented Ahmed al-Darbi, a Saudi al-Qaeda member who pleaded guilty to terrorism charges..." | "pleaded guilty" is not in the criminal-allegation list ("convicted of" and "found guilty of" are) |
| "Al-Darbi's sister was married to Khalid al-Mihdhar, one of the five hijackers..." | the relative rule requires the sentence to be reputational on its own, and "hijackers" is in no trigger list |
| four sentences of criticism from three named critics | no response from Mamdani or Kassem is required anywhere |

The damage is juxtapositional: Mamdani, to a pen, to Kassem, to a former
client, to that client's sister's husband. Every rule in the filter is
per-sentence, so no rule can see the chain. The headline
("NYC Mayor Mamdani Gives 9/11 Pen to Al-Qaeda Terrorist's Former Lawyer") is
never passed through the filter at all: headlines only get
`normalize_headline`, which strips outlet suffixes and shout words.

### Options

1. **Widen the verification and allegation vocabulary.** Add "pleaded guilty",
   "pled guilty", "hijacker", "bombing", "member of". Cheap, already the shape
   of the existing rule. Catches the al-Darbi sentence. E-05 does this today as
   an advisory check.
2. **Require that a named accuser be introduced.** Weak here: all three critics
   are introduced by name and title, and the card is still unfair.
3. **Drop claims about non-public relatives and associates** whether or not the
   sentence is reputational on its own, and treat a chain of association
   sentences as one claim. Catches the sister sentence, which is the single
   most defamatory line on the card.
4. **Right of reply.** When a summary criticises a named living person, it must
   carry that person's response, or state that none was given, sourced from the
   articles. Otherwise regenerate with that instruction; drop if the article set
   contains no response and there is more than one critic.

**Recommendation: 1, 3 and 4 together, and run the filter on headlines.** Option
4 is the journalistic rule and the only one that addresses what actually made
the card unfair, and it is checkable by the critique model with the article text
in the prompt (L-06). Options 1 and 3 are deterministic and cheap. Option 2 is
not worth the complexity.

Open question for the CEO: right of reply as a **drop** or a **regenerate**?
Dropping is safer and, at 20 slots with a 35-candidate bench, affordable.

---

## 5c. One side's terminology in Void's voice

### What it does now

The neutral-construction rule exists, but not where it was assumed. It is a
headline RE-RANKING lexicon inside the clusterer: `_CONTESTED_POLICY_TOPICS`
plus `_LOADED_HEADLINE_PHRASES` penalise a loaded candidate headline and reward
a procedural one, symmetric by design. It covers abortion, immigration, guns
and gender topics, has no geopolitical vocabulary, and only re-ranks among
member headlines. It never touches summary bodies. If every member headline is
loaded, the least loaded one still ships.

Summary bodies have one abstract prompt sentence ("Neutral framing of competing
legitimate perspectives") and a warning-only prohibited-terms scan whose list is
about sensationalism, not contested terminology.

### What shipped on 2026-09-06

Unquoted and unattributed, in Void's own voice:

| rank | text |
|---|---|
| 24 | "clearing terrorists and their strategic underground network... funded by the Iranian terror regime" (IDF release phrasing, verbatim) |
| 24 | "The IDF struck several weapons storage facilities and terrorist infrastructure" |
| 22 | "the 25th anniversary of the 9/11 Islamic terror attacks" |
| 5 | "Huckabee's use of the term terrorists is typically reserved for Palestinian militants" (the scare quotes were stripped, so Void appears to endorse the usage) |
| 26 | "The Spanish opposition is described as engaging in warmongering"; "Sánchez is seen as standing alone in defence of Morocco" |
| 49 | "Milei had reiterated Argentina's sacred claim to the Falklands" |

Defensible and correctly left alone: "right-wing extremist" (a German
intelligence classification), "genocide" inside a quotation and in a Hague
conviction, "known as Las Malvinas" as a gloss.

False positives any lexicon must avoid, all present in the same feed:
"Schleswig Foot Regiment" (contains "regime"), "baby bottlenose dolphin",
"Russia's full-scale invasion of Ukraine" (the military sense).

### Proposal

A symmetric contested-terms table, term to neutral construction, applied to
summary bodies. Shipping as advisory rule E-07 today, with word boundaries and
a context guard on "invasion" so the military sense passes. A term is flagged
only when it sits outside quotation marks AND its sentence carries no
attribution cue.

The passive shapes ("is described as", "is seen as") are rule E-08.

**The post-processor does not rewrite.** Rewriting text in place is exactly how
the pronoun bug happened. The validator flags; the critique pass regenerates
with the table in the prompt.

Decision needed: promote E-07 and E-08 from advisory to enforced. On today's
feed that is 1 card in the top 20 and 5 in the top 50.

---

## 5d. Content-free summaries

### What it does now

Nothing counts absence. `_collapse_unknown_padding` collapses a run of
CONSECUTIVE unknown sentences, keeping the first. The 09-06 Bolivia card
interleaves them, so `prev_unknown` resets every other sentence and nothing
collapses.

### The card

"Bolivia Army Base Blasts Leave Two Dead, 14 Missing", 8 sentences, 134 words,
two facts and one location. Five of the eight assert absence of information:
the cause "remains under investigation", details "have not been immediately
released", the toll "is based on initial reports", investigations "are ongoing",
the damage "is still being evaluated".

The obvious phrase list scores this card **0 of 8**, because it says none of
those things in the expected words. Using the summarizer's own unknown-padding
vocabulary scores it **5 of 8**, and every other displayed card in six runs
scores at most 1.

### Proposal

Rule E-09, shipping as advisory: fail at three or more absence sentences, or a
quarter of a card of six or more sentences. The gap between the Bolivia card
(62 percent) and the next worst (8 percent) is a factor of eight, so any
threshold in that range isolates it with no false positives on six runs of real
data.

Action on failure: regenerate once with "state unknowns once", then drop. At 20
slots with a 35-candidate bench, dropping a card that carries two facts in eight
sentences costs nothing.

---

## What is being asked

1. **5a**: approve deleting the pronoun scrubber (this deletes working code and
   is the only proposal that can regress a run before the critique pass lands).
2. **5b**: confirm options 1, 3 and 4, and choose drop or regenerate for right
   of reply.
3. **5c**: promote E-07 and E-08 from advisory to enforced, and confirm the
   contested-terms table reads as symmetric.
4. **5d**: promote E-09 from advisory to enforced.
