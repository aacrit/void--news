# Do we need all 1,061 sources?

Measured 2026-09-23 against the `void-state-snapshot` from pipeline run #375
(78,328 articles, 1,597 printed stories, 41 printed days). Reproduce with:

    python3 scripts/roster/measure_prune_candidates.py <pipeline_state.db>

**Answer: yes for the roster, no for the Bench.** The roster is not carrying
1,061 outlets' worth of dead weight, and the two problems the question names,
duplicate wire prints and low-quality data, are both real and neither is fixed
by making the roster smaller.

---

## First, a correction

An earlier pass in this session reported "never reached the front page: 750"
and "no text AND never printed: 367". Both were wrong. They came from a join on
`printed_stories.article_id`, a column that does not exist; the join threw
`OperationalError`, the counter stayed empty, and every outlet therefore looked
unprinted. Front-page presence lives in `printed_stories.members`, a JSON array
carrying `source_id` per member. Read correctly, **646 outlets have reached the
front page and 416 have not**, and 307 of that 416 are outlets that fetched
nothing at all.

## What the roster actually contains

| population | outlets |
|---|---|
| on the roster | 1,061 |
| **reached the front page at least once in 41 days** | **646** |
| fetched something but never printed | 109 |
| never fetched one article | 312 |

| front page carried by | share of all appearances |
|---|---|
| top 50 outlets | 44.2% |
| top 100 | 62.8% |
| top 200 | 82.1% |
| top 300 | 91.5% |
| top 500 | 99.0% |

The tail is thin, and it is thin on purpose: the last 146 outlets carry 1% of
appearances and a large share of the 158 countries. Cutting them buys nothing
measurable and costs the geographic claim on `/sources`.

## Low-quality data: the obvious metric is the wrong one

367 outlets have 20 or more articles and **zero** stored body text. It is
tempting to read that as 367 outlets' worth of junk. It is the opposite. These
are the us_major rows in that bucket:

> Associated Press, Bloomberg, CNN, Chicago Tribune, HuffPost, Newsmax,
> Reuters, The Hill, The New York Times, The Wall Street Journal,
> The Washington Post, USA Today, United Press International

They block non-browser clients, so we hold their headlines and nothing else.
334 of the 367 reach the front page regularly. **Pruning on text availability
deletes the front page.** The defect here is not that these rows exist, it is
that a reader cannot tell a headline-scored card from a body-scored one:
`confidence` is exported per article and the frontend reads it nowhere.

The genuinely low-quality population is different and smaller:

- **312 outlets fetched nothing in 41 days.** Four are us_major (MSNBC, The
  Guardian US, FiveThirtyEight, The Washington Times) and several are
  significant internationally (DPA International, China Daily, The Chosun
  Ilbo). These are **broken feeds to repair, not outlets to drop**; the feed
  verifier built this week (`scripts/roster/verify_feeds.py`) is the tool for
  it and has already moved 200 outlets off Google News.
- **109 outlets fetch and never print**, median 12 articles each. Austin
  American-Statesman, New Era (Namibia), The National (Papua New Guinea), The
  Nassau Guardian. Low volume, real journalism, and the only rows Void has in
  several countries. They are the price of the 158-country claim.

## Duplicate wire prints: real, measured, and not a roster problem

Within printed stories whose member titles are still in the window (142
stories, 3,673 members), near-identical copy accounts for **824 rows, 22.4% of
what the Bench counts as separate coverage**. Sixty-six groups run five or more
outlets deep; the widest is 31 outlets on one story.

This confirms the 27.1% measured on 2026-09-22 over 35 clusters, on a sample
four times larger, and it is a **deduplication** defect. Dropping outlets does
not stop the survivors reprinting one wire; it only means the same duplicate is
drawn from a shallower pool. The fix already exists and has never run in
production: `deduplicator.WIRE_SLUGS` matched 5 of the roster's 40 wires and now
derives all 40 from the roster, so a wire's own copy is no longer tagged as the
duplicate of a subscriber that filed first.

## What to do, in order

1. **Ship the wire-attribution fix.** Written and gated
   (`tests/test_wire_attribution.py`), sitting on a branch. This is the actual
   answer to duplicate wire prints.
2. **Surface `confidence` on the card.** Thirteen us_major outlets are scored on
   a headline and the page does not say so. This is a Rule 1 exposure, not a
   polish item.
3. **Repair, do not prune, the 312 dead feeds.** Run the verifier over them.
   Drop only what the verifier cannot find a working feed for.
4. **Leave the 109 low-volume outlets alone.** They cost one fetch a day and
   hold the country count up.

## What is NOT claimed here

- That the 41-day window is the whole picture. An outlet can be seasonal, and
  `printed_stories` reaches further back than the article rows do, which is why
  only 10.9% of printed members still resolve to a stored title. The
  syndication figure is measured on what resolves.
- That 22.4% is the syndication rate of the corpus. It is the rate **inside
  printed stories**, which is where it matters. Verbatim headline duplication
  across the whole 76,006-article corpus is 0.6%, because subscribers
  re-headline wire copy, which is exactly why a verbatim test is the wrong one.
