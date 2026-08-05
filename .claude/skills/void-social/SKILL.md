---
name: void-social
description: "Generate the daily Void News Social trio (Vision + Method + Example) as a downloadable manual-upload bundle. Nothing is posted."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /void-social — Void News Social (daily trio)

Generate one **Vision**, one **Method**, and one **Example** Instagram post (each a 3-slide carousel in the Void News brand), then hand the CEO a downloadable bundle they upload BY HAND. Example always uses today's real top story from the live feed.

**Posting is PARKED (2026-08-05). Nothing is auto-posted.** This pipeline is generate-only: it renders the slides, writes per-platform captions, and packages everything into an artifact the CEO downloads and uploads manually.

## Steps

### 1. Dispatch generation (renders slides + writes captions + builds the bundle)
Rendering needs the Next.js dev server + Playwright, so it runs in GitHub Actions, not locally. `mode=generate` runs generator -> Playwright capture -> Gemini captions -> bundle export.
```bash
gh workflow run ig-pipeline.yml -f mode=generate -f track=void
```
Confirm it queued: `gh run list --workflow=ig-pipeline.yml --limit 1`.

### 2. Wait for it to finish (~5-9 min)
```bash
RID=$(gh run list --workflow=ig-pipeline.yml --limit 1 --json databaseId -q '.[0].databaseId')
for i in $(seq 1 40); do s=$(gh run view $RID --json status -q .status); echo "[$i] $s"; [ "$s" = "completed" ] && break; sleep 20; done
gh run view $RID --json conclusion -q .conclusion
```
Run the poll loop with `run_in_background: true` so you are notified on completion instead of blocking.

### 3. Download the bundle artifact
```bash
gh run download $RID --dir ./social_bundle
```
This pulls `social_out/<YYYY-MM-DD>/`. Open `index.html` in that folder: it previews every post with its 3 slide thumbnails, the three platform columns (**Instagram / X / Bluesky**) with the exact copy to paste, a visible **INTENT** callout per post, and a note wherever one platform's text matches another. Each post also has its own folder with `slide-1/2/3.png` and `caption-instagram.txt`, `caption-x.txt`, `caption-bluesky.txt`, `intent.txt`.

### 4. Report to the CEO — manual upload
Summarize the three posts (Vision / Method / Example) and each one's **INTENT** line. Tell the CEO to, per post: pick the platform caption they want, **add their personal touch to match the INTENT**, then upload the slide images and paste the copy by hand on each platform. Call out anything off (unfilled placeholders, missing captions, hallucinated quotes, off-brand copy). **Do NOT publish — nothing here posts.**

## Notes
- **Per-platform variants:** every post ships an Instagram caption (+ hashtags), an X variant (<=280 chars, 1-2 hashtags), a Bluesky variant (<=300 chars, plain), and a one-sentence director's-note **intent**. All follow the voice rules (no em/en dashes, show-don't-tell).
- Migrations 073 + 074 must be applied (073 widens `ig_posts.pillar`; 074 adds `caption_x`/`caption_bluesky`/`intent`). If 074 is unapplied, X/Bluesky are still derived by trimming the IG caption.
- **Posting is parked.** The `publish` workflow mode (ships to IG + Bluesky) is disabled/manual-only and reachable solely by an explicit `gh workflow run ig-pipeline.yml -f mode=publish`. No cron auto-posts.
- The related commands are `/history-social` and `/weekly-social` for the ad-hoc tracks.
- Optional local preview alternative: `python -m pipeline.social.ig_review --track void --open` (renders the same drafts without the artifact bundle).
