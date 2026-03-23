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
    import logging, time as _time
    body = {"channel": channel, "text": text}
    if blocks:
        body["blocks"] = blocks
    headers = {
        "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}",
        "Content-Type": "application/json",
    }
    log = logging.getLogger(__name__)
    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json=body,
            )
            data = r.json()
            if data.get("ok"):
                return data
            # Slack returned ok:false — log and retry (may be transient)
            last_err = data.get("error", "unknown")
            log.warning("Slack API error (attempt %d/3): %s", attempt + 1, last_err)
        except Exception as exc:
            last_err = str(exc)
            log.warning("Slack request failed (attempt %d/3): %s", attempt + 1, last_err)
        if attempt < 2:
            _time.sleep(2 ** attempt)  # 1s, 2s backoff
    # All retries exhausted — return last response or error dict
    log.error("Slack post failed after 3 attempts: %s (channel=%s)", last_err, channel)
    return {"ok": False, "error": last_err}

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
                 blocked: str, pending: str, attention: str,
                 meeting_mode: str, blocker_details: str = "") -> str:
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
    blocker_details: sprint risks — items at risk of not completing on time.
        Include high-SP pending tasks, external dependencies, unassigned urgent items.
        Example: '• ⚡ RBAC Guards (8 SP) — @Fabiano — urgent, not started
        • ⚡ Azure BAA — @Flavio — external dependency, waiting on vendor'
    """
    today = date.today().strftime("%B %d, %Y")
    blocks = [
        _hdr(f"📊 Sprint Digest — {today}"),
        _sec(f"*Executive Summary*\n{executive_summary}"),
        _div(),
        _sec(
            f"*✅ Done*\n{done or '_None_'}\n\n"
            f"*🔄 In Progress*\n{in_progress or '_None_'}\n\n"
            f"*🚫 Blocked*\n{blocked or '_None_'}\n\n"
            f"*⏳ To Do*\n{pending or '_None_'}"
        ),
        _div(),
        _sec(f"*⚠️ Needs Attention*\n{attention or '_All clear_'}"),
        _div(),
    ]
    # Add sprint risks section if there are items at risk
    if blocker_details and blocker_details.strip():
        blocks.append(_sec(f"*⚡ Sprint Risks*\n{blocker_details}"))
        blocks.append(_div())
    blocks.append(_sec(f"*🎯 Meeting Mode*\n{meeting_mode}"))
    blocks.append(_ctx("_Posted by CareSpace PM AI_"))

    r = _api(SLACK["standup"], f"Sprint Digest {today}", blocks)
    return json.dumps({"ok": r.get("ok")})


# ── Sprint Plan ───────────────────────────────────────────────────────────────

@tool("Post Sprint Plan to Slack")
def post_sprint_plan(sprint_list_id: str) -> str:
    """
    Posts the sprint planning results to #pm-sprint-board.
    Fetches sprint name and tasks directly from ClickUp — only list ID needed.
    sprint_list_id: ClickUp list ID of the sprint to post about
    """
    from shared.tools.clickup_helpers import _clickup_api
    from shared.config.context import SP_CUSTOM_FIELD_ID

    # Fetch list name (= sprint name) and tasks directly from ClickUp
    list_info = _clickup_api(f"list/{sprint_list_id}")
    sprint_name = list_info.get("name", sprint_list_id)
    data = _clickup_api(f"list/{sprint_list_id}/task?archived=false")
    tasks = data.get("tasks", [])

    total_sp = 0
    lines = []
    for t in tasks:
        assignees = [a.get("username", "?") for a in t.get("assignees", [])]
        assignee_str = ", ".join(assignees) if assignees else "unassigned"
        sp = next((cf.get("value") for cf in t.get("custom_fields", [])
                    if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), "?")
        if sp != "?":
            total_sp += int(sp)
        url = t.get("url", "")
        name_link = f"<{url}|{t['name']}>" if url else t['name']
        lines.append(f"• *{name_link}*  →  _{assignee_str}_  `{sp} SP`")

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


def _trunc(text: str, max_chars: int = 2800) -> str:
    """Truncate text to Slack's block limit (3000 chars). Adds note if cut."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n_… (truncated — see ClickUp for full details)_"


