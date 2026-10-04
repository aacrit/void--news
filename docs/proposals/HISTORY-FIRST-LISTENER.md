# History audio: the first-time listener

Proposal, 2026-10-04. Written by the script writer (Fable) after the CEO's note on the
eight finished Orpheus episodes: "Voice and delivery seems great. But are we giving
enough info to a first timer about the story itself? Let's make sure of that."

Scope: the eight cinematic variants in `data/history/scripts/variants/`, read as a
general adult who has never heard of the event and may live outside the region. The
pilot revision is `partition-of-india.firsttime.txt` in the same directory. The approved
cinematic variants are untouched, the event YAML is untouched, no export was re-run.

Line numbers below are the line numbers of the committed `.cinematic.txt` files.

---

## 1. What was measured

Two checkpoints, five questions, marked yes / partial / no:

- **Checkpoint A**, the end of OPEN + TITLE (about 90 seconds in).
- **Checkpoint B**, the end of SCENE 1.
- **WHERE** (a country or continent a newcomer can place), **WHEN** (a year), **WHO**
  (the sides or actors, named), **WHAT** (what happened, in one sentence a newcomer
  could repeat), **WHY** (the stakes, shown as a particular, never asserted).

Then, across the whole episode: every person the narrator names, with or without a role
on first mention; every term, institution, place or acronym a newcomer would not know,
glossed or not on first use; whether each SCENE orients in its first line (a time and a
place); whether the five PERSPECTIVEs explain their own sources; and what a newcomer
needs that the episode never says. For each missing thing the record was checked
(the event YAML, the ledger, the thesis) before it was called addable, because under
Rule 1 only what the record holds can go into a script.

The standard this proposes was then applied to Partition and gated (section 6).

---

## 2. Scorecards

### 2a. The five questions

| Episode | A: where | A: when | A: who | A: what | A: why | B: where | B: when | B: who | B: what | B: why |
|---|---|---|---|---|---|---|---|---|---|---|
| Partition of India | partial | yes | no | partial | yes | partial | yes | partial | no | partial |
| Apollo 11 | partial | yes | no | yes | yes | partial | yes | partial | yes | partial |
| Srebrenica | partial | yes | no | partial | partial | partial | yes | partial | no | partial |
| Cambodian genocide | partial | yes | no | yes | yes | partial | yes | partial | partial | partial |
| Scramble for Africa | yes | yes | partial | yes | yes | yes | yes | partial | yes | yes |
| 1918 influenza | partial | yes | n/a | yes | yes | partial | yes | partial | yes | partial |
| Haitian Revolution | no | yes | partial | no | partial | partial | yes | no | partial | no |
| Armenian genocide | partial | yes | partial | yes | partial | partial | yes | partial | yes | partial |

Reading across: WHEN is always answered (the TITLE carries it). WHAT in one sentence
is answered before the end of SCENE 1 in two episodes of eight (Apollo, Scramble).
WHERE is placed for a newcomer in one (Scramble: Berlin, Africa). WHO at Checkpoint A
is answered in none: every cold open withholds the names, which is the format doing its
job, but nothing after the TITLE then pays the debt.

### 2b. Names, terms, signposts

