# CareSpace AI PM Crews

Five AI-driven CrewAI crews orchestrated as a production Flow — managing project delivery for CareSpace, a healthcare SaaS with 18 engineers across 6 countries.

**The contract:** Team curates Sprint Candidates. AI handles everything else.

---

## Architecture

```
carespace-pm-crews-final/
├── pyproject.toml                       # type = "flow" (CrewHub)
├── src/
│   ├── main.py                          # PMCrewsFlow — single Flow dispatcher
│   ├── crews/                           # 5 AI-driven crews
│   │   ├── backlog/                     # GitHub import + sync + backlog hygiene
│   │   ├── daily_pulse/                 # Sprint digest + task health → #pm-standup
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
- **before_kickoff optimization** — deterministic work (dedup, normalize, data gathering) runs before LLM, reducing token cost
- **Stale task detection** — checks ClickUp comments (not bot-bumped timestamps)
- **PR coverage** — flags in-progress sprint tasks with no open PR

### Design Principles

- **AI suggests, team decides** — crews never override human sprint selections
- **GitHub is source of truth** — ClickUp tasks sync status from GitHub issues
- **Backlog stays unassigned** — assignees are set during sprint planning only
- **Sprint-scoped reporting** — daily pulse only covers current sprint, never backlog
- **3 task sources** — GitHub (engineering), Vanta (compliance, `[Vanta]` prefix), Design (Buena team, `design` tag)
- **Single pipeline** — all work enters via GitHub → backlog crew → ClickUp backlog
- **Sprint Candidates** — staging area where team curates what goes into the sprint
- **No noise** — empty sections hidden, no "None" lines, no backlog dumps
- **Batch tools** — Python handles API calls/pagination, AI handles analysis/decisions

---

## Data Flow

```
/backlog skill ──→ GitHub Issue ──→ Backlog Crew ──→ MASTER BACKLOG
                                      (every 3h)
                                   • before_kickoff: Dedup → Normalize → SP
                                   • Agent 1: Import + sync
                                   • Agent 2: Backlog health + priorities
                                   • Agent 3: Post combined report
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

### 1. Backlog Crew (intake + triage merged)
**Schedule:** Every 3 hours | **Posts to:** `#pm-engineering`

Full backlog pipeline in one run:
- **before_kickoff** (deterministic, no LLM): dedup across all 3 lists (Master Backlog, Sprint lists, Sprint Candidates), normalize design tasks (skips Vanta), estimate SP
- **Agent 1** — GitHub import + two-way sync across all 3 lists (GitHub closed = ClickUp complete)
- **Agent 2** — scan backlog health (include_closed=true for accurate counts), make priority decisions
- **Agent 3** — post ONE combined report to `#pm-engineering` (total items, bugs, features, compliance, design, tasks — every action item has clickable ClickUp + GitHub links)

### 2. Daily Pulse Crew
**Schedule:** Mon-Fri 07:45 PDT | **Posts to:** `#pm-standup`

Sprint-only digest with per-task health analysis:
- **before_kickoff** (no LLM): gathers sprint tasks, stale checks, PR coverage
- **Agent** — analyzes pre-gathered data, writes digest, posts via `post_standup`
- **Task health** — each problematic task listed once with all issues
- **Meeting mode** — standup or open slot based on risk count

### 3. Sprint Crew
**Schedule:** Bi-weekly Sun 18:00 PDT | **Posts to:** `#pm-sprint-board`

Executor, not decision-maker. Checks Sprint Candidates → validates → finalizes.
If empty, warns team (does NOT auto-plan from backlog).

### 4. Retrospective Crew
**Schedule:** Bi-weekly Friday 16:00 PDT | **Posts to:** `#pm-sprint-board`

Closes sprint: completed → archived, incomplete → backlog with "carryover" tag.
Calculates velocity, per-engineer breakdown, recommends next sprint capacity.

### 5. Huddle Notes Crew
**Schedule:** Daily 11:00 PDT | **Writes to:** vault only

- **before_kickoff** (no LLM): fetches today's huddle from Slack, resolves user IDs to names
- **Agent** — summarizes pre-fetched content into structured markdown (zero tools)
- If no huddle today, writes nothing to vault

---

## Daily Schedule (Oregon/PDT)

All times PDT (America/Los_Angeles).

```
*/3h   backlog            Import + sync + hygiene + health → #pm-engineering
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
├── backlog/                # Import summaries + backlog health reports
├── huddles/                # Meeting notes with real names (53 historical + daily)
└── context/                # Rolling state (overwritten each run)
    ├── velocity.md         # Latest velocity data (from retrospective)
    └── backlog-health.md   # Latest backlog snapshot (from backlog crew)
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
| `#pm-engineering` | Backlog | Import results, backlog health |

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
| `GITHUB_TOKEN` | Backlog, daily pulse, vault tools (ghp_ format) |
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

**AI does everything else** — import, sync, dedup, normalize, estimate,
sprint finalization, daily digest, task health analysis, huddle archival,
vault persistence, and carryover management.
