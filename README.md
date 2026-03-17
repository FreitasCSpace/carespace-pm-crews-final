# CareSpace Autonomous PM Crews

Ten CrewAI crews that automate project management for CareSpace — a healthcare SaaS platform with 18 engineers across frontend, backend, mobile, AI/CV, and infra.

**The human contract is simple:** add work to the Master Backlog. AI does the rest — scoring, sprint planning, assignment, standup, triage, compliance, reporting, and escalation.

---

## Architecture

```
carespace-pm-crews/
├── orchestrator.py               # Parallel runner — all 10 crews via asyncio
├── shared/
│   ├── config/context.py         # Single source of truth: ClickUp IDs, team, scoring
│   └── tools/                    # ClickUp, GitHub, Slack, Vanta integrations
├── crews/
│   ├── intake_crew/              # GitHub → Master Backlog
│   ├── sprint_crew/              # Score + plan + assign (merged)
│   ├── daily_pulse_crew/         # Standup + blocker detection (merged)
│   ├── triage_crew/              # SLA + rules + auto-assign (merged)
│   ├── retrospective_crew/       # Sprint metrics + retro doc
│   ├── pr_radar_crew/            # Stale PRs + CI failures
│   ├── compliance_crew/          # Vanta → tagged backlog tasks
│   ├── deal_intel_crew/          # GTM pipeline health
│   ├── customer_success_crew/    # Onboarding SLA + churn risk
│   └── exec_report_crew/         # Exec dashboard + crew health + marketing
├── .env.example
└── .gitignore
```

### Design Principles

- **One backlog** — everything lands in Master Backlog. No scattered lists.
- **Tags, not lists** — domain visibility (frontend, backend, mobile, etc.) via tags and saved Views.
- **2 ClickUp spaces** — CareSpace Engine (product/engineering) + GTM & Revenue (sales/marketing/CS).
- **10 crews, not 15** — redundant crews merged. Sprint planning + assignment = one pass. Standup + blocker detection = one pass.
- **Sprints auto-created** — sprint_crew creates new sprint lists automatically. No pre-provisioning.

---

## ClickUp Workspace Structure

```
📅 CareSpace Engine
├── 📋 Backlog
│   └── Master Backlog              ← THE single intake point
├── 📅 Sprints
│   └── (auto-created by sprint_crew each cycle)
├── ⚙️ Operations
│   ├── 🚨 Alerts & Escalations     ← SLA breaches, blockers, compliance
│   └── 📊 Sprint History & Metrics ← Velocity tracking, crew health
└── 📚 Playbooks
    ├── 📖 Crew Playbooks
    ├── 📋 Sprint Ceremonies
    ├── 🚨 Escalation Procedures
    └── 🔄 Onboarding & Offboarding

💰 GTM & Revenue
├── 🎯 Pipeline
│   ├── Active Deals                ← All verticals, one list
│   └── At-Risk & Stalled           ← AI-flagged deals
├── 📣 Marketing
│   ├── Content & Campaigns
│   └── Product Launches
└── 🧑‍💼 Customer Success
    ├── Onboarding & Accounts
    └── Support Escalations
```

**2 spaces. 7 folders. 11 lists.** Domain visibility via tags + saved Views.

### Tag System

| Category | Tags |
|----------|------|
| **Domain** | `frontend`, `backend`, `mobile`, `sdk`, `ai-cv`, `infra`, `bots`, `video` |
| **Type** | `bug`, `feature`, `tech-debt`, `security`, `compliance`, `pr-review`, `ci-fix`, `task` |
| **Source** | `github`, `vanta`, `client-feedback`, `internal` |
| **Vertical** | `healthcare`, `insurance`, `employers`, `senior-care`, `sports`, `construction`, `manufacturing`, `corrections`, `public-services` |

---

## Crew Reference

### 1. `intake_crew` — GitHub Issue Intake
**Schedule:** Daily 08:00 + webhooks
**Cron:** `0 8 * * *`

