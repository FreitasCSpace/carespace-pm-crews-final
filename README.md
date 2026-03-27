# CareSpace AI PM Crews

Nine AI-driven CrewAI crews orchestrated as a production Flow — managing project delivery for CareSpace, a healthcare SaaS with 18 engineers across 6 countries.

**The contract:** Team curates Sprint Candidates. AI handles everything else.

---

## Architecture

```
carespace-pm-crews-final/
├── pyproject.toml                       # type = "flow" (CrewHub)
├── src/
│   ├── main.py                          # PMCrewsFlow — single Flow dispatcher
│   ├── crews/                           # 9 AI-driven crews
│   │   ├── compliance/                  # Vanta health + compliance monitoring
│   │   ├── intake/                      # GitHub issues → Master Backlog + close sync
│   │   ├── daily_pulse/                 # Sprint Digest → #pm-standup
│   │   ├── sla/                         # Sprint SLA enforcement + alerts
│   │   ├── triage/                      # Dedup → normalize → estimate SP → scan → decide
│   │   ├── sprint/                      # Sprint Candidates → Sprint (team-curated)
│   │   ├── retrospective/               # Sprint close, carryovers, velocity
│   │   ├── exec_report/                 # Weekly executive dashboard
│   │   └── huddle_notes/                # Slack huddle → action items → ClickUp tasks
│   └── shared/
│       ├── config/context.py            # Single source of truth: IDs, team, thresholds
│       ├── tools/                       # ClickUp, GitHub, Slack, Vanta, Vault tools
│       ├── guardrails.py                # Task validation functions
│       ├── vault_hooks.py               # Vault read/write for cross-crew context
│       ├── models/                      # Pydantic output models
│       └── skills/                      # CrewAI Skills (pm-context, compliance, sprint)
└── .env
```

### Production Features

- **Flow orchestration** — single `PMCrewsFlow` dispatches to crews via CrewHub
- **Vault memory** — crews persist output to `carespace-pm-vault` GitHub repo; read context from previous runs
- **Planning** — `planning=True` on all crews (step-by-step plan before execution)
- **Reasoning** — `reasoning=True` on triage, exec, retro, sprint agents
- **Skills** — domain knowledge injected into all agents (PM context, HIPAA/SOC2, sprint methodology)
- **Structured outputs** — Pydantic models for type-safe data between tasks
- **Guardrails** — validate task outputs before accepting them

### Design Principles

- **AI suggests, team decides** — crews never override human sprint selections
- **GitHub is source of truth** — ClickUp tasks sync status from GitHub issues
- **Backlog stays unassigned** — assignees are set during sprint planning only
- **Single pipeline** — all work enters via GitHub → intake crew → ClickUp backlog
- **Sprint Candidates** — staging area where team curates what goes into the sprint
- **No noise** — SLA alerts only for sprint items, not backlog
- **One channel per crew** — no cross-posting or spam
- **Tags for visibility** — domain (frontend, backend), type (bug, feature), source (github, design)
- **Batch tools** — Python handles API calls/pagination, AI handles analysis/decisions

---

## ClickUp Workspace

```
📦 CareSpace.Ai Engine (901313687155)
├── 📂 Backlog (901317811713)
│   └── Master Backlog (901326439232)     ← Single intake point
├── 📋 Sprint Planning (901317852083)
│   └── Sprint Candidates (901326510572)  ← Team curates here
├── 📅 Sprints (901317811717)
│   └── Sprint N — auto-created           ← Active sprint
├── ⚙️ Operations (901317811718)
│   ├── Alerts & Escalations (901326439234)
│   └── Sprint History (901326439238)
└── 📚 Playbooks (901317811721)
```

**ClickUp statuses:** TO DO → IN PROGRESS → BLOCKED → COMPLETE

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
                   (901326510572)    ←── AI suggestions
                          │
                          ▼
                   Sprint Crew (finalizes) ──→ ACTIVE SPRINT
                                                    │
                                              Daily Pulse (daily digest)
                                              SLA Crew (every 6h — breach alerts)
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

### 1. Compliance Crew
**Schedule:** Daily 06:30 PDT | **Posts to:** `#pm-compliance`

Two-agent workflow: gather_agent (Vanta API) → post_agent (Slack).
Health indicator: RED/YELLOW/GREEN based on Vanta test pass rate.
Owner: Luis Freitas (sole compliance person).

### 2. Intake Crew
**Schedule:** Daily 07:00 PDT | **Posts to:** `#pm-engineering`

1. **Import** — scans all carespace-ai GitHub repos. Creates ClickUp tasks with tags.
2. **Sync** — two-way GitHub↔ClickUp status sync. GitHub is source of truth.

