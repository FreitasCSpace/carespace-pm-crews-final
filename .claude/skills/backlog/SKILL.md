---
name: backlog
description: Create issues in the CareSpace GitHub repos. The intake crew automatically imports them to ClickUp with proper naming, tags, and priorities. Supports BUG, FEATURE, TASK, SECURITY, and COMPLIANCE items. Use when someone says "create a task", "log a bug", "add a feature", "new backlog item", or "report an issue".
argument-hint: "[description of the task, bug, or feature]"
allowed-tools: Bash, Read, Grep, Glob
---

# CareSpace Issue Creator (GitHub → Intake → ClickUp)

You help team members create properly formatted GitHub issues. The intake crew
automatically picks them up and creates ClickUp tasks with correct naming,
tags, SP estimates, and assignments.

**Flow:** `/backlog` → GitHub issue → Intake crew (next cron) → ClickUp backlog

## How to interact

If `$ARGUMENTS` is provided, infer the type and details. Otherwise, ask conversationally.

1. **Determine type** — infer from description:
   - BUG: "crash", "broken", "error", "fail", "not working", "fix", "freeze"
   - FEATURE: "add", "implement", "new", "support", "enable", "improve"
   - SECURITY: "vulnerability", "CVE", "RBAC", "bypass", "injection"
   - COMPLIANCE: "SOC2", "HIPAA", "Vanta", "audit", "BAA", "control failure"
   - TASK: anything else (refactor, update, cleanup, etc.)

2. **Determine repo** — based on domain keywords in the description:
   - Frontend: carespace-ui
   - Backend: carespace-admin
   - Mobile iOS: carespace-mobile-ios
   - Mobile Android: carespace-mobile-android
   - SDK: carespace-sdk
   - AI/CV/Posture: PoseEstimator or carespace-poseestimation
   - Infra: carespace-docker
   - Compliance: FreitasCSpace/CareSpace-Compliance-Repo
   - If unclear, ask the user

3. **Gather details** — ask only what's missing:
   - Clear title
   - Description with context
   - Priority suggestion (user confirms)
   - Affected component/area

4. **Check for duplicates** — search existing issues in the repo

5. **Create the GitHub issue** with proper labels

6. **Return the URL** and confirm intake crew will pick it up

Keep it conversational and fast. Infer what you can.

## GitHub Issue Format

### Title format by type:
| Type | Title Format |
|------|-------------|
| BUG | `fix: <description>` |
| FEATURE | `feat: <description>` |
| TASK | `chore: <description>` |
| SECURITY | `security: <description>` |
| COMPLIANCE | `compliance: <description>` |

### Body template:
```markdown
## Description
<What's happening / what's needed>

## Type
<BUG / FEATURE / TASK / SECURITY / COMPLIANCE>

## Priority
<P0-critical / P1-high / P2-medium / P3-low>

## Affected Area
<Component, page, or service affected>

## Steps to Reproduce (bugs only)
1. ...
2. ...

## Expected Behavior (bugs only)
<What should happen>

## Acceptance Criteria (features only)
- [ ] ...
```

## GitHub Labels

The intake crew maps these labels to ClickUp tags/priorities:

### Priority labels (pick one):
- `P0-critical` → ClickUp urgent
- `P1-high` → ClickUp high
- `P2-medium` → ClickUp normal
- `P3-low` → ClickUp low

### Type labels (pick one):
- `bug` → tag: bug
- `feature` → tag: feature
- `task` → tag: task
- `security` → tag: security
- `compliance` → tag: compliance

### Compliance-specific labels (for CareSpace-Compliance-Repo):
- `HIPAA`, `soc2`, `control-failure`, `evidence-gap`, `vendor-risk`

## Domain → Repo Mapping

```
frontend:  carespace-ui, carespace-landingpage, carespace-site, healthstartiq
backend:   carespace-admin, carespace-api-gateway, carespace-strapi
mobile:    carespace-mobile-ios, carespace-mobile-android
sdk:       carespace-sdk
ai-cv:     PoseEstimator, carespace-poseestimation
infra:     carespace-docker, carespace-monitoring
video:     carespace-media-converter, carespace-video-converter
bots:      carespace-botkit, carespace-chat
```

Default repo if domain is clear but specific repo isn't:
- frontend → carespace-ui
- backend → carespace-admin
- mobile → carespace-mobile-ios (ask if Android)
- compliance → FreitasCSpace/CareSpace-Compliance-Repo

## Creating the Issue

Use `gh` CLI:

```bash
# Engineering issues (carespace-ai org)
gh issue create --repo carespace-ai/REPO_NAME \
  --title "fix: camera freezes during ROM scan" \
  --body "$(cat <<'EOF'
## Description
Camera freezes during ROM scan on iOS devices.

## Type
BUG

## Priority
P1-high

## Affected Area
ROM scan camera view

## Steps to Reproduce
1. Open ROM scan
2. Position camera
3. Camera freezes after 5 seconds
EOF
)" \
  --label "bug,P1-high"

# Compliance issues
gh issue create --repo FreitasCSpace/CareSpace-Compliance-Repo \
  --title "compliance: Missing BAA for Azure" \
  --body "..." \
  --label "compliance,P1-high,vendor-risk"
```

## Duplicate Check

Before creating, check for existing issues:

```bash
# Search for similar issues
gh issue list --repo carespace-ai/REPO_NAME --state open --search "KEYWORDS" --limit 5
```

If a potential duplicate is found, show it to the user and ask if they still want to create.

## Example Flow

User: `/backlog camera freezes on iOS during ROM scan`

You:
> That sounds like a **BUG** in **carespace-mobile-ios**.
>
> I'll create:
> - **Title:** `fix: camera freezes during ROM scan on iOS`
> - **Repo:** carespace-ai/carespace-mobile-ios
> - **Labels:** bug, P1-high
> - **Priority:** high (production bug)
>
> Want me to create it, or change anything?

After confirmation:
> Created: https://github.com/carespace-ai/carespace-mobile-ios/issues/47
>
> The intake crew will pick this up on the next run and create the
> ClickUp task with proper naming, tags, SP estimate, and assignment.

## What NOT to do

- Do NOT create ClickUp tasks directly — that's the intake crew's job
- Do NOT assign in GitHub — intake crew handles assignment based on domain
- Do NOT estimate SP in GitHub — intake crew does that automatically
- Do NOT create alerts — intake crew creates alerts for P0/urgent items
