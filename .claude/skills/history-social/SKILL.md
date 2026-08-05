---
name: history-social
description: "Ad-hoc: generate a Void History Instagram showcase post as a downloadable manual-upload bundle. Nothing is posted."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /history-social — History Social (ad-hoc)

Generate ONE **Void History** showcase post (a 3-slide carousel in the umber History brand: event + date, its multiple perspectives / "no winner declared", CTA), then hand the CEO a downloadable bundle they upload BY HAND. The generator picks a historical event that has not been posted yet.

**Posting is PARKED (2026-08-05). Nothing is auto-posted.** Generate-only: render slides, write per-platform captions, package an artifact for manual upload.

## Steps

### 1. Dispatch generation
`mode=generate` runs generator -> Playwright capture -> Gemini captions -> bundle export.
```bash
gh workflow run ig-pipeline.yml -f mode=generate -f track=history
```
(To feature a specific event, note the generator supports `--event <slug>` from `data/history/events/`; the workflow does not expose an `event` input, so either add one or run the generator directly in an environment with the render server + secrets. Default picks an unposted event.)

### 2. Wait for it to finish (~5-9 min)
```bash
RID=$(gh run list --workflow=ig-pipeline.yml --limit 1 --json databaseId -q '.[0].databaseId')
for i in $(seq 1 40); do s=$(gh run view $RID --json status -q .status); echo "[$i] $s"; [ "$s" = "completed" ] && break; sleep 20; done
gh run view $RID --json conclusion -q .conclusion
```
Prefer `run_in_background: true` so you are notified on completion.

### 3. Download the bundle artifact
```bash
gh run download $RID --dir ./social_bundle
```
Open `social_out/<YYYY-MM-DD>/index.html`: it previews the post's 3 slide thumbnails, the **Instagram / X / Bluesky** columns with exact copy, and the **INTENT** callout. The post's own folder (under `history/`) holds `slide-1/2/3.png` + `caption-instagram.txt`, `caption-x.txt`, `caption-bluesky.txt`, `intent.txt`.

### 4. Report to the CEO — manual upload
Summarize the event chosen, the perspectives shown, and the **INTENT** line. Tell the CEO to pick a platform caption, add their personal touch to match the INTENT, then upload the images + paste the copy by hand. **Do NOT publish — nothing here posts.**

## Notes
- **Per-platform variants:** Instagram caption (+ hashtags), X (<=280 chars, 1-2 hashtags), Bluesky (<=300 chars, plain), plus a one-sentence director's-note **intent**. Voice rules apply to all (no em/en dashes).
- Migrations 073 + 074 must be applied (074 adds the variant + intent columns; if unapplied, X/Bluesky are derived by trimming the IG caption).
- **Posting is parked.** The `publish` mode is disabled/manual-only; no cron auto-posts.
- Umber brand accent (`--palette-history`), "Void History" wordmark. Optional local preview: `python -m pipeline.social.ig_review --track history --open`.
