# Writing a History episode

This is the complete brief for drafting one episode script. It is written to
be handed to a drafter with nothing else: one event, this document, and the
validators. If you are reading it as a checklist before you write, read the
whole thing first, then open the event.

Output ONE file: `data/history/scripts/<slug>.txt`. Nothing else.

## Before anything: the one rule that cannot bend

**Everything spoken in the episode comes from that event's own YAML.**
`data/history/events/<slug>.yaml`. Not from what you already know about the
event. If a fact is true, famous, and not in that file, it does not go in the
script. This is not pedantry, it is the only thing standing between this
catalogue and a history programme that confidently says things nobody
checked. Two examples, both mine, both caught only by grepping the file
afterwards: an East India Company official deciphering the Ashokan edicts,
and a leaning cathedral in Mexico City. Both true. Both cut.

`H-10` warns on every capitalised word that has no root anywhere in the event
record. It is a WARNING, not a blocker, because ordinary geography trips it.
When it fires, you have three honest answers: it is in the file and the
warning is noise, or you can rewrite the line without the name, or you cut
the claim. "I'm confident it's true" is not one of them.

## The shape

```
## OPEN            N   the misconception. 3-4 lines, no names needed yet
## TITLE           N   "<title>. <date>."
## SCENE 1 | <t>   N   arrive late: one moment, one place. 4-6 lines
## DOCUMENT | author | work | date
                   N   narration NAMING the speaker, then
                   M   or F reads the quote
## ASIDE           N   what that meant. Short, direct, 2-3 lines
## REST                (no words: a held pause with the music alone)
## SCENE 2..5      N
## TURN | Five accounts
                   N   one framing line before the accounts begin
## PERSPECTIVE | <title> | <viewpoint_type>
                   N   this account in ITS OWN terms, 4-6 lines
                   M/F its own witness, where the data has one
## REST | short
## TURN | What each one leaves out
                   N   one line per account, and no account is spared
## CLOSE           N   ends on a particular, never on a moral
## SAY
Name = RESPELLING
```

`N:` narrates. `M:` and `F:` read quoted speech ONLY, and are matched to the
speaker's sex. A woman reading Nehru is jarring; it is the one thing the CEO
sent back.

## The seven references, and what each one is allowed to do

Averaged together they make mush, because they disagree. Each owns a job.

| reference | its job | where |
|---|---|---|
| Veritasium | you think you know this; you do not | COLD OPEN only |
| Screenplay | arrive late, leave early. A scene, not a summary | every SCENE |
| Ken Burns | present tense, accumulating particulars, documents read aloud | the spine |
| MKBHD | "here is what that actually meant" | the ASIDE |
| Conflicted | moral seriousness without solemnity | register, throughout |
| Vsauce | the zoom-out that reframes it | the late TURN |
| NPR / NYT | restraint, attribution before claim | sound, and the CLOSE |

## The cold open is the hardest 90 seconds

Find the thing most listeners believe that the event's own record contradicts,
and open on that. It must be IN THE DATA.

Worked examples from shipped episodes:
- **Tenochtitlan**: five hundred Spaniards did not defeat an empire. There
  were ~900 Spaniards and 75,000-200,000 indigenous soldiers with their own
  commanders. And the god story appears in no pre-conquest Nahuatl source.
- **Rwanda**: the word used at the time was tribal. Roadblocks were up within
  an hour, the lists were typed in advance, and the identity card came from a
  Belgian administration in the 1930s.
- **Berlin Wall**: nobody decided to open it. A spokesman had not read his
  briefing notes and an officer decided not to shoot.
- **Iran**: the engine was a funeral custom. Mourning on the fortieth day
  meant every massacre scheduled the next protest.

If the best you can find is "this was important and here is why", you have
not found it yet. Go back to the data.

**Do not reuse another episode's opening move.** Four episodes that all open
"two things about X" is a formula, and a formula is what makes seventy eight
episodes sound like one programme instead of seventy eight stories.

## Every side gets its own case. This is the whole point.

The first Partition draft got this wrong in the way every draft will want to:
it summarised all five perspectives in about 280 words and characterised each
one BY WHAT IT OMITS. That is a debunking format wearing a balance costume.
Every account got introduced only to be knocked down, and the strongest fact
in the Pakistani case was simply missing.

So:
1. A `PERSPECTIVE` segment per account in the data. Its argument in its own
   terms, its strongest fact, its own witness if the data has one. Write it as
   if you were persuaded by it.
2. ONLY THEN a closing `TURN` that names what each one leaves out.
3. That turn spares nobody, including the account a sympathetic listener
   holds. The Zionist account and the Palestinian account both get a line. The
   survivors' account and the perpetrators' account both get a line.

`H-09` enforces the existence of the segments. It cannot enforce that you
argued them fairly. That part is on you.

Where an account is a perpetrator's or a denial-adjacent one, say plainly in
the framing line before the accounts that these are not five positions on
whether it happened, and present that account as what was said AT THE TIME,
which is evidence rather than a competing version of events.

## Sound and length

- **Numbers as words.** "thirty three thousand seven hundred and seventy one".
- **No dashes** in spoken copy. Two sentences, or a comma.
- **One idea per line.** The line is the unit of synthesis.
- **Attribution before the claim**, always: name the speaker, then the quote.
- **1,500-1,950 words. This is a hard gate, not a target.** `H-07` fails the
  script outside 8-15 minutes, and the arithmetic is `words / 145 + 1.1`, so
  2,015 words is the ceiling and anything above it does not render at all.
  The first two delegated drafts both came in near 2,350 because the event
  records are rich and every fact earns its place on the page. They do not
  all earn their place in the ear. **Count the words before you run the
  gate**, and if you are over, cut whole lines rather than trimming clauses:
  a scene with four lines is a scene, a scene with six is a summary.
- **`## SAY`**: a respelling for every proper noun a synthesiser will mangle.
  `Tenochtitlan = ten-och-TEET-lan`. Generous is better than sparse.
- **`## REST`** four to seven times, where the listener needs somewhere to put
  what they just heard. After a document that lands hard. Before the accounts.
  Before the close. The CEO's note on the first cut was that it never stopped.

## The close

Ends on a particular, never on a moral. A fact, small and concrete, that the
listener finishes themselves.

- The railway charged the full adult rate above ten, half under ten, and
  nothing at all for children under four.
- Thirty four people came out of Murambi, found the next morning among the
  dead.
- The rock is still on the cliff face. You can walk up and read the number.

## Finish by running the gates

```
python - <<'PY'
import sys; sys.path.insert(0,'pipeline')
import yaml
from history.script_format import parse_script, validate_script
ev = yaml.safe_load(open('data/history/events/<slug>.yaml'))
s = parse_script(open('data/history/scripts/<slug>.txt').read(), '<slug>')
print(s.words, 'words,', round(s.minutes,1), 'min')
for f in validate_script(s, ev): print(f.id, f.level, f.segment, '-', f.detail)
PY
```

Zero `fail` findings, or it is not done. Read every `warn` and act on it.
