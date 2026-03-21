# CareSpace AI Project Management — Team Manual

> **Read time:** 10 minutes
> **Last updated:** March 18, 2026
> **For:** All CareSpace engineers and team leads

---

## What Is This?

CareSpace now uses an **AI-powered project management system** that handles the heavy PM work automatically. You don't need to learn a new tool or change how you code. You just need to understand 3 things:

1. **Where your work lives** (ClickUp)
2. **What the AI does for you** (everything except coding)
3. **What you need to do** (5 simple things)

---

## Your Daily Routine (5 Minutes)

### Every Morning at 7:45am (Oregon time)

The AI posts a **Sprint Digest** to `#pm-standup` in Slack. It looks like this:

```
📊 Sprint Digest — March 18, 2026

Executive Summary
• Sprint 1 — 12 days remaining
• Progress: 30% complete (15/48 SP)
• Status: 🟡 At Risk — 2 tasks stale

✅ Done
• Fix Card Width — @Andre (3 SP)

🔄 In Progress
• Auth middleware fix — @Willian (3 SP)

🚫 Blocked
None

⏳ Pending
• Patient Onboarding — @Andre (5 SP)
• ROM Calculation — @Andre (5 SP)

⚠️ Needs Attention
• carespace-ui PR #36 — 35 days old (CRITICAL)

🎯 Meeting Mode
🟢 OPEN SLOT: No blockers. Available for strategic discussion.
```

**Your action:** Read it. Takes 2 minutes. If you see your name under "Pending" — that's your work to start. If you see "Blocked" — speak up in the meeting.

---

## What You Need To Do

### 1. Work From the Sprint List

Your tasks for the next 2 weeks are in **ClickUp → Sprints → Sprint N**.

- Open ClickUp → `📅 Sprints` folder → current sprint
- You'll see tasks assigned to you with priority and SP
- When you **start** a task: move it to **"In Progress"**
- When you **finish** a task: move it to **"Done"**

That's it. The AI handles everything else.

### 2. Update Task Status (This Is Critical)

The AI reads task statuses every morning to build the standup. If your task is stuck but still shows "In Progress" for 3+ days, the AI will flag it as **stale** and post it to `#pm-alerts`.

| When... | Set status to... |
|---------|-----------------|
| You start working on a task | **In Progress** |
| You finish a task | **Done** / **Complete** |
| You're blocked and can't continue | **Blocked** |
| You need a code review | **In Review** (optional) |

**If you don't update status, the AI assumes you're stuck.**

### 3. Report Blockers Immediately

If you're blocked:
1. Set the task status to **"Blocked"** in ClickUp
2. Add a comment explaining what's blocking you:
   - *"Waiting on API endpoint from Fabiano"*
   - *"Depends on Azure infra change"*
   - *"Need design decision from Flavio"*

The AI will:
- Flag it in the next standup
- Post it to `#pm-alerts`
- Trace the dependency chain
- Classify severity (CRITICAL if blocking the sprint goal)

### 4. Don't Ignore GitHub Issues

When you create or find bugs in GitHub, the AI automatically imports them into ClickUp. You don't need to manually create ClickUp tasks — the `intake_crew` does this every morning.

