# CareSpace AI PM Crews

Ten AI-driven CrewAI crews that manage project delivery for CareSpace — a healthcare SaaS with 19 engineers across 6 countries.

**The contract:** Team curates Sprint Candidates. AI handles everything else.

---

## Architecture

```
carespace-pm-crews/
├── orchestrator.py               # Parallel runner (--daily, --weekly, --sprint)
├── shared/
│   ├── config/context.py         # Single source of truth: IDs, team, scoring, thresholds
│   ├── tools/                    # ClickUp, GitHub, Slack, Vanta tools (batch pattern)
│   └── guardrails.py             # Task validation functions for all crews
├── crews/                        # 10 AI-driven crews
│   ├── intake_crew/              # GitHub + VantaCrews → Master Backlog + close sync
│   ├── triage_crew/              # Dedup → estimate SP → scan → decide → execute
│   ├── sprint_crew/              # Sprint Candidates → Sprint (team-curated)
│   ├── daily_pulse_crew/         # Sprint Digest → #pm-standup
│   ├── pr_radar_crew/            # Stale PRs + CI failures
│   ├── compliance_crew/          # Vanta API health + compliance monitoring
│   ├── retrospective_crew/       # Sprint close, carryovers, velocity
│   ├── deal_intel_crew/          # GTM pipeline health
│   ├── customer_success_crew/    # Onboarding SLA + churn detection
│   └── exec_report_crew/         # Weekly executive dashboard
├── .claude/skills/
│   ├── backlog/                  # /backlog — create GitHub issues
│   └── sprint-plan/              # /sprint-plan — interactive sprint planning
└── .env.example
```

### Design Principles

- **AI suggests, team decides** — crews never override human sprint selections
- **GitHub is source of truth** — ClickUp tasks sync status from GitHub issues
- **Backlog stays unassigned** — assignees are set during sprint planning only
- **Single pipeline** — all work enters via GitHub → intake crew → ClickUp backlog
- **Sprint Candidates** — staging area where team curates what goes into the sprint
- **No noise** — SLA/alerts only for sprint items, not backlog
- **One channel per crew** — no cross-posting or spam
- **Tags for visibility** — domain (frontend, backend), type (bug, feature), source (github, vanta)
- **Batch tools** — Python handles API calls/pagination, AI handles analysis/decisions
- **Task "move" = copy + delete** — ClickUp API has no move endpoint

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

💰 GTM & Revenue (901313687157)
├── 🎯 Pipeline
│   ├── Active Deals (901326439255)
│   └── At-Risk Deals (901326439258)
├── 📣 Marketing
│   ├── Content & Campaigns (901326439261)
│   └── Product Launches (901326439262)
└── 🧑‍💼 Customer Success
    ├── Onboarding & Accounts (901326439266)
    └── Support Escalations (901326439271)
```

**ClickUp statuses:** TO DO → IN PROGRESS → BLOCKED → COMPLETE

---

## Data Flow

```
/backlog skill ──→ GitHub Issue ──→ Intake Crew ──→ MASTER BACKLOG
                                                        │
                                                   Triage Crew (every 6h)
                                                   • Dedup → Unassign → SP → Alerts
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

### 1. `intake_crew` — GitHub → ClickUp Pipeline
**Schedule:** Daily 07:00 PDT (cron: `0 14 * * *`)

Two-step workflow:
1. **Import** — scans 59 GitHub repos + VantaCrews compliance repo. Cached dedup loads full backlog once, checks in memory. Creates tasks in "to do" status, unassigned.
2. **Sync** — two-way GitHub↔ClickUp status sync. GitHub is source of truth: closed issues → complete tasks, open issues → reopened tasks.

**Posts to:** `#pm-engineering` (only when changes made) | **Guardrail:** None

---

### 2. `triage_crew` — Backlog Quality Enforcement
**Schedule:** Every 6 hours (cron: `0 */6 * * *`)

1. `dedup_backlog_cleanup` — remove duplicate tasks
2. `bulk_estimate_sp` — estimate SP on tasks without points + remove any assignees (backlog must stay unassigned)
3. `scan_backlog_for_triage` — health report
4. `execute_triage_actions` — priority adjustments, grouped alerts
5. Aging backlog detection (>21 days old)

**No assignments.** Backlog items stay unassigned — assignees are set during sprint planning.

