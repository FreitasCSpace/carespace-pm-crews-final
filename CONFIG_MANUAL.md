# CareSpace PM Crews — Configuration Manual

How to customize every aspect of the autonomous PM system.
Most settings live in one file: `shared/config/context.py`.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Team & People](#team--people)
3. [Sprint Planning](#sprint-planning)
4. [Task Scoring & Prioritization](#task-scoring--prioritization)
5. [SLA Thresholds](#sla-thresholds)
6. [GitHub Repos & Domain Routing](#github-repos--domain-routing)
7. [Tags & Classification](#tags--classification)
8. [ClickUp Structure (Spaces, Folders, Lists)](#clickup-structure)
9. [Slack Channels](#slack-channels)
10. [Crew Schedules](#crew-schedules)
11. [Compliance Settings](#compliance-settings)
12. [Vulnerability SLA](#vulnerability-sla)
13. [GitHub Batch Import](#github-batch-import)
14. [Stale PR & CI Thresholds](#stale-pr--ci-thresholds)
15. [Environment Variables](#environment-variables)
16. [LLM / Model Configuration](#llm--model-configuration)
17. [Crew Agent Tuning](#crew-agent-tuning)

---

## Quick Reference

| What you want to change | Where |
|--------------------------|-------|
| Add/remove team members | `shared/config/context.py` → `TEAM` |
| Change domain leads | `shared/config/context.py` → `DOMAIN_LEADS` |
| Tune sprint capacity | `shared/config/context.py` → `SCORE` |
| Adjust story point estimates | `shared/config/context.py` → `SP_ESTIMATE` |
| Change bug SLA windows | `shared/config/context.py` → `BUG_SLA` |
| Add a new GitHub repo | `shared/config/context.py` → `REPO_DOMAIN` |
| Change Slack channels | `shared/config/context.py` → `SLACK` |
| Change crew schedules | `orchestrator.py` → `PM_CREWS` |
| Change the LLM model | `.env` → `OPENAI_MODEL_NAME` |
| Tune how a crew reasons | `crews/<name>/src/<name>/config/agents.yaml` |
| Tune what a crew does | `crews/<name>/src/<name>/config/tasks.yaml` |

---

## Team & People

**File:** `shared/config/context.py` lines 176-197

### Team Members (`TEAM`)

Each engineer has four properties:

```python
TEAM = {
    "github_username": {
        "domains": ["frontend", "backend"],  # What they work on
        "cap_sp":  20,                        # Story points per sprint
        "max_tasks": 4,                       # Max concurrent tasks
        "cu_id":   "49000180",               # ClickUp user ID
    },
}
```

**To add someone:**
1. Get their ClickUp user ID (Profile > API > User ID)
2. Add entry to `TEAM` with their GitHub username as key
3. List their domain expertise in `domains`
4. Set `cap_sp` (typical: 16-20) and `max_tasks` (typical: 3-4)

**To remove someone:**
Delete their entry from `TEAM`. Triage crew will stop assigning them work.

**What uses this:** `triage_crew` (auto-assignment), `sprint_crew` (capacity planning)

### Domain Leads (`DOMAIN_LEADS`)

**File:** `shared/config/context.py` lines 200-214

Fallback assignees when no specific match is found:

```python
DOMAIN_LEADS = {
    "frontend":   "49000180",   # andreCarespace
    "backend":    "49000181",   # fabiano-carespace
    "mobile":     "93908270",   # YeddulaBharath
    "compliance": "118004891",  # luis freitas
    # ...
}
```

Change the ClickUp user ID to reassign domain leadership.

---

## Sprint Planning

**File:** `shared/config/context.py` lines 224-250

### Sprint Folder

```python
SPRINT_FOLDER_ID = FOLDERS["sprints"]  # 901317811717
```

Where `sprint_crew` creates new sprint lists. Change only if you move the Sprints folder in ClickUp.

### Story Points Custom Field

```python
SP_CUSTOM_FIELD_ID = "1662e3e7-b018-47b7-8881-e30f6831c674"
```

The ClickUp custom field used for story points. This is a Number field (no 100-point cap). If you recreate the field, update this ID.

### Compliance Cap

```python
MAX_COMPLIANCE_PER_SPRINT = 3
```

**Line 219.** Limits how many compliance tasks go into one sprint. Luis is the sole compliance owner — this prevents his sprint from being 100% compliance.

Increase if you add more compliance-capable team members.

---

## Task Scoring & Prioritization

**File:** `shared/config/context.py` lines 229-250

### Scoring Algorithm (`SCORE`)

Controls how `triage_crew` and `sprint_crew` rank backlog tasks:

```python
SCORE = {
    "priority_weight":  {"urgent": 100, "high": 70, "normal": 40, "low": 10},
    "security_multi":   2.0,     # Security tasks scored 2x
    "blocker_multi":    1.8,     # Blockers scored 1.8x
    "compliance_multi": 1.5,     # Compliance scored 1.5x
    "client_multi":     1.3,     # Client-reported scored 1.3x
    "age_per_week":     0.5,     # +0.5 score per week old
    "velocity_buffer":  0.80,    # Sprint budget = 80% of team velocity
    "default_velocity": 60,      # Default velocity if no sprint history (SP)
}
```

**Common tweaks:**
- Raise `security_multi` to prioritize security work higher
- Lower `velocity_buffer` (e.g. 0.70) for more conservative sprints
- Raise `default_velocity` if team delivers more than 60 SP/sprint
- Adjust `priority_weight` to change how much priority affects ranking

### Auto Story Point Estimates (`SP_ESTIMATE`)

When a task has no SP set, `triage_crew` estimates based on type:

```python
SP_ESTIMATE = {
    "security":        8,
    "bug_low":         2,
    "bug_medium":      5,
    "bug_high":        8,
    "feature_small":   5,
    "feature_medium":  13,
    "feature_large":   21,
    "pr_review":       2,
    "ci_fix":          3,
}
```

Adjust based on your team's actual velocity. If features take longer than expected, increase the feature estimates.

---

## SLA Thresholds

### Bug SLA (`BUG_SLA`)

**File:** `shared/config/context.py` line 255

Hours before a bug escalates to #pm-alerts:

```python
BUG_SLA = {"urgent": 4, "high": 24, "normal": 72, "low": 168}
```

- `urgent`: 4 hours (half a workday)
- `high`: 24 hours (1 day)
- `normal`: 72 hours (3 days)
- `low`: 168 hours (7 days)

`triage_crew` flags tasks at 80% of SLA (e.g., urgent bugs at 3.2h). Tighten these if you want faster response.

---

## GitHub Repos & Domain Routing

**File:** `shared/config/context.py` lines 93-124

### Repo-to-Domain Map (`REPO_DOMAIN`)

When `intake_crew` imports a GitHub issue, it tags it based on which repo it came from:

```python
REPO_DOMAIN = {
    "carespace-ui":          "frontend",
    "carespace-admin":       "backend",
    "carespace-mobile-ios":  "mobile",
    "carespace-sdk":         "sdk",
    "PoseEstimator":         "ai-cv",
    "carespace-docker":      "infra",
    # ... 25+ repos
}
```

**To add a new repo:**
1. Add `"repo-name": "domain"` to `REPO_DOMAIN`
2. Make sure the domain exists in `DOMAIN_TAGS`
3. Next `intake_crew` run will auto-tag issues from that repo

**Repos not in this map are still imported** — they just won't get an automatic domain tag.

### Keyword Fallback (`DOMAIN_KEYWORDS`)

**Lines 162-171.** When repo mapping isn't available, `triage_crew` matches keywords in the task title/description:

```python
DOMAIN_KEYWORDS = {
    "frontend": ["ui", "react", "css", "storybook", "nextjs", ...],
    "backend":  ["api", "endpoint", "gateway", "strapi", "auth", ...],
    "mobile":   ["android", "ios", "flutter", "swift", ...],
    # ...
}
```

Add keywords to improve auto-classification accuracy.

### GitHub Organization

**File:** `shared/tools/github.py` line 20

```python
ORG = "carespace-ai"
```

Also in `shared/config/context.py` line 10:
```python
GITHUB_ORG = "carespace-ai"
```

Change both if your GitHub org name changes.

---

## Tags & Classification

**File:** `shared/config/context.py` lines 69-87

Four tag categories that crews apply to tasks:

### Domain Tags
```python
DOMAIN_TAGS = ["frontend", "backend", "mobile", "sdk", "ai-cv", "infra", "bots", "video"]
```
Used by: intake, triage, pr_radar. Drives auto-assignment and filtering.

### Type Tags
```python
TYPE_TAGS = ["bug", "feature", "tech-debt", "security", "compliance", "pr-review", "ci-fix", "task"]
```
Used by: intake, triage. Drives SLA rules and scoring.

### Source Tags
```python
SOURCE_TAGS = ["github", "vanta", "client-feedback", "internal"]
```
Tracks where work originated.

### Vertical Tags (GTM)
```python
VERTICAL_TAGS = ["healthcare", "insurance", "employers", "senior-care", "sports",
                 "construction", "manufacturing", "corrections", "public-services"]
```
Used by: `deal_intel_crew` for pipeline segmentation.

**To add a new tag:** Add to the relevant list. Crews will start using it automatically.

---

## ClickUp Structure

**File:** `shared/config/context.py` lines 15-62

### Spaces (line 15)
```python
SPACES = {
    "engine": "901313687155",   # Product, engineering, ops
    "gtm":    "901313687157",   # Sales, marketing, customer success
}
```

### Folders (line 23)
```python
FOLDERS = {
    "backlog":           "901317811713",
    "sprints":           "901317811717",
    "operations":        "901317811718",
    "playbooks":         "901317811721",
    "pipeline":          "901317811738",
    "marketing":         "901317811726",
    "customer_success":  "901317811730",
}
```

### Lists (line 38)
```python
L = {
    "master_backlog":       "901326439232",   # Single intake point
    "alerts":               "901326439234",   # Alerts & Escalations
    "sprint_history":       "901326439238",   # Sprint History & Metrics
    "active_deals":         "901326439255",   # Active Deals
    "at_risk_deals":        "901326439258",   # At-Risk Deals
    "content_campaigns":    "901326439261",   # Content & Campaigns
    "product_launches":     "901326439262",   # Product Launches
    "onboarding_accounts":  "901326439266",   # Onboarding & Accounts
    "support_escalations":  "901326439271",   # Support Escalations
}
```

**Warning:** These IDs are hardcoded. If you delete/recreate lists in ClickUp, update the IDs here. Multiple crews reference the same lists — missing IDs will break task creation.

---

## Slack Channels

**File:** `shared/config/context.py` lines 260-269

```python
SLACK = {
    "standup":     "#pm-standup",          # daily_pulse posts here
    "sprint":      "#pm-sprint-board",     # sprint, retrospective post here
    "engineering": "#pm-engineering",      # intake, pr_radar post here
    "alerts":      "#pm-alerts",           # triage, pr_radar, customer_success post alerts
    "gtm":         "#pm-gtm",             # deal_intel posts here
    "exec":        "#pm-exec-updates",    # exec_report posts here
    "compliance":  "#pm-compliance",      # compliance posts here
    "cs":          "#pm-customer-success", # customer_success posts here
}
```

To redirect a crew's output: change the channel name. Make sure the Slack bot is invited to the new channel.

---

## Crew Schedules

**File:** `orchestrator.py` lines 28-115

Each crew has a `cron` field (5-field cron, UTC time):

| Crew | Cron (UTC) | Local (PDT) | Frequency |
|------|-----------|-------------|-----------|
| compliance | `0 7 * * *` | 00:00 | Daily |
| intake | `0 8 * * *` | 01:00 | Daily |
| daily_pulse | `0 8 * * 1-5` | 01:00 | Mon-Fri |
| customer_success | `30 8 * * *` | 01:30 | Daily |
| pr_radar | `0 10 * * *` | 03:00 | Daily |
| triage | `0 */6 * * *` | Every 6h | 4x/day |
| deal_intel | `0 7 * * 1` | Mon 00:00 | Weekly |
| sprint | `0 18 * * 0` | Sun 11:00 | Biweekly |
| retrospective | `0 16 * * 5` | Fri 09:00 | Biweekly |
| exec_report | `0 17 * * 5` | Fri 10:00 | Weekly |

**Note:** The crons in `orchestrator.py` are used for local `--daily`/`--weekly` runs. Actual production scheduling is done via CrewHub. The reference schedule in `context.py` (lines 274-287) shows the production cron values.

### Schedule Groups (line 118)

```python
SCHEDULE_GROUPS = {
    "daily":  ["compliance", "intake", "daily_pulse", "customer_success", "pr_radar", "triage"],
    "weekly": ["deal_intel", "exec_report"],
    "sprint": ["sprint", "retrospective"],
}
```

To add a crew to a group, add its key to the list.

---

## Compliance Settings

**File:** `shared/config/context.py` lines 130-160

### Compliance Repo

```python
COMPLIANCE_REPO = "FreitasCSpace/CareSpace-Compliance-Repo"
```

Where Vanta-generated compliance issues live. `compliance_crew` reads from here.

### Label-to-Priority/Tag Map

```python
COMPLIANCE_LABEL_MAP = {
    "P0-critical": {"priority": "urgent"},
    "P1-high":     {"priority": "high"},
    "P2-medium":   {"priority": "normal"},
    "P3-low":      {"priority": "low"},
    "HIPAA":       {"tag": "hipaa"},
    "soc2":        {"tag": "soc2"},
    # ...
}
```

Maps GitHub labels from the compliance repo to ClickUp priorities and tags. Add new labels here when Vanta creates new issue types.

---

## Vulnerability SLA

**File:** `shared/tools/vanta.py` line 212

```python
SLA = {"critical": 7, "high": 30, "medium": 90, "low": 180}
```

Days before a vulnerability breaches SLA:
- Critical: 7 days
- High: 30 days
- Medium: 90 days
- Low: 180 days

Used by `compliance_crew` and `exec_report_crew` for health scoring.

---

## GitHub Batch Import

**File:** `shared/tools/github.py` lines 20-21

```python
ORG = "carespace-ai"
BATCH_SIZE = 25
```

- `BATCH_SIZE`: How many GitHub issues `intake_crew` processes per batch. Lower = lighter on GitHub API rate limits. Higher = faster imports.

---

## Stale PR & CI Thresholds

These are defined in the crew YAML configs, not in `context.py`:

| Threshold | Value | File | Crew |
|-----------|-------|------|------|
| Stale PR | >7 days | `pr_radar_crew/config/tasks.yaml` | pr_radar |
| Critical stale PR | >30 days | `pr_radar_crew/config/tasks.yaml` | pr_radar |
| Stale task (no update) | >3 days | `daily_pulse_crew/config/tasks.yaml` | daily_pulse |
| Stale PR (standup) | >7 days | `daily_pulse_crew/config/tasks.yaml` | daily_pulse |
| Unresolved alert | >24 hours | `daily_pulse_crew/config/tasks.yaml` | daily_pulse |

To change these: edit the number in the task description. The LLM reads these as instructions, not code — just change "7 days" to "5 days" etc.

---

## Environment Variables

**File:** `.env` (create from `.env.example`)

| Variable | Required | Used by | Notes |
|----------|----------|---------|-------|
| `CLICKUP_API_TOKEN` | Yes | All crews | `pk_...` format |
| `GITHUB_TOKEN` | Yes | intake, pr_radar, daily_pulse | `ghp_...` format, needs repo scope |
| `OPENAI_API_KEY` | Yes | All crews | LLM provider API key |
| `SLACK_BOT_TOKEN` | Yes | All crews | `xoxb-...` format, needs chat:write scope |
| `VANTA_CLIENT_ID` | For compliance | compliance, exec_report | Vanta API client |
| `VANTA_CLIENT_SECRET` | For compliance | compliance, exec_report | Vanta API secret |
| `OPENAI_MODEL_NAME` | No | All crews | Override default model (see below) |

---

## LLM / Model Configuration

**File:** `.env`

```bash
OPENAI_MODEL_NAME=gpt-4o
```

CrewAI uses this environment variable to select the model. Works with any OpenAI-compatible provider:

- **OpenAI:** `gpt-4o`, `gpt-4o-mini`
- **Gemini:** Set via CrewAI's LLM config (see CrewAI docs)
- **Claude:** Set via CrewAI's LLM config

The system is model-agnostic — no crew has hardcoded model references. All crews inherit from the environment.

---

## Crew Agent Tuning

Each crew has two YAML files that control how the AI agent thinks and acts:

```
crews/<crew_name>/src/<crew_name>/config/
    agents.yaml    # WHO the agent is (role, goal, backstory)
    tasks.yaml     # WHAT the agent does (step-by-step instructions)
```

### agents.yaml

```yaml
agent_name:
  role: >
    The agent's title (e.g., "Daily Sprint Intelligence Agent")
  goal: >
    What success looks like (e.g., "Generate 2-minute executive summary")
  backstory: >
    Detailed context and instructions. This is the main lever for
    tuning agent behavior. The LLM uses this as its personality
    and decision-making framework.
  allow_delegation: false
```

**Tuning tips:**
- `backstory` is the most impactful field — more detail = more precise behavior
- Include explicit rules ("ALWAYS check duplicates BEFORE creating tasks")
- Include anti-patterns ("Do NOT create tasks for passing CI checks")
- Reference specific ClickUp list IDs so the agent targets the right lists

### tasks.yaml

```yaml
task_name:
  description: >
    Step-by-step instructions. The LLM follows these literally.
    Include thresholds, list IDs, tool names, and output format.
  expected_output: >
    What the result should look like (JSON format, confirmation, etc.)
  agent: agent_name
  context:            # Optional: chain tasks — this task receives
    - previous_task   # the output of previous_task as input
```

**Tuning tips:**
- Be explicit about tool names (e.g., "use `post_standup` NOT `post`")
- Specify exact list IDs for task creation
- Define thresholds as numbers ("stale = >7 days", "critical = >30 days")
- Use `context` to chain tasks that depend on each other

### Crew-specific tuning files

| Crew | agents.yaml | tasks.yaml |
|------|------------|------------|
| compliance | `crews/compliance_crew/src/compliance_crew/config/` | Same |
| intake | `crews/intake_crew/src/intake_crew/config/` | Same |
| daily_pulse | `crews/daily_pulse_crew/src/daily_pulse_crew/config/` | Same |
| customer_success | `crews/customer_success_crew/src/customer_success_crew/config/` | Same |
| pr_radar | `crews/pr_radar_crew/src/pr_radar_crew/config/` | Same |
| triage | `crews/triage_crew/src/triage_crew/config/` | Same |
| deal_intel | `crews/deal_intel_crew/src/deal_intel_crew/config/` | Same |
| sprint | `crews/sprint_crew/src/sprint_crew/config/` | Same |
| retrospective | `crews/retrospective_crew/src/retrospective_crew/config/` | Same |
| exec_report | `crews/exec_report_crew/src/exec_report_crew/config/` | Same |
