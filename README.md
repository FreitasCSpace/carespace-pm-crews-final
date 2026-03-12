# CareSpace Autonomous PM Crews

13 CrewAI crews for fully autonomous CareSpace project management, designed to run on [CrewHub](https://github.com/your-org/crewhub).

## Architecture

```
carespace-pm-crews/
├── shared/                     # Shared tools & configuration
│   ├── config/context.py       # ClickUp workspace IDs, routing, team config
│   └── tools/                  # ClickUp, GitHub, Slack, Vanta integrations
├── crews/                      # 13 independent CrewHub-compatible crews
│   ├── intake_crew/            # GitHub issue intake -> ClickUp routing
│   ├── sprint_planning_crew/   # Automated sprint planning & list creation
│   ├── assignment_crew/        # Task assignment by domain + workload
│   ├── standup_crew/           # Daily standup generation & posting
│   ├── retrospective_crew/     # Sprint retro with velocity analysis
│   ├── bug_triage_crew/        # Bug SLA enforcement & triage
│   ├── pr_radar_crew/          # Stale PR & CI failure detection
│   ├── deal_intel_crew/        # GTM pipeline intelligence
│   ├── customer_success_crew/  # CS health monitoring & churn detection
│   ├── marketing_ops_crew/     # Content calendar & launch checklist automation
│   ├── compliance_crew/        # SOC2/HIPAA monitoring via Vanta
│   ├── exec_report_crew/       # Weekly executive health dashboard
│   └── blocker_radar_crew/     # Cross-workspace dependency detection
└── .env.example
```

## Crews

| # | Crew | Schedule | What it does |
|---|------|----------|-------------|
| 1 | **intake** | Daily 08:00 + webhook | GitHub issues -> ClickUp tasks, routed by domain |
| 2 | **sprint_planning** | Bi-weekly Sunday 18:00 | Score backlog, create sprint list, fill to 80% velocity |
| 3 | **assignment** | After planning + on-demand | Assign tasks by domain match + workload + repo history |
| 4 | **standup** | Mon-Fri 09:00 | Post standup, flag stale tasks, escalate blockers |
| 5 | **retrospective** | Bi-weekly Friday 16:00 | Velocity analysis, retro doc, next sprint capacity |
| 6 | **bug_triage** | Every 6 hours | SLA enforcement (4h/24h/72h/7d), security reclassification |
| 7 | **pr_radar** | Daily 10:00 | Stale PRs, CI failures, duplicate branches |
| 8 | **deal_intel** | Monday 07:00 | Sales pipeline health across 9 verticals |
| 9 | **customer_success** | Daily 08:30 | Onboarding SLA, churn risk, support escalation |
| 10 | **marketing_ops** | Mon + Wed 09:00 | Content calendar, launch GTM checklists |
| 11 | **compliance** | Daily 07:00 | Vanta -> ClickUp: SOC2, HIPAA, vulns, BAA gaps |
| 12 | **exec_report** | Friday 17:00 | 5-dimension health dashboard to ClickUp Docs + Slack |
| 13 | **blocker_radar** | Daily 09:05 | Dependency chains with business impact analysis |

## Setup

1. Copy `.env.example` to `.env` and fill in your API tokens
2. Connect this repo to CrewHub (Settings > Repositories > Add)
3. CrewHub auto-detects all 13 crews from `pyproject.toml` files
4. Configure schedules in CrewHub or use chain triggers

## Required API Tokens

| Token | Used by | Get it from |
|-------|---------|-------------|
| `CLICKUP_API_TOKEN` | All crews | ClickUp Settings > Apps > API Token |
| `GITHUB_TOKEN` | intake, planning, standup, retro, pr_radar, assignment | GitHub Settings > Developer settings > PAT |
| `OPENAI_API_KEY` | All crews (LLM) | platform.openai.com > API Keys |
| `SLACK_BOT_TOKEN` | standup, planning, retro, bug_triage, pr_radar, deal_intel, exec_report, compliance | api.slack.com > Your App > OAuth |
| `VANTA_CLIENT_ID` | compliance, exec_report | app.vanta.com > Settings > API |
| `VANTA_CLIENT_SECRET` | compliance, exec_report | app.vanta.com > Settings > API |

## Human + AI Contract

**Humans do:**
1. Add items to Master Backlog (ClickUp)
2. Set priorities (urgent/blocker tags)
3. Review the Alerts & SLA Watchlist daily
4. Make binary decisions when AI flags them

**AI does everything else** -- sprint planning, task assignment, standups, bug triage, PR monitoring, compliance scanning, executive reporting, and blocker detection.
