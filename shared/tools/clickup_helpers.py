"""
tools/clickup_helpers.py
Helper tools that wrap ClickUp MCP search to provide list-level task queries
and duplicate detection. These complement the MCP-injected ClickUp tools.
"""

import os, json
from crewai.tools import tool
from shared.config.context import L, WORKSPACE_ID, SP_ESTIMATE


def _clickup_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    """Direct ClickUp API v2 call for operations MCP doesn't expose."""
    import urllib.request
    token = os.environ.get("CLICKUP_PERSONAL_TOKEN", "")
    url = f"https://api.clickup.com/api/v2/{endpoint}"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


@tool("Get Tasks By List")
def get_tasks_by_list(list_id: str, status: str = "", include_closed: bool = False) -> str:
    """
    Returns all tasks in a ClickUp list. Use list IDs from shared.config.context.L.
    status: optional filter — 'to do', 'in progress', 'complete', etc.
    include_closed: if True, also returns closed/done tasks.
    Returns: id, name, status, assignees, priority, due_date, tags, url.
    """
    try:
        params = f"?archived=false&include_closed={str(include_closed).lower()}"
        if status:
            params += f"&statuses[]={status}"
        data = _clickup_api(f"list/{list_id}/task{params}")
        tasks = data.get("tasks", [])
        out = []
        for t in tasks:
            out.append({
                "id": t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status", "unknown"),
                "assignees": [
                    {"id": a["id"], "username": a.get("username", "")}
                    for a in t.get("assignees", [])
                ],
                "priority": t.get("priority", {}).get("priority", "none") if t.get("priority") else "none",
                "points": t.get("points"),
                "due_date": t.get("due_date"),
                "tags": [tag["name"] for tag in t.get("tags", [])],
                "date_updated": t.get("date_updated"),
                "url": t.get("url", ""),
            })
        return json.dumps(out, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Check Duplicate Task")
def check_duplicate_task(title_fragment: str, list_id: str = "") -> str:
    """
    Searches ClickUp for tasks matching a title fragment to prevent duplicates.
    Returns matching tasks with id, name, list, status, url.
    Use before creating a new task to verify it doesn't already exist.
    list_id: optional — restrict search to a specific list.
    """
    try:
        params = f"list/{list_id}/task?archived=false" if list_id else None
        if params:
            data = _clickup_api(params)
            tasks = data.get("tasks", [])
            fragment_lower = title_fragment.lower()
            matches = [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "status": t.get("status", {}).get("status", "unknown"),
                    "url": t.get("url", ""),
                }
                for t in tasks
                if fragment_lower in t["name"].lower()
            ]
        else:
            # Search across workspace
            search_url = f"team/{WORKSPACE_ID}/task?search={title_fragment}&archived=false"
            data = _clickup_api(search_url)
            tasks = data.get("tasks", [])
            matches = [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "list": t.get("list", {}).get("name", "unknown"),
                    "status": t.get("status", {}).get("status", "unknown"),
                    "url": t.get("url", ""),
                }
                for t in tasks
            ]
        return json.dumps({
            "query": title_fragment,
            "found": len(matches),
            "matches": matches,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _estimate_sp(name: str, priority: str) -> int:
    """Heuristic SP estimate from task name and priority."""
    nl = name.lower()
    if any(w in nl for w in ["security", "vulnerability", "cve", "rbac", "bypass"]):
        return SP_ESTIMATE["security"]
    if any(w in nl for w in ["bug", "fix", "broken", "error", "crash"]):
        if priority in ("urgent", "high"):
            return SP_ESTIMATE["bug_high"]
        if priority == "low":
            return SP_ESTIMATE["bug_low"]
        return SP_ESTIMATE["bug_medium"]
    if any(w in nl for w in ["feature", "implement", "add", "new", "build", "create"]):
        if any(w in nl for w in ["pipeline", "engine", "full", "system", "architecture"]):
            return SP_ESTIMATE["feature_large"]
        if any(w in nl for w in ["page", "component", "endpoint", "api", "screen"]):
            return SP_ESTIMATE["feature_medium"]
        return SP_ESTIMATE["feature_small"]
    if any(w in nl for w in ["pr #", "review", "stale"]):
        return SP_ESTIMATE["pr_review"]
    if any(w in nl for w in ["ci", "pipeline", "deploy", "build"]):
        return SP_ESTIMATE["ci_fix"]
    return SP_ESTIMATE["feature_small"]  # default


@tool("Auto-Estimate Story Points")
def auto_estimate_sp(list_id: str, dry_run: bool = True) -> str:
    """
    Estimates story points for tasks without SP in a given list.
    dry_run=True (default): shows estimates without updating.
    dry_run=False: writes SP to ClickUp tasks via API.
    Returns: task name, current_sp, estimated_sp, updated (bool).
    """
    try:
        data = _clickup_api(f"list/{list_id}/task?archived=false")
        tasks = data.get("tasks", [])
        results = []
        for t in tasks:
            current_sp = t.get("points")
            if current_sp is not None:
                results.append({"name": t["name"], "current_sp": current_sp, "action": "skipped"})
                continue
            pri = t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal"
            est = _estimate_sp(t["name"], pri)
            if not dry_run:
                _clickup_api(f"task/{t['id']}", method="PUT", payload={"points": est})
            results.append({
                "name": t["name"],
                "estimated_sp": est,
                "updated": not dry_run,
            })
        total_est = sum(r.get("estimated_sp", r.get("current_sp", 0)) or 0 for r in results)
        return json.dumps({
            "list_id": list_id,
            "tasks_processed": len(results),
            "total_sp": total_est,
            "dry_run": dry_run,
            "results": results,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
