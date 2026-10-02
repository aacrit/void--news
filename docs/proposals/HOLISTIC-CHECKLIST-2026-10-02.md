# Holistic fix checklist, 2026-10-02

Every finding from the six live audits (`docs/proposals/HOLISTIC-PLAN-2026-10-02.md`
and the audit reports it cites), grouped into eight workstreams that touch
separate files, so they can run in parallel. Each workstream is built in its own
worktree and merged one branch at a time (CLAUDE.md: one live `claude/*` branch).

CEO decisions, answered 2026-10-02: 1(b) state media get their own rung outside
the wings; 2(b) the card prints its count; 3(a) one vote per outlet; 4(a) the
share card follows `leanShape`; 5(b) Weekly drops tech and sports until each has
a sourced corpus; 6(b) the audio band floats with sourced words, floor 14 min;
7(a) **Games are un-hidden now** (overriding the recommendation); 8(b) the
pronoun scrubber is retired.

Legend: [ ] open, [x] done and on main, [~] done in code, needs a CEO action
outside the repo (listed under "CEO actions").

## WS-A Infra and CI (owner: bug-fixer)
- [ ] P0-1 `pipeline.yml` dispatches `deploy-cloudflare.yml` after the data commit; live-freshness check
- [ ] P0-2 every cron off minute 0 and 30; gate in `test_docs_facts.py`
- [ ] P0-7 auto-merge refuses a diff touching `.github/**`; ref passed via env and quoted; CODEOWNERS; gate
- [ ] Sec M1 scrape runs in a job with no write token or secrets, handing off by artifact
- [ ] P2-5 (CI half) `npm audit` and `pip-audit` gates; `dependabot.yml`; actions pinned to SHAs
- [ ] P2-7 SessionStart hook: one call per workflow, stdin JSON, skipped never masks failed, PyYAML pin; fixture
- [ ] P2-8 inventory test (no test file outside a workflow); pushing workflows run the four pre-commit gates; `db-cleanup.yml` unscheduled
- [ ] Sec L4 `permissions:` on the four workflows that lack it
- [ ] Audit 3 opt 6 Pair Test and Anchor Pairs once a day

## WS-B Audio and History data (owner: audio-engineer, media-archaeologist)
- [ ] P0-3 delete Issue #26 MP3s, sidecars and unreferenced pilots; inverse orphan gate; live 404 check
- [ ] P0-4 thesis audio contradicting corrected scripts (Haitian Revolution, Scramble for Africa): script SHA-256 in the manifest, gate on any clone; re-render
- [ ] P0-8 four broken exhibit image hashes; URL derived from MD5; T-21
- [ ] P2-9 four episodes over 15:00; four time-bound claims; over-ceiling list derived by script
- [ ] P2-11 40 junk media credits; em dash in a source title; self-host Commons images
- [ ] Audit 4 LOW feed item title "US Exits Iraq.:"; duration rounding parity between `/audio` and feeds

## WS-C Rule 1 grounding (owner: nlp-engineer)
- [ ] P1-1 deterministic per-paragraph grounding for TL;DR, Opinion, On Air (cut, never regenerate)
- [ ] P1-2 E-13 decimals and number-to-subject attachment
- [ ] P1-3 E-14 keeps punctuation (dropped ellipsis fails)
- [ ] P1-4 grounding index built from full bodies before step 10
- [ ] P1-5 cluster contamination: coherence cuts, "Separately," banned, E-16
- [ ] P1-6 kill-list words and dash in the rule-based fallback strings; literal scan gate
- [ ] P1-9 prompt-injection boundary on every prompt; gate
- [ ] P2-10 per-article summaries capped at 300 characters; gate
- [ ] Audit 1 item 7 hedge-as-attribution (E-15) promoted to blocking for derived products
- [ ] Audit 1 item 9 the brief keeps one story per paragraph; gate
- [ ] Audit 1 item 14 sources that disagree are published as disagreement (prompt + check)
- [ ] Audit 1 item 15 stale counts ("currently N") flagged
- [ ] Decision 8 retire the pronoun scrubber (Block 5a)
- [ ] Archived cards from 2026-10-01 corrected (Iraq 4,419, Hegseth quote, Putin/Kanye, pensions tail, "Q&An")

