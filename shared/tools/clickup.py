"""
tools/clickup.py
All ClickUp @tool functions. Import any of these into any agent.
Covers: read, write, move, assign, alert, doc, audit logging.
"""

import os, json, requests
from datetime import datetime, timedelta
from crewai.tools import tool
from shared.config.context import L, WORKSPACE_ID

BASE = "https://api.clickup.com/api/v2"
PMAP = {"urgent": 1, "high": 2, "normal": 3, "low": 4}

def _h():
    return {"Authorization": os.environ["CLICKUP_API_TOKEN"], "Content-Type": "application/json"}

def _get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=_h(), params=params)
    r.raise_for_status()
    return r.json()

def _post(path, body):
    r = requests.post(f"{BASE}{path}", headers=_h(), json=body)
    r.raise_for_status()
    return r.json()

def _put(path, body):
    r = requests.put(f"{BASE}{path}", headers=_h(), json=body)
    r.raise_for_status()
    return r.json()

def _sp(task):
    for cf in task.get("custom_fields", []):
        if any(k in cf.get("name", "").lower() for k in ["story", "point", "sp", "estimate"]):
            try: return int(float(cf.get("value") or 0))
            except: return 0
    te = task.get("time_estimate") or 0
    return round(int(te) / 240) if te else 0

def _age(task):
    ts = task.get("date_updated") or task.get("date_created")
    if not ts: return 0
    return max(0, (datetime.utcnow() - datetime.utcfromtimestamp(int(ts) / 1000)).days)

def _fmt(t, list_id=None):
    return {
        "id": t["id"],
        "name": t["name"],
        "status": t["status"]["status"].lower(),
        "priority": (t.get("priority") or {}).get("priority", "none"),
        "assignees": [a["username"] for a in t.get("assignees", [])],
        "story_points": _sp(t),
        "stale_days": _age(t),
        "due_date": t.get("due_date"),
        "tags": [x["name"] for x in t.get("tags", [])],
        "url": t.get("url", ""),
        **({"list_id": list_id} if list_id else {}),
    }

def _is_done(status):
    return status.lower() in ("done", "complete", "completed", "closed")


# ---- READ ----

@tool("Get Tasks From List")
def get_tasks(list_id: str, status_filter: str = "", include_closed: bool = False) -> str:
    """
    Fetch all tasks from a ClickUp list.
    list_id: the ClickUp list ID.
    status_filter: comma-separated statuses to include (empty = all).
    include_closed: set True for retro/reporting (includes done/closed tasks).
    Returns JSON array with: id, name, status, priority, assignees, story_points, stale_days, due_date, tags, url.
    """
    data = _get(f"/list/{list_id}/task", {
        "limit": 200,
        "include_closed": "true" if include_closed else "false",
    })
    sf = [s.strip().lower() for s in status_filter.split(",") if s.strip()]
    tasks = data.get("tasks", [])
    if sf:
        tasks = [t for t in tasks if t["status"]["status"].lower() in sf]
    return json.dumps([_fmt(t, list_id) for t in tasks], indent=2)


@tool("Get Tasks From Multiple Lists")
def get_tasks_multi(list_ids: str, status_filter: str = "", include_closed: bool = False) -> str:
    """
    Fetch tasks from multiple ClickUp lists at once.
    list_ids: comma-separated list IDs.
    Returns tasks with list_id attached -- use for cross-space aggregation.
    """
    sf = [s.strip().lower() for s in status_filter.split(",") if s.strip()]
    out = []
    for lid in [x.strip() for x in list_ids.split(",") if x.strip()]:
        try:
            data = _get(f"/list/{lid}/task", {
                "limit": 200,
                "include_closed": "true" if include_closed else "false",
            })
            for t in data.get("tasks", []):
                if sf and t["status"]["status"].lower() not in sf:
                    continue
                out.append(_fmt(t, lid))
        except Exception as e:
            out.append({"list_id": lid, "error": str(e)})
    return json.dumps(out, indent=2)


@tool("Get Unassigned Tasks")
def get_unassigned(list_id: str) -> str:
    """
    Returns all tasks in a list with no assignees.
    Use before running assignment logic to find what needs to be claimed.
    """
    data = _get(f"/list/{list_id}/task", {"limit": 200})
    out = [_fmt(t, list_id) for t in data.get("tasks", []) if not t.get("assignees")]
    return json.dumps(out, indent=2)