Scans all 59 carespace-ai GitHub repos for open issues and PRs not yet in ClickUp. Creates tasks in Master Backlog with domain + type + source tags. Cross-links ClickUp task URL back to GitHub issue.

**Golden rule:** always calls `check_duplicate_task` before creating. Zero duplicates.

**Tools:** `get_issues`, `get_prs`, `get_contributors`, `get_tasks_by_list`, `check_duplicate_task`, `comment_issue`, `post`

---

### 2. `sprint_crew` — Sprint Planning + Assignment
**Schedule:** Bi-weekly Sunday 18:00
**Cron:** `0 18 * * 0` (every other week)

Scores the entire Master Backlog using:
```
score = priority_weight × security_multi × blocker_multi × compliance_multi + age_bonus
```

Fills sprint to 80% of rolling velocity (default 48 SP). Scans GitHub for stale PRs (>7d) and CI failures — adds them as sprint tasks. Auto-estimates missing story points by type.

Then assigns every task in one pass:
1. Match domain tag to engineer domains
2. Check workload — never exceed max_tasks
3. Prefer repo contributors from GitHub history
4. Tie-break: lowest SP in progress
5. Set due dates: 1d (urgent), 2d (high), 5d (normal)

**Tools:** `get_issues`, `get_stale_prs`, `get_ci`, `get_contributors`, `get_tasks_by_list`, `check_duplicate_task`, `auto_estimate_sp`, `post_sprint_plan`, `post`

*Merged from: sprint_planning_crew + assignment_crew*

---

### 3. `daily_pulse_crew` — Standup + Blocker Detection
**Schedule:** Mon–Fri 08:00
**Cron:** `0 8 * * 1-5`

Morning heartbeat. Pulls current sprint, categorises by status (Done/In Progress/Blocked), detects stale tasks (>3d no update), scans for blocker keywords in descriptions, traces dependency chains with business impact.

Severity classification: CRITICAL (<3d to deadline), HIGH (<7d), MEDIUM (<14d), LOW (>14d).

Posts standup to `#standup`. Escalates each blocker individually to `#alerts`. CRITICAL blockers also go to `#engineering`.

**Tools:** `get_stale_prs`, `get_ci`, `get_tasks_by_list`, `post_standup`, `post_blocker`, `post`

*Merged from: standup_crew + blocker_radar_crew*

---

### 4. `triage_crew` — SLA Enforcement + Rules
**Schedule:** Every 6 hours
**Cron:** `0 */6 * * *`

Single-pass scan of Master Backlog + current sprint. Enforces all rules:

| Rule | What it does |
|------|-------------|
| Security reclassification | Tasks tagged `security` → forced to urgent priority |
| SLA enforcement | urgent=4h, high=24h, normal=72h, low=7d — creates alerts on breach |
| Unassigned bug assignment | Tags `bug` with no assignee → assign to domain lead |
| Priority correction | Keywords (crash, data loss, PHI, HIPAA) → escalate to urgent |
| G1: PHI compliance | Done tasks tagged `hipaa`/`phi` → add `compliance-reviewed` tag |
| G3: Story points gate | Sprint tasks without SP → auto-estimate |
| G7: HIPAA watchers | Tasks tagged `hipaa` → auto-add compliance watchers |
| S4: Security priority | Tasks tagged `security` → ensure urgent |
| S6: Stale detection | In Progress >3d → create stale alert |

**Tools:** `get_tasks_by_list`, `check_duplicate_task`, `auto_estimate_sp`, `update_clickup_task`, `add_tag_to_task`, `create_clickup_task`, `post_sla_breach`, `post_blocker`, `post`

*Merged from: bug_triage_crew + clickup_rules_crew*

---

### 5. `retrospective_crew` — Sprint Metrics & Retro
**Schedule:** Bi-weekly Friday 16:00
**Cron:** `0 16 * * 5` (every other week)

Calculates velocity, completion rate, per-engineer breakdown, carry-overs. Writes retro document to ClickUp Docs with health scoring (GREEN ≥80%, YELLOW ≥60%, RED <60%).

