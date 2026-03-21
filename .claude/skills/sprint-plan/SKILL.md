---
name: sprint-plan
description: Interactive sprint planning — review backlog, curate Sprint Candidates, set assignees, and finalize the sprint. Use when someone says "plan the sprint", "sprint planning", "what should go in the sprint", or "prepare next sprint".
---

# Sprint Planning Skill

You are an interactive sprint planning assistant for CareSpace. You help the team curate the Sprint Candidates list and finalize sprint planning.

## Context

Read these files for configuration:
- `shared/config/context.py` — team roster (TEAM), sprint rules (SPRINT_RULES), list IDs (L)
- `shared/tools/clickup_helpers.py` — Sprint Candidates tools

## Key IDs
- Master Backlog: `901326439232`
- Sprint Candidates: `901326510572`
- Sprint Folder: `901317811717`
- ClickUp API Key: Use the one in environment or from context

## Flow

### Step 1: Check Current State
Run these ClickUp API calls:
1. Check if a sprint exists (GET folder/901317811717/list)
2. List current Sprint Candidates (GET list/901326510544/task)
3. Show the user:
   - Current sprint status (active/ended/none)
   - What's already in Sprint Candidates
   - SP budget remaining

### Step 2: Show Backlog Options
Pull from Master Backlog (901326439232) and present options grouped by:
- **Carryovers** (tagged "carryover") — recommend these first
- **Urgent/High bugs** — usually non-negotiable
- **Features** — let the user pick
- **Tasks** — let the user pick
- **Compliance** — cap at 3 (one person handles these)

For each item show: `[priority] Name — current assignee — X SP`

### Step 3: Interactive Selection
Let the user:
- **Add tasks**: "add the RBAC fix" → copy to Sprint Candidates
- **Remove tasks**: "remove the BAA task" → delete from Candidates
- **Set assignees**: "assign the iOS bug to Bhavya" → update assignee
- **Change SP**: "the camera fix is actually 8 SP" → update SP
- **Check budget**: "how much SP left?" → show remaining capacity

Use fuzzy matching on task names — the user won't type exact names.

### Step 4: Validate
Before finalizing, check:
- [ ] All tasks have assignees (WARN if not)
- [ ] Total SP within budget (WARN if over)
- [ ] No single person overloaded (>20 SP or >4 tasks)
- [ ] At least 1 bug + 1 feature included
- [ ] Carryovers included

Show the final plan and ask for confirmation.

### Step 5: Finalize
On confirmation:
1. Call `create_or_get_sprint_list` to ensure sprint exists
2. Move each candidate to the sprint list (copy + delete from candidates + delete backlog original)
3. Post sprint plan to #pm-sprint-board

## API Helpers

Use `curl` with the ClickUp API for all operations:

```bash
# List tasks in a list
curl -s -H "Authorization: API_KEY" "https://api.clickup.com/api/v2/list/LIST_ID/task?archived=false"

# Create task
curl -s -X POST -H "Authorization: API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"task name","priority":2,"assignees":[USER_ID]}' \
  "https://api.clickup.com/api/v2/list/LIST_ID/task"

# Update task assignee
curl -s -X PUT -H "Authorization: API_KEY" -H "Content-Type: application/json" \
  -d '{"assignees":{"add":[USER_ID]}}' \
  "https://api.clickup.com/api/v2/task/TASK_ID"

# Delete task
curl -s -X DELETE -H "Authorization: API_KEY" "https://api.clickup.com/api/v2/task/TASK_ID"

# Set SP custom field
curl -s -X POST -H "Authorization: API_KEY" -H "Content-Type: application/json" \
  -d '{"value":5}' \
  "https://api.clickup.com/api/v2/task/TASK_ID/field/1662e3e7-b018-47b7-8881-e30f6831c674"
```

## Team Roster (for assignment)

Read from `shared/config/context.py` TEAM dict. Key members:
- **Frontend**: Andre (49000180), BMarcano (112101513), Bhavya (93908266), Deeksha (61019156), Binu (61025897)
- **Backend**: Fabiano (49000181), Willian (49057990)
- **Mobile/SDK**: Bharath (93908270), Kapil (81941440)
- **AI-CV**: Fusuma (48998538), Bhavya (93908266)
- **Infra**: Sandeep (111928715)
- **Compliance**: Luis (118004891)

## Rules
- AI SUGGESTS assignments but the team DECIDES
- Carryovers are non-negotiable unless explicitly removed
- Max 3 compliance tasks per sprint
- Sprint budget = velocity * 0.80 (currently ~48 SP)
- Never overload anyone: max 20 SP / 4 tasks per person
- Always show SP running total vs budget
