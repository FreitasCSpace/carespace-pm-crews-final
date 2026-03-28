# CareSpace PM Crews — Configuration Manual

How to customize every aspect of the autonomous PM system.
Most settings live in one file: `src/shared/config/context.py`.

---

## Quick Reference

| What you want to change | Where |
|--------------------------|-------|
| Add/remove team members | `context.py` → `TEAM` |
| Change sprint capacity | `context.py` → `SPRINT_RULES` |
| Adjust SP estimates | `context.py` → `SP_ESTIMATE` |
| Add a new GitHub repo | `context.py` → `REPO_DOMAIN` |
| Change Slack channels | `context.py` → `SLACK` |
| Change stale task/PR thresholds | `crews/daily_pulse/config/tasks.yaml` |
| Tune crew behavior | `crews/<name>/config/agents.yaml` + `tasks.yaml` |
| Change the LLM model | `.env` → `OPENAI_MODEL_NAME` |

---

## Team & People

### Team Members (`TEAM`)

**File:** `src/shared/config/context.py`

Each engineer has:

```python
TEAM = {
    "github_username": {
        "domains": ["frontend", "backend"],  # What they work on
        "cap_sp":  20,                        # Story points per sprint
        "max_tasks": 4,                       # Max concurrent tasks
        "cu_id":   "49000180",               # ClickUp user ID
        "slack_name": "Andre Dutra",         # Slack display name
    },
}
```

**To add someone:** Get their ClickUp user ID, add entry to `TEAM`.
**To remove someone:** Delete their entry. Triage stops assigning them.

### Non-Engineering Staff

```python
NON_ENGINEERING = {
    "luis": {"cu_id": "118004891", "slack_name": "Luis Freitas", "role": "Compliance"},
}
```

---

## Sprint Planning

### Sprint Rules (`SPRINT_RULES`)

```python
SPRINT_RULES = {
    "budget_sp": 48,         # Max story points per sprint
    "duration_days": 14,     # Sprint length
    "min_features": 3,       # Must include at least 3 features
    "max_compliance": 3,     # Max compliance tasks per sprint
}
```

### Sprint Candidates

The team curates `Sprint Candidates` (list `901326510572`). The Sprint Crew
finalizes from this list — it does NOT auto-pick from the backlog.

### Story Point Estimates (`SP_ESTIMATE`)

Auto-assigned by triage when a task has no SP:

```python
SP_ESTIMATE = {
    "security": 8, "bug_low": 2, "bug_medium": 5, "bug_high": 8,
    "feature_small": 5, "feature_medium": 13, "feature_large": 21,
}
```

---

## GitHub Repos & Domain Routing

### Repo-to-Domain Map (`REPO_DOMAIN`)

When intake imports a GitHub issue, it tags by repo:

```python
REPO_DOMAIN = {
    "carespace-ui":          "frontend",
    "carespace-admin":       "backend",
    "carespace-mobile-ios":  "mobile",
    "carespace-sdk":         "sdk",
    "carespace-docker":      "infra",
}
```

**To add a new repo:** Add `"repo-name": "domain"`.

### GitHub Organization

```python
GITHUB_ORG = "carespace-ai"
```

---

## ClickUp Structure

### Lists (`L`)

```python
L = {
    "master_backlog":       "901326439232",   # Single intake point
    "sprint_candidates":    "901326510572",   # Team curates here
    "alerts":               "901326439234",   # Alerts & Escalations
    "sprint_history":       "901326439238",   # Sprint History
}
```

**Warning:** If you delete/recreate lists in ClickUp, update IDs here.

### Sprint Folder & SP Field

```python
SPRINT_FOLDER_ID = "901317811717"
SP_CUSTOM_FIELD_ID = "1662e3e7-b018-47b7-8881-e30f6831c674"
```

---

## Slack Channels

```python
SLACK = {
    "standup":     "#pm-standup",          # Daily Pulse
    "sprint":      "#pm-sprint-board",     # Sprint + Retro
    "engineering": "#pm-engineering",      # Intake + Triage
}
```