@tool("Post Triage Summary to Slack")
def post_triage_summary(priorities_set: str, assignments: str,
                        story_points: str, alerts: str, reasoning: str) -> str:
    """
    Posts a structured triage summary to #pm-engineering. Template enforced.
    USE THIS for triage results — not the generic 'post' tool.
    Do NOT add separators or headers — the tool handles formatting.

    priorities_set: bullet list of priority changes (or 'None')
    assignments: bullet list of assignments made (or 'None')
    story_points: summary of SP set (or 'None')
    alerts: bullet list of alerts created (or 'None')
    reasoning: why these decisions were made
    """
    today = date.today().strftime("%B %d, %Y")
    blocks = [
        _hdr(f"🔍 Triage Report — {today}"),
        _sec(_trunc(f"*Priorities Changed*\n{priorities_set or '_None_'}")),
        _sec(_trunc(f"*Story Points Set*\n{story_points or '_None_'}")),
        _div(),
        _sec(_trunc(f"*Alerts Created*\n{alerts or '_None_'}")),
        _div(),
        _sec(_trunc(f"*Reasoning*\n{reasoning}")),
        _ctx("_Triage by CareSpace PM AI_"),
    ]
    r = _api(SLACK["engineering"], f"Triage Report {today}", blocks)
    return json.dumps({"ok": r.get("ok")})


_pr_radar_posted = False
_exec_posted = False


@tool("post_pr_radar_report")
def post_pr_radar(stale_prs: str, critical_prs: str, ci_status: str,
                  summary: str) -> str:
    """
    Posts the PR & CI radar report to #pm-engineering. Template enforced.
    Do NOT use the generic 'post' tool — use this instead.

    stale_prs: bullet list of stale PRs with age and link
    critical_prs: bullet list of critical stale PRs (>30d)
    ci_status: CI status summary (failures or 'All passing ✅')
    summary: one-line totals (e.g. '5 stale PRs, 1 critical, 0 CI failures')
    """
    global _pr_radar_posted
    today = date.today().strftime("%B %d, %Y")

    # In-process dedup — never post twice in the same run
    if _pr_radar_posted:
        return json.dumps({"ok": True, "skipped": "already_posted_this_run"})

    # Slack history dedup — only one PR radar per day.
    try:
        import time as _time
        dedup_resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"},
            params={"channel": SLACK["engineering"], "oldest": str(_time.time() - 3600 * 4), "limit": 20},
            timeout=10,
        )
        for msg in dedup_resp.json().get("messages", []):
            if f"PR Radar {today}" in msg.get("text", ""):
                _pr_radar_posted = True
                return json.dumps({"ok": False, "skipped": "already_posted_today"})
    except Exception:
        pass  # If dedup check fails, proceed with posting

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
        _ctx("_PR Radar by CareSpace PM AI_"),
    ])
    _pr_radar_posted = True
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