| Episode | Names without a role at first mention (line) | Terms used before glossed (line) | Scenes that open without a time or place |
|---|---|---|---|
| Partition | Abell 40, Nehru 57, Nawab of Bhopal 86, Ismay 91, Liaquat Ali Khan 91, Jinnah 166 | Punjab commission 40, the award 46, Constituent Assembly and the pledge 57, Viceroy 75, Kashmir 87, tehsils 90, West Punjab 99, the two Punjabs 111, Dominion 143, Chief Liaison Officer 144, Congress and the League 154, princely states 160, lakhs 196; Pakistan is not spoken by the narrator until 215 | SCENE 4 (98), SCENE 6 (133) |
| Apollo 11 | Armstrong 37 (role implied), Glushko 134 (partial); Aldrin and Collins are never spoken at all, though both are in the record | "a country" 25 (the United States is first named at 56), Tranquility Base and Eagle 44, suborbital hop 56, rope memory 72, Sputnik 132 (not "the first satellite"), N one 134, Sea of Crises 135, Cape Kennedy and the Southern Christian Leadership Conference 141 | SCENE 3 (71) |
| Srebrenica | Karadzic 50, Karremans 51, Mladic 56, Krstic 56, Atlagic and Martinovic 153, Karcic 173 (partial) | Bosnia unlocated 22, Drina Corps 50, the tribunal 66 (introduced only at 123), the Secretariat 67, Dutchbat 165 (only inside a read), Republika Srpska 153, the municipalities 172; "Bosnian Muslim" is first heard inside a read at 124; the war of 1992-95 is never stated | none (dated throughout) |
| Cambodia | Sihanouk 150, Pol Pot 150, Nate Thayer 150, Nuon Chea and Khieu Samphan 177 | Khmer Rouge 34 (who they were is never said), Angkar 35, the court 25 and 67 (never named as the UN-backed tribunal until 177), cadres 80, the convention of 1948 122, the Council 150 (the Security Council, never introduced), Ieng Sary 171 (in a read), base person 198 | SCENE 2 (49), SCENE 4 (89: "the last morning" of what is said only in the CLOSE) |
| Scramble | Bismarck 38, Rennell Rodd 174, Rodney, Fanon and Nkrumah 181 (partial), Abd el-Kader, the Mahdi and al-Mukhtar 196; Menelik 173 is named but Ethiopia never is | the Congo 39, Matabeleland 59 (Zimbabwe is in the record), British South Africa Company 59 (Rhodes is never spoken), indunas 60, the Charter 73, Hornkrans 78, Herero 80, Congo Free State 95 (Leopold and Belgium are never spoken), Mantumba 102, Bolobo 189 | none; every scene opens on a place and a date (the best of the eight) |
| 1918 influenza | Nirala 104 (the record calls him a poet), Hatchett, Mecher and Lipsitch 157, Johnson and Mueller 185, Spreeuwenberg 187 | the war is never named (the First World War is in the record), Camp Devens 33 (an army camp of that war), Sanitary Commissioner 78, Registrar-General 88, Western Samoa 122 (administered by New Zealand, in the record), the commission 174 | SCENE 2 (57: a day, no year or country), SCENE 3 (76), SCENE 4 (104) |
| Haiti | Toussaint Louverture 69, Leclerc 157, Charles the Tenth 184 (the record says King) | Saint-Domingue 30 (never glossed as the French colony that became Haiti until a read at 149), "the workshops of the North" 40 (the enslaved, never said in SCENE 1), the commission of the French Convention 41, the Caiman 42, Haut-du-Cap and the Cap 49 and 60, fort de Joux 91, Gonaives 115, vodou 146, the hundred and fifty million francs 171 (explained at 185) | none; every scene opens on a place and a date |
| Armenia | Enver 144, Umit Kurt 161 (partial), Lemkin 170 (the record says jurist) | the Porte 33 and 49, Constantinople 31 (never placed as the Ottoman capital), Trebizond and Sivas 51, the war is never named outside the reads (the record carries it), "the Young Turk regime" 162 (in a read), the Republic 131 (of Turkey, partial); who the Armenians were (a Christian people of the empire, about two million, both in the record) is never said | SCENE 4 (105, partial) |

One Rule 1 flag found on the way: Armenian genocide line 66 calls Scheubner-Richter "the
German administrator there"; the record calls him the German vice-consul in Erzurum. A
role the record does not give is a claim, and that one should be corrected at the next
re-render whatever is decided here.

### 2c. The PERSPECTIVE sections

