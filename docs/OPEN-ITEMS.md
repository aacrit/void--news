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

**Step 6b overwrites measured bias scores with defaults.** Documented with
evidence in `docs/proposals/NEXT-LEVEL-2026-09-20.md` (finding 1 and the
"intentional damper" analysis). Not fixed in any branch: the CEO asked that
clustering, ranking and bias not be touched without a deliberate decision.
The fix is small (preload `bias_scores` for the 36h lookback into
`article_bias_map`; never write a defaults row) and needs a pipeline run to
prove it before anything is built on the scores.



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

**Two live episodes serve audio that contradicts their own script.**
`great-leap-forward` presents a secondhand Mao remark, and
`gutenberg-printing-press` an attributed line from a Dominican friar, as
verbatim speech. Both scripts were corrected for H-11 and neither was
re-rendered. `tests/test_history_audio.py` now fails on exactly this and stays
red until both are re-rendered. No script work needed; the fix is a render.

**Live History episodes that run over the 15 minute format ceiling.** Congo
Free State 15.46, Rise of Islam 15.43, Russian Revolution 15.37, Indian
Independence 15.36. All sit under the audio gate's 15.5, so they shipped and
still serve. Peloponnesian War renders at about 15.2 and joins this list when
it publishes.

(An earlier version of this entry named Peloponnesian War instead of Russian
Revolution. Peloponnesian War's 15.2 came from a render log, not the manifest:
that run was rejected at publish over a different episode, so it never went
live. Read the manifest for what is serving, not a render log for what was
made.)

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

**House promos (2026-09-20).** The pool (`data/promos/house.yaml`, 24 promos)
validates and is rendered in `af_kore` (American, CEO: "prefer American voice");
`af_sarah` is the alternate (`VOID_PROMO_VOICE`). On Air, Weekly and History
pick a promo up at render time only when `data/promos/rendered/` carries a
render whose sha matches the pool; otherwise they ship exactly as before.
The 73 published History episodes are **not stitched yet**: dispatch
`.github/workflows/stitch-promos.yml` (render: false if the committed
renders are the ones wanted), outside 11:00-17:00 UTC, and read the guard
numbers it prints per episode. A dry run on three live episodes (ottoman-empire,
partition-of-india, algerian-war, pulled from the site with `--from-site`)
passed every guard: integrated loudness unchanged at -16.4 LUFS, true peak
-1.3 to -1.5 dBTP, promo window within 1.7 dB of the closing speech. First daily run after this lands: confirm the
served On Air MP3's last chapter is kind `promo` and A-04 still passes.

**Podcast channel.** `podcast-history.xml` (73 items) and `podcast-weekly.xml`
now generate and are linked from `/listen` and `layout.tsx`. Not submitted to
Apple Podcasts or Spotify (`docs/PODCAST-DISTRIBUTION.md` has the checklist;
the owner mailbox must be monitored for Apple's verification mail). Weekly
and History covers exist as SVG only; the JPGs need the brand render step.
`frontend/public/podcast-us.xml` was deleted (dead Supabase host, nothing
regenerated it); the US edition gets a feed again when it renders again. The world feed
was cut from 9 items to the episodes whose MP3s exist (7 of 9 enclosures
returned 404 because audio retention keeps two dated files).



**Weekly — DISCHARGED 2026-09-20.** Vol. I, No. 1 ran on the new Sunday cadence
and is live. Everything rev 71/72 left unverified now has evidence:
`departments` carries Technology and Sports & Culture (the first departments
the section has ever published), `opinions` carries five essays with the first
two paired, `week_days` recorded seven days, every brief item carries a
`cluster_id` and a section kicker, and `build-data/weekly-issues.json` took its
append. Enforcement fired on six pieces, named each finding, regenerated all
six, and shipped the cleaner attempt every time (opinion 4 went 310 to 354
words; opinion 2 lost "crucial"). `_spread_over_week` logged "10 stories across
3 day(s) of the week" against the old all-ten-from-one-date. All nine
`verify_sections` W-checks pass against the served page, W-08 included, which
was red on the live site before this branch.

What it exposed, all now fixed: a `NameError` on the last line before
persistence that discarded four minutes of paid generation (and the import-wall
premise that had exempted the whole generator file from testing), and a brief
length check that tested a ceiling with no floor, which passed a column with
nine of ten items below the spec.

**Still short of spec, and not yet solved:** the model undershoots every length
target and regeneration narrows the gap without closing it. Cover 2 shipped at
507 words against 800-1200, two opinions below the 400 floor, and the briefs at
40-49 against 55-75. The enforcement is working as designed (measure,
regenerate once naming the findings, ship the cleaner attempt); the prompts are
what need strengthening. Three uses of "significant" also survived two attempts
and are on the page. They are deliberately NOT stripped mechanically: deleting
the word from "widespread protests and significant disruption" changes what the
sentence says, so this needs a rewrite, not a regex.

**No cover image** was found for the issue. W-03 treats that as acceptable
(better than an unlicensed one) but a magazine cover with no photograph is a
standing gap.

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

## History: 70 over-escaped apostrophes reach the reader

Found 2026-09-21 by a drafter working the dash pass, who flagged it rather than
silently editing text outside its remit.

70 string values across `apartheid`, `bandung-conference`, `mongol-empire`,
`silk-road` and `the-crusades` carry a literal doubled apostrophe, and it
reaches `frontend/public/data/history.json`. Readers see `Mandela''s`,
`Biko''s`, `Chang''an`, `the world''s tallest equestrian statue`, and
`Jami'' al-Tawarikh` for what should be `Jami' al-Tawarikh`.

The diagnosis is certain. In a single-quoted YAML scalar `''` is the escape for
one apostrophe and the parser collapses it, so anything still doubled AFTER
`yaml.safe_load` is an escape written into a scalar that does not honour it.

What is NOT certain is where each one sits, and that is why this is written
down rather than fixed. Every sampled instance is on a CONTINUATION line of a
multi-line scalar, with no `key:` prefix to say how the scalar opened. A
line-based replacement cannot tell a plain continuation from the continuation
of a single-quoted scalar, where `''` is correct and must stay. A first attempt
proved it: it broke all four files it touched, and only a "revert anything that
will not re-parse" guard kept the damage at zero.

The sound fix is a formatting-preserving round trip (`ruamel.yaml`, not
installed here) or a scalar-span tracker that knows which quoting style opened
the block. Not a regex.

Worth doing with the tree quiet, since the same five files were being rewritten
by the dash pass when this was found.
