# Open Items

What is unfinished, what to watch on the next run, and what was deliberately
left alone. Moved out of `CLAUDE.md` on 2026-09-20 so it is read when it is
needed rather than at the start of every session.

`CLAUDE.md` keeps a one-line index of these; the reasoning lives here.
When an item is discharged, delete it from this file and note it in
`docs/CHANGELOG.md` — a stale open item costs more than a missing one,
because it sends the next session chasing a fixed bug.

---

## Blocked on a CEO decision

**Block 5a — the pronoun scrubber rewrites quoted speech.** It converts
we/our/us/my and has no rule for "I", so it leaves a sentence in two voices.
On the live 09-09 feed it turned Ted Cruz's "a traumatic experience for all of
us" into "for all of them" — a real person's words, altered, in production.
`E-07` and `E-08` ship ADVISORY pending this call. Proposal:
`docs/proposals/EDITORIAL-VOICE-2026-09.md`.

**The lean gate went quiet on 60% of the feed.** On 09-09 it emitted ZERO
directional labels: 12 of 20 cards read "Flat". Suppressors, in order of how
often they fired: `margin < 8` (8 cards), `confidence < 0.5` (6),
`measured < 10` (3). The mechanism worth understanding before anyone touches a
threshold: `leanShareTilt` divides by L+C+R, so a story carried 14 left to 5
right lands at 0.153 against a 0.20 threshold purely because 40 neutral wire
articles dilute it, while a nearly identical 16:6 story passes.

The page also shows "Flat" (we could not measure) and "Center" (we measured,
it is balanced) as if a reader could tell them apart. This is the product's
differentiator going silent, and loosening it unilaterally changes what Void
claims about its own confidence. It needs a decision, not a tweak.

---

## Known defects, not yet fixed

**Four live History episodes run over the 15 minute format ceiling.** Congo
Free State 15.46, Rise of Islam 15.43, Indian Independence 15.36, Peloponnesian
War 15.2. All sit under the audio gate's 15.5, so they shipped and still serve.

This is not a regression. The runtime estimator modelled non-speech time as a
flat 1.1 minutes, so it could not see them; it now spends silence per segment
(2026-09-20) and H-07 warns on each. The warning is the first honest report of
a condition that was already live.

Each is a re-cut of roughly 100-200 words followed by a re-render, in the
manner of `september-11-attacks`: drop whole lines that repeat a fact the
script tells better elsewhere, never trim clauses, and protect the cold open,
the closing turn, every perspective's strongest fact and witness, and the
close. Left alone for now because they are live and serving, and four re-cuts
is its own piece of work rather than a footnote to another one.

**The Sigil disagrees with its own caption.** It paints a direction, and
sometimes consensus-green, on cards whose caption reads "Flat".

**Mobile first paint shows the desktop card variant**, then swaps after
hydration. Not a content bug: the 20 cards, their text and their canonical
anchors are all in the served HTML, no rule hides them under 767px, and a
crawler or a JS-off reader gets the full feed. It is a one-frame layout flash.
`HomeContent` must seed `isMobile=false` to match SSR (reading `data-viewport`
synchronously caused React #418 on every iPhone-width route), so the fix is
rendering both variants and choosing in CSS — not moving the check earlier.

**`_coherence_factor` returns 1.0 for a single-token topic bag**, so the
ranker's only incoherence discount is a no-op on exactly the clusters it was
written for.

**`editorial_importance` is applied twice in ranking.** Added additively in
`importance_ranker.py:1382-1388` (±6.7 points around the ei pivot) and
multiplied again in `feed_ranker.py:350-354` (±3%/point, clamped
[0.88, 1.12]), so a high-ei story gets both. Documented, not yet collapsed.

**Revolt serves MOCK data and cannot be un-hidden.** `revolt/data.ts` falls
back to `MOCK_EVENTS` when the browser Supabase client has no credentials,
which is always true in the Cloudflare build. It needs the same static-JSON
treatment `history/data.ts` got in rev 69 before the 301 comes off.

---

## Watch on the next run

**Weekly, Monday 12:00 UTC** — the first post-rebuild run, and the one thing in
rev 71/72 unverified end to end. It is the run that first persists
`departments` and `opinions`, first writes 55-75 word briefs with section
kickers, and first appends to `build-data/weekly-issues.json`. Check that the
guarded ALTER adds both columns, that `Tech brief` / `Sports page` land in
`departments`, and that the commit step stages all three weekly artifacts.

**Weekly audio** — the first episode has never been heard. The workflow carries
the Kokoro venv and model cache, but nothing has run it.

**Daily pipeline, after rev 65** (the rev-64 list is DISCHARGED: 09-07/08/09
were clean, `14208/14208 re-ranked`, `Errors: 0`, verify-production green):

- `[8c.6]` coherence: the trimmed count should fall sharply from 17 clusters /
  55 members. Read the removals; every one should be a story you would not put
  in that cluster.
- `[8d.15]` merge now runs after the title clean. Expect roughly 1 merge where
  09-09 got 0, and a `survivor summary invalidated` line beside it.
- `[8d.2]` critique: `N cards read, M carried a finding` should rise well above
  09-09's 2 of 35, now that the editorial rules are judged from the card.
- `Bench lifted` should be single digits, not 48. A large lift means a sentinel
  leaked into the minimum again; the harness asserts this too.
- No card in the top 20 should be a listicle, a shopping page or a photo
  gallery, and no headline should carry quotation marks around words no source
  printed.

---

## Deliberately not done, with reasons

**Ranking signal weights are unchanged.** They must not be tuned against a
baseline where the re-rank was dead. Re-run `pipeline/evals/replay_ordering.py`
after a week of post-fix runs first.

**The coherence pass abstains** rather than trimming a cluster with no modal
vocabulary. That is a clustering defect, and trimming would pick an arbitrary
half.

**A deterministic L-03** (split the headline on a semicolon, flag when the
halves share no subject) was tried and REJECTED on measurement: it flags 84 of
the 96 semicolon headlines in the archive, because "development; consequence"
is ordinary headline grammar. Recorded so it is not retried.

**Audio is not on R2.** The deploy pulls ~470 MB and still finishes in under
three minutes; at 78 episodes it is ~950 MB and still a few minutes. Flagged as
a scaling worry, measured, and not one yet — but it is the reason binaries keep
accruing in git history.

---

## Housekeeping backlog

- Last Lighthouse point to clear 90 (home/weekly ~88/89 mobile, gzip-measured).
  The old "code-split `@supabase/supabase-js` off the critical path" item is
  obsolete now it is off the read path. Re-measure before acting.
- a11y follow-ups: feedback error messaging, weekly heading.
- Security MED-2: CSP `unsafe-inline`.
- `IP_SALT` must be set as a real secret in prod (`wrangler secret put
  IP_SALT`) — the checked-in value in `worker/wrangler.toml` is a dev
  placeholder. The D1 `database_id` there is genuinely provisioned.
- iOS/Android signing, first store submission, branch protection.