All eight introduce each account in its own terms and name a source for most reads
(a court, a report, a named author, a foundation). None carries a line before the
accounts saying what the whole episode was built from. Four carry fragments of one
(Partition 112 and 189, Scramble 181 and 198, Haiti 177, Armenia 160: "books this
programme could not read"), scattered where they arise rather than stated once where a
newcomer would use them. The denial account in Srebrenica (130, 152) and the regime's
account in Cambodia (148) are framed correctly as evidence rather than versions.

### 2d. What a newcomer needs that the episode never says

Checked against the record. "In record" means the YAML, the ledger or the thesis carries
it, so it can be added; "not in record" means it cannot.

| Episode | Needed and in the record | Needed and NOT in the record |
|---|---|---|
| Partition | That India was British and this was independence; the names India and Pakistan, said by the narrator; that the division ran on religion (Muslim-majority districts to Pakistan); that two provinces, the Punjab and Bengal, were cut; which half of the Punjab went where; that the Sikhs were the third community of the Punjab; roles for Nehru and Jinnah | A role for Sir George Abell, Lord Ismay or Liaquat Ali Khan (the record names them only as writers and recipients of letters); a plain gloss of "Viceroy" beyond "last Viceroy of India, oversaw transfer of power"; the value of a lakh as a bare number (the record defines it only by example, "17 lacs i.e. a million and about seven hundred thousand", so H-18 cannot see 100,000) |
| Apollo 11 | Aldrin (second to walk) and Collins (orbited alone); the United States, named in the OPEN; Sputnik as the first satellite | Nothing material |
| Srebrenica | Where Bosnia is and what the war was (Bosnia and Herzegovina declared independence from Yugoslavia in April 1992; a war to December 1995); that the attackers were the Bosnian Serb army and the dead Bosnian Muslim men and boys; roles for Mladic, Karadzic, Krstic, Karremans | Who Atlagic and Martinovic are beyond their names (the record holds the paper, not the authors) |
| Cambodia | Who the Khmer Rouge were (a communist movement, the regime called Democratic Kampuchea) and that Pol Pot led it; roles for Nuon Chea and Khieu Samphan; Phnom Penh as the capital; that the court was set up with the United Nations (already partly at 177); Thayer's interview as a journalist's (the record names the Far Eastern Economic Review) | What "Angkar" means (the record holds the word only inside Vann Nath's testimony); Sihanouk's role (no hit in the record) |
| Scramble | Leopold of Belgium and the Congo Free State; Ethiopia for Menelik; Bismarck as German Chancellor; Namibia and Zimbabwe as present-day names | What an induna is (not in the record) |
| 1918 influenza | The First World War as the carrier (troopships, "the war built the roads"); Nirala as a Hindi poet; Camp Devens as an army camp; Western Samoa under New Zealand | A role for Johnson and Mueller or Spreeuwenberg (the record holds the citations only) |
| Haiti | That Saint-Domingue was France's Caribbean sugar colony and became Haiti; that the rising was by enslaved people (500,000 in the record); "the world's first Black republic" (the subtitle); Toussaint as formerly enslaved and governor; Leclerc as the general Bonaparte sent; Charles the Tenth as King of France | Nothing material |
| Armenia | The First World War as the setting; the Armenians as a Christian people of the Ottoman Empire, about two million in 1914; Constantinople as the capital; Enver as War Minister; Lemkin as a jurist | A gloss of "the Porte" (the record uses the term without defining it; the OPEN's own "the government" at 31 is the sourced form, so the term can be dropped rather than glossed) |

---

## 3. Findings, ranked

1. **No episode says what happened in one sentence before its first scene ends.** The
   cold open withholds on purpose; nothing after the TITLE then pays the debt. A
   newcomer reaches the first document knowing a date and a mood. (8 of 8; 2 recover
   by the end of SCENE 1.)
2. **The place is not placed.** Bosnia, Saint-Domingue, Phnom Penh, Constantinople,
   "a country" that landed on the Moon, Matabeleland, Camp Devens: named, never located
   in terms a newcomer can hold. (6 of 8.)
3. **Names arrive without a job.** Thirty one first mentions across the eight carry no
   role. The worst runs are Srebrenica (four commanders in one scene), Cambodia (the
   leader of the regime at line 150, never introduced), Partition (Nehru, Jinnah).
4. **Institutions are used before they are introduced**: "the tribunal" (Srebrenica
   66), "the Council" (Cambodia 150), "the court" (Cambodia 25), "the Porte" (Armenia
   33), "Dutchbat" (Srebrenica 165).
5. **The war that frames the event is never named** in the three episodes that sit
   inside one: the Bosnian war, and the First World War twice.
6. **No "how we know" line.** Every episode rests on a specific, limited record and says
   so only in fragments.
7. **No CLOSE restates the facts.** All eight close on the motif, which is right; none
   spends one line before it on the particulars a newcomer should leave with.
8. **Scene signposting is mostly good** (Scramble, Haiti, Armenia open every scene on a
   place and a date) and weakest in the influenza episode (three scenes open without a
   place or a year) and Cambodia (two).

---

## 4. The orientation standard

Eight rules for the script brief, written so that a Burns episode stays a Burns episode.
The register is kept by the form: present tense, declarative, one fact per sentence,
documents still read plainly, and no sentence that tells the listener what it is about
to do. The CEO's note is met by making orientation a property of SCENE 1 and of first
mentions, not by adding a preamble.

### O-1. The establishing passage

**Adopted, adapted.** The suggestion was an establishing passage right after the TITLE,
3 to 5 short lines: place, year, sides, stakes. Adopted, with one change: it is the
first three or four lines of SCENE 1, in the scene's own present tense, not a segment of
its own. A separate segment costs 5.3 seconds of silence grammar and, more
important, shifts every chapter index, and the published theses point at chapters
(`episode_marks`, T-10). Inside SCENE 1 the passage orients and then the scene arrives.

Content, each as a particular: the country or continent in words a newcomer can place;
the year; the sides, named; what happened, in one sentence; and the stakes shown
(a number, a document, a consequence), never asserted. Budget: 60 to 100 words.

Pilot: "The summer of nineteen forty seven. India is British, and Britain is leaving."
Then the plan read to the House of Commons, the two new countries by name, the religious
basis of the division, and the two provinces the line must cross.

### O-2. A role with every first-mentioned name

**Adopted.** Every person the narrator names carries, in the same line as the first
mention, a role from the record or the function they have in the story. "Cyril
Radcliffe, a British barrister who had never been to India." Where the record gives no
role (Abell, Ismay, Liaquat in Partition), the name is carried by its function ("the man
who answered them", "answering for the Viceroy", "who protested from the Pakistani side")
or cut. A name the listener cannot use is cut before any line of narration is.

### O-3. A gloss with every term

**Adopted.** Every institution, office, legal term, local administrative word and
acronym is glossed on first use, in an appositive of under ten words, or replaced by
the plain word. "The Constituent Assembly of India, the body that will write its
constitution." "Three of the four tehsils that make up Gurdaspur." "Two independent
Dominions, two new countries." Where the record itself does not define the word (Angkar,
induna, Porte, lakh as a number), the term is dropped or carried in a form the record
licenses, not glossed from memory.

### O-4. Every scene opens on a time and a place

**Adopted.** The first line of every SCENE carries a time cue (a date, a year, "two
months later", "go back a week") and a place cue (a town, a building, "the same hall").
The format already says "arrive late: one moment, one place"; this makes the place and
the moment audible in the first sentence.

### O-5. One "how we know" line before the accounts

**Adopted.** The TURN that opens the five accounts carries one line naming the kinds of
document the episode was built from and that larger works could not be read. The
fragments now scattered through the scripts ("in books this programme could not read")
fold into it. The denial or perpetrator framing line stays where it is.

### O-6. The CLOSE restates the particulars

**Adopted, adapted.** The CLOSE keeps its ending on a particular and its motif. Before
them, one or two lines restate what a newcomer should leave with, as facts not as a
moral: the year, the two sides, the one number the record best supports, the thing that
is still open. The pilot: "Two countries were made from one on the fifteenth of August,
nineteen forty seven. The line through the Punjab was signed on the twelfth and
published after the ceremonies."

### O-7. Each account says who holds it

**Already in force, now stated.** The first line of every PERSPECTIVE names whose account
it is (a state, a people, a profession, a court) before it argues. All eight do this.

### O-8. The war, when there is one

**New.** Where the event sits inside a war the record names, the war is named in the
establishing passage. It is the first thing a newcomer reaches for.

### Rejected

- A spoken preamble ("This episode tells the story of...") or a narrator's summary
  before the OPEN: it is the textbook voice the series exists not to have, and the cold
  open's enigma depends on the facts arriving late.
- A glossary read aloud, or a "key figures" roll call: a list is not a scene.
- Repeating the orientation at every scene: once, early, and then the signpost (O-4).

### Word budget: what to cut to make room

The standard costs 150 to 250 words of narration on a script written to the ceiling.
In order:

1. A second document from the same speaker, folded into one line of narration (the
   pilot folds Mountbatten's press conference into SCENE 3; the public/private contrast
   survives, the second voice does not).
2. Asides merged into the DOCUMENT segment they follow, as trailing narration: the
   Cambodian variant already does this. Each segment saved is about 13 words of H-07
   budget at 146 wpm, because the silence grammar is priced per segment.
3. The second TURN at 15 to 30 words a line, never 45.
4. Names with no role and no function in the story (Prasad in the pilot).
5. Repeated refusals ("could not be read here") to one how-we-know line.
6. Never a read, and never a perspective.

---

## 5. Checks a gate could run

Each is written against `pipeline/history/script_format.py` as it stands. "Mechanisable"
means a regex or a lookup against the YAML can fail it; "reader" means the gate can only
point and a person must judge.

| Check | What it asserts | Mechanisable? |
|---|---|---|
| **H-23 establishing window** | Within the first 120 words after the TITLE: a spoken year between 1000 and 2100 (`spoken_numbers`), and a place token from the YAML's `country` or `region`, or a capitalised YAML token that is not in `key_figures`. | Yes, as a warn. WHAT and WHY in one sentence cannot be read by a regex: reader. |
| **H-24 first-mention role** | For every `key_figures` name and every DOCUMENT `author` surname spoken in an N: line, the first such line also carries a role cue: a stemmed word from that figure's YAML `role`, a word from a role lexicon (minister, president, general, judge, governor, viceroy, ambassador, consul, commander, chairman, barrister, poet, painter, survivor, historian, economist, prince, king), or an appositive comma directly after the name. | Yes, approximately; it will pass a bad appositive and must stay a warn. The sense is the reader's. |
| **H-25 acronyms and institutions** | Any all-capitals token of three letters or more (ECCC, ICTY, NATO, CUP) and any token from a short per-catalogue list (Porte, Dutchbat, Angkar, tehsil, induna, Dominion, Viceroy) appears first in an N: line that also carries "the X, <gloss>" or the plain word. | Acronyms and the list: yes. The open class of terms: reader. |
| **H-26 scene signpost** | The first N: line of every SCENE carries a time cue (a spoken year, a month, an ordinal day, or one of later / earlier / that night / go back / the same) and a capitalised place token from the YAML that is not a person. | Yes, as a warn; "the same hall" and pronoun places will need the reader. |
| **H-27 how we know** | The TURN segment preceding the first PERSPECTIVE contains one of: could read, this programme, held here, the record, from what. | Yes, trivially. |
| **H-28 closing particulars** | The CLOSE carries the event's `date_sort` year as a spoken number and the YAML `country` word (or, for multi-country events, two perspective names). | Yes. Whether the restatement is a fact and not a moral: reader. |
| **O-8 the war** | If the YAML text contains "World War", "war that had begun" or `category: war`, the first 120 words after the TITLE contain "war". | Yes. |

Every one of these should land as a warning first, over the 78 committed scripts, and be
read the way H-10 was read: the flags are either noise, a rewrite, or a cut. A rule
nobody can fail is not enforced, but a rule that fires on every honest script teaches
the writer to wave it through. The pilot would pass all seven today.

---

## 6. The Partition pilot

File: `data/history/scripts/variants/partition-of-india.firsttime.txt`. Sources: the
event YAML, `data/history/evidence/partition-of-india/`, and the published thesis
`data/history/theses/partition-of-india.md`. Nothing else.

### Before and after

| | cinematic (approved) | first-time (pilot) |
|---|---|---|
| words | 1,800 | 1,876 |
| narration / reads | 1,481 / 319 | 1,589 / 287 |
| segments | 41 | 36 |
| minutes at bm_lewis 146 wpm (H-07) | 14.89 | 14.96 |
| minutes at 160 wpm | 13.81 | 13.84 |
| scenes / documents / asides / rests / turns / perspectives | 6 / 11 / 7 / 7 / 2 / 5 | 6 / 10 / 3 / 7 / 2 / 5 |
| document reads, each verbatim from a named extract | 11 | 10 |
| Nehru clip slot | signed, admitted at 28.05 s | unchanged, admitted at 28.05 s |

### Orientation lines added, verbatim

SCENE 1 (the establishing passage, O-1, O-3):

> The summer of nineteen forty seven. India is British, and Britain is leaving.
>
> On the third of June the Prime Minister reads the plan to the House of Commons in London: from the fifteenth of August, two independent Dominions, two new countries, India and Pakistan.
>
> The division runs on religion: Muslim-majority districts to Pakistan, the rest to India. Two provinces hold both kinds, the Punjab in the west and Bengal in the east.
>
> The line through them is not drawn. One sentence of the statement decides what it will be made of.

Roles and glosses (O-2, O-3), each at first mention:

> Clement Attlee, the Prime Minister of Britain, reading the statement to Parliament.
>
> Two commissions are to draw the line, one for the Punjab and one for Bengal. Their secretaries asked for a map, and Sir George Abell, who answered them, sent none: any map, read with the figures of nineteen forty one, would suffice.
>
> Cyril Radcliffe, a British barrister who had never been to India, chaired both. He had until the fifteenth of August.
>
> Cyril Radcliffe, in his decision, which the record calls the award.
>
> The fourteenth of August, in Delhi. The Constituent Assembly of India, the body that will write its constitution, is sitting, and towards midnight Jawaharlal Nehru, soon to be India's first Prime Minister, rises to move the pledge.
>
> One district of the Punjab explains why the line is still argued about. In Gurdaspur every count puts the Muslim share a little over half, and the judges of the commission could not agree which count should rule.
>
> On its northern edge lies Kashmir, a princely state with a ruler of its own, so placed that it could join either country.
>
> Lord Mountbatten, the last Viceroy of India, overseeing the handover, told the press on the fourth of June that the commission was unlikely to put the whole of Gurdaspur on the Pakistani side.
>
> In private, two months later and eight days before the award was signed, Mountbatten received the Nawab of Bhopal, a prince with a state to place. The record his staff kept has him saying this.
>
> The award gave India three of the four tehsils that make up Gurdaspur, citing a canal and a hydro-electric scheme. Its reasons do not mention Kashmir.
>
> Lord Ismay, answering for the Viceroy, told Liaquat Ali Khan, who protested from the Pakistani side, that the Viceroy had said from the outset he must have nothing to do with the commissions.
>
> The Fact Finding Organisation of the Government of India examined nearly fifteen thousand witnesses, from two thousand and ninety four of the nineteen thousand nine hundred and fourteen villages of West Punjab, the half that went to Pakistan.
>
> The migration too: the House of Commons was told in December that eight and a half million had moved between the two halves of the Punjab, Hindus and Sikhs east into India, Muslims west into Pakistan.
>
> That December, the two governments agreed that abducted persons were to be restored to their own country, even against their wishes.
>
> The following April, the officer India kept in Lahore for the recovery reported about a hundred women still to be found in one district, and sixteen recovered between the first and the twenty fifth.
>
> The British account is administrative. The Indian National Congress, the party of Nehru, and the Muslim League, the party of Jinnah, both accepted the plan; Indian leaders chose the commissions and drafted their terms, and the Viceroy kept clear of the award.
>
> On the state, it holds that something was built from almost nothing. Muhammad Ali Jinnah, leader of the League and founder of Pakistan, addressed its assembly on the eleventh of August.
>
> Khushi Muhammad Jut was seven, one of the Muslims of a village in Ludhiana district that the line left in India.
>
> And none of the five is a Sikh account, though the Sikhs were one of the three communities of the Punjab and the plan cut them in two; the Viceroy, once he had sent for a map, said he was astounded.

How we know (O-5), in the first TURN:

> They are argued from what this programme could read: the statements, awards, telegrams and letters of that year, one official count of the dead, and four survivors recorded by the Partition Archive. Each gets its own case first.

The CLOSE (O-6):

> Two countries were made from one on the fifteenth of August, nineteen forty seven. The line through the Punjab was signed on the twelfth and published after the ceremonies.
>
> In nineteen seventy one, East Pakistan broke away, and Bangladesh became a third country born from the first partition.

Each of these traces: "India is British, Britain is leaving" and "two independent
Dominions ... India and Pakistan" to the Independence Act (`src-iia-1947.sec1`) and the
YAML summary; the religious basis and the two provinces to the 3 June statement
(`src-hansard-19470603.p36`, `.p37`) and the YAML; Radcliffe chairing both commissions
to `src-hansard-19470710.p2448`; Nehru's and Jinnah's roles and the Constituent
Assembly's purpose to `key_figures` and the Indian nationalist narrative; Kashmir on
Gurdaspur's northern edge to the award's schedule (`src-radcliffe-punjab.item1`) and
"so placed that it could join either" to `src-top-xii.item335`; Bhopal as a state to the
same record; "Hindus and Sikhs east, Muslims west" and East Pakistan to the YAML; the
Sikhs as one of three communities to `src-hansard-19470710.p2448` and the Viceroy's
astonishment to `src-top-xi.item59`; the liaison officer in Lahore to the ledger entry
`src-clo-19480429`; Liaquat "from the Pakistani side" to the ledger's `positions`, which
lists him as a holder of the Pakistani account.

### Cut to make room

From the cinematic variant: the Mountbatten press-conference READ (its fact is narrated
in SCENE 3, so the public/private contrast survives), Rajendra Prasad (a name without a
role a newcomer could use), the line on larger death figures in unread books, the
Governor's 13 August letter in the Force aside (the 20,000 estimate is kept), the second
Hindustani clause, the "signed and dated" aside (the CLOSE now carries it), the elders'
trailing line, one sentence each from the Indian account and the second TURN, and four
asides now run as trailing narration inside their DOCUMENT segments (SCENE 1 Radcliffe,
SCENE 2 Nehru, SCENE 4 Khosla, SCENE 5 Jenkins). No perspective was shortened below
parity. A gloss of "lakh" was written and cut: H-18 could not find 100,000 in the
record, which defines the word only by example.

### Gate output, final run

`parse_script` + `validate_script` against the repo YAML, the verbatim check of every
read against its `# extract:`, `clips.evaluate`, the whole-line delivery rules, H-07:

```
== validate_script (H-01..H-18)
  WARN H-10 DOCUMENT: 'Radio' is spoken in the script and appears nowhere in this event's data: source it or cut it
== verbatim: every M:/F: read against its # extract:
  10 reads checked   (all ok, each a whitespace-folded substring of the named extract or rendering)
== clips.evaluate
  slot clip-nehru-tryst-19470814: admitted=True seconds=28.05
== delivery rules (whole-line)
  warn 47 words in line: DOCUMENT Jawaharlal Nehru [M]      (verbatim read)
  warn 46 words in line: DOCUMENT Muhammad Ali Jinnah [M]   (verbatim read)
  clean
== length
  1876 words, 36 segments -> 14.96 min at bm_lewis 146 wpm (ceiling 1881 words for 15.00); at 160 wpm 13.84 min
  shape: 6 scenes, 10 documents, 3 asides, 7 rests, 2 turns, 5 perspectives
  narration 1589 words, reads 287 words
== RESULT: PASS (0 fail-level finding(s))
```

The one warn, `Radio`, is the same finding the live and cinematic scripts carry on the
clip's honest credit line (`HISTORY-SCRIPT-ALGORITHM-REVIEW.md` 2d). The two 46 and 47
word reads are verbatim extracts and are reported, not failed.

`tests/test_history_script.py`, `tests/test_history_copy.py` and
`tests/test_history_quote_ledger.py` pass on the tree as committed (they glob
`data/history/scripts/*.txt` and the events; the variants directory is outside their
scope, and nothing else was changed).

### Promotion note

If this variant replaces the live script, the thesis's `episode_marks` (chapters 0, 5
and 14) must be re-pointed: the segment count fell from 41 to 36, and T-10 checks the
chapter index and title against the served manifest. SCENE 1 is now titled "The map"
rather than "The count"; chapter 5 keeps the title "The force that was supposed to hold".

---

## 7. What a newcomer needs that the sources do not carry

So it cannot be added, under Rule 1, until the record does:

- **Partition**: a role for Sir George Abell, Lord Ismay or Liaquat Ali Khan; a plain
  gloss of "Viceroy"; the value of a lakh as a number H-18 can see.
- **Cambodia**: what "Angkar" means; who Sihanouk was.
- **Scramble**: what an induna is.
- **Srebrenica**: who Atlagic and Martinovic are, beyond their paper.
- **1918 influenza**: a role for Johnson and Mueller, or Spreeuwenberg.
- **Armenia**: a gloss of "the Porte" (the sourced form is the OPEN's own "the
  government", so the term can go rather than be glossed).

Everything else in section 2d is in the record and can be written in.
