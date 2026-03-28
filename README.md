# CareSpace AI PM Crews

Six AI-driven CrewAI crews orchestrated as a production Flow — managing project delivery for CareSpace, a healthcare SaaS with 18 engineers across 6 countries.

**The contract:** Team curates Sprint Candidates. AI handles everything else.

---

## Architecture

```
carespace-pm-crews-final/
├── pyproject.toml                       # type = "flow" (CrewHub)
├── src/
│   ├── main.py                          # PMCrewsFlow — single Flow dispatcher
│   ├── crews/                           # 6 AI-driven crews
│   │   ├── intake/                      # GitHub → ClickUp backlog sync
│   │   ├── daily_pulse/                 # Sprint digest + task health → #pm-standup
│   │   ├── triage/                      # Backlog hygiene (dedup, SP, priorities)
│   │   ├── sprint/                      # Finalize sprint from candidates
│   │   ├── retrospective/              # Sprint close, carryovers, velocity
│   │   └── huddle_notes/               # Slack huddle → vault summary
│   └── shared/
│       ├── config/context.py            # Single source of truth: IDs, team, thresholds
│       ├── tools/                       # ClickUp, GitHub, Slack, Vault tools
│       ├── guardrails.py                # Task validation functions
│       ├── vault_hooks.py               # Vault read/write for cross-crew context
│       ├── models/                      # Pydantic output models
│       └── skills/                      # CrewAI Skills
└── .env
```

### Production Features

- **Flow orchestration** — `PMCrewsFlow` dispatches to crews via CrewHub on Azure
- **Vault memory** — crews persist output to `carespace-pm-vault` GitHub repo
- **Planning** — `planning=True` on all crews (step-by-step plan before execution)
- **Structured outputs** — Pydantic models for type-safe data between tasks
- **Guardrails** — validate task outputs before accepting them
- **Stale task detection** — checks ClickUp comments (not bot-bumped timestamps)
- **PR coverage** — flags in-progress sprint tasks with no open PR

### Design Principles

- **AI suggests, team decides** — crews never override human sprint selections
- **GitHub is source of truth** — ClickUp tasks sync status from GitHub issues
- **Backlog stays unassigned** — assignees are set during sprint planning only
- **Sprint-scoped reporting** — daily pulse only covers current sprint, never backlog
- **Single pipeline** — all work enters via GitHub → intake crew → ClickUp backlog
- **Sprint Candidates** — staging area where team curates what goes into the sprint
- **No noise** — empty sections hidden, no "None" lines, no backlog dumps
- **Batch tools** — Python handles API calls/pagination, AI handles analysis/decisions

---

## Data Flow

```
/backlog skill ──→ GitHub Issue ──→ Intake Crew ──→ MASTER BACKLOG
                                                        │
                                                   Triage Crew (every 6h)
                                                   • Dedup → Normalize → SP → Priorities
                                                        │
                          ┌─────────────────────────────┘
                          ▼
                   Sprint Candidates ←── Team adds tasks + sets assignees
                   (staging area)    ←── /sprint-plan skill (guided)
                          │
                          ▼
                   Sprint Crew (finalizes) ──→ ACTIVE SPRINT
                                                    │
                                              Daily Pulse (task health + digest)
                                                    │
                                                    ▼
                                                  DONE
                                                    │
                                              Retrospective Crew
                                              • Completed → archived
                                              • Incomplete → backlog + "carryover" tag

Huddle Notes: Slack huddles → vault (daily, no ClickUp tasks)
GitHub↔ClickUp Sync: GitHub closed → ClickUp complete (and vice versa)
```

---

## Crew Reference

### 1. Intake Crew
**Schedule:** Every 3 hours | **Posts to:** `#pm-engineering`

Scans all carespace-ai GitHub repos, creates ClickUp tasks with tags.
Two-way sync: GitHub closed = ClickUp complete, GitHub reopened = ClickUp "to do".

### 2. Daily Pulse Crew
**Schedule:** Mon-Fri 07:45 PDT | **Posts to:** `#pm-standup`

Sprint-only digest with per-task health analysis:
- **Sprint status** — done/in-progress/blocked/to-do (empty sections hidden)
- **Task health** — each problematic task listed once with all issues:
  stale (no comments 3d+), missing PR, unassigned, stale PR
- **Meeting mode** — standup or open slot based on risk count

All tasks link to ClickUp. Clean format: `Task Name — @assignee · 3 SP`

### 3. Triage Crew
**Schedule:** Every 3 hours (15min after intake) | **Posts to:** `#pm-engineering`

