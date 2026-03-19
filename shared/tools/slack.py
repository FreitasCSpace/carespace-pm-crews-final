"""
tools/slack.py
Slack posting tools. Every crew that communicates uses these.
All posts use Slack Block Kit for consistent, clean formatting.
Requires SLACK_BOT_TOKEN in environment.
"""

import os, json, requests
from datetime import date
from crewai.tools import tool
from shared.config.context import SLACK

def _api(channel: str, text: str, blocks=None) -> dict:
    body = {"channel": channel, "text": text}
    if blocks:
        body["blocks"] = blocks
    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    return r.json()

PE = {"urgent": "P0", "high": "P1", "normal": "P2", "low": "P3", "none": "--"}
HS = lambda pct: "GREEN" if pct >= 80 else ("YELLOW" if pct >= 60 else "RED")

def _hdr(t): return {"type": "header", "text": {"type": "plain_text", "text": t}}
def _sec(t): return {"type": "section", "text": {"type": "mrkdwn", "text": t}}
def _div():  return {"type": "divider"}
def _ctx(t): return {"type": "context", "elements": [{"type": "mrkdwn", "text": t}]}


# ── Generic post ──────────────────────────────────────────────────────────────

@tool("Post to Slack Channel")
def post(channel: str, message: str) -> str:
    """
    Posts a plain mrkdwn message to any Slack channel.
    Use for quick notifications that don't need structured blocks.
    """
    r = _api(channel, message)
    return json.dumps({"ok": r.get("ok"), "ts": r.get("ts")})


# ── Daily Standup Digest ──────────────────────────────────────────────────────