Huddle Notes does not post to Slack — vault only.

### Required Bot Scopes

| Scope | Used for |
|-------|----------|
| `chat:write` | Post messages |
| `channels:read` | Resolve channel names to IDs |
| `channels:history` | Read messages (dedup, huddle detection) |
| `files:read` | Read huddle canvas files |
| `users:read` | Resolve user IDs to names |

---

## Crew Schedules

| Crew | Schedule | Cron (UTC) |
|------|----------|-----------|
| Intake | Every 3 hours | `0 */3 * * *` |
| Triage | Every 3 hours (15min after intake) | `15 */3 * * *` |
| Daily Pulse | Mon-Fri 07:45 PDT | `45 14 * * 1-5` |
| Huddle Notes | Daily 08:00 PDT | `0 15 * * *` |
| Retrospective | Bi-weekly Fri 16:00 PDT | `0 23 * * 5` |
| Sprint | Bi-weekly Sun 18:00 PDT | `0 1 * * 1` |

---

## Stale Task & PR Thresholds

Defined in task YAML configs (LLM reads as instructions):

| Threshold | Value | File |
|-----------|-------|------|
| Stale task (no comments) | 3 days | `crews/daily_pulse/config/tasks.yaml` |
| Stale PR | 7 days | `crews/daily_pulse/config/tasks.yaml` |
| Missing PR (in progress) | immediate | `crews/daily_pulse/config/tasks.yaml` |
| Aging backlog item | 21 days | `crews/triage/config/tasks.yaml` |

To change: edit the number in the task description.

---

## Vault Configuration

**File:** `src/shared/tools/vault.py`

```python
VAULT_REPO = "FreitasCSpace/carespace-pm-vault"

CREW_DIRS = {
    "intake": "intake",
    "daily_pulse": "sprint/daily",
    "triage": "backlog",
    "sprint_plan": "sprint/plans",
    "sprint_retro": "sprint/retros",
    "huddle_notes": "huddles",
    "context": "context",
}
```

**File:** `src/shared/vault_hooks.py` — controls reads/writes per crew:
- `CREW_READS` — static files to read before running
- `CREW_DYNAMIC_READS` — latest file from a directory
- `CREW_WRITES` — where output goes (date or datetime filename)
- `CREW_CONTEXT_WRITES` — rolling state files (triage → `backlog-health.md`, retro → `velocity.md`)

---

## Environment Variables

| Variable | Required | Used by |
|----------|----------|---------|
| `CLICKUP_API_TOKEN` | Yes | All crews (`pk_` format) |
| `GITHUB_TOKEN` | Yes | Intake, Daily Pulse, Vault (`ghp_` format) |
| `OPENAI_API_KEY` | Yes | All crews (LLM) |
| `SLACK_BOT_TOKEN` | Yes | Daily Pulse, Intake, Huddle Notes (`xoxb_` format) |
| `OPENAI_MODEL_NAME` | No | Override default model (default: `gpt-4o`) |

---

## Crew Agent Tuning

Each crew has two YAML config files:

```
src/crews/<crew_name>/config/
    agents.yaml    # WHO — role, goal, backstory
    tasks.yaml     # WHAT — step-by-step instructions
```

### Crew config locations

| Crew | Config path |
|------|------------|
| Intake | `src/crews/intake/config/` |
| Daily Pulse | `src/crews/daily_pulse/config/` |
| Triage | `src/crews/triage/config/` |
| Sprint | `src/crews/sprint/config/` |
| Retrospective | `src/crews/retrospective/config/` |
| Huddle Notes | `src/crews/huddle_notes/config/` |

### Tuning tips

- `backstory` in agents.yaml is the main lever — more detail = more precise behavior
- Include explicit rules: "ALWAYS do X before Y"
- Include anti-patterns: "Do NOT create tasks for passing CI"
- Thresholds in task descriptions are read as instructions — just change the number
- `context` in tasks.yaml chains tasks: downstream task receives upstream output
