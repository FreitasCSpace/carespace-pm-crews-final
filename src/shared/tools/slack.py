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

    # Slack section blocks have a 3000 char limit — truncate long fields
    def _trim(text: str, limit: int = 2800) -> str:
        if not text or len(text) <= limit:
            return text
        # Cut at last newline before limit to keep bullets clean
        cut = text[:limit].rfind("\n")
        if cut < limit // 2:
            cut = limit
        return text[:cut] + "\n_(truncated — too many items)_"

    blocks = [
        _hdr(f"📊 Sprint Digest — {today}"),
        _sec(f"*Executive Summary*\n{_trim(executive_summary)}"),
        _div(),
    ]

    # Sprint status — only add sections that have content
    if done and done.strip() and done.strip().lower() != "none":
        blocks.append(_sec(f"*✅ Done*\n{_trim(done)}"))
        blocks.append(_div())
    if in_progress and in_progress.strip() and in_progress.strip().lower() != "none":
        blocks.append(_sec(f"*🔄 In Progress*\n{_trim(in_progress)}"))
        blocks.append(_div())
    if blocked and blocked.strip() and blocked.strip().lower() != "none":
        blocks.append(_sec(f"*🚫 Blocked*\n{_trim(blocked)}"))
        blocks.append(_div())
    if pending and pending.strip() and pending.strip().lower() != "none":
        blocks.append(_sec(f"*⏳ To Do*\n{_trim(pending)}"))
        blocks.append(_div())

    # Task health (unified attention + risks)
    blocks.append(_sec(f"*⚠️ Task Health*\n{_trim(attention) or '_All tasks healthy ✅_'}"))
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


@tool("Post Sprint Status to Slack")
def post_sprint_status(headline: str, detail: str) -> str:
    """
    Posts a sprint status message to #pm-sprint-board using the same
    Block Kit format as post_sprint_plan. Use this for status messages
    like "sprint is active" or "no candidates" — NOT for sprint plans.

    headline: one-line status, e.g. "Sprint 1 — Active until Apr 12"
    detail: body text with context, e.g. "3 Sprint Candidates being collected for next sprint."
    """
    r = _api(SLACK["sprint"], headline, [
        _hdr(f"📅 {headline}"),
        _div(),
        _sec(detail),
        _ctx("_Sprint plan by CareSpace PM AI_"),
    ])
    return json.dumps({"ok": r.get("ok")})


