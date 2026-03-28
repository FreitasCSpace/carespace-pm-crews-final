# CareSpace AI Project Management — Team Manual

> **Read time:** 8 minutes
> **Last updated:** March 28, 2026
> **For:** All CareSpace engineers and team leads

---

## What Is This?

CareSpace uses an **AI-powered project management system** with 6 automated crews that handle the heavy PM work. You don't need to learn a new tool or change how you code. You just need to understand:

1. **Where your work lives** (ClickUp)
2. **What the AI does for you** (everything except coding)
3. **What you need to do** (5 simple things)

---

## Your Daily Routine (5 Minutes)

### Every Morning at 7:45am (Oregon time)

The AI posts a **Sprint Digest** to `#pm-standup` in Slack. It shows:

- **Sprint status** — what's done, in progress, blocked, to do
- **Task health** — per-task analysis of problems (stale, missing PR, unassigned)
- **Meeting mode** — standup needed or open slot

Every task links directly to ClickUp. The format is clean:

```
🔄 In Progress
• UITabBar fix — @kishorkumar · 3 SP

⚠️ Task Health
• Calendar Program UI — unassigned · 5 SP · to do
  - No comments for 9d
  - Unassigned — assign during sprint planning
```

**Your action:** Read it. Takes 2 minutes. If you see your name — that's your work.

---

## What You Need To Do

### 1. Work From the Sprint List

Your tasks are in **ClickUp → Sprints → Sprint N**.

- Open ClickUp → `📅 Sprints` folder → current sprint
- You'll see tasks assigned to you with priority and SP
- When you **start** a task: move it to **"In Progress"**
- When you **finish** a task: move it to **"Done"**

### 2. Update Task Status (Critical)

The AI checks task status and **comment activity** daily. If your task has no comments for 3+ days, it gets flagged as stale. If you're "in progress" with no PR opened, it gets flagged too.

| When... | Set status to... |
|---------|-----------------|
| You start working | **In Progress** |
| You finish | **Done** / **Complete** |
| You're blocked | **Blocked** (add a comment explaining why) |

**If you don't update status or add comments, the AI assumes you're stuck.**

### 3. Report Blockers Immediately

If you're blocked:
1. Set the task status to **"Blocked"** in ClickUp
2. Add a comment explaining what's blocking you

The AI will flag it in the next standup digest.

### 4. Create GitHub Issues for New Work

When you find bugs or need new features:
1. Create a GitHub issue in the relevant repo
2. Label it properly (bug, enhancement, etc.)
3. The **intake crew** imports it into ClickUp automatically every morning

You can also add tasks directly to the **Master Backlog** in ClickUp with tags.

### 5. Review Pull Requests on Time

The AI monitors sprint-related PRs. If your PR sits unreviewed for 7+ days, it gets flagged in the daily digest as a stale PR.

---

## How the Sprint Works

### Sprint Cycle (Every 2 Weeks)

```
Before sprint:  Team curates Sprint Candidates (staging area)
Sunday 6pm:     Sprint Crew finalizes the sprint from candidates
Mon-Fri:        You work on sprint tasks
                AI posts daily digest at 7:45am
Friday 4pm:     Retrospective — velocity, completion, carryovers
```

### Sprint Candidates — The Staging Area

The AI does NOT auto-pick tasks for sprints. Instead:

1. Team adds tasks to **Sprint Candidates** (a staging list in ClickUp)
2. Team sets assignees and verifies SP estimates
3. The Sprint Crew validates and finalizes on Sunday

**You control what goes into the sprint. AI just executes the finalization.**

### Story Points (SP)

Each task has an SP estimate (set by AI during triage, adjustable by you):

| SP | Effort | Example |
|----|--------|---------|
| 2 | Quick fix | Typo, CSS tweak, config change |
| 3 | Small task | Bug fix, minor component update |
| 5 | Standard | New component, API endpoint |
| 8 | Complex | Multi-file feature, security fix |
| 13 | Large | New module, architecture change |
| 21 | Epic | Full system, major refactor |

If the estimate is wrong, change the SP custom field in ClickUp.

---

## ClickUp Guide

### Where to Find Things

```
📦 CareSpace.Ai Engine
├── 📋 Backlog
│   └── Master Backlog       ← Everything that needs doing (AI manages)
├── 📋 Sprint Planning
│   └── Sprint Candidates    ← Team curates what goes into the sprint
├── 📅 Sprints
│   └── Sprint N             ← YOUR WORK IS HERE
└── ⚙️ Operations
    └── 🚨 Alerts            ← Escalations
```

### Task Statuses

| Status | Meaning |
|--------|---------|
| **To Do** | Not started — in your queue |
| **In Progress** | You're actively working on it |
| **Blocked** | You can't continue — add a comment explaining why |
| **Done** | Complete — tested and working |