Recommends next sprint capacity: `completed_sp × 0.80`.

Logs velocity data to Sprint History list for trend tracking.

**Tools:** `get_stale_prs`, `get_ci`, `get_activity`, `get_tasks_by_list`, `post_retro`, `post`

---

### 6. `pr_radar_crew` — Stale PR & CI Radar
**Schedule:** Daily 10:00
**Cron:** `0 10 * * *`

Scans all GitHub PRs across the org. Stale PRs (>7d) → task in Master Backlog tagged `[domain, pr-review, github]`. Critical stale (>30d) → urgent alert. CI failures on main → task tagged `[domain, ci-fix, github]`. Detects duplicate branches.

**Tools:** `get_prs`, `get_ci`, `get_stale_prs`, `get_contributors`, `get_tasks_by_list`, `post_blocker`, `post`

---

### 7. `compliance_crew` — Vanta Compliance Sweep
**Schedule:** Daily 07:00
**Cron:** `0 7 * * *`

Pulls live Vanta data every morning. For every finding, creates a remediation task in Master Backlog with compliance/security tags. HIPAA and SOC 2 are existential — one finding can lose a $10M deal.

| Source | Tags | SLA |
|--------|------|-----|
| SOC 2 failing controls | `compliance`, `soc2`, `vanta` | 7 days |
| HIPAA failing controls | `compliance`, `hipaa`, `vanta` | 5 days |
| Critical vulnerabilities | `security`, domain, `vanta` | 3 days |
| BAA gaps | `compliance`, `hipaa`, `baa`, `vanta` | 2 days (urgent) |
| Overdue access reviews | `compliance`, `soc2` | Immediate alert |
| People risks (offboarded w/ access) | `security`, `compliance` | Immediate alert |

Writes daily compliance report to ClickUp Docs. Posts critical findings to `#compliance`.

**Tools:** All 10 Vanta getters, `get_tasks_by_list`, `check_duplicate_task`, `post_compliance`, `post`

---

### 8. `deal_intel_crew` — GTM Pipeline Health
**Schedule:** Monday 07:00
**Cron:** `0 7 * * 1`

Analyses the Active Deals list across 9 verticals (via tags). Identifies at-risk deals (stale >7d, no assignee, no next step). Moves them to At-Risk & Stalled. Detects vertical coverage gaps. Surfaces top 3 deals to accelerate. Always tracks Echelon specifically.

**Tools:** `get_tasks_by_list`, `post_gtm`, `post`

---

### 9. `customer_success_crew` — Onboarding & Churn
**Schedule:** Daily 08:30
**Cron:** `30 8 * * *`

Monitors Onboarding & Accounts (30-day SLA) and Support Escalations. Churn signals: no login 14+ days, >3 open tickets, renewal <60 days. Routes client feedback to Master Backlog as `[FEEDBACK]` tasks.

**Tools:** `get_tasks_by_list`, `check_duplicate_task`, `post_cs_alert`, `post`

---

### 10. `exec_report_crew` — Executive Dashboard
**Schedule:** Friday 17:00
**Cron:** `0 17 * * 5`

Weekly 5-minute read for leadership. Synthesises signal across 5 health dimensions (each GREEN/YELLOW/RED):

1. **Engineering** — sprint completion %, velocity trend, stale tasks
2. **GTM** — deals at risk, pipeline value, coverage gaps
3. **Compliance** — Vanta health, failing controls, BAA gaps
4. **Customer Success** — churn risk, onboarding SLA
5. **Bug Health** — open bugs, average age, SLA breaches

Also runs crew health check (absorbed from workspace_health_crew) and marketing monitoring (absorbed from marketing_ops_crew — flags overdue content, auto-creates GTM launch checklists 14d before launches).

Writes report to ClickUp Docs. Posts summary to `#exec-updates`.

**Tools:** `get_health_summary`, `get_tasks_by_list`, `check_duplicate_task`, `create_clickup_task`, `post_exec`, `post`