**SLA alerts only for sprint items**, not backlog. Max 3 compliance/sprint.

**Posts to:** `#pm-engineering` | **Memory:** Yes | **Guardrail:** `validate_triage_actions`

---

### 3. `sprint_crew` — Sprint Planning (Team-Curated)
**Schedule:** Bi-weekly Sunday 18:00 PDT (cron: `0 1 * * 1`)

Sprint crew is an **executor**, not a decision-maker.
1. Check Sprint Candidates list (team-curated staging area)
2. If candidates exist → validate assignments, budget, carryovers
3. `finalize_sprint_from_candidates` → move to sprint
4. If empty → warn team (does NOT auto-plan from backlog)

**Budget:** 48 SP (velocity 60 × 80%) | **Max compliance:** 3/sprint

**Posts to:** `#pm-sprint-board` | **Memory:** Yes | **Guardrail:** `validate_sprint_plan`

---

### 4. `daily_pulse_crew` — Sprint Digest
**Schedule:** Mon–Fri 07:45 PDT (cron: `45 14 * * 1-5`)

Structured digest:
- **Executive Summary** — sprint timing (pre-calculated), progress, status
- **Sprint Status** — Done/In Progress/Blocked/To Do (literal ClickUp status)
- **Needs Attention** — stale PRs, CI failures
- **Sprint Risks** — items at risk of not completing (high SP pending, external deps)
- **Meeting Mode** — STANDUP (risks exist) or OPEN SLOT

Posts **ONLY** to `#pm-standup`. No other channels.

**Memory:** Yes | **Guardrail:** `validate_standup_data`

---

### 5. `pr_radar_crew` — Stale PR & CI Radar
**Schedule:** Daily 10:00 PDT (cron: `0 17 * * *`)

Stale >7d → backlog task. Critical >30d → urgent alert. CI failures → backlog task.
CI repos: carespace-ui, carespace-admin, carespace-api-gateway, carespace-sdk.

**Posts to:** `#pm-engineering` | **Guardrail:** `validate_pr_radar_output`

---

### 6. `compliance_crew` — Compliance Health
**Schedule:** Daily 06:30 PDT (cron: `30 13 * * *`)

Two-agent workflow (prevents duplicate Slack posts):
1. **gather_agent** — calls Vanta API directly (no MCP) + ClickUp compliance task count
2. **post_agent** — posts ONE combined report to Slack

Health indicator based on real Vanta test data:
- **RED** — test pass rate < 70% OR critical unowned tests failing
- **YELLOW** — test pass rate < 90% OR critical tests failing (owned)
- **GREEN** — ≥ 90% passing, no critical failures

Owner: Luis Freitas (sole compliance person).

**Posts to:** `#pm-compliance` | **Guardrail:** `validate_compliance_output`

---

### 7. `retrospective_crew` — Sprint Close & Velocity
**Schedule:** Bi-weekly Friday 16:00 PDT (cron: `0 23 * * 5`)

Closes sprint: completed → archived, incomplete → backlog with "carryover" tag + priority bump.
Calculates velocity, per-engineer breakdown, recommends next sprint capacity.

**Posts to:** `#pm-sprint-board` | **Memory:** Yes | **Guardrail:** `validate_retro_metrics`

---

### 8. `deal_intel_crew` — GTM Pipeline
**Schedule:** Monday 07:00 PDT (cron: `0 14 * * 1`)

Monitors Active Deals across 9 verticals. Flags at-risk (>7d no update), coverage gaps.

**Posts to:** `#pm-gtm` | **Guardrail:** `validate_deal_intel`

---

### 9. `customer_success_crew` — Onboarding & Churn
**Schedule:** Daily 08:30 PDT (cron: `30 15 * * *`)

Onboarding SLA (30d), churn signals (>14d no login, >3 open tickets), support escalations.
Only posts when issues found — no empty reports.

**Posts to:** `#pm-customer-success` | **Guardrail:** `validate_cs_output`

---

### 10. `exec_report_crew` — Executive Dashboard
**Schedule:** Friday 17:00 PDT (cron: `0 0 * * 6`)

5-dimension health dashboard: Engineering, GTM, Compliance, Customer Success, Bug Health.
Traffic light format with risks and wins.

**Posts to:** `#pm-exec-updates` | **Memory:** Yes | **Guardrail:** `validate_exec_report`

---

## Daily Schedule (Oregon/PDT)

