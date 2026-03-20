---
name: backlog
description: Create tasks in the CareSpace ClickUp Master Backlog. Supports BUG, FEATURE, TASK, SECURITY, and COMPLIANCE items with proper naming, tags, priorities, and team assignments. Use when someone says "create a task", "log a bug", "add a feature", "new backlog item", or "report an issue".
argument-hint: "[description of the task, bug, or feature]"
allowed-tools: Bash, Read, Grep, Glob
---

# CareSpace Backlog Task Creator

You help team members create properly formatted tasks in the ClickUp Master Backlog.

## How to interact

If `$ARGUMENTS` is provided, infer the task type and details from it. Otherwise, ask conversationally.

1. **Determine type** — infer from description or ask:
   - BUG: "crash", "broken", "error", "fail", "not working", "fix"
   - FEATURE: "add", "implement", "new", "support", "enable"
   - SECURITY: "vulnerability", "CVE", "RBAC", "bypass", "injection"
   - COMPLIANCE: "SOC2", "HIPAA", "Vanta", "audit", "BAA", "control failure"
   - TASK: anything else (refactor, update, cleanup, etc.)

2. **Gather details** — ask only what's missing:
   - Title/description
   - Repo (if engineering) or compliance framework (if compliance)
   - Priority (suggest based on type, confirm)
   - Assignee (suggest based on domain, confirm)
   - Story points (suggest based on type/size, confirm)

3. **Check for duplicates** before creating

4. **Create the task** via ClickUp API

5. **Return the URL** to the user

Keep it conversational and fast. Don't ask unnecessary questions — infer what you can.

## Naming Formats

| Type | Format | Example |
|------|--------|---------|
| BUG | `[BUG] <title> (<repo>#<N>)` | `[BUG] Login crashes on iOS (carespace-mobile-ios#145)` |
| FEATURE | `[FEATURE] <title> (<repo>#<N>)` | `[FEATURE] Add SSO support (carespace-admin#89)` |
| TASK | `[TASK] <title> (<repo>#<N>)` | `[TASK] Update dependencies (carespace-ui#412)` |
| SECURITY | `[SECURITY] <title> (<repo>#<N>)` | `[SECURITY] SQL injection in search (carespace-admin#234)` |
| COMPLIANCE | `[COMPLIANCE] <title> (#<N>)` | `[COMPLIANCE] Missing BAA for Azure (#432)` |

- If no GitHub issue number, omit the `(repo#N)` part
- Titles max 150 characters
- Type prefix is ALWAYS uppercase in brackets

## Tag Rules

Every task gets 3 tags minimum: **domain + type + source**

**Type tags:** `bug`, `feature`, `task`, `security`, `compliance`, `tech-debt`
**Source tags:** `github`, `vanta`, `client-feedback`, `internal`
**Domain tags:** `frontend`, `backend`, `mobile`, `sdk`, `ai-cv`, `infra`, `bots`, `video`

### Tag combinations by type:
- BUG from GitHub: `[domain, "bug", "github"]`
- BUG internal: `[domain, "bug", "internal"]`
- FEATURE: `[domain, "feature", "github"]` or `[domain, "feature", "internal"]`
- SECURITY: `[domain, "security", "github"]`
- COMPLIANCE: `["compliance", "vanta"]` + optional: `"soc2"`, `"hipaa"`, `"security"`
- TASK: `[domain, "task", "github"]` or `[domain, "task", "internal"]`

## Priority Mapping

| Priority | ClickUp Value | When to use |
|----------|---------------|-------------|
| urgent | 1 | Security issues, P0, critical production bugs |
| high | 2 | Most bugs, blocking issues, P1 |
| normal | 3 | Features, tasks, P2 (default) |
| low | 4 | Nice-to-haves, P3, tech debt |

## Domain Mapping (repo to domain)

```
frontend: carespace-ui, carespace-landingpage, carespace-site, healthstartiq
backend:  carespace-admin, carespace-api-gateway, carespace-crud
mobile:   carespace-mobile-android, carespace-mobile-ios
sdk:      carespace-sdk
ai-cv:    PoseEstimator, carespace-poseestimation
infra:    carespace-docker, carespace-monitoring, carespace-k8s
video:    carespace-jitsi, carespace-videocall
```

## Story Point Estimates

| Type | Size | SP |
|------|------|----|
| Security issue | — | 8 |
| Bug | low | 2 |
| Bug | medium | 5 |
| Bug | high/critical | 8 |
| Feature | small | 5 |
| Feature | medium | 13 |
| Feature | large | 21 |
| Task | — | 3-5 |
| PR review | — | 2 |
| CI fix | — | 3 |

## Team Members (for assignment suggestions)

| Name | ClickUp ID | Domain |
|------|-----------|--------|
| Andre C Dutra | 49000180 | frontend |
| Fabiano Fiorentin | 49000181 | backend |
| Willian Schaitel | 49057990 | backend |
| Bharath | 93908270 | sdk, ai-cv |
| Flavio Fusuma | 48998538 | infra, compliance |
| Luis Freitas | 118004891 | compliance, management |
| Bhavya Saurabh | 49069843 | mobile, frontend |

## ClickUp API

**Create task:**
```bash
curl -s -X POST "https://api.clickup.com/api/v2/list/{LIST_ID}/task" \
  -H "Authorization: {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "[TYPE] title",
    "description": "description text",
    "priority": 3,
    "tags": ["domain", "type", "source"],
    "assignees": [USER_ID]
  }'
```

**IDs:**
- Master Backlog: `901326439232`
- Alerts list: `901326439234`
- SP custom field: `1662e3e7-b018-47b7-8881-e30f6831c674`

**Duplicate check** — before creating, search the backlog:
```bash
curl -s "https://api.clickup.com/api/v2/list/901326439232/task?archived=false&include_closed=true&page=0" \
  -H "Authorization: {API_KEY}"
```
Search task names for the title fragment. If found, warn the user.

**Set story points** after creation:
```bash
curl -s -X POST "https://api.clickup.com/api/v2/task/{TASK_ID}/field/1662e3e7-b018-47b7-8881-e30f6831c674" \
  -H "Authorization: {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"value": 5}'
```

## Auto-alert rules

Create an additional alert in the Alerts list (901326439234) when:
- Type is SECURITY (always) — priority urgent, tags: `[domain, "security", "urgent"]`
- Type is COMPLIANCE with priority urgent — tags: `["compliance", "urgent"]`

Alert name format: `[ALERT] <title>`

## API Key

Look for the ClickUp API key in this order:
1. Environment variable `CLICKUP_API_KEY`
2. Ask the user to provide it

## Example Flow

User: `/backlog camera freezes during ROM scan on iOS`

You:
> Got it — that sounds like a **BUG** in **carespace-mobile-ios** (mobile domain).
>
> Here's what I'll create:
> - **Name:** `[BUG] Camera freezes during ROM scan on iOS`
> - **Priority:** high (production bug)
> - **Assignee:** Bhavya Saurabh (mobile)
> - **SP:** 5 (medium bug)
> - **Tags:** mobile, bug, internal
>
> Want me to create it, or change anything?

After confirmation, create and return the ClickUp URL.