@tool("post_executive_report")
def post_exec(health_dashboard: str, key_metrics: str, sprint_analysis: str,
              compliance: str, gtm: str, risks: str, wins: str,
              decisions_needed: str = "") -> str:
    """
    Posts the weekly executive report to #pm-exec-updates. Template enforced.
    Do NOT use generic 'post' — use this for the exec report.

    health_dashboard: one-line traffic light per dimension with key number, e.g.:
      '🔴 Engineering: 0% (0/46 SP) | 🟢 GTM: $0 at risk | 🔴 Compliance: 51% pass rate | 🟡 CS: no data | 🟢 Bugs: 0 open'

    key_metrics: 3-5 bullet KPIs the CEO/CTO needs at a glance, e.g.:
      '• Sprint velocity: 0/46 SP delivered (0%) — sprint starts tomorrow
       • Backlog: 332 tasks | 1 open bug
       • Compliance pass rate: 51% (target: 95%) — 13 critical controls failing
       • GTM: 0 deals at risk | pipeline healthy'

    sprint_analysis: detailed sprint breakdown with per-engineer status, e.g.:
      'Sprint 1 — Mar 23 to Apr 05 (Day 0 of 14)
       • 0 done | 0 in progress | 8 to do | 0 blocked
       • 0/46 SP delivered
       Engineer breakdown:
       — Fabiano: RBAC Guards (8 SP) + Auth middleware (5 SP) → to do
       — Bharath: Production Readiness (8 SP) → to do
       — Andre: Cover Images ×2 + Pre-Existing Conditions (15 SP) → to do
       — Sandeep: Vanta API (5 SP) → to do
       — Luis: Employee exit evidence (5 SP) → to do'

    compliance: compliance analysis with business impact, e.g.:
      'Vanta: RED — 51% test pass rate (target: 95%)
       • 13 critical controls failing — SOC 2 audit at risk
       • BAA gaps: Azure + Google Workspace → PHI processing legally blocked
       • 20+ HIPAA evidence items overdue → breach notification risk
       • 282 open compliance tasks in backlog
       Impact: audit readiness blocked until BAA + evidence gaps resolved'

    gtm: GTM pipeline analysis, e.g.:
      '• 0 deals at risk
       • Pipeline: [value if available]
       • No launches within 14 days'

    risks: top risks with business impact + owner + mitigation, e.g.:
      '1. 🔴 BAA gap — Azure + Google Workspace
          Impact: PHI processing legally blocked → HIPAA violation exposure
          Owner: Luis | Action: Escalate to Azure/Google account teams this week
       2. 🔴 SOC 2 controls failing (13 critical)
          Impact: audit readiness at risk → customer trust + enterprise sales blocked
          Owner: Luis + Sandeep | Action: Vanta remediation sprint
       3. 🟡 RBAC Guards bypassed (admin#80, 8 SP)
          Impact: authorization checks returning true — security vulnerability in prod
          Owner: Fabiano | Action: P0 — patch this sprint'

    wins: concrete wins with business relevance, e.g.:
      '• Sprint 1 fully staffed: 8 tasks, 46 SP, all assigned (100%)
       • No GTM deals at risk — pipeline healthy
       • Intake + triage crews running autonomously daily'

    decisions_needed: items requiring CEO/CTO action or decision (omit if none), e.g.:
      '• BAA with Azure — needs executive escalation to account team
       • SOC 2 remediation resourcing — Sandeep at capacity, may need additional help'
    """
    global _exec_posted
    today = date.today().strftime("%B %d, %Y")

    # In-process dedup — never post twice in the same run
    if _exec_posted:
        return json.dumps({"ok": True, "skipped": "already_posted_this_run"})

    # Slack history dedup — only one exec report per day.
    try:
        import time as _time
        dedup_resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"},
            params={"channel": SLACK["exec"], "oldest": str(_time.time() - 3600 * 4), "limit": 20},
            timeout=10,
        )
        for msg in dedup_resp.json().get("messages", []):
            if f"CareSpace Weekly Status — {today}" in msg.get("text", ""):
                _exec_posted = True
                return json.dumps({"ok": False, "skipped": "already_posted_today"})
    except Exception:
        pass  # If dedup check fails, proceed with posting

    blocks = [
        _hdr(f"📊 CareSpace Weekly Status — {today}"),
        _sec(health_dashboard),
        _div(),
        _sec(f"*📈 Key Metrics*\n{key_metrics}"),
        _div(),
        _sec(f"*🏗️ Sprint Analysis*\n{sprint_analysis}"),
        _div(),
        _sec(f"*🔒 Compliance*\n{compliance}"),
        _div(),
        _sec(f"*💰 GTM Pipeline*\n{gtm}"),
        _div(),
        _sec(f"*⚡ Top Risks*\n{risks}"),
        _div(),
        _sec(f"*🏆 Wins This Week*\n{wins}"),
    ]
    if decisions_needed and decisions_needed.strip():
        blocks.append(_div())
        blocks.append(_sec(f"*🔴 Decisions Needed*\n{decisions_needed}"))
    blocks.append(_ctx("_Executive report by CareSpace PM AI_"))
    r = _api(SLACK["exec"], f"CareSpace Weekly Status — {today}", blocks)
    _exec_posted = True
    return json.dumps({"ok": r.get("ok")})