### Tags You'll See

| Tag | Meaning |
|-----|---------|
| `bug` | Bug report from GitHub |
| `feature` | New feature or enhancement |
| `task` | General task or tech debt |
| `security` | Security issue |
| `frontend` / `backend` / `mobile` | Domain |
| `github` | Came from GitHub issue |
| `design` | Design task (Buena team) |
| `meeting` | From a Slack huddle |

---

## Slack Channels

| Channel | What you'll see | Your action |
|---------|----------------|-------------|
| `#pm-standup` | Daily sprint digest at 7:45am | **Read it every morning** |
| `#pm-sprint-board` | Sprint plan + retro summaries | Read when sprint starts/ends |
| `#pm-engineering` | Import reports, backlog health | Check if something needs you |

**You only NEED to check `#pm-standup` daily.** Everything else is supplementary.

---

## The 6 AI Crews

| Crew | What it does | When |
|------|-------------|------|
| **Intake** | Imports GitHub issues to ClickUp, syncs statuses | Daily 7:00am |
| **Daily Pulse** | Sprint digest + per-task health analysis | Mon-Fri 7:45am |
| **Triage** | Dedup, normalize, estimate SP, check backlog health | Every 6 hours |
| **Sprint** | Finalize sprint from Sprint Candidates | Bi-weekly Sunday |
| **Retrospective** | Close sprint, carryovers, velocity | Bi-weekly Friday |
| **Huddle Notes** | Fetch Slack huddle notes → save to vault | Daily |

### What the AI Does NOT Do

- ❌ Write code for you
- ❌ Close GitHub issues (you do this when fixed)
- ❌ Choose what goes into the sprint (team curates candidates)
- ❌ Make design decisions
- ❌ Review pull requests
- ❌ Know if something works (only you can test)

---

## Common Situations

### "I finished my task"
1. Move the task to **Done** in ClickUp
2. Close the GitHub issue if there was one
3. It'll show as "Done" in tomorrow's digest

### "I'm stuck / blocked"
1. Move the task to **Blocked** in ClickUp
2. Add a comment: *"Blocked by: [what's blocking you]"*
3. The AI will flag it in the next digest

### "I found a bug"
1. Create a GitHub issue in the relevant repo
2. Label it (bug, priority)
3. Intake crew imports it to ClickUp backlog automatically

### "I need to add a new task"
Add it to the **Master Backlog** in ClickUp with tags (type + domain).
Or create a GitHub issue — the intake crew imports it.

### "My task is taking longer than expected"
Add a comment with an update. As long as there's activity, the AI won't flag it as stale.

### "I see my task flagged as stale"
The AI checks for ClickUp comments, not just status changes. Add a comment to your task — even a brief update like "still working on X" — and it won't be flagged next time.

### "My task says 'no PR opened'"
The AI checks if in-progress tasks have a matching open PR on GitHub. If you're working on code, open a draft PR so the AI can track it.

---

## For Team Leads

### Your Extra Responsibilities

1. **Curate Sprint Candidates** before each sprint
   - Add tasks from backlog to Sprint Candidates list
   - Set assignees and verify SP estimates
   - The Sprint Crew finalizes on Sunday

2. **Check the daily digest** for your team
   - Task Health section shows who's stuck
   - Stale tasks (3d+ no comments) need a check-in

3. **Adjust priorities** when needed
   - Change priority in ClickUp — triage respects it
   - If urgent, set to **Urgent** — triage picks it up within 6 hours

4. **Unblock your team**
   - When a task is flagged as blocked, you're the escalation path

---

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│          YOUR DAILY CHECKLIST               │
│                                             │
│  □ Read #pm-standup (7:45am digest)         │
│  □ Update task status in ClickUp            │
│  □ Add comments to active tasks             │
│  □ Open draft PRs for in-progress work      │
│  □ Move completed tasks to Done             │
│                                             │
│  That's it. The AI handles the rest.        │
└─────────────────────────────────────────────┘
```

---

## FAQ

**Q: Do I need to learn ClickUp?**
A: Just the basics — find your tasks, move them between status columns.

**Q: What if the AI assigns me a task I can't do?**
A: Tell your lead. They'll reassign it.

**Q: What happens if I don't update my task?**
A: After 3 days with no comments, the AI flags it as "stale" in the digest.

**Q: Why does my task say "no PR opened"?**
A: The AI checks if in-progress tasks have a matching PR on GitHub. Open a draft PR to track your work.

**Q: Can I add tasks to the sprint myself?**
A: Add to Sprint Candidates, not the sprint directly. The Sprint Crew finalizes.

**Q: Who do I ask if something isn't working?**
A: Post in `#pm-engineering`.
