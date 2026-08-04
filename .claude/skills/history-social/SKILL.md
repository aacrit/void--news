---
name: history-social
description: "Ad-hoc: generate a Void History Instagram showcase post (a historical event, multiple perspectives) as a draft, then render it for review. Nothing is posted."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /history-social — History Social (ad-hoc)

Generate ONE **Void History** showcase post (a 3-slide carousel in the umber History brand: event + date, its multiple perspectives / "no winner declared", CTA) and open it for review. The generator picks a historical event that has not been posted yet. Everything is a DRAFT.

## Steps

### 1. Dispatch generation
```bash
gh workflow run ig-pipeline.yml -f mode=draft -f track=history
```
(To feature a specific event, note that the generator supports `--event <slug>` from `data/history/events/`; the workflow does not yet expose an `event` input, so either add one or run the generator directly in an environment with the render server + secrets. Default picks an unposted event.)

### 2. Wait for it to finish (~4-8 min)
```bash
RID=$(gh run list --workflow=ig-pipeline.yml --limit 1 --json databaseId -q '.[0].databaseId')
for i in $(seq 1 40); do s=$(gh run view $RID --json status -q .status); echo "[$i] $s"; [ "$s" = "completed" ] && break; sleep 20; done
gh run view $RID --json conclusion -q .conclusion
```
Prefer `run_in_background: true` so you are notified on completion.

### 3. Render for review + open
```bash
python -m pipeline.social.ig_review --track history --open
```

### 4. Report to the CEO
Summarize the event chosen, the perspectives shown, and the caption; flag anything the review marked. Do NOT publish (use the `publish` workflow mode once approved).

## Notes
- Migration 073 must be applied (adds `history` etc. to the `ig_posts.pillar` CHECK, though `history` was already allowed).
- Umber brand accent (`--palette-history`), "Void History" wordmark.