@tool("Get Stale Tasks")
def get_stale(list_id: str, days: int = 3) -> str:
    """
    Returns non-done tasks with no update in more than N days.
    These are the silent killers -- marked In Progress but actually stuck.
    days: threshold (default 3 for standup, use 7+ for sprint health check).
    """
    data = _get(f"/list/{list_id}/task", {"limit": 200})
    out = []
    for t in data.get("tasks", []):
        if _is_done(t["status"]["status"]): continue
        age = _age(t)
        if age >= days:
            f = _fmt(t, list_id)
            f["stale_days"] = age
            out.append(f)
    return json.dumps(out, indent=2)


@tool("Get Sprint Velocity")
def get_velocity(sprint_list_id: str) -> str:
    """
    Calculate sprint results: completion rate, velocity, carry-over, per-engineer breakdown.
    Use at end of sprint for retro and next-sprint capacity calculation.
    """
    data = _get(f"/list/{sprint_list_id}/task", {"limit": 200, "include_closed": "true"})
    planned_sp = done_sp = planned_n = done_n = 0
    done, carry, by_eng = [], [], {}

    for t in data.get("tasks", []):
        s = t["status"]["status"]
        sp = _sp(t) or 3
        planned_sp += sp
        planned_n += 1
        for a in t.get("assignees", []):
            k = a["username"]
            by_eng.setdefault(k, {"planned_sp": 0, "done_sp": 0, "planned_n": 0, "done_n": 0})
            by_eng[k]["planned_sp"] += sp
            by_eng[k]["planned_n"] += 1

        if _is_done(s):
            done_sp += sp
            done_n += 1
            done.append(t["name"])
            for a in t.get("assignees", []):
                by_eng[a["username"]]["done_sp"] += sp
                by_eng[a["username"]]["done_n"] += 1
        else:
            carry.append({"name": t["name"], "status": s, "url": t.get("url", "")})

    rate = round(done_n / planned_n * 100, 1) if planned_n else 0
    return json.dumps({
        "planned_tasks": planned_n, "completed_tasks": done_n, "completion_rate_pct": rate,
        "planned_sp": planned_sp, "completed_sp": done_sp,
        "carry_over": carry, "completed": done, "by_engineer": by_eng,
        "next_sprint_recommended_sp": round(done_sp * 0.80),
    }, indent=2)


@tool("Get Team Workload")
def get_workload(list_ids: str) -> str:
    """
    Returns open task count and SP in progress per team member across given lists.
    list_ids: comma-separated list IDs.
    Always call before assigning to avoid overloading engineers.
    """
    wl = {}
    for lid in [x.strip() for x in list_ids.split(",") if x.strip()]:
        try:
            data = _get(f"/list/{lid}/task", {"limit": 200})
            for t in data.get("tasks", []):
                if _is_done(t["status"]["status"]): continue
                for a in t.get("assignees", []):
                    k = a["username"]
                    wl.setdefault(k, {"open_tasks": 0, "sp_in_progress": 0})
                    wl[k]["open_tasks"] += 1
                    wl[k]["sp_in_progress"] += _sp(t) or 3
        except: pass
    return json.dumps(wl, indent=2)


@tool("Get Workspace Members")
def get_members() -> str:
    """
    Returns all workspace members with ClickUp id, username, email.
    Use to map GitHub handles to ClickUp user IDs for task assignment.
    """
    data = _get(f"/team/{WORKSPACE_ID}/member")
    return json.dumps([{
        "id": m.get("user", {}).get("id"),
        "username": m.get("user", {}).get("username"),
        "email": m.get("user", {}).get("email"),
        "role": m.get("role"),
    } for m in data.get("members", [])], indent=2)


# ---- WRITE ----

@tool("Create Task")
def create_task(list_id: str, name: str, description: str,
                priority: str = "normal", assignee_ids: str = "",
                due_date: str = "", tags: str = "") -> str:
    """
    Creates a ClickUp task in the specified list.
    list_id: target list ID (use L dict from context.py).
    priority: urgent / high / normal / low.
    assignee_ids: comma-separated ClickUp numeric user IDs.
    due_date: YYYY-MM-DD.
    tags: comma-separated tag names (must exist in space).
    Returns {task_id, url}.
    """
    body: dict = {
        "name": name,
        "markdown_description": description,
        "priority": PMAP.get(priority, 3),
    }
    if assignee_ids:
        body["assignees"] = [int(i.strip()) for i in assignee_ids.split(",") if i.strip()]
    if due_date:
        body["due_date"] = int(datetime.strptime(due_date, "%Y-%m-%d").timestamp() * 1000)
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    r = _post(f"/list/{list_id}/task", body)
    return json.dumps({"task_id": r["id"], "url": r.get("url", "")})


