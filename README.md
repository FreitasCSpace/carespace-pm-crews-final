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
│   │   ├── intake/                      # GitHub issues → Master Backlog + close sync
│   │   ├── daily_pulse/                 # Sprint Digest → #pm-standup
│   │   ├── triage/                      # Dedup → normalize → estimate SP → scan → decide
│   │   ├── sprint/                      # Sprint Candidates → Sprint (team-curated)
│   │   ├── retrospective/               # Sprint close, carryovers, velocity
│   │   └── huddle_notes/                # Slack huddle → action items → ClickUp tasks
│   └── shared/
│       ├── config/context.py            # Single source of truth: IDs, team, thresholds
│       ├── tools/                       # ClickUp, GitHub, Slack, Vault tools
│       ├── guardrails.py                # Task validation functions
│       ├── vault_hooks.py               # Vault read/write for cross-crew context
│       ├── models/                      # Pydantic output models
│       └── skills/                      # CrewAI Skills (pm-context, sprint)
└── .env
```

### Production Features

- **Flow orchestration** — single `PMCrewsFlow` dispatches to crews via CrewHub
- **Vault memory** — crews persist output to `carespace-pm-vault` GitHub repo; read context from previous runs
- **Planning** — `planning=True` on all crews (step-by-step plan before execution)
- **Reasoning** — `reasoning=True` on triage, retro, sprint agents
- **Skills** — domain knowledge injected into all agents
- **Structured outputs** — Pydantic models for type-safe data between tasks
- **Guardrails** — validate task outputs before accepting them

### Design Principles

- **AI suggests, team decides** — crews never override human sprint selections
- **GitHub is source of truth** — ClickUp tasks sync status from GitHub issues
- **Backlog stays unassigned** — assignees are set during sprint planning only
- **Single pipeline** — all work enters via GitHub → intake crew → ClickUp backlog
- **Sprint Candidates** — staging area where team curates what goes into the sprint
- **One channel per crew** — no cross-posting or spam
- **Tags for visibility** — domain (frontend, backend), type (bug, feature), source (github, design)
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
                                     ←── AI suggestions
                          │
                          ▼
                   Sprint Crew (finalizes) ──→ ACTIVE SPRINT
                                                    │
                                              Daily Pulse (sprint digest + task health)
                                                    │
                                                    ▼
                                                  DONE
                                                    │
                                              Retrospective Crew
                                              • Completed → archived
                                              • Incomplete → backlog + "carryover" tag

GitHub↔ClickUp Sync (runs with intake):
  • GitHub closed → ClickUp complete
  • GitHub open → ClickUp reopened to "to do"
```

---

## Crew Reference

### 1. Intake Crew
**Schedule:** Daily 07:00 PDT | **Posts to:** `#pm-engineering`

1. **Import** — scans all carespace-ai GitHub repos. Creates ClickUp tasks with tags.
2. **Sync** — two-way GitHub↔ClickUp status sync. GitHub is source of truth.

### 2. Daily Pulse Crew
**Schedule:** Mon–Fri 07:45 PDT | **Posts to:** `#pm-standup`

Structured sprint digest: Executive Summary, Sprint Status (done/in-progress/blocked/todo),
Task Health (per-task analysis: stale comments, missing PRs, unassigned, stale PRs),
Meeting Mode.

### 3. Triage Crew
**Schedule:** Every 6 hours | **Posts to:** `#pm-engineering`

1. Dedup backlog
2. Normalize design tasks (Buena team — no GitHub link = design tag)
3. Estimate SP on unestimated tasks
4. Scan backlog health (priorities, aging >21d)
5. Execute priority adjustments
6. Post backlog health report

### 4. Sprint Crew
**Schedule:** Bi-weekly Sunday 18:00 PDT | **Posts to:** `#pm-sprint-board`

Executor, not decision-maker. Checks Sprint Candidates → validates → finalizes.
If empty, warns team (does NOT auto-plan from backlog).

### 5. Retrospective Crew
**Schedule:** Bi-weekly Friday 16:00 PDT | **Posts to:** `#pm-sprint-board`

Closes sprint: completed → archived, incomplete → backlog with "carryover" tag + priority bump.
Calculates velocity, per-engineer breakdown, recommends next sprint capacity.

### 6. Huddle Notes Crew
**Schedule:** On demand | **Posts to:** `#pm-engineering`

Extracts action items from Slack huddle notes → creates ClickUp tasks → posts recap.

---

## Daily Schedule (Oregon/PDT)

```
07:00  intake             GitHub import + sync → #pm-engineering
07:45  daily_pulse        Sprint Digest → #pm-standup
*/6h   triage             Backlog health → #pm-engineering

Fri    retrospective      Sprint retro → #pm-sprint-board (bi-weekly)
Sun    sprint             Finalize sprint → #pm-sprint-board (bi-weekly)
```

---

## Vault (Cross-Crew Memory)

Crews persist output to `FreitasCSpace/carespace-pm-vault` GitHub repo and read
context from previous runs. This replaces CrewAI's built-in memory.

```
carespace-pm-vault/
├── sprint/
│   ├── daily/          # Daily pulse digests (task health, progress)
│   ├── plans/          # Sprint plans (sprint-N.md)
│   └── retros/         # Sprint retrospectives (sprint-N.md)
├── backlog/            # Triage reports (backlog health, priorities)
├── intake/             # GitHub import summaries
├── huddles/            # Meeting notes from Slack huddles
└── context/            # Rolling state files (overwritten each run)
    ├── velocity.md     # Latest velocity data (from retro)
    └── backlog-health.md  # Latest backlog snapshot (from triage)
```

**How it works:**
- Each crew writes its output after every run (dated markdown files)
- `context/` files are rolling snapshots — always the latest state
- Crews read context from previous runs to detect trends and deltas
- Huddle notes: first run fetches all history, subsequent runs fetch daily

---

## Slack Channels

| Channel | Crew(s) | Content |
|---------|---------|---------|
| `#pm-standup` | Daily Pulse | Sprint Digest (Mon-Fri) |
| `#pm-sprint-board` | Sprint, Retrospective | Sprint plan, retro summary |
| `#pm-engineering` | Intake, Triage, Huddle Notes | Tasks, backlog health, huddle recaps |

**Rule:** Each crew posts to ONE channel only. No cross-posting.

---

## Setup

### Required Secrets

| Secret | Used by |
|--------|---------|
| `CLICKUP_API_TOKEN` | All crews (pk_ format) |
| `GITHUB_TOKEN` | intake, daily_pulse, vault tools (ghp_ format) |
| `OPENAI_API_KEY` | All crews (LLM + planning) |
| `SLACK_BOT_TOKEN` | All crews (xoxb_ format) |

### Configuration

All tunable values in `src/shared/config/context.py`:
- Team roster, domains, capacity
- Sprint budget (48 SP)
- Thresholds (stale PR days, aging backlog)
- Slack channels, list IDs, scoring weights

---

## Human + AI Contract

**Team does:**
1. Create issues via `/backlog` or GitHub
2. Curate Sprint Candidates (add tasks, set assignees)
3. Review `#pm-standup` daily
4. Move tasks to "done" when complete
5. Run `/sprint-plan` before each sprint

**AI does everything else** — intake, sync, dedup, normalize, estimate, triage, sprint finalization, standup, huddle note extraction, vault persistence, and carryover management.