Backlog hygiene pipeline:
1. Dedup (remove duplicate tasks)
2. Normalize design tasks (Buena team)
3. Estimate SP on unestimated tasks
4. Scan health (priorities, aging >21d)
5. Execute priority adjustments
6. Post backlog health report

### 4. Sprint Crew
**Schedule:** Bi-weekly Sunday 18:00 PDT | **Posts to:** `#pm-sprint-board`

Executor, not decision-maker. Checks Sprint Candidates → validates → finalizes.
If empty, warns team (does NOT auto-plan from backlog).

### 5. Retrospective Crew
**Schedule:** Bi-weekly Friday 16:00 PDT | **Posts to:** `#pm-sprint-board`

Closes sprint: completed → archived, incomplete → backlog with "carryover" tag.
Calculates velocity, per-engineer breakdown, recommends next sprint capacity.

### 6. Huddle Notes Crew
**Schedule:** Daily 11:00 PDT | **Writes to:** vault only

Fetches today's huddle notes from Slack (`#carespace-team`), resolves user IDs
to real names, produces structured summary (attendees, topics, actions, decisions,
blockers). Saves to vault. No ClickUp tasks, no Slack posting.
If no huddle today, writes nothing.

---

## Daily Schedule (Oregon/PDT)

All times PDT (America/Los_Angeles).

```
*/3h   intake             GitHub import + sync → #pm-engineering
*/3h   triage             Backlog health → #pm-engineering (+15min after intake)
07:45  daily_pulse        Sprint Digest → #pm-standup
11:00  huddle_notes       Slack huddle → vault (if huddle occurred)

Fri 16:00  retrospective  Sprint retro → #pm-sprint-board (bi-weekly)
Sun 18:00  sprint         Finalize sprint → #pm-sprint-board (bi-weekly)
```

---

## Vault (Cross-Crew Memory)

Crews persist output to `FreitasCSpace/carespace-pm-vault` GitHub repo and read
context from previous runs.

```
carespace-pm-vault/
├── sprint/
│   ├── daily/              # Daily pulse digests (task health, progress)
│   ├── plans/              # Sprint plans (sprint-N.md)
│   └── retros/             # Sprint retrospectives (sprint-N.md)
├── backlog/                # Triage reports (backlog health, priorities)
├── intake/                 # GitHub import summaries
├── huddles/                # Meeting notes with real names (53 historical + daily)
└── context/                # Rolling state (overwritten each run)
    ├── velocity.md         # Latest velocity data (from retro)
    └── backlog-health.md   # Latest backlog snapshot (from triage)
```

**How it works:**
- Each crew writes dated markdown files after every run
- `context/` files are rolling snapshots — always the latest state
- Crews read previous context to detect trends and deltas
- Huddle notes: historical archive seeded, crew fetches daily only
- No write if crew has nothing to report (e.g. no huddle today)

---

## Slack Channels

| Channel | Crew | Content |
|---------|------|---------|
| `#pm-standup` | Daily Pulse | Sprint digest + task health (Mon-Fri) |
| `#pm-sprint-board` | Sprint, Retro | Sprint plan, retrospective summary |
| `#pm-engineering` | Intake, Triage | Import results, backlog health |

Huddle Notes crew does not post to Slack — vault only.

---

## Setup

### Required Slack Bot Scopes

| Scope | Used for |
|-------|----------|
| `chat:write` | Post messages to channels |
| `channels:read` | Resolve channel names to IDs |
| `channels:history` | Read channel messages (standup dedup, huddle detection) |
| `files:read` | Read huddle canvas files from Slack archives |
| `users:read` | Resolve Slack user IDs to real names |

### Required Secrets

| Secret | Used by |
|--------|---------|
| `CLICKUP_API_TOKEN` | All crews (pk_ format) |
| `GITHUB_TOKEN` | Intake, daily pulse, vault tools (ghp_ format) |
| `OPENAI_API_KEY` | All crews (LLM + planning) |
| `SLACK_BOT_TOKEN` | Daily pulse, huddle notes (xoxb_ format) |

### Configuration

All tunable values in `src/shared/config/context.py`:
- Team roster (18 engineers), domains, capacity per person
- Sprint budget (48 SP), sprint duration (2 weeks)
- Thresholds: stale PR days, stale task days, aging backlog cutoff
- Slack channels, ClickUp list IDs, scoring weights

---

## Human + AI Contract

**Team does:**
1. Create issues via `/backlog` or GitHub
2. Curate Sprint Candidates (add tasks, set assignees)
3. Review `#pm-standup` daily
4. Move tasks to "done" when complete
5. Run `/sprint-plan` before each sprint

**AI does everything else** — intake, sync, dedup, normalize, estimate, triage,
sprint finalization, daily digest, task health analysis, huddle archival,
vault persistence, and carryover management.