### 3. Daily Pulse Crew
**Schedule:** Mon–Fri 07:45 PDT | **Posts to:** `#pm-standup`

Structured digest: Executive Summary, Sprint Status (done/in-progress/blocked/todo),
Needs Attention (stale PRs, critical >30d PRs, CI failures, stale issues >3d),
Sprint Risks, Meeting Mode.

### 4. SLA Crew
**Schedule:** Every 6 hours | **Posts to:** `#pm-alerts`

Monitors ONLY active sprint tasks against SLA thresholds. Creates alerts for
breaches, DMs assignees. Silent when healthy (no post if no issues).

### 5. Triage Crew
**Schedule:** Every 6 hours | **Posts to:** `#pm-engineering`

1. Dedup backlog
2. Normalize design tasks (Buena team — no GitHub link = design tag)
3. Estimate SP on unestimated tasks
4. Scan backlog health (priorities, aging >21d)
5. Execute priority adjustments (no alerts — SLA crew handles those)
6. Post backlog health report

### 6. Sprint Crew
**Schedule:** Bi-weekly Sunday 18:00 PDT | **Posts to:** `#pm-sprint-board`

Executor, not decision-maker. Checks Sprint Candidates → validates → finalizes.
If empty, warns team (does NOT auto-plan from backlog).

### 7. Retrospective Crew
**Schedule:** Bi-weekly Friday 16:00 PDT | **Posts to:** `#pm-sprint-board`

Closes sprint: completed → archived, incomplete → backlog with "carryover" tag + priority bump.
Calculates velocity, per-engineer breakdown, recommends next sprint capacity.

### 8. Exec Report Crew
**Schedule:** Friday 17:00 PDT | **Posts to:** `#pm-exec-updates`

Health dashboard: Engineering, Compliance, Bug Health. Traffic light format.
Reads vault context from all other crews for trend analysis.

### 9. Huddle Notes Crew
**Schedule:** On demand | **Posts to:** `#pm-engineering`

Extracts action items from Slack huddle notes → creates ClickUp tasks → posts recap.

---

## Daily Schedule (Oregon/PDT)

```
06:30  compliance         Vanta health → #pm-compliance
07:00  intake             GitHub import + sync → #pm-engineering
07:45  daily_pulse        Sprint Digest → #pm-standup
*/6h   sla               Sprint SLA checks → #pm-alerts
*/6h   triage             Backlog health → #pm-engineering

Fri    exec_report        Weekly dashboard → #pm-exec-updates
Fri    retrospective      Sprint retro → #pm-sprint-board (bi-weekly)
Sun    sprint             Finalize sprint → #pm-sprint-board (bi-weekly)
```

---

## Vault (Cross-Crew Memory)

Crews persist output to `FreitasCSpace/carespace-pm-vault` GitHub repo and read
context from previous runs. This replaces CrewAI's built-in memory.

```
carespace-pm-vault/
├── sprints/{plans, retros, daily}/   # Sprint lifecycle data
├── triage/                           # Backlog health reports
├── compliance/                       # Daily Vanta health deltas
├── sla/                              # SLA breach logs
├── intake/                           # Import summaries
├── exec/                             # Weekly exec reports
├── huddles/                          # Meeting action items
└── context/                          # Rolling state (velocity, backlog, compliance)
```

---

## Slack Channels

| Channel | Crew(s) | Content |
|---------|---------|---------|
| `#pm-standup` | Daily Pulse | Sprint Digest (Mon-Fri) |
| `#pm-sprint-board` | Sprint, Retrospective | Sprint plan, retro summary |
| `#pm-engineering` | Intake, Triage, Huddle Notes | Tasks, backlog health, huddle recaps |
| `#pm-alerts` | SLA | SLA breaches and escalations |
| `#pm-exec-updates` | Exec Report | Executive summary (weekly) |
| `#pm-compliance` | Compliance | Vanta health (daily) |

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
| `VANTA_CLIENT_ID` | compliance, exec_report |
| `VANTA_CLIENT_SECRET` | compliance, exec_report |

### Configuration

All tunable values in `src/shared/config/context.py`:
- Team roster, domains, capacity
- Sprint budget (48 SP), compliance cap (3)
- Thresholds (stale PR days, SLA hours, aging backlog)
- Slack channels, list IDs, scoring weights

---

## Human + AI Contract

**Team does:**
1. Create issues via `/backlog` or GitHub
2. Curate Sprint Candidates (add tasks, set assignees)
3. Review `#pm-standup` daily
4. Move tasks to "done" when complete
5. Run `/sprint-plan` before each sprint

**AI does everything else** — intake, sync, dedup, normalize, estimate, triage, sprint finalization, standup, SLA enforcement, compliance monitoring, executive reporting, huddle note extraction, vault persistence, and carryover management.
