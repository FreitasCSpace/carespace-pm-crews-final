# CareSpace Autonomous PM Crews

Ten AI-driven CrewAI crews that autonomously manage project delivery for CareSpace — a healthcare SaaS with 18 engineers across 6 countries.

**The human contract:** add work to the Master Backlog. AI does the rest.

---

## Architecture

```
carespace-pm-crews/
├── orchestrator.py               # Parallel runner (--daily, --weekly, --sprint, --bootstrap)
├── dedup.py                      # Standalone dedup cleanup tool
├── shared/
│   ├── config/context.py         # Single source of truth: IDs, team, scoring, SP field
│   └── tools/                    # ClickUp, GitHub, Slack tools (batch pattern)
├── crews/                        # 10 AI-driven crews
│   ├── intake_crew/              # GitHub + VantaCrews → Master Backlog
│   ├── triage_crew/              # AI-driven: scan → analyze → decide → execute
│   ├── sprint_crew/              # AI-driven: scan → plan → select → move
│   ├── daily_pulse_crew/         # Sprint Intelligence Digest
│   ├── pr_radar_crew/            # Stale PRs + CI failures
│   ├── compliance_crew/          # Vanta health + compliance monitoring
│   ├── retrospective_crew/       # Sprint metrics + velocity tracking
│   ├── deal_intel_crew/          # GTM pipeline health
│   ├── customer_success_crew/    # Onboarding SLA + churn detection
│   └── exec_report_crew/         # Weekly executive dashboard
├── .env.example
└── .gitignore
```

### Design Principles

- **One backlog** — everything lands in Master Backlog. No scattered lists.
- **Tags for visibility** — domain (frontend, backend), type (bug, feature), source (github, vanta).
- **AI decides, Python executes** — batch tools handle API calls/pagination, AI handles analysis/decisions.
- **Story Points via Custom Field** — free and unlimited (native points capped at 100 on free plan).
- **Task "move" = copy + close** — ClickUp v2 API has no move. Tasks copied to sprint, backlog original closed.
- **Sprint detection** — crews auto-detect active sprint. No manual list IDs needed.
- **Structured Slack** — every channel has a dedicated Block Kit tool. No unformatted text dumps.
- **Alert dedup** — fuzzy matching prevents duplicate alerts across triage runs.

---

## ClickUp Workspace

```
📅 CareSpace.Ai Engine
├── 📋 Backlog
│   └── Master Backlog              ← THE single intake point
├── 📅 Sprints
│   └── Sprint N — auto-created     ← Active sprint detection
├── ⚙️ Operations
│   ├── 🚨 Alerts & Escalations     ← [ALERT] prefixed, tagged, deduped
│   └── 📊 Sprint History & Metrics ← Velocity logs from retrospective
└── 📚 Playbooks
    └── SOPs and procedures

💰 GTM & Revenue
├── 🎯 Pipeline
│   ├── Active Deals
│   └── At-Risk & Stalled
├── 📣 Marketing
│   ├── Content & Campaigns
│   └── Product Launches
└── 🧑‍💼 Customer Success
    ├── Onboarding & Accounts
    └── Support Escalations
```

**Custom Fields:** SP (Number) — space-level, visible in all lists.

---

## Crew Reference

### 1. `intake_crew` — GitHub + Compliance Issue Intake
**Schedule:** Daily 08:00 | **Cron:** `0 8 * * *`

Two batch tools, one Slack post. Scans 59 GitHub repos AND the VantaCrews compliance repo (500+ issues). Dedup checks backlog + sprint + closed tasks.

**Tools:** `batch_import_engineering`, `batch_import_compliance`, `post`
**Posts to:** `#pm-engineering`

---

### 2. `triage_crew` — AI-Driven Quality Enforcement
**Schedule:** Every 6 hours | **Cron:** `0 */6 * * *`

**Pattern: scan → AI analyzes → decide → execute**

1. `dedup_backlog_cleanup` — removes duplicate tasks
2. `bulk_assign_and_estimate` — assigns ALL unassigned + sets SP via custom field
3. `scan_backlog_for_triage` — health report for AI
4. AI decides: priority adjustments, grouped alerts, team balance
5. `execute_triage_actions` — applies decisions with alert dedup

**Compliance:** max 3/sprint, all assigned to Luis Freitas (118004891).
**Posts to:** `#pm-alerts` via `post_triage_summary`

---

### 3. `sprint_crew` — AI-Driven Sprint Planning
**Schedule:** Bi-weekly Sunday 18:00 | **Cron:** `0 18 * * 0`

**Pattern: create/detect sprint → scan → AI plans → execute**