# ── Engineer DM Notifications ─────────────────────────────────────────────────

_slack_user_cache: dict | None = None

def _resolve_slack_id(display_name: str) -> str:
    """Resolve a Slack display name to a user ID via users.list. Cached per process."""
    global _slack_user_cache
    if _slack_user_cache is None:
        _slack_user_cache = {}
        try:
            resp = requests.get(
                "https://slack.com/api/users.list",
                headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"},
                timeout=15,
            )
            for member in resp.json().get("members", []):
                if member.get("deleted") or member.get("is_bot"):
                    continue
                uid = member["id"]
                profile = member.get("profile", {})
                for field in ("display_name", "real_name", "name"):
                    val = (profile.get(field) or member.get(field, "")).strip().lower()
                    if val:
                        _slack_user_cache[val] = uid
        except Exception:
            pass
    return _slack_user_cache.get(display_name.strip().lower(), "")


@tool("notify_task_assignee")
def notify_task_assignee(task_id: str, message: str) -> str:
    """
    Sends a Slack DM to the assignee(s) of a ClickUp task.
    Use for SLA breach alerts and blocker notifications so engineers
    are informed directly, not just via channel posts.

    task_id: ClickUp task ID
    message: what to tell the engineer (e.g. 'Your task has breached SLA — please update status or flag a blocker.')
    """
    from shared.config.context import CU_TO_SLACK_NAME
    import urllib.request as _req

    # Fetch task to get assignees and name
    try:
        cu_token = os.environ.get("CLICKUP_PERSONAL_TOKEN", os.environ.get("CLICKUP_API_TOKEN", ""))
        req = _req.Request(
            f"https://api.clickup.com/api/v2/task/{task_id}",
            headers={"Authorization": cu_token},
        )
        with _req.urlopen(req, timeout=15) as resp:
            task = json.loads(resp.read().decode())
    except Exception as e:
        return json.dumps({"ok": False, "error": f"Failed to fetch task: {e}"})

    task_name = task.get("name", task_id)
    assignees  = task.get("assignees", [])

    sent, skipped = [], []
    for a in assignees:
        cu_id      = str(a.get("id", ""))
        username   = a.get("username", cu_id)
        slack_name = CU_TO_SLACK_NAME.get(cu_id, "")

        if not slack_name:
            skipped.append(f"{username} (no slack_name mapped)")
            continue

        slack_uid = _resolve_slack_id(slack_name)
        if not slack_uid:
            skipped.append(f"{username} ('{slack_name}' not found in workspace)")
            continue

        r = _api(slack_uid, f"🔔 *{task_name}*\n{message}")
        if r.get("ok"):
            sent.append(username)
        else:
            skipped.append(f"{username}: {r.get('error', 'unknown')}")

    return json.dumps({"ok": bool(sent), "sent": sent, "skipped": skipped})


# ── Compliance ────────────────────────────────────────────────────────────────

