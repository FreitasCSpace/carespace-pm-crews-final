Create a task in the CareSpace ClickUp Master Backlog (list 901326439232).

Ask the user what they want to create. Guide them through the process based on the type.

## Task Types

### BUG
- Name format: `[BUG] <description> (<repo>#<issue_number>)` or `[BUG] <description>` if no GitHub issue
- Tags: `[domain, "bug", "github"]` (or `"internal"` instead of `"github"` if no issue)
- Priority: urgent if critical/security-related, high for most bugs, normal for minor
- Domain: determine from repo or ask user (frontend, backend, mobile, sdk, ai-cv, infra)

### FEATURE
- Name format: `[FEATURE] <description> (<repo>#<issue_number>)` or `[FEATURE] <description>`
- Tags: `[domain, "feature", "github"]` or `[domain, "feature", "internal"]`
- Priority: normal (default), high if blocking other work
- Domain: determine from repo or ask user

### TASK
- Name format: `[TASK] <description> (<repo>#<issue_number>)` or `[TASK] <description>`
- Tags: `[domain, "task", "github"]` or `[domain, "task", "internal"]`
- Priority: normal (default)
- Domain: determine from repo or ask user

### SECURITY
- Name format: `[SECURITY] <description> (<repo>#<issue_number>)`
- Tags: `[domain, "security", "github"]`
- Priority: urgent (always)
- Domain: determine from repo
- Also creates an alert in Alerts list (901326439234) with: `[ALERT] <description>`

### COMPLIANCE
- Name format: `[COMPLIANCE] <description> (#<issue_number>)` or `[COMPLIANCE] <description>`
- Tags: `["compliance", "vanta"]` + any of: `"soc2"`, `"hipaa"`, `"security"`
- Priority: P0=urgent, P1=high, P2=normal, P3=low
- Assignee: Luis Freitas (118004891) is compliance owner
- If urgent: also create alert in Alerts list with `[ALERT] <description>`, tags `["compliance", "urgent"]`

## Domain Mapping (repo to domain)
- frontend: carespace-ui, carespace-landingpage, carespace-site, healthstartiq
- backend: carespace-admin, carespace-api-gateway, carespace-crud
- mobile: carespace-mobile-android, carespace-mobile-ios
- sdk: carespace-sdk
- ai-cv: PoseEstimator, carespace-poseestimation
- infra: carespace-docker, carespace-monitoring, carespace-k8s
- video: carespace-jitsi, carespace-videocall

## Story Point Estimates
- Security: 8 SP
- Bug (low): 2 SP, Bug (medium): 5 SP, Bug (high): 8 SP
- Feature (small): 5 SP, Feature (medium): 13 SP, Feature (large): 21 SP
- Task: 3-5 SP

## Team Members (for assignment)
- Andre C Dutra (49000180): frontend
- Fabiano Fiorentin (49000181): backend
- Willian Schaitel (49057990): backend
- Bharath (93908270): sdk, ai-cv
- Flavio Fusuma (48998538): infra, compliance
- Luis Freitas (118004891): compliance, management
- Bhavya Saurabh (49069843): mobile, frontend

## Duplicate Check
Before creating, ALWAYS check for duplicates first:
- Use the ClickUp API to search Master Backlog for the task name fragment
- If a similar task exists, tell the user and ask if they want to proceed

## Process
1. Ask what type (bug/feature/task/security/compliance) — or infer from their description
2. Ask for the description/title
3. Ask which repo (if applicable) — or determine domain directly
4. Suggest priority based on type, confirm with user
5. Suggest assignee based on domain, confirm with user
6. Suggest story points, confirm with user
7. Check for duplicates
8. Create the task via ClickUp API: POST https://api.clickup.com/api/v2/list/901326439232/task
9. If security/urgent compliance: also create alert in list 901326439234
10. Return the ClickUp task URL to the user

## API Details
- API Key: Use environment variable CLICKUP_API_KEY or ask user
- Workspace: 31124097
- Master Backlog list: 901326439232
- Alerts list: 901326439234
- Story Points custom field ID: 1662e3e7-b018-47b7-8881-e30f6831c674

## Important
- Keep titles under 150 characters
- Always include the task type prefix in brackets: [BUG], [FEATURE], [TASK], [SECURITY], [COMPLIANCE]
- Always tag with at least: domain + type + source
- Be conversational — this is meant to make backlog creation easy for anyone on the team