```
06:30  compliance_crew       Vanta health → #pm-compliance
07:00  intake_crew           GitHub import + sync → #pm-engineering
07:45  daily_pulse_crew      Sprint Digest → #pm-standup
08:30  customer_success_crew Onboarding + churn → #pm-customer-success
10:00  pr_radar_crew         Stale PRs + CI → #pm-engineering
*/6h   triage_crew           Dedup + unassign + estimate + triage → #pm-engineering

Mon    deal_intel_crew       Pipeline → #pm-gtm
Fri    exec_report_crew      Weekly dashboard → #pm-exec-updates
Fri    retrospective_crew    Sprint retro → #pm-sprint-board (bi-weekly)
Sun    sprint_crew           Finalize sprint → #pm-sprint-board (bi-weekly)
```

---

## Interactive Skills

### `/backlog` — Create Issues
Creates GitHub issues that the intake crew imports to ClickUp automatically.

```
User: /backlog camera freezes on iOS during ROM scan
  → GitHub issue in carespace-ai/carespace-mobile-ios
  → Intake crew (next run) creates ClickUp task with naming, tags, SP
```

### `/sprint-plan` — Interactive Sprint Planning
Guided session to curate Sprint Candidates before sprint starts.

```
User: /sprint-plan
  → Shows backlog options + current candidates
  → User adds/removes tasks, sets assignees, adjusts SP
  → Validates budget, carryovers, team load
  → Finalizes on confirmation
```

---

## Slack Channels

| Channel | Crew(s) | Content |
|---------|---------|---------|
| `#pm-standup` | Daily Pulse | Sprint Digest (Mon-Fri) |
| `#pm-sprint-board` | Sprint, Retrospective | Sprint plan, retro summary |
| `#pm-engineering` | Intake, Triage, PR Radar | New tasks, sync, triage, stale PRs |
| `#pm-alerts` | (auto from tools) | Critical alerts only |
| `#pm-gtm` | Deal Intel | Pipeline report (weekly) |
| `#pm-exec-updates` | Exec Report | Executive summary (weekly) |
| `#pm-compliance` | Compliance | Vanta health (daily) |
| `#pm-customer-success` | Customer Success | Onboarding/support issues |

**Rule:** Each crew posts to ONE channel only. No cross-posting.

---

## Setup

### Required Secrets

| Secret | Used by |
|--------|---------|
| `CLICKUP_API_TOKEN` | All crews (pk_ format) |
| `GITHUB_TOKEN` | intake, pr_radar, daily_pulse (ghp_ format) |
| `OPENAI_API_KEY` or `GEMINI_API_KEY` | All crews (LLM — model-agnostic) |
| `SLACK_BOT_TOKEN` | All crews (xoxb_ format) |
| `VANTA_CLIENT_ID` | compliance, exec_report (direct API) |
| `VANTA_CLIENT_SECRET` | compliance, exec_report (direct API) |

### Configuration

All tunable values in `shared/config/context.py`:
- Team roster, domains, capacity
- Sprint budget (48 SP), compliance cap (3)
- Thresholds (stale PR days, SLA hours, aging backlog)
- Slack channels, list IDs, scoring weights

See the **Configuration Manual** in ClickUp for detailed documentation.

---

## Team

| Engineer | Domains | ClickUp ID | Cap SP |
|----------|---------|------------|--------|
| Luis Freitas | compliance (sole owner) | 118004891 | — |
| Flavio Fusuma | ai-cv, sdk, mobile, backend | 48998538 | 20 |
| Andre C Dutra | frontend | 49000180 | 20 |
| Fabiano Fiorentin | backend, infra | 49000181 | 18 |
| Bhavya Saurabh | ai-cv, frontend | 93908266 | 18 |
| Bharath | mobile, sdk | 93908270 | 16 |
| Binu | frontend, backend | 61025897 | 20 |
| + 12 Nexturn team | various | see context.py | 16 each |

---

## Human + AI Contract

**Team does:**
1. Create issues via `/backlog` or GitHub
2. Curate Sprint Candidates (add tasks, set assignees)
3. Review `#pm-standup` daily
4. Move tasks to "done" when complete
5. Run `/sprint-plan` before each sprint

**AI does everything else** — intake, sync, dedup, estimate, triage, sprint finalization, standup, PR monitoring, compliance, reporting, carryovers, and escalation.