@tool("post_compliance_report")
def post_compliance(health_headline: str, changes_section: str,
                    needs_action_section: str, sprint_compliance_section: str,
                    footer_stats: str) -> str:
    """
    Posts the daily delta-based compliance report to #pm-compliance.
    Template enforced — pass preformatted mrkdwn for each section.

    health_headline: e.g. 'RED (5 consecutive days) -- 51% pass rate'
    changes_section: delta since yesterday with links, or 'First run -- no previous data'
    needs_action_section: critical unowned items with links, or 'All critical items have owners'
    sprint_compliance_section: sprint tasks with links, or '' to omit section
    footer_stats: e.g. '282 total | 11 critical | 51% Vanta pass rate'
    """
    today = date.today().strftime("%B %d, %Y")

    # Dedup guard
    try:
        import time as _time
        dedup_resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"},
            params={"channel": SLACK["compliance"], "oldest": str(_time.time() - 3600 * 4), "limit": 20},
            timeout=10,
        )
        for msg in dedup_resp.json().get("messages", []):
            if f"Compliance Health" in msg.get("text", "") and today in msg.get("text", ""):
                return json.dumps({"ok": False, "skipped": "already_posted_today"})
    except Exception:
        pass

    health_upper = health_headline.upper()
    emoji = "\U0001f7e2" if "GREEN" in health_upper else ("\U0001f7e1" if "YELLOW" in health_upper else "\U0001f534")

    blocks = [
        _hdr(f"\U0001f512 Compliance Health \u2014 {today}"),
        _sec(f"*{emoji} {health_headline}*"),
        _div(),
        _sec(f"*\U0001f4ca Changes Since Yesterday*\n{_trunc(changes_section) or '_No data_'}"),
        _div(),
        _sec(f"*\U0001f6a8 Needs Action*\n{_trunc(needs_action_section) or '_All clear_'}"),
    ]
    if sprint_compliance_section:
        blocks.append(_div())
        blocks.append(_sec(f"*\U0001f3c3 Sprint Compliance*\n{_trunc(sprint_compliance_section)}"))
    blocks.extend([
        _div(),
        _sec(f"*\U0001f4c8 {footer_stats}*"),
        _ctx("_Compliance report by CareSpace PM AI_"),
    ])

    r = _api(SLACK["compliance"], f"Compliance Health {today}", blocks)
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