*Absorbed: workspace_health_crew + marketing_ops_crew*

---

## Parallel Orchestrator

`orchestrator.py` runs crews concurrently via `akickoff()` + `asyncio.gather()`.

```bash
# Run all 10 crews
python orchestrator.py

# Run specific crews
python orchestrator.py --crews intake,triage,daily_pulse

# Run by schedule group
python orchestrator.py --daily     # compliance, intake, daily_pulse, customer_success, pr_radar, triage
python orchestrator.py --weekly    # deal_intel, exec_report
python orchestrator.py --sprint    # sprint, retrospective
```

Reports wall-clock time vs sequential equivalent with speedup factor.

---

## How It All Runs Together

```
07:00  compliance_crew       Vanta → tagged tasks in backlog
08:00  intake_crew           GitHub → tagged tasks in backlog
08:00  daily_pulse_crew      Standup + blocker detection → #standup, #alerts
08:30  customer_success_crew Onboarding + churn → #customer-success
10:00  pr_radar_crew         Stale PRs + CI → tasks in backlog
*/6h   triage_crew           SLA + rules + auto-assign (runs 00:00, 06:00, 12:00, 18:00)

Mon    deal_intel_crew       Pipeline health → #gtm
Fri    exec_report_crew      Exec dashboard → #exec-updates
Fri    retrospective_crew    Sprint retro → ClickUp Docs (bi-weekly)
Sun    sprint_crew           Plan + assign next sprint (bi-weekly)
```

### Data Flow

```
Humans add work ──→ MASTER BACKLOG ←── intake_crew (GitHub)
                         │              ←── compliance_crew (Vanta)
                         │              ←── pr_radar_crew (stale PRs, CI)
                         │              ←── customer_success_crew (feedback)
                         │
                    triage_crew (every 6h)
                    • SLA enforcement
                    • Auto-priority security
                    • Auto-assign unassigned bugs
                         │
                    sprint_crew (bi-weekly)
                    • Score all backlog items
                    • Fill sprint to 80% velocity
                    • Assign by domain + workload
                         │
                         ▼
                    CURRENT SPRINT ←── daily_pulse_crew (daily standup + blockers)
                         │
                         ▼
                       DONE ──→ retrospective_crew (velocity, retro doc)
                              ──→ exec_report_crew (weekly dashboard)
```

---

## Slack Channels

| Channel | Crews posting | Content |
|---------|--------------|---------|
| `#standup` | daily_pulse | Daily standup (Done/In Progress/Blocked) |
| `#sprint-board` | sprint, retrospective | Sprint plan, retro summary |
| `#engineering` | intake, pr_radar, exec_report | New tasks, CI failures, crew health |
| `#alerts` | daily_pulse, triage, compliance | SLA breaches, blockers, security |
| `#gtm` | deal_intel | Pipeline health report |
| `#exec-updates` | exec_report | Weekly executive dashboard |
| `#compliance` | compliance | Critical compliance findings |
| `#customer-success` | customer_success | Churn risk, support escalations |

---

## Setup

### 1. Environment Variables

```bash
cp .env.example .env
# Fill in your API tokens
```

### 2. Required Secrets

| Token | Used by | Get it from |
|-------|---------|-------------|
| `CLICKUP_API_TOKEN` | All crews | ClickUp Settings → Apps → API Token |
| `GITHUB_TOKEN` | intake, sprint, daily_pulse, retro, pr_radar | GitHub Settings → Developer settings → PAT |
| `OPENAI_API_KEY` | All crews (LLM) | platform.openai.com → API Keys |
| `SLACK_BOT_TOKEN` | All crews | api.slack.com → Your App → OAuth |
| `VANTA_CLIENT_ID` | compliance, exec_report | app.vanta.com → Settings → API |
| `VANTA_CLIENT_SECRET` | compliance, exec_report | app.vanta.com → Settings → API |

### 3. Running Standalone