@tool("Update Task")
def update_task(task_id: str, status: str = "", assignee_id: str = "",
                priority: str = "", due_date: str = "") -> str:
    """
    Updates a task's status, assignee, priority, or due date.
    Only provide the fields you want to change -- omit the rest.
    assignee_id: single ClickUp numeric user ID.
    due_date: YYYY-MM-DD.
    """
    body: dict = {}
    if status:      body["status"] = status
    if assignee_id: body["assignees"] = {"add": [int(assignee_id)]}
    if priority:    body["priority"] = PMAP.get(priority, 3)
    if due_date:    body["due_date"] = int(datetime.strptime(due_date, "%Y-%m-%d").timestamp() * 1000)
    if body:
        _put(f"/task/{task_id}", body)
    return f"Task {task_id} updated: {list(body.keys())}"


@tool("Add Comment to Task")
def add_comment(task_id: str, comment: str, notify: bool = False) -> str:
    """
    Adds a comment to a ClickUp task.
    notify: set True to ping all assignees.
    Use to log AI decisions, cross-link GitHub issues, or explain assignments.
    """
    _post(f"/task/{task_id}/comment", {"comment_text": comment, "notify_all": notify})
    return f"Comment added to {task_id}"


@tool("Move Task to List")
def move_task(task_id: str, target_list_id: str) -> str:
    """
    Moves a task to a different list.
    Primary use: Backlog to Sprint, Sprint to archive after retro.
    """
    _post(f"/task/{task_id}/move", {"list_id": target_list_id})
    return f"Task {task_id} moved to {target_list_id}"


@tool("Create Sprint List")
def create_sprint_list(sprint_name: str, end_date: str) -> str:
    """
    Creates a new sprint list inside the Sprint folder (901317765699).
    sprint_name: e.g. 'Sprint 7 -- Jun 8-Jun 22'
    end_date: YYYY-MM-DD
    Returns {list_id, name}.
    """
    from shared.config.context import FOLDERS
    end = datetime.strptime(end_date, "%Y-%m-%d")
    r = _post(f"/folder/{FOLDERS['sprint']}/list", {
        "name": sprint_name,
        "due_date": int(end.timestamp() * 1000),
    })
    return json.dumps({"list_id": r["id"], "name": r["name"]})


@tool("Create Alert Task")
def create_alert(name: str, description: str, priority: str = "urgent") -> str:
    """
    Creates a task in the Alerts & SLA Watchlist (901326336266).
    Use for: SLA breaches, P0 bugs, blockers, compliance failures, stale PRs >30d.
    This is the human attention queue -- anything here needs a human decision.
    """
    return create_task(L["alerts_sla"], name, description, priority)


@tool("Write ClickUp Doc Page")
def write_doc_page(document_id: str, page_name: str, content_md: str) -> str:
    """
    Creates a new page in a ClickUp document.
    document_id: e.g. 'xnum1-4273' (Sprint Engine doc).
    content_md: full markdown content.
    Use for: retro reports, sprint summaries, exec reports, compliance logs.
    """
    r = _post(f"/workspaces/{WORKSPACE_ID}/docs/{document_id}/pages", {
        "name": page_name,
        "content": content_md,
        "content_format": "text/md",
    })
    return f"Doc page '{page_name}' created in {document_id} (id={r.get('id', 'ok')})"


@tool("Log Automation Run")
def log_run(crew_name: str, action: str, result: str) -> str:
    """
    Creates an audit log entry in the Automation Rules Registry (901326336259).
    Call at the END of every crew run -- this is how we know what the AI did and when.
    crew_name: name of the crew that ran.
    action: what it did (short summary).
    result: outcome (JSON string or plain text summary).
    """
    from datetime import date
    name = f"[{date.today().isoformat()}] {crew_name}: {action[:70]}"
    desc = (
        f"**Crew:** {crew_name}\n"
        f"**Action:** {action}\n"
        f"**Result:** {result}\n"
        f"**UTC Timestamp:** {datetime.utcnow().isoformat()}"
    )
    return create_task(L["automation_registry"], name, desc, priority="low")
