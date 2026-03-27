---
name: sprint-methodology
description: Sprint planning rules, velocity calculation, and capacity management. Use for sprint planning, retrospectives, and daily pulse analysis.
metadata:
  author: CareSpace
  version: "1.0"
---

# Sprint Methodology

## Sprint Structure
- Duration: 14 days (biweekly)
- Planning: Sunday evening
- Daily pulse: Mon-Fri 07:45 PDT
- Retrospective: Friday 16:00 PDT (end of sprint)

## Story Points
Estimation heuristics by type:
- Security: 8 SP
- Bug (high): 8 SP, Bug (medium): 5 SP, Bug (low): 2 SP
- Feature (large): 21 SP, Feature (medium): 13 SP, Feature (small): 5 SP
- PR review: 2 SP, CI fix: 3 SP

## Velocity & Capacity
- Default velocity: 60 SP
- Velocity buffer: 80% (budget = last_velocity × 0.80)
- Sprint budget: ~48 SP (default)
- Recommended mix: 1-2 bugs + 3-5 features + 2-3 tasks + 2-3 compliance
- Minimum features per sprint: 3
- Maximum compliance tasks per sprint: 3

## Sprint Health Assessment
Based on sprint progress vs elapsed time:
- time_pct = elapsed_days / total_days
- done_pct = done_sp / total_sp
- On Track (green): done_pct >= time_pct - 0.05
- At Risk (yellow): done_pct between time_pct - 0.15 and time_pct - 0.05
- Behind (red): done_pct < time_pct - 0.15

## Carryover Rules
Tasks not completed by sprint end:
1. Move back to Master Backlog
2. Tag with "carryover"
3. Bump priority by 1 level (normal → high, high → urgent)
4. Sprint crew picks carryovers FIRST for next sprint

## Backlog Hygiene
- Tasks in Master Backlog stay UNASSIGNED until sprint planning
- All tasks need [TYPE] prefix and source tag
- Tasks without GitHub link = design tasks (tag: design)
- Aging threshold: 21 days with no update

## Meeting Mode
Based on sprint health:
- Blockers exist → STANDUP MODE: 15-min focused session
- No blockers → OPEN SLOT: available for strategic discussion