```bash
# Run all crews
python orchestrator.py

# Run a single crew
cd crews/intake_crew/src && python -m intake_crew.main

# Run daily schedule
python orchestrator.py --daily
```

### 4. Running in CrewHub

1. Add repo via CrewHub UI → Repositories → Add
2. Set secrets in Settings → Secrets
3. Configure ClickUp MCP Server in Settings → MCP Servers:

```json
{
  "name": "clickup",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@anthropic/clickup-mcp-server"],
  "env": {
    "CLICKUP_API_TOKEN": "<your-token>"
  }
}
```

4. Set schedules:

| Crew | Cron | Description |
|------|------|-------------|
| `compliance` | `0 7 * * *` | Daily 07:00 |
| `intake` | `0 8 * * *` | Daily 08:00 |
| `daily_pulse` | `0 8 * * 1-5` | Mon–Fri 08:00 |
| `customer_success` | `30 8 * * *` | Daily 08:30 |
| `pr_radar` | `0 10 * * *` | Daily 10:00 |
| `triage` | `0 */6 * * *` | Every 6 hours |
| `deal_intel` | `0 7 * * 1` | Monday 07:00 |
| `exec_report` | `0 17 * * 5` | Friday 17:00 |
| `retrospective` | `0 16 * * 5` | Bi-weekly Friday 16:00 |
| `sprint` | `0 18 * * 0` | Bi-weekly Sunday 18:00 |

---

## Human + AI Contract

**Humans do:**
1. Add items to Master Backlog
2. Set priority tags (urgent/blocker) when needed
3. Review Alerts & Escalations daily
4. Make binary decisions when AI flags them

**AI does everything else** — sprint planning, task assignment, standups, bug triage, SLA enforcement, PR monitoring, compliance scanning, executive reporting, and blocker detection.

---

## Team Configuration

18 engineers configured in `shared/config/context.py`:

| Engineer | Domains | Max Tasks | SP Cap |
|----------|---------|-----------|--------|
| fusuma | ai-cv, sdk, mobile, backend | 4 | 20 |
| andreCarespace | frontend | 4 | 20 |
| binunexturn | frontend, backend | 4 | 20 |
| fabiano-carespace | backend, infra | 3 | 18 |
| bhavyasaurabh | ai-cv, frontend | 3 | 18 |
| BMarcano | frontend | 3 | 18 |
| YeddulaBharath | mobile, sdk | 3 | 16 |
| R-Kapil-Kumar | mobile, sdk | 3 | 16 |
| Deekshakain | frontend | 3 | 16 |
| + 9 Nexturn extended team | various | 3 | 16 |

Domain leads (auto-assignment fallback):
- **frontend:** andreCarespace
- **backend:** fabiano-carespace
- **mobile:** YeddulaBharath
- **ai-cv / security:** bhavyasaurabh
- **infra:** sandeep

---

## Sprint Scoring Algorithm

```
score = priority_weight × security_multi × blocker_multi × compliance_multi + age_bonus
```

| Factor | Values |
|--------|--------|
| Priority weight | urgent=100, high=70, normal=40, low=10 |
| Security multiplier | ×2.0 |
| Blocker multiplier | ×1.8 |
| Compliance multiplier | ×1.5 |
| Client multiplier | ×1.3 |
| Age bonus | +0.5 per week since creation |
| Velocity buffer | 80% (fill sprints to 80% of capacity) |

Story point estimates (auto):
| Type | SP |
|------|----|
| Security | 8 |
| Bug (low/medium/high) | 2 / 5 / 8 |
| Feature (small/medium/large) | 5 / 13 / 21 |
| PR review | 2 |
| CI fix | 3 |

---

## Bug SLA Thresholds

| Priority | Resolution SLA | Escalation |
|----------|---------------|------------|
| Urgent | 4 hours | Immediate alert to #alerts |
| High | 24 hours | Alert after breach |
| Normal | 72 hours | Alert after breach |
| Low | 7 days | Alert after breach |