def _trunc(text: str, max_chars: int = 2800) -> str:
    """Truncate text to Slack's block limit (3000 chars). Adds note if cut."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n_… (truncated — see ClickUp for full details)_"


@tool("Post Triage Summary to Slack")
def post_triage_summary(backlog_snapshot: str, hygiene_actions: str,
                        design_tasks: str, aging_items: str,
                        priority_distribution: str) -> str:
    """
    Posts a structured backlog health report to #pm-engineering.
    Template enforced — do NOT use the generic 'post' tool.

    backlog_snapshot: one-line totals, e.g.:
      '342 tasks | 12 bugs | 45 features | 280 compliance | 5 other'
    hygiene_actions: bullet list of what triage did this run, e.g.:
      '• 3 duplicates removed
       • 5 tasks estimated (SP set)
       • 2 priorities adjusted (normal → high)'
      Or 'Backlog clean — no actions needed' if nothing changed.
    design_tasks: unused (kept for compatibility) — pass empty string ''
    aging_items: bullet list of backlog items >21d with no updates, e.g.:
      '• [BUG] Login crash — urgent — 28d old
       • [FEATURE] Export PDF — normal — 35d old'
      Or 'None — all items fresh' if no aging items.
    priority_distribution: compact breakdown, e.g.:
      'Urgent: 3 | High: 12 | Normal: 280 | Low: 47'
    """
    today = date.today().strftime("%B %d, %Y")
    blocks = [
        _hdr(f"📋 Backlog Health — {today}"),
        _sec(f"*{backlog_snapshot}*"),
        _div(),
        _sec(_trunc(f"*🔧 Hygiene Actions*\n{hygiene_actions or '_No actions needed_'}")),
        _div(),
        _sec(_trunc(f"*⏳ Aging Items (>21d)*\n{aging_items or '_All items fresh_'}")),
        _div(),
        _sec(f"*📊 Priority Distribution*\n{priority_distribution}"),
        _ctx("_Backlog health by CareSpace PM AI_"),
    ]
    r = _api(SLACK["engineering"], f"Backlog Health {today}", blocks)
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



# ── Huddle Notes ─────────────────────────────────────────────────────────────

_user_name_cache: dict[str, str] = {}


def _resolve_user_names(text: str) -> str:
    """Replace Slack user IDs (@U0497770PL2) with real names."""
    import re
    headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"}
    user_ids = set(re.findall(r'@(U[A-Z0-9]{8,})', text))
    for uid in user_ids:
        if uid in _user_name_cache:
            text = text.replace(f'@{uid}', _user_name_cache[uid])
            continue
        try:
            resp = requests.get(
                "https://slack.com/api/users.info",
                headers=headers,
                params={"user": uid},
                timeout=5,
            )
            data = resp.json()
            if data.get("ok"):
                user = data["user"]
                name = (user.get("real_name") or user.get("profile", {}).get("real_name")
                        or user.get("name") or uid)
                _user_name_cache[uid] = name
                text = text.replace(f'@{uid}', name)
        except Exception:
            pass
    return text


def _resolve_channel_id(channel_name: str) -> str | None:
    """Resolve a channel name (#foo or foo) to a Slack channel ID."""
    import logging
    log = logging.getLogger(__name__)
    name = channel_name.lstrip("#")
    headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"}
    cursor = ""
    while True:
        params = {"types": "public_channel,private_channel", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = requests.get(
                "https://slack.com/api/conversations.list",
                headers=headers, params=params, timeout=15,
            )
            data = resp.json()
            for ch in data.get("channels", []):
                if ch.get("name") == name:
                    return ch["id"]
            cursor = data.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                break
        except Exception as e:
            log.warning("Channel resolve failed: %s", e)
            break
    return None


@tool("fetch_huddle_notes")
def fetch_huddle_notes(channel: str = "#carespace-team", lookback_hours: int = 168) -> str:
    """
    Fetches Slack huddle notes from the last 7 days and resolves user IDs to real names.
    Returns ALL huddles found — the crew deduplicates against the vault.

    channel: Slack channel name (default #carespace-team)
    lookback_hours: how far back to search (default 168h = 7 days)
    """
    import time as _time
    from datetime import datetime
    import logging
    log = logging.getLogger(__name__)

    headers = {
        "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}",
    }

    # Resolve channel name to ID
    channel_id = _resolve_channel_id(channel)
    if not channel_id:
        return json.dumps({"error": f"Could not find channel {channel}"})

    oldest = str(_time.time() - lookback_hours * 3600)
    oldest_ts = int(float(oldest))
    seen_ts = set()  # Dedup across both methods
    huddles = []

    # ── Method 1: Search Slack files for huddle canvases ──
    try:
        files_resp = requests.get(
            "https://slack.com/api/files.list",
            headers=headers,
            params={
                "channel": channel_id,
                "ts_from": oldest_ts,
                "types": "canvas,quip",
                "count": 50,
            },
            timeout=15,
        )
        files_data = files_resp.json()
        if not files_data.get("ok"):
            log.debug("files.list failed: %s — falling back to channel history", files_data.get("error"))
        for f in files_data.get("files", []):
            title = f.get("title", "")
            if "huddle" not in title.lower():
                continue
            file_id = f.get("id", "")
            # Get full content — quip canvases need url_private download
            content = ""
            try:
                fi_resp = requests.get(
                    "https://slack.com/api/files.info",
                    headers=headers,
                    params={"file": file_id},
                    timeout=10,
                )
                fi_data = fi_resp.json().get("file", {})
                content = fi_data.get("plain_text", "") or fi_data.get("preview", "")
                # Quip canvases have empty plain_text — download via url_private
                if not content and fi_data.get("url_private"):
                    try:
                        dl_resp = requests.get(
                            fi_data["url_private"],
                            headers=headers,
                            timeout=15,
                        )
                        if dl_resp.status_code == 200:
                            # Strip HTML tags for clean text
                            import re
                            html = dl_resp.text
                            # Remove img tags, scripts, styles
                            html = re.sub(r'<(img|script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
                            html = re.sub(r'<img[^>]*/?>', '', html)
                            # Convert common elements to readable text
                            html = re.sub(r'<br\s*/?>', '\n', html)
                            html = re.sub(r'<hr[^>]*/?>', '\n---\n', html)
                            html = re.sub(r'<li[^>]*>', '• ', html)
                            html = re.sub(r'<h[12][^>]*>', '\n## ', html)
                            html = re.sub(r'</h[12]>', '\n', html)
                            html = re.sub(r'<h[3-6][^>]*>', '\n### ', html)
                            html = re.sub(r'</h[3-6]>', '\n', html)
                            # Remove remaining tags
                            html = re.sub(r'<[^>]+>', '', html)
                            # Clean up whitespace
                            content = re.sub(r'\n{3,}', '\n\n', html).strip()
                    except Exception:
                        pass
                if not content:
                    content = title
            except Exception:
                content = title

            created = f.get("created", 0)
            try:
                dt = datetime.fromtimestamp(created)
                meeting_date = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                meeting_date = "unknown"

            # Resolve Slack user IDs to real names
            content = _resolve_user_names(content)

            ts_key = str(created)
            if ts_key not in seen_ts:
                seen_ts.add(ts_key)
                huddles.append({
                    "date": meeting_date,
                    "channel": channel,
                    "poster": f.get("user", ""),
                    "text": title,
                    "canvas_content": content[:5000],
                    "ts": ts_key,
                    "source": "files_api",
                })
    except Exception as e:
        log.debug("files.list search failed: %s", e)

    # ── Method 2: Scan channel history for huddle messages ──
    try:
        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params={"channel": channel_id, "oldest": oldest, "limit": 200},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            if not huddles:
                return json.dumps({"error": f"Slack API: {data.get('error', 'unknown')}"})
            # If we already found huddles via files API, continue with those
            return json.dumps({"huddles_found": len(huddles), "huddles": huddles})
        messages = data.get("messages", [])
    except Exception as e:
        if not huddles:
            return json.dumps({"error": f"Failed to fetch channel history: {e}"})
        return json.dumps({"huddles_found": len(huddles), "huddles": huddles})
    for msg in messages:
        msg_text = msg.get("text", "")
        files = msg.get("files", [])
        msg_lower = msg_text.lower()

        is_huddle = False
        canvas_content = ""

        # Detection 1: 🎧 emoji or "huddle notes" in message text
        if "\U0001f3a7" in msg_text or "huddle notes" in msg_lower or "huddle note" in msg_lower:
            is_huddle = True
            canvas_content = msg_text

        # Detection 2: Canvas/quip files (Slack AI huddle summaries)
        for f in files:
            ftype = f.get("filetype", "")
            ftitle = f.get("title", "").lower()
            if ftype in ("quip", "canvas") or "huddle" in ftitle:
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

        # Detection 3: Attachments with huddle references
        if not is_huddle:
            for att in msg.get("attachments", []):
                att_text = (att.get("title", "") + att.get("text", "")).lower()
                if "huddle" in att_text:
                    is_huddle = True
                    canvas_content = att.get("text", "") or att.get("fallback", "")
                    break

        if not is_huddle:
            continue

        # Also fetch thread replies — huddle content may be in the thread
        ts = msg.get("ts", "")
        if not canvas_content or len(canvas_content.strip()) < 50:
            try:
                thread_resp = requests.get(
                    "https://slack.com/api/conversations.replies",
                    headers=headers,
                    params={"channel": channel_id, "ts": ts, "limit": 20},
                    timeout=10,
                )
                replies = thread_resp.json().get("messages", [])
                thread_texts = []
                for r in replies[1:]:  # Skip parent message
                    r_text = r.get("text", "")
                    if r_text:
                        thread_texts.append(r_text)
                    for f in r.get("files", []):
                        file_id = f.get("id")
                        if file_id:
                            try:
                                fr = requests.get(
                                    "https://slack.com/api/files.info",
                                    headers=headers,
                                    params={"file": file_id},
                                    timeout=10,
                                )
                                fd = fr.json().get("file", {})
                                fc = fd.get("plain_text", "") or fd.get("preview", "")
                                if fc:
                                    thread_texts.append(fc)
                            except Exception:
                                pass
                if thread_texts:
                    canvas_content = (canvas_content + "\n\n" + "\n".join(thread_texts)).strip()
            except Exception:
                pass

        try:
            dt = datetime.fromtimestamp(float(ts))
            meeting_date = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            meeting_date = "unknown"

        if ts not in seen_ts:
            seen_ts.add(ts)
            huddles.append({
                "date": meeting_date,
                "channel": channel,
                "poster": msg.get("user", ""),
                "text": msg_text[:500] if msg_text else "",
                "canvas_content": canvas_content[:5000] if canvas_content else "",
                "ts": ts,
                "source": "channel_history",
            })

    if not huddles:
        return json.dumps({"huddles_found": 0, "message": f"No huddle notes in {channel} in last {lookback_hours}h"})

    return json.dumps({"huddles_found": len(huddles), "huddles": huddles})


