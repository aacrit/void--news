---
name: weekly-social
description: "Ad-hoc: generate a Void Weekly Instagram showcase post (the week's edition) as a draft, then render it for review. Nothing is posted."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /weekly-social — Weekly Social (ad-hoc)

Generate ONE **Void Weekly** showcase post (a 3-slide carousel in the red Weekly brand: issue cover, the week's key / most-contested stories, CTA) from the latest weekly digest, and open it for review. Everything is a DRAFT.

## Steps

### 1. Dispatch generation
```bash
gh workflow run ig-pipeline.yml -f mode=draft -f track=weekly
```

### 2. Wait for it to finish (~4-8 min)
```bash
RID=$(gh run list --workflow=ig-pipeline.yml --limit 1 --json databaseId -q '.[0].databaseId')
for i in $(seq 1 40); do s=$(gh run view $RID --json status -q .status); echo "[$i] $s"; [ "$s" = "completed" ] && break; sleep 20; done
gh run view $RID --json conclusion -q .conclusion
```
Prefer `run_in_background: true` so you are notified on completion.

### 3. Render for review + open
```bash
python -m pipeline.social.ig_review --track weekly --open
```

### 4. Report to the CEO
Summarize the issue number, cover headline, and the stories featured; flag anything the review marked. Do NOT publish (use the `publish` workflow mode once approved).

## Notes
- Migration 073 must be applied (adds `weekly` to the `ig_posts.pillar` CHECK).
- Needs at least one row in `weekly_digests`; sources issue_number + cover headline + most-contested stories.
- Red brand accent (`--palette-weekly`), "Void Weekly" wordmark.