@tool("Post Daily Standup to Slack")
def post_standup(executive_summary: str, done: str, in_progress: str,
                 blocked: str, pending: str, attention: str, meeting_mode: str) -> str:
    """
    Posts the structured daily sprint digest to #pm-standup.
    Template is enforced — just pass the content for each section.
    Do NOT add separators or headers — the tool handles formatting.

    executive_summary: 3-4 bullet points (sprint health, progress, risks)
    done: bullet list of completed items (or 'None')
    in_progress: bullet list of active items with assignee and SP
    blocked: bullet list of blocked items with reason
    pending: bullet list of not-started items with assignee and SP
    attention: stale PRs, CI failures, stale tasks
    meeting_mode: either 'STANDUP: X blockers...' or 'OPEN SLOT: No blockers...'
    """
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["standup"], f"Sprint Digest {today}", [
        _hdr(f"📊 Sprint Digest — {today}"),
        _sec(f"*Executive Summary*\n{executive_summary}"),
        _div(),
        _sec(
            f"*✅ Done*\n{done or '_None_'}\n\n"
            f"*🔄 In Progress*\n{in_progress or '_None_'}\n\n"
            f"*🚫 Blocked*\n{blocked or '_None_'}\n\n"
            f"*⏳ Pending*\n{pending or '_None_'}"
        ),
        _div(),
        _sec(f"*⚠️ Needs Attention*\n{attention or '_All clear_'}"),
        _div(),
        _sec(f"*🎯 Meeting Mode*\n{meeting_mode}"),
        _ctx("_Posted by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Sprint Plan ───────────────────────────────────────────────────────────────

@tool("Post Sprint Plan to Slack")
def post_sprint_plan(sprint_name: str, tasks_json: str, total_sp: int) -> str:
    """
    Posts the sprint planning results to #pm-sprint-board.
    sprint_name: e.g. 'Sprint 1 — Mar 23 to Apr 05'
    tasks_json: JSON array of {name, priority, assignee, story_points}
    total_sp: total story points committed
    """
    tasks = json.loads(tasks_json)
    lines = [
        f"• *{t['name']}*  →  _{t.get('assignee', 'unassigned')}_  `{t.get('story_points', '?')} SP`"
        for t in tasks
    ]
    r = _api(SLACK["sprint"], f"Sprint plan: {sprint_name}", [
        _hdr(f"📅 {sprint_name}"),
        _sec(f"*{len(tasks)} tasks committed  •  {total_sp} story points*"),
        _div(),
        _sec("\n".join(lines) or "_No tasks selected_"),
        _ctx("_Sprint plan by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Alerts & Escalations ─────────────────────────────────────────────────────

@tool("Post Triage Report to Slack")
def post_blocker(description: str, task_url: str, owner: str, impact: str = "") -> str:
    """
    Posts a structured alert/blocker to #pm-alerts. Template enforced.
    Do NOT use the generic 'post' tool for alerts — use this instead.

    description: what happened (e.g., 'BLOCKER: API timeout')
    task_url: link to the relevant task or 'N/A' for summaries
    owner: who is responsible
    impact: business impact or action summary
    """
    today = date.today().strftime("%B %d, %Y")
    sections = [_hdr(f"🚨 Alert — {today}")]

    if description:
        sections.append(_sec(f"*{description}*"))
    if owner and owner != "N/A":
        sections.append(_sec(f"*Owner:* {owner}"))
    if task_url and task_url != "N/A":
        sections.append(_sec(f"*Task:* {task_url}"))
    if impact:
        sections.append(_div())
        sections.append(_sec(f"*Details:*\n{impact}"))

    sections.append(_ctx("_Alert by CareSpace PM AI_"))
    r = _api(SLACK["alerts"], f"Alert: {description[:60]}", sections)
    return json.dumps({"ok": r.get("ok")})


@tool("Post Triage Summary to Slack")
def post_triage_summary(priorities_set: str, assignments: str,
                        story_points: str, alerts: str, reasoning: str) -> str:
    """
    Posts a structured triage summary to #pm-alerts. Template enforced.
    USE THIS for triage results — not the generic 'post' tool.
    Do NOT add separators or headers — the tool handles formatting.

    priorities_set: bullet list of priority changes (or 'None')
    assignments: bullet list of assignments made (or 'None')
    story_points: summary of SP set (or 'None')
    alerts: bullet list of alerts created (or 'None')
    reasoning: why these decisions were made
    """
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["alerts"], f"Triage Report {today}", [
        _hdr(f"🔍 Triage Report — {today}"),
        _sec(
            f"*Priorities Changed*\n{priorities_set or '_None_'}\n\n"
            f"*Assignments*\n{assignments or '_None_'}\n\n"
            f"*Story Points*\n{story_points or '_None_'}"
        ),
        _div(),
        _sec(f"*Alerts Created*\n{alerts or '_None_'}"),
        _div(),
        _sec(f"*Reasoning*\n{reasoning}"),
        _ctx("_Triage by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


@tool("Post PR Radar Report to Slack")
def post_pr_radar(stale_prs: str, critical_prs: str, ci_status: str,
                  tasks_created: str, summary: str) -> str:
    """
    Posts the PR & CI radar report to #pm-engineering. Template enforced.
    Do NOT use the generic 'post' tool — use this instead.

    stale_prs: bullet list of stale PRs with age and link
    critical_prs: bullet list of critical stale PRs (>30d)
    ci_status: CI status summary (failures or 'All passing ✅')
    tasks_created: what tasks/alerts were created
    summary: one-line totals (e.g. '5 stale PRs, 1 critical, 0 CI failures')
    """
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["engineering"], f"PR Radar {today}", [
        _hdr(f"🔀 PR & CI Radar — {today}"),
        _sec(f"*{summary}*"),
        _div(),
        _sec(
            f"*⚠️ Stale PRs (>7d)*\n{stale_prs or '_None_'}\n\n"
            f"*🔴 Critical (>30d)*\n{critical_prs or '_None_'}"
        ),
        _div(),
        _sec(f"*🔧 CI Status*\n{ci_status or '_All passing ✅_'}"),
        _div(),
        _sec(f"*📋 Actions Taken*\n{tasks_created or '_None_'}"),
        _ctx("_PR Radar by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


@tool("Post Blocker Summary to Engineering Slack")
def post_blocker_summary(blockers_detail: str, blocker_count: int, meeting_mode: str) -> str:
    """
    Posts a SINGLE consolidated blocker summary to #pm-engineering.
    Use this INSTEAD of posting individual blockers one-by-one.

    blockers_detail: formatted list of blockers, each with:
      - Name and link
      - Owner/assignee
      - Why it's blocking (description/impact)
      - Recommended action
      Example:
        '• 🔴 [ALERT] Vendor Risk: Azure — Missing BAA (#180)
           Owner: @Flavio Fusuma, @Luis Freitas
           Impact: HIPAA compliance blocked — cannot process PHI without BAA
           Action: Escalate to Azure account team
         • 🔴 [SECURITY] RBAC Guards Bypassed (#80)
           Owner: @Fabiano Fiorentin
           Impact: Authorization checks returning true unconditionally
           Action: Patch RolesGuard and RelationshipValidatorGuard'
    blocker_count: total number of blockers
    meeting_mode: 'STANDUP: X blockers...' or 'OPEN SLOT: No blockers...'
    """
    today = date.today().strftime("%B %d, %Y")
    emoji = "🔴" if blocker_count > 0 else "🟢"
    r = _api(SLACK["engineering"], f"Blockers: {blocker_count} flagged", [
        _hdr(f"{emoji} Daily Blockers — {today}"),
        _sec(f"*{blocker_count} blocker(s) flagged for today's standup*"),
        _div(),
        _sec(blockers_detail or "_No blockers — all clear_"),
        _div(),
        _sec(f"*🎯 {meeting_mode}*"),
        _ctx("_Blocker summary by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


@tool("Post SLA Breach Alert to Slack")
def post_sla_breach(bug_name: str, task_url: str, priority: str, hours_open: int) -> str:
    """
    Posts an SLA breach alert to #pm-alerts.
    """
    sla = {"urgent": 4, "high": 24, "normal": 72, "low": 168}.get(priority, 24)
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["alerts"], f"SLA BREACH: {bug_name}", [
        _hdr(f"⏰ SLA Breach — {today}"),
        _sec(
            f"*{priority.upper()} task open {hours_open}h* (SLA: {sla}h)\n\n"
            f"*Task:* {bug_name}\n"
            f"*Link:* {task_url}"
        ),
        _ctx("_SLA alert by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Sprint Retrospective ─────────────────────────────────────────────────────

@tool("Post Sprint Retrospective to Slack")
def post_retro(sprint_name: str, completion_pct: float,
               velocity_sp: int, carry_over: int, doc_url: str) -> str:
    """Posts end-of-sprint retrospective summary to #pm-sprint-board."""
    health = HS(completion_pct)
    emoji = "🟢" if health == "GREEN" else ("🟡" if health == "YELLOW" else "🔴")
    r = _api(SLACK["sprint"], f"Retro: {sprint_name}", [
        _hdr(f"📝 Retrospective — {sprint_name}"),
        _sec(
            f"*{emoji} {health}*\n\n"
            f"• Completion: *{completion_pct}%*\n"
            f"• Velocity: *{velocity_sp} SP*\n"
            f"• Carry-over: *{carry_over} tasks*"
        ),
        _div(),
        _sec(f"📄 Full report: {doc_url}"),
        _ctx("_Retrospective by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── GTM Pipeline ──────────────────────────────────────────────────────────────

@tool("Post GTM Intelligence to Slack")
def post_gtm(headline: str, deals_at_risk: int, pipeline_value: str,
             gaps: str, actions: str) -> str:
    """Posts the weekly GTM pipeline intelligence report to #pm-gtm."""
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["gtm"], "GTM Pipeline Update", [
        _hdr(f"💰 GTM Pipeline — {today}"),
        _sec(headline),
        _sec(f"• *Deals at risk:* {deals_at_risk}\n• *Pipeline value:* {pipeline_value}"),
        _div(),
        _sec(f"*Coverage gaps:*\n{gaps or '_None detected_'}"),
        _div(),
        _sec(f"*Recommended actions:*\n{actions}"),
        _ctx("_GTM report by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Executive Report ──────────────────────────────────────────────────────────

@tool("Post Executive Report to Slack")
def post_exec(health_dashboard: str, sprint_status: str, compliance: str,
              risks: str, wins: str) -> str:
    """
    Posts the weekly executive report to #pm-exec-updates. Template enforced.
    Do NOT use generic 'post' — use this for the exec report.

    health_dashboard: traffic light status per dimension (engineering, GTM, compliance, etc.)
    sprint_status: sprint progress summary (tasks done, SP, % complete)
    compliance: compliance health summary
    risks: top 3 risks with owner and mitigation
    wins: wins this week
    """
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["exec"], "Weekly Status Report", [
        _hdr(f"📊 CareSpace Weekly Status — {today}"),
        _sec(f"*Health Dashboard*\n{health_dashboard}"),
        _div(),
        _sec(f"*Sprint Status*\n{sprint_status}"),
        _div(),
        _sec(f"*Compliance*\n{compliance}"),
        _div(),
        _sec(f"*Top Risks*\n{risks}"),
        _div(),
        _sec(f"*Wins This Week*\n{wins}"),
        _ctx("_Executive report by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Compliance ────────────────────────────────────────────────────────────────

@tool("Post Compliance Report to Slack")
def post_compliance(vanta_health: str, open_tasks: str,
                    critical_findings: str, status_summary: str) -> str:
    """
    Posts the daily compliance health report to #pm-compliance as ONE message.
    Template enforced — just pass content for each section.

    vanta_health: Vanta status (e.g., 'GREEN — 0 critical issues' or 'RED — 3 critical')
    open_tasks: open compliance task count and sample
    critical_findings: bullet list of critical findings (or 'None')
    status_summary: one-line status (e.g., 'Vanta Health: GREEN | Tasks: 268 | Alerts: 0')
    """
    today = date.today().strftime("%B %d, %Y")
    health_upper = vanta_health.split("—")[0].strip().upper() if "—" in vanta_health else vanta_health.upper()
    emoji = "🟢" if "GREEN" in health_upper else ("🟡" if "YELLOW" in health_upper else "🔴")
    r = _api(SLACK["compliance"], f"Compliance Report {today}", [
        _hdr(f"🔒 Compliance Health — {today}"),
        _sec(f"*{emoji} {vanta_health}*"),
        _div(),
        _sec(f"*Open Compliance Tasks*\n{open_tasks or '_None_'}"),
        _div(),
        _sec(f"*Critical Findings*\n{critical_findings or '_None — all clear_'}"),
        _div(),
        _sec(f"*{status_summary}*"),
        _ctx("_Compliance report by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Customer Success ──────────────────────────────────────────────────────────

@tool("Post Customer Success Alert to Slack")
def post_cs_alert(account_name: str, risk_type: str, detail: str) -> str:
    """Posts a customer success risk alert to #pm-customer-success."""
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["cs"], f"CS Alert: {account_name}", [
        _hdr(f"🧑‍💼 Customer Success — {today}"),
        _sec(
            f"*Account:* {account_name}\n"
            f"*Risk:* {risk_type}\n"
            f"*Detail:* {detail}"
        ),
        _ctx("_CS alert by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})