## WS-D Security and privacy (owner: void-ciso specifies, bug-fixer implements)
- [~] P1-7 Worker votes and replies keyed on server IP hash, per-IP caps, parent check; vitest
- [~] P1-8 privacy page names every stored field; device class not full UA; no `detail` in 500; `IP_SALT` from a secret
- [ ] P2-5 (deps half) npm and pip bumps; `worker/package-lock.json`
- [ ] Sec L1 honest scraper user agent
- [ ] Sec L2/L3 no `Access-Control-Allow-Origin: *` on HTML; drop the unused Insights allowance
- [ ] Sec L5 `LIMIT` on `GET /api/ship/requests`
- [~] P0-6 Cloudflare rule documented; zero-429 first-party assets check in `verify_production.py`

## WS-E Bias display honesty (owner: nlp-engineer, frontend-fixer)
- [ ] P1-10 "blend" removed; `/press` reads `engine.json`; copy gate
- [ ] P1-11 one per-outlet histogram computed once, read by card and Bench; equality gate; `Bench.tsx` comment corrected
- [ ] P1-12 About demos carry real counts; gate
- [ ] P1-13 Bench mark card shows baseline, text shift, "placed from outlet only"
- [ ] Decision 1 state-affiliated outlets on their own rung, out of the shape word
- [ ] Decision 2 card prints the count; "N measured" renamed "N placed"
- [ ] Decision 4 share card follows `leanShape`; OPEN-ITEMS lean-gate entry rescoped

## WS-F UX and front-end weight (owner: frontend-fixer, perf-optimizer)
- [ ] P1-14 first-visit explainer and legend link; tour on arrival
- [ ] P1-15 player visible wherever audio plays, History included
- [ ] P1-16 `/audio` and `/weekly` say The Argument was withdrawn; feed link hidden while empty
- [ ] P1-17 letter fallback on every roster mark; lazy loading; sprite
- [ ] P2-4 route-scoped CSS, no unused preloads, `sizes` on History images; transfer budgets
- [ ] UX F8 layout shift at 768 and wider; History rail under the footer
- [ ] UX F9 tap targets (Bench marks, footer, logos, seek, speed, era jumps)
- [ ] UX F10 one tab stop per card on mobile
- [ ] UX F11 wordmark contrast in light mode

## WS-G Weekly (owner: nlp-engineer)
- [ ] P0-5 Issue #26: Frederiksen attribution restored, two quotes demoted to paraphrase, invented clause cut; W-T22 quotation gate
- [ ] Audit 4 item 4 Issue #26 remaining unsourced: Sports & Culture piece, three recap items, unsourced numbers, pipeline jargon, "60,000 articles" vs 2,355, duplicated `opinion_topic`
- [ ] P1-18 tech and sports filters; full sourced corpus to writers; length re-checked after the cut; cut sentences not pieces
- [ ] Decision 5 drop tech and sports until sourced
- [ ] Decision 6 audio band floats with sourced words, floor 14 min

## WS-H Pipeline runtime and durability (owner: perf-optimizer)
- [ ] P2-1 rank only pool-eligible clusters; Kokoro 4 workers; phase timings in `engine.json`; runtime gate
- [ ] P2-2 MP3s out of git (release assets, manifest with SHA-256)
- [ ] P2-3 state DB and phrase_counts growth: retention sweep, prune check
- [ ] P2-6 quarantined sources reviewed per cause; gate
- [ ] P2-12 flash call meter in `engine.json`; gate over 18

## WS-I Games (owner: frontend-fixer, game-content-writer)
- [ ] Decision 7 un-hide Games: remove the 301s, refresh content banks, nav and sitemap entries, headless scenarios, copy gates

## CEO actions (outside the repo)
- [ ] Cloudflare: exempt `/_next/static/*`, `/logos/*`, `/brand/*`, `/audio/*` from the rate-limit rule (P0-6)
- [ ] GitHub: required status checks and CODEOWNERS review on `main` (P0-7)
- [ ] Worker: `wrangler secret put IP_SALT`, apply the D1 migration, `npm run deploy` in `worker/` (P1-7, P1-8)
- [ ] Revoke the retired Supabase project's anon key if the project still exists