- Detects active sprint (won't create duplicates)
- AI builds balanced sprint: bugs first, features, tasks, compliance (max 3)
- Considers team workload and domain balance
- Moves tasks via copy + close (preserves all metadata)

**Posts to:** `#pm-sprint-board` via `post_sprint_plan`

---

### 4. `daily_pulse_crew` — Sprint Intelligence Digest
**Schedule:** Mon–Fri 08:00 | **Cron:** `0 8 * * 1-5`

Structured digest replacing 90-minute standups:

- **Executive Summary** — CEO reads in 2 min (health %, SP, risks)
- **Sprint Status** — Done, In Progress, Blocked, Pending with assignees + SP
- **Needs Attention** — stale tasks, stale PRs with links, CI failures (only failures)
- **Meeting Mode** — 🔴 Standup (blockers exist) or 🟢 Open Slot (no blockers)

Auto-detects active sprint. **Posts to:** `#pm-standup` via `post_standup`

---

### 5. `pr_radar_crew` — Stale PR & CI Radar
**Schedule:** Daily 10:00 | **Cron:** `0 10 * * *`

Scans GitHub PRs. Stale (>7d) → backlog task. Critical (>30d) → urgent alert with tags. CI failures → backlog task with Actions link. Dedup before creating.

**Posts to:** `#pm-engineering` via `post_pr_radar`

---

### 6. `compliance_crew` — Compliance Health Monitor
**Schedule:** Daily 07:00 | **Cron:** `0 7 * * *`

Pulls Vanta health (MCP tool) + counts ClickUp compliance tasks. Posts ONE combined report — not separate messages.

**Posts to:** `#pm-compliance` via `post_compliance`

---

### 7. `retrospective_crew` — Sprint Metrics & Velocity
**Schedule:** Bi-weekly Friday 16:00 | **Cron:** `0 16 * * 5`

Auto-finds sprint. Calculates completion %, velocity SP, per-engineer breakdown, carry-overs. Logs velocity to Sprint History list for trend tracking.

**Posts to:** `#pm-sprint-board` via `post_retro`

---

### 8. `deal_intel_crew` — GTM Pipeline Health
**Schedule:** Monday 07:00 | **Cron:** `0 7 * * 1`

Monitors Active Deals across 9 verticals. Flags at-risk deals, coverage gaps. Surfaces top opportunities.

**Posts to:** `#pm-gtm` via `post_gtm`

---

### 9. `customer_success_crew` — Onboarding & Churn
**Schedule:** Daily 08:30 | **Cron:** `30 8 * * *`

Monitors onboarding SLA (30-day), churn signals, support escalations. Routes feedback to backlog.

**Posts to:** `#pm-customer-success` via `post_cs_alert`

---

### 10. `exec_report_crew` — Executive Dashboard
**Schedule:** Friday 17:00 | **Cron:** `0 17 * * 5`

5-dimension health dashboard (Engineering, GTM, Compliance, CS, Bugs). Auto-finds sprint. Structured report with traffic lights, risks, and wins.

**Posts to:** `#pm-exec-updates` via `post_exec`

---

## Daily Schedule

```
07:00  compliance_crew       Vanta health → #pm-compliance
08:00  intake_crew           GitHub + VantaCrews → backlog
08:00  daily_pulse_crew      Sprint digest → #pm-standup
08:30  customer_success_crew Onboarding + churn → #pm-customer-success
10:00  pr_radar_crew         Stale PRs + CI → #pm-engineering
*/6h   triage_crew           AI triage → #pm-alerts

Mon    deal_intel_crew       Pipeline → #pm-gtm
Fri    retrospective_crew    Sprint retro → #pm-sprint-board
Fri    exec_report_crew      Weekly dashboard → #pm-exec-updates
Sun    sprint_crew           AI sprint planning → #pm-sprint-board
```

### Data Flow

```
Humans add work ──→ MASTER BACKLOG ←── intake_crew (GitHub + VantaCrews)
                         │
                    triage_crew (every 6h)
                    • Dedup → Bulk assign + SP → AI priorities → Alerts
                         │
                    sprint_crew (bi-weekly)
                    • AI plans → copy to sprint → close backlog original
                         │
                         ▼
                    CURRENT SPRINT ←── daily_pulse_crew (daily digest)
                         │
                         ▼
                       DONE ──→ retrospective_crew (velocity + retro)
                              ──→ exec_report_crew (weekly dashboard)
```

---

## Slack Channels

| Channel | Tool | Crew | Format |
|---------|------|------|--------|
| `#pm-standup` | `post_standup` | daily_pulse | Block Kit: exec summary, status, attention, meeting mode |
| `#pm-sprint-board` | `post_sprint_plan` / `post_retro` | sprint, retrospective | Block Kit: task list, velocity |
| `#pm-engineering` | `post_pr_radar` | pr_radar, intake | Block Kit: stale PRs, CI, actions |
| `#pm-alerts` | `post_triage_summary` / `post_blocker` | triage, daily_pulse, pr_radar | Block Kit: priorities, assignments, alerts, reasoning |
| `#pm-gtm` | `post_gtm` | deal_intel | Block Kit: pipeline, gaps, actions |
| `#pm-exec-updates` | `post_exec` | exec_report | Block Kit: health dashboard, risks, wins |
| `#pm-compliance` | `post_compliance` | compliance | Block Kit: Vanta health, tasks, findings |
| `#pm-customer-success` | `post_cs_alert` | customer_success | Block Kit: account, risk, detail |

All posts use Slack Block Kit — headers, dividers, context footers. No unformatted text.

---

## Setup

### Required Secrets (CrewHub → Settings → Secrets)

| Secret | Used by |
|--------|---------|
| `CLICKUP_API_TOKEN` | All crews (pk_ format) |
| `GITHUB_TOKEN` | intake, sprint, daily_pulse, retro, pr_radar |
| `OPENAI_API_KEY` | All crews (LLM) |
| `SLACK_BOT_TOKEN` | All crews (xoxb_ format) |
| `VANTA_CLIENT_ID` | compliance (via MCP) |
| `VANTA_CLIENT_SECRET` | compliance (via MCP) |

### MCP Servers (CrewHub → Settings → MCP Servers)

**ClickUp:**
```json
{
  "name": "clickup",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic/clickup-mcp-server"],
  "env": { "CLICKUP_API_TOKEN": "<pk_token>" }
}
```

**Vanta:**
```json
{
  "name": "vanta",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@vantasdk/vanta-mcp-server"],
  "env": { "VANTA_API_KEY": "<vanta_key>" }
}
```

### Cron Schedules (CrewHub → Actions)

| Crew | Cron | Description |
|------|------|-------------|
| `ComplianceCrew` | `0 7 * * *` | Daily 07:00 |
| `IntakeCrewCrew` | `0 8 * * *` | Daily 08:00 |
| `DailyPulseCrew` | `0 8 * * 1-5` | Mon–Fri 08:00 |
| `CustomerSuccessCrew` | `30 8 * * *` | Daily 08:30 |
| `PrRadarCrew` | `0 10 * * *` | Daily 10:00 |
| `TriageCrew` | `0 */6 * * *` | Every 6 hours |
| `DealIntelCrew` | `0 7 * * 1` | Monday 07:00 |
| `ExecReportCrew` | `0 17 * * 5` | Friday 17:00 |
| `RetrospectiveCrewCrew` | `0 16 * * 5` | Bi-weekly Friday 16:00 |
| `SprintCrew` | `0 18 * * 0` | Bi-weekly Sunday 18:00 |

### First Run (Cold Start)

```bash
python orchestrator.py --bootstrap
```

Runs sequentially: intake → triage → sprint. Populates backlog from GitHub, assigns everything, creates first sprint.

---

## Key Technical Decisions

| Decision | Why |
|----------|-----|
| **SP via custom field** (not native points) | Native points capped at 100 on free plan. Custom field is free + unlimited. |
| **Task move = copy + close** | ClickUp v2 API has no move endpoint. Tested all approaches — none work. |
| **Batch tools pattern** | LLM can't handle 300+ individual tool calls. Python does bulk work, AI makes decisions. |
| **Alert dedup** | Fuzzy match (3+ common words) prevents duplicate alerts across triage runs. |
| **`[ALERT]` prefix enforced** | Python auto-prefixes if AI forgets. Consistent naming for filtering. |
| **Tags on alerts, no SP** | Alerts are notifications, not work items. Tags enable filtering. |
| **Active sprint detection** | `create_or_get_sprint_list` checks end date — won't create duplicates. |
| **Intake checks closed + sprint** | Dedup loads backlog (incl. closed) + sprint tasks to prevent re-import. |
| **VantaCrews integration** | Compliance issues from FreitasCSpace/CareSpace-Compliance-Repo. Labels mapped to tags. |

---

## Human + AI Contract

**Humans do:**
1. Add items to Master Backlog
2. Set priority tags when needed
3. Review `#pm-alerts` daily
4. Make decisions when AI flags them
5. Move tasks to "done" when complete

**AI does everything else** — intake, triage, sprint planning, standup, PR monitoring, compliance, reporting, and escalation.

---

## Team Configuration

| Engineer | Domains | ClickUp ID |
|----------|---------|------------|
| Luis Freitas | compliance (sole owner) | 118004891 |
| Andre C Dutra | frontend | 49000180 |
| Flavio Fusuma | ai-cv, sdk, mobile, backend | 48998538 |
| fabiano-carespace | backend, infra | 49000181 |
| bhavyasaurabh | ai-cv, frontend | 93908266 |
| YeddulaBharath | mobile, sdk | 93908270 |
| sandeep | backend, infra | 111928715 |
| + 11 Nexturn team | various | see context.py |

**Compliance cap:** max 3 compliance tasks per sprint (Luis handles alone).