But you DO need to:
- **Label your GitHub issues** properly (bug, enhancement, etc.)
- **Close GitHub issues** when fixed (the AI doesn't close them for you)

### 5. Review Pull Requests on Time

The AI monitors stale PRs. If your PR sits unreviewed for **7+ days**, it:
- Creates a review task in the backlog
- Posts it to `#pm-engineering`
- If **30+ days**: creates an urgent alert in `#pm-alerts`

**When you see a PR review request**, try to review within 3 days.

---

## How the Sprint Works

### Sprint Cycle (Every 2 Weeks)

```
Sunday 6pm:  AI creates Sprint N+1
             Scores all backlog tasks
             Picks ~10-12 tasks (bugs + features + tasks + compliance)
             Moves them to the sprint list
             Posts plan to #pm-sprint-board

Mon-Fri:     You work on your sprint tasks
             AI posts daily standup at 7:45am
             AI checks for blockers and stale tasks

Friday 4pm:  AI runs retrospective (bi-weekly)
             Posts velocity and completion metrics
             Recommends next sprint capacity

Friday 5pm:  AI posts weekly exec report
             Health dashboard across all dimensions
```

### What Goes Into a Sprint?

The AI selects tasks based on:

| Priority | What gets picked first |
|----------|----------------------|
| 1 | **Critical bugs** — production issues, security (urgent/high priority) |
| 2 | **Features** — at least 3 per sprint (moves the product forward) |
| 3 | **Tasks** — tech debt, refactoring, CI fixes |
| 4 | **Compliance** — max 3 per sprint (Luis handles these) |

The sprint budget is **48 Story Points**. The AI won't over-commit.

### Story Points (SP)

Each task has an SP estimate set by the AI:

| SP | Effort | Example |
|----|--------|---------|
| 2 | Quick fix | Typo, CSS tweak, config change |
| 3 | Small task | Bug fix, minor component update |
| 5 | Standard task | New component, API endpoint, feature page |
| 8 | Complex task | Multi-file feature, security fix, integration |
| 13 | Large feature | New module, architecture change |
| 21 | Epic | Full system, major refactor |

If you think the AI estimated wrong, tell your lead — they can adjust it.

---

## ClickUp Guide (For You)

### Where to Find Things

```
📅 CareSpace.Ai Engine
├── 📋 Backlog
│   └── Master Backlog  ← Everything that needs doing (AI manages this)
├── 📅 Sprints
│   └── Sprint 1        ← YOUR WORK IS HERE
├── ⚙️ Operations
│   └── 🚨 Alerts       ← Escalations (you'll see these in Slack too)
```

### Task Views You Should Use

1. **"My Tasks"** — filter by your name to see only your work
2. **Sprint Board** — Kanban view of the current sprint (drag cards between columns)
3. **By Priority** — see urgent items first

### Task Statuses

| Status | Meaning |
|--------|---------|
| **To Do** | Not started — it's in your queue |
| **In Progress** | You're actively working on it |
| **In Review** | PR submitted, waiting for review |
| **Blocked** | You can't continue — add a comment explaining why |
| **Done** | Complete — tested and working |

### Tags You'll See

| Tag | Meaning |
|-----|---------|
| `bug` | Bug report from GitHub |
| `feature` | New feature or enhancement |
| `task` | General task or tech debt |
| `security` | Security issue — always urgent |
| `compliance` | HIPAA/SOC2 compliance task (Luis handles these) |
| `frontend` / `backend` / `mobile` | Domain |
| `github` | Came from GitHub issue |

---

## Slack Channels

| Channel | What you'll see | Your action |
|---------|----------------|-------------|
| `#pm-standup` | Daily sprint digest at 7:45am | **Read it every morning** |
| `#pm-sprint-board` | Sprint plan + retro summaries | Read when sprint starts |
| `#pm-engineering` | New tasks imported, PR radar reports | Check if anything is assigned to you |
| `#pm-alerts` | Blockers, SLA breaches, triage reports | Act if you're the owner |
| `#pm-compliance` | Compliance health (Luis mainly) | Ignore unless tagged |
| `#pm-exec-updates` | Weekly exec dashboard | Optional read |

**You only NEED to check `#pm-standup` daily.** Everything else is supplementary.

---

## Common Situations

### "I finished my task"
1. Move the task to **Done** in ClickUp
2. If there was a GitHub issue, close it in GitHub too
3. The AI will report it as "Done" in tomorrow's standup

### "I'm stuck / blocked"
1. Move the task to **Blocked** in ClickUp
2. Add a comment: *"Blocked by: [what's blocking you]"*
3. The AI will flag it in the next standup and post to `#pm-alerts`
4. Discuss in the morning meeting if needed

### "I found a bug"
1. Create a GitHub issue in the relevant repo
2. Label it appropriately (bug, priority)
3. The AI will import it into ClickUp backlog automatically
4. It'll be triaged and possibly added to the next sprint

### "I need to add a new task"
1. Add it to the **Master Backlog** in ClickUp
2. Add tags: type (bug/feature/task) + domain (frontend/backend/etc.)
3. The AI will assign it, estimate SP, and prioritize it

Or simply create a GitHub issue — the AI imports it.

### "My task is taking longer than expected"
1. Keep the status as **In Progress**
2. Add a comment with an update: *"Taking longer because..."*
3. If you won't finish this sprint, tell your lead — it becomes a carry-over

### "I want to change my task's priority"
Tell your lead. They can adjust priority in ClickUp, and the AI will respect it in the next triage run.

### "I see a stale alert about my PR"
1. Check the PR — is it still relevant?
2. If yes: request a reviewer or review it yourself
3. If no: close the PR
4. The alert will disappear in the next PR radar run

### "I got assigned a task I don't understand"
1. Read the task description — it usually has a GitHub issue link
2. Click the GitHub link for full context
3. If still unclear, ask in Slack or the morning meeting

---

## What the AI Does (You Don't Have To)

| AI does this | So you don't have to... |
|-------------|------------------------|
| Import GitHub issues to ClickUp | Manually create ClickUp tasks |
| Assign tasks to domain experts | Figure out who should do what |
| Estimate story points | Spend time in estimation meetings |
| Plan sprints (pick tasks, balance team) | Sit in 2-hour planning meetings |
| Post daily standup | Go around the room for 90 minutes |
| Detect stale tasks and blockers | Chase people for status updates |
| Monitor PRs and CI | Manually check GitHub Actions |
| Track compliance health | Read Vanta dashboards daily |
| Generate exec reports | Write weekly status updates |
| Enforce SLA on bugs | Remember which bugs are overdue |

### What the AI Does NOT Do

- ❌ Write code for you
- ❌ Close GitHub issues (you do this when fixed)
- ❌ Make design decisions
- ❌ Choose technical approach
- ❌ Review pull requests
- ❌ Talk to customers
- ❌ Know if something works (only you can test)

---

## For Team Leads

### Your Extra Responsibilities

1. **Review the sprint plan** when it's posted to `#pm-sprint-board`
   - Does the mix make sense?
   - Is anyone overloaded?
   - Are the right features included?

2. **Check `#pm-alerts` daily**
   - Blockers need your decision
   - SLA breaches need your attention
   - Stale tasks might need a check-in with the engineer

3. **Adjust priorities** when needed
   - The AI respects priority changes you make in ClickUp
   - If something urgent comes up mid-sprint, set it to **Urgent**
   - The triage crew will escalate it in the next 6-hour run

4. **Unblock your team**
   - When the AI flags a blocker, you're the escalation path
   - Make the decision or find the person who can

### When the AI Gets It Wrong

The AI makes judgment calls. Sometimes it's wrong:
- **Wrong priority?** Change it in ClickUp. Triage will respect it.
- **Wrong assignee?** Reassign in ClickUp. Sprint crew won't override.
- **Wrong SP estimate?** Edit the SP custom field in ClickUp.
- **Missed a task?** Add it to the backlog with proper tags.

The AI learns from the data — better tags and descriptions = better decisions.

---

## For Leadership (CEO/CTO)

### Your 2-Minute Daily

1. Open `#pm-standup` in Slack
2. Read the **Executive Summary** (first 4 lines)
3. That's it. You know where everything stands.

### Your 5-Minute Weekly

1. Open `#pm-exec-updates` on Friday evening
2. Read the health dashboard (traffic lights)
3. Check top 3 risks
4. Celebrate wins

### If You Need to Reprioritize

1. Open the task in ClickUp
2. Change its priority to **Urgent**
3. The AI will pick it up in the next triage run (every 6 hours)
4. If it's truly urgent, post in `#pm-alerts` — the team will see it

**Do NOT** message engineers directly asking "when is this done?" — the answer is in the standup digest.

---

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│          YOUR DAILY CHECKLIST               │
│                                             │
│  □ Read #pm-standup (7:45am digest)         │
│  □ Update task status in ClickUp            │
│  □ Report any blockers immediately          │
│  □ Review PRs assigned to you              │
│  □ Move completed tasks to Done             │
│                                             │
│  That's it. The AI handles the rest.        │
└─────────────────────────────────────────────┘
```

---

## FAQ

**Q: Do I need to learn ClickUp?**
A: Just the basics — find your tasks, drag them between status columns. The AI handles everything else.

**Q: What if the AI assigns me a task I can't do?**
A: Tell your lead. They'll reassign it in ClickUp.

**Q: What if I disagree with the sprint plan?**
A: Talk to your lead before the sprint starts. They can adjust tasks.

**Q: Do I need to attend the daily meeting?**
A: Yes, but it should be 15 minutes max. The AI already posted the status — the meeting is only for blockers and decisions.

**Q: What happens if I don't update my task status?**
A: After 3 days, the AI flags it as "stale" in `#pm-alerts`. Your lead will check in.

**Q: Can I add tasks to the sprint myself?**
A: Add to the Master Backlog with proper tags. The AI will consider it for the next sprint. Don't add directly to the sprint list.

**Q: What if ClickUp is down?**
A: Work normally. The AI will catch up when ClickUp is back. Your code doesn't depend on ClickUp.

**Q: Who do I ask if something isn't working?**
A: Post in `#pm-engineering`. The AI system is maintained by the automation team.
