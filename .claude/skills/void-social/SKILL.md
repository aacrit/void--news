---
name: void-social
description: "Generate the daily Void News Social trio (Vision + Method + Example) as Instagram drafts, then render them for review. Nothing is posted."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /void-social — Void News Social (daily trio)

Generate one **Vision**, one **Method**, and one **Example** Instagram post (each a 3-slide carousel in the Void News brand) and open them in a review sheet. Example always uses today's real top story from the live feed. Everything is a DRAFT — nothing is published.

## Steps

### 1. Dispatch generation (renders slides + writes captions)
The render step needs the Next.js dev server + Playwright, so generation runs in GitHub Actions, not locally.
```bash
gh workflow run ig-pipeline.yml -f mode=draft -f track=void
```
Confirm it queued: `gh run list --workflow=ig-pipeline.yml --limit 1`.

### 2. Wait for it to finish (~4-8 min)
Poll until the run completes (it runs generator -> Playwright capture -> Gemini captions):
```bash
RID=$(gh run list --workflow=ig-pipeline.yml --limit 1 --json databaseId -q '.[0].databaseId')
for i in $(seq 1 40); do s=$(gh run view $RID --json status -q .status); echo "[$i] $s"; [ "$s" = "completed" ] && break; sleep 20; done
gh run view $RID --json conclusion -q .conclusion
```
Run the poll loop with `run_in_background: true` so you are notified on completion instead of blocking.

### 3. Render the drafts for review + open in the browser
```bash
python -m pipeline.social.ig_review --track void --open
```
This writes an HTML sheet of every carousel slide + caption + hashtags and opens it, flagging any broken (red) or questionable (amber) drafts.

### 4. Report to the CEO
Summarize the three posts (Vision / Method / Example), call out anything the review flagged (unfilled placeholders, missing captions, near-duplicates, hallucinated quotes, off-brand copy), and give the honest recommendation. Do NOT publish. To publish approved drafts later, the `publish` workflow mode ships them to Instagram (+ Bluesky).

## Notes
- Migration 073 must be applied (widens `ig_posts.pillar` to vision/method/example) or the vision + example inserts fail.
- The daily cron already runs `--track void`; this command is the on-demand path.
- The related commands are `/history-social` and `/weekly-social` for the adhoc tracks.