@tool("post_cs_summary")
def post_cs_summary(onboarding_health: str, support_health: str,
                    churn_risks: str, actions_taken: str) -> str:
    """
    Posts a daily customer success summary to #pm-customer-success.
    Only call this if there are actual issues to report — skip if healthy.

    onboarding_health: e.g. '5 active, 1 stale (>7d), 0 unowned'
    support_health: e.g. '3 open tickets, 1 unresponsive (>24h), 0 stale'
    churn_risks: details of flagged accounts, or 'None detected'
    actions_taken: alerts created, feedback routed, etc.
    """
    today = date.today().strftime("%B %d, %Y")
    r = _api(SLACK["cs"], f"CS Summary {today}", [
        _hdr(f"🧑‍💼 Customer Success Summary — {today}"),
        _sec(
            f"*Onboarding Health*\n{onboarding_health}\n\n"
            f"*Support Health*\n{support_health}\n\n"
            f"*Churn Risks*\n{churn_risks}"
        ),
        _div(),
        _sec(f"*Actions Taken*\n{actions_taken}"),
        _ctx("_CS summary by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


# ── Huddle Notes ─────────────────────────────────────────────────────────────

@tool("fetch_huddle_notes")
def fetch_huddle_notes(channel: str = "#carespace-team", lookback_hours: int = 24) -> str:
    """
    Fetches recent Slack huddle notes from a channel.
    Scans conversation history for huddle note messages (Canvas attachments
    posted by Slack AI after a huddle ends).
    Returns structured data: date, attendees, summary, key topics.

    channel: Slack channel to scan (default #carespace-team)
    lookback_hours: how far back to search (default 24h)
    """
    import time as _time
    headers = {
        "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}",
    }
    oldest = str(_time.time() - lookback_hours * 3600)

    try:
        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params={"channel": channel, "oldest": oldest, "limit": 50},
            timeout=15,
        )
        messages = resp.json().get("messages", [])
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch channel history: {e}"})

    huddles = []
    for msg in messages:
        msg_text = msg.get("text", "")
        files = msg.get("files", [])

        is_huddle = False
        canvas_content = ""

        # Check for Canvas files (huddle notes)
        for f in files:
            if f.get("filetype") in ("quip", "canvas") or "huddle" in f.get("title", "").lower():
                is_huddle = True
                file_id = f.get("id")
                if file_id:
                    try:
                        file_resp = requests.get(
                            "https://slack.com/api/files.info",
                            headers=headers,
                            params={"file": file_id},
                            timeout=10,
                        )
                        file_data = file_resp.json().get("file", {})
                        canvas_content = (
                            file_data.get("plain_text", "")
                            or file_data.get("preview", "")
                            or file_data.get("content", "")
                            or f.get("title", "")
                        )
                    except Exception:
                        canvas_content = f.get("title", "")
                break

        # Check message text for huddle indicators
        if not is_huddle and "huddle notes" in msg_text.lower():
            is_huddle = True
            canvas_content = msg_text

        # Check attachments (older format)
        if not is_huddle:
            for att in msg.get("attachments", []):
                if "huddle" in att.get("title", "").lower() or "huddle" in att.get("text", "").lower():
                    is_huddle = True
                    canvas_content = att.get("text", "") or att.get("fallback", "")
                    break

        if not is_huddle:
            continue

        ts = msg.get("ts", "")
        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(float(ts))
            meeting_date = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            meeting_date = "unknown"

        huddles.append({
            "date": meeting_date,
            "channel": channel,
            "poster": msg.get("user", ""),
            "text": msg_text[:500] if msg_text else "",
            "canvas_content": canvas_content[:3000] if canvas_content else "",
            "ts": ts,
        })

    if not huddles:
        return json.dumps({"huddles_found": 0, "message": f"No huddle notes in {channel} in last {lookback_hours}h"})

    return json.dumps({"huddles_found": len(huddles), "huddles": huddles})


@tool("post_huddle_actions")
def post_huddle_actions(meeting_date: str, attendees: str, summary: str,
                        action_items_json: str, decisions: str) -> str:
    """
    Posts a huddle analysis summary with action items to #pm-engineering.
    Call EXACTLY ONCE per huddle.

    meeting_date: e.g. '2026-03-19'
    attendees: comma-separated names e.g. 'Andre, Fabiano, Luis, Camila'
    summary: 2-3 sentence meeting summary
    action_items_json: JSON array of objects with 'name', 'assignee', 'url' keys
    decisions: bullet-point list of decisions, or 'None'
    """
    try:
        items = json.loads(action_items_json) if action_items_json else []
    except (json.JSONDecodeError, TypeError):
        items = []

    if items:
        items_text = "\n".join(
            f"\u2022 {it.get('name', '?')} \u2014 {it.get('assignee', 'unassigned')}"
            + (f" \u2192 <{it['url']}|task>" if it.get("url") else "")
            for it in items
        )
    else:
        items_text = "_No action items identified_"

    blocks = [
        _hdr(f"\U0001f399\ufe0f Huddle Recap \u2014 {meeting_date}"),
        _sec(f"*Attendees:* {attendees}"),
        _div(),
        _sec(f"*Summary*\n{_trunc(summary)}"),
        _div(),
        _sec(f"*\u2705 Action Items ({len(items)} tasks created)*\n{_trunc(items_text)}"),
    ]
    if decisions and decisions.strip().lower() != "none":
        blocks.append(_div())
        blocks.append(_sec(f"*\U0001f4cb Decisions*\n{_trunc(decisions)}"))
    blocks.append(_ctx("_Huddle recap by CareSpace PM AI_"))

    r = _api(SLACK["engineering"], f"Huddle Recap {meeting_date}", blocks)
    return json.dumps({"ok": r.get("ok"), "tasks_created": len(items)})
