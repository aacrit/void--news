# The Void News editorial standard

Every rule Void News enforces on generated text was, until now, written as a
negative: a regex added the day a specific defect reached the front page. There
was no statement of what a publishable story looks like, so nothing could say
whether a story was good, only that it had not yet failed a known test.

This document is that positive statement. Each rule has a stable ID and exactly
one implementation, `pipeline/editorial/standard.py`, with two consumers:

* the **pipeline**, before a summary is stored (Block 2: regenerate once on a
  failure, drop the candidate on a second), and
* the **served-output gate**, `scripts/verify_production.py`, against the HTML
  production actually serves.

One definition, two consumers. A defect that reaches a reader is reported by
the ID that should have caught it, which is also how the run log names it.

## Status

`S-*`, `F-*` and the `E-*` rules marked ENFORCED are live in the gate today.
The `E-*` rules marked ADVISORY are implemented and run, but print without
failing the build, pending CEO review of this document; `--strict` promotes
them. `L-*` rules need the model in the loop and are wired in Block 2.

## What a publishable story is

### Structural

| ID | Rule | Status | Derivation |
|---|---|---|---|
| S-01 | The card links to `/story/<uuid>/`, one anchor per card | ENFORCED | A `/?story=` link loads the homepage, is not indexable and is not a share target. Shipped on the last two to four cards of six consecutive editions. |
| S-02 | The summary runs to at least 300 characters | ENFORCED | Two satire or opinion columns that shipped as news ("Edward Williams States American Democracy Has Been Killed", "Israel Wants Rods From God") were each two sentences. On the 08-25 feed the only sub-300 summary was 286 characters and the next shortest was 1,037. |
| S-03 | The summary ends in terminal punctuation | ENFORCED | A truncated summary means the generator was cut off; the rest of the card cannot be trusted either. |
| S-04 | Quotation marks are balanced | ENFORCED | An orphan quote mark changes who said what. |
| S-05 | No doubled capitalized word (`TheThe`) | ENFORCED | Concatenation artifact from the summarizer's sentence joining. |
| S-06 | No broken spacing in abbreviations or decimals (`U. S.`, `3. 5`) | ENFORCED | A sitewide corruption shipped this way once. |

### Editorial

| ID | Rule | Status | Derivation |
|---|---|---|---|
| E-01 | The first sentence states the event, not a reaction to it | L-01 | A card that opens on the reaction makes the reader hunt for what happened. |
| E-02 | Quotations are verbatim; pronouns inside quotation marks are never altered | L-02 | See E-03. |
| E-03 | No first-person pronoun outside quotation marks | ENFORCED | Void speaks in the third person. |
| E-04 | No sentence begins with a lowercase subordinating conjunction | ENFORCED | An orphan clause is the tail of a sentence whose head was dropped. |
| E-05 | No reputational or criminal claim about a named individual without attribution | ENFORCED | Deterministic, and the pipeline drops the sentence rather than shipping it. |
| E-06 | A summary that criticises a named living person carries that person's response, or records that none was given | L-06 | The 09-06 Mamdani card quoted three critics and no response. This is the ordinary journalistic rule and the model can check it against the article set. |
| E-07 | No contested terminology outside quotation marks where a neutral construction exists and the sentence carries no attribution | ADVISORY | The 09-06 feed put "funded by the Iranian terror regime" and "the 9/11 Islamic terror attacks" in Void's own voice, unquoted and unattributed. The rule is symmetric: it neutralises loaded phrasing from either direction. |
| E-08 | No unattributed passive evaluation ("is described as", "is seen as") | ADVISORY | Passive voice that smuggles a judgement in without an author. |
| E-09 | Sentences asserting absence of information are not the substance of the card | ADVISORY | The 09-06 Bolivia card carried two facts in eight sentences; five said some version of "details have not been released". Threshold: three or more absence sentences, or a quarter of a card of six or more sentences. Across six runs no other displayed card exceeded one. |
| E-10 | A location named in the headline is not contradicted by the summary | L-07 | "Malvinas Islands" led a story headlined "Falkland Islands". A regex cannot tell a place from any other capitalised opener: the first draft flagged "Mudslides Kill Dozens". |
| E-11 | No second-person pronoun outside quotation marks | ADVISORY | "Vance also told El-Sayed to keep their wife's name the hell out of your mouth" shipped: the scrubber rewrote `my` and had no rule for `your`, so Void addressed the reader. |

### Feed level

| ID | Rule | Status | Derivation |
|---|---|---|---|
| F-01 | Exactly one story carries the Top story badge | ENFORCED | Two lead cards rendered once; zero is equally wrong and was previously accepted. |
| F-02 | No two headlines share four or more content-word stems | ENFORCED | The same story shipped twice under two headlines repeatedly. |
| F-03 | The card label, the Sigil and the Deep Dive agree on the lean | ENFORCED (extremes) | The extremes are checked today; three-way agreement is Block 4. |
| F-04 | The header count equals the cards rendered, and both equal the configured feed size | ENFORCED | A page that renders 12 of 20 and says "12 stories loaded" used to pass. |
| F-05 | The wordmark appears once in the header and once in the footer | ENFORCED | It doubled once. |

### Rules that need the model

These cannot be settled by regex. They run in the Block 2 critique pass, one
batched flash-lite request per group of candidates, with the article set in the
prompt.

| ID | Rule |
|---|---|
| L-01 | The first sentence states the event, not a reaction (E-01) |
| L-02 | Every quotation appears verbatim in a source article, pronouns included (E-02) |
| L-03 | The card describes one event |
| L-04 | The card is news, not opinion, satire or commerce |
| L-05 | The card does not contradict itself, and every age, title and number is sourced |
| L-06 | Criticism of a named living person carries their response or notes its absence (E-06) |
| L-07 | The summary does not contradict a location named in the headline (E-10) |

## Thresholds, and where they come from

| Constant | Value | Derivation |
|---|---|---|
| Minimum summary length | 300 characters | The largest value that clears every real story by a wide margin while catching the two-sentence satire columns. |
| Duplicate headline overlap | 4 shared stems | Below this, unrelated stories collide. |
| Absence-sentence limits | 3 sentences, or 25 percent of 6 or more | Isolates the Bolivia card (5 of 8) from every other card in six runs (maximum 1). |
| Lean label suppression | fewer than 10 scored articles | At a within-cluster standard deviation of 12.5, ten articles hold the standard error under 4, which is under half a 7-band width. |
| Feed size | `frontend/config/feed.json` | One source of truth for the pipeline, the frontend, the gate and CI. |

## Instrumentation

Block 2 records a per-run block on `pipeline_runs.llm_metrics` under
`editorial`: candidates, passed, pass rate, failures by ID, regenerated,
dropped. The run log prints one line, so a quality regression shows up before a
reader finds it:

```
Editorial: 33/35 candidates clean (94.3%) | 2 regenerated, 0 dropped | worst: E-03 x2, S-02 x1
```

## Related

* `pipeline/editorial/standard.py`: the implementation, stdlib only.
* `scripts/verify_production.py`: the served-output consumer.
* `tests/test_editorial_standard.py`: one planted defect per ID.
* `docs/VOICE-BRAND.md`: the prose statement of voice these rules serve.
* `docs/proposals/EDITORIAL-VOICE-2026-09.md`: open proposals (Block 5).
