"""
tools/clickup_helpers.py
Helper tools that wrap ClickUp MCP search to provide list-level task queries
and duplicate detection. These complement the MCP-injected ClickUp tools.
"""

import os, json, time
from datetime import date, timedelta
from collections import defaultdict
from crewai.tools import tool
from shared.config.context import L, WORKSPACE_ID, SP_ESTIMATE, SPRINT_FOLDER_ID, SP_CUSTOM_FIELD_ID


def _clickup_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    """Direct ClickUp API v2 call for operations MCP doesn't expose."""
    import urllib.request
    token = os.environ.get("CLICKUP_PERSONAL_TOKEN",
            os.environ.get("CLICKUP_API_TOKEN", ""))
    url = f"https://api.clickup.com/api/v2/{endpoint}"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.request.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"HTTP {e.code}: {error_body[:200]}")


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
            # Get SP from custom field (preferred) or native points (fallback)
            sp = t.get("points")
            for cf in t.get("custom_fields", []):
                if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None:
                    sp = int(cf["value"])
                    break

            out.append({
                "id": t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status", "unknown"),
                "assignees": [
                    {"id": a["id"], "username": a.get("username", "")}
                    for a in t.get("assignees", [])
                ],
                "priority": t.get("priority", {}).get("priority", "none") if t.get("priority") else "none",
                "points": sp,
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
            # Search across workspace (URL-encode the search term)
            from urllib.parse import quote
            search_url = f"team/{WORKSPACE_ID}/task?search={quote(title_fragment)}&archived=false"
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


@tool("Update ClickUp Task")
def update_clickup_task(task_id: str, updates: dict) -> str:
    """
    Update a ClickUp task. Supported fields in updates dict:
    - status: str (e.g. "to do", "in progress", "done", "refinement", "qa")
    - priority: int (1=urgent, 2=high, 3=normal, 4=low)
    - assignees: {"add": [user_id], "rem": [user_id]}
    - points: int (story points)
    - due_date: epoch ms
    Returns the updated task summary.
    """
    try:
        result = _clickup_api(f"task/{task_id}", method="PUT", payload=updates)
        return json.dumps({
            "id": result.get("id"),
            "name": result.get("name"),
            "status": result.get("status", {}).get("status"),
            "updated_fields": list(updates.keys()),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Add Tag To Task")
def add_tag_to_task(task_id: str, tag_name: str) -> str:
    """
    Add a tag to a ClickUp task. Tag name is case-insensitive.
    Common tags: compliance-reviewed, hipaa, phi, security, blocker, stale-alert.
    """
    try:
        from urllib.parse import quote
        _clickup_api(f"task/{task_id}/tag/{quote(tag_name)}", method="POST")
        return json.dumps({"task_id": task_id, "tag_added": tag_name})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("create_task_in_list")
def create_clickup_task(list_id: str, name: str, description: str = "",
                        priority: int = 3, assignees: list[int] = None,
                        tags: list[str] = None, points: int = None) -> str:
    """
    Create a new task in a ClickUp list. USE THIS instead of MCP create_click_up_task.
    list_id: target list ID.
    priority: 1=urgent, 2=high, 3=normal, 4=low.
    assignees: list of ClickUp user IDs.
    tags: list of tag name strings.
    points: story points (set via custom field after creation).
    Returns the created task id, name, and url.
    """
    try:
        payload = {"name": name, "priority": priority}
        if description:
            payload["description"] = description
        if assignees:
            payload["assignees"] = assignees
        if tags:
            payload["tags"] = tags
        # Don't set native points (plan limited) — use custom field after
        result = _clickup_api(f"list/{list_id}/task", method="POST", payload=payload)
        task_id = result.get("id")
        # Set SP via custom field if provided
        if points is not None and task_id:
            _set_sp(task_id, points)
        return json.dumps({
            "id": task_id,
            "name": result.get("name"),
            "url": result.get("url"),
            "status": result.get("status", {}).get("status"),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def _move_task_to_sprint(task_id: str, target_list_id: str) -> str | None:
    """Move a task from backlog to sprint by creating a full copy in the
    sprint list and closing the backlog original. Returns the new task ID
    or None on failure.

    ClickUp v2 API does NOT support moving tasks between lists.
    This is the only reliable approach: copy + close.
    """
    try:
        # 1. Get full source task details
        src = _clickup_api(f"task/{task_id}")

        # 2. Create copy in sprint with all metadata
        pri_map = {"urgent": 1, "high": 2, "normal": 3, "low": 4}
        pri = src.get("priority", {}).get("priority", "normal") if src.get("priority") else "normal"
        assignee_ids = [a["id"] for a in src.get("assignees", [])]
        tag_names = [t["name"] for t in src.get("tags", [])]

        new_task = _clickup_api(
            f"list/{target_list_id}/task",
            method="POST",
            payload={
                "name": src["name"],
                "description": src.get("description", ""),
                "priority": pri_map.get(pri, 3),
                "assignees": assignee_ids,
                "tags": tag_names,
            },
        )
        new_id = new_task.get("id")
        if not new_id:
            return None

        # 3. Copy SP custom field to new task
        src_sp = next((cf.get("value") for cf in src.get("custom_fields", [])
                       if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
        if src_sp is not None:
            _set_sp(new_id, int(src_sp))

        # 4. Close backlog original (status: complete)
        _clickup_api(f"task/{task_id}", method="PUT", payload={"status": "complete"})

        return new_id
    except Exception:
        return None


def _assign_task(task_id: str, user_id: str) -> bool:
    """Assign a task to a user. Returns True on success."""
    try:
        _clickup_api(f"task/{task_id}", method="PUT",
                     payload={"assignees": {"add": [int(user_id)]}})
        return True
    except Exception:
        return False


@tool("Scan Backlog For Triage")
def scan_backlog_for_triage() -> str:
    """
    Scans Master Backlog tasks for hygiene issues AND checks the active
    sprint for SLA breaches.

    Backlog scan (hygiene — always relevant):
    - unassigned: tasks with no assignee
    - wrong_priority: tasks that may need priority adjustment
    - no_story_points: tasks missing SP estimates
    - by_tag / by_priority: distribution counts

    Sprint scan (SLA — only for committed work):
    - sla_at_risk: tasks IN THE ACTIVE SPRINT approaching or breaching SLA

    SLA only applies to sprint items because backlog tasks are inventory,
    not committed work. Flagging backlog items as SLA breaches creates noise.
    """
    from shared.config.context import BUG_SLA
    from datetime import datetime

    now_ms = int(datetime.utcnow().timestamp() * 1000)

    summary = {
        "total_tasks": 0,
        "unassigned": [],
        "wrong_priority": [],
        "no_story_points": [],
        "sla_at_risk": [],
        "by_tag": {},
        "by_priority": {},
    }

    try:
        # ── Step 1: Load active sprint task IDs for SLA filtering ────────
        sprint_task_ids = set()
        try:
            # Find active sprint list in the Sprints folder
            folder_data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
            for lst in folder_data.get("lists", []):
                if "sprint" in lst["name"].lower():
                    sprint_data = _clickup_api(
                        f"list/{lst['id']}/task?archived=false&include_closed=false"
                    )
                    for st in sprint_data.get("tasks", []):
                        sprint_task_ids.add(st["id"])
        except Exception:
            pass  # If sprint lookup fails, SLA checks run on nothing (safe)

        summary["sprint_tasks_found"] = len(sprint_task_ids)

        # ── Step 2: Scan Master Backlog for hygiene ──────────────────────
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}")
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        # Also include sprint tasks for SLA check
        all_task_ids = {t["id"] for t in all_tasks}
        for sid in sprint_task_ids:
            if sid not in all_task_ids:
                try:
                    t = _clickup_api(f"task/{sid}")
                    all_tasks.append(t)
                except Exception:
                    pass

        summary["total_tasks"] = len(all_tasks)

        for t in all_tasks:
            tags = [tag["name"] for tag in t.get("tags", [])]
            pri = t.get("priority", {}).get("priority", "none") if t.get("priority") else "none"
            assignees = t.get("assignees", [])
            points = t.get("points")
            created_ms = int(t.get("date_created", "0"))
            age_hours = round((now_ms - created_ms) / (1000 * 3600), 1) if created_ms else 0
            name = t["name"]

            # Count by tag and priority
            for tag in tags:
                summary["by_tag"][tag] = summary["by_tag"].get(tag, 0) + 1
            summary["by_priority"][pri] = summary["by_priority"].get(pri, 0) + 1

            task_info = {
                "id": t["id"],
                "name": name[:100],
                "tags": tags,
                "priority": pri,
                "age_hours": age_hours,
                "has_sp": points is not None,
                "assignee_count": len(assignees),
            }

            # Unassigned tasks (backlog hygiene — always relevant)
            if not assignees:
                summary["unassigned"].append(task_info)

            # No story points (backlog hygiene — always relevant)
            if points is None:
                summary["no_story_points"].append({"id": t["id"], "name": name[:80], "priority": pri})

            # SLA at risk — ONLY for tasks in the active sprint
            if t["id"] in sprint_task_ids:
                sla_hours = BUG_SLA.get(pri, 168)
                if age_hours > sla_hours * 0.8:  # 80% of SLA = at risk
                    task_info["sla_hours"] = sla_hours
                    task_info["breached"] = age_hours > sla_hours
                    task_info["in_sprint"] = True
                    summary["sla_at_risk"].append(task_info)

            # Potential wrong priority (AI should verify)
            name_lower = name.lower()
            if pri not in ("urgent",):
                if "security" in tags:
                    summary["wrong_priority"].append({**task_info, "reason": "security tag but not urgent"})
                elif any(w in name_lower for w in ["crash", "data loss", "breach", "unauthorized"]):
                    summary["wrong_priority"].append({**task_info, "reason": f"title suggests critical issue"})
                elif any(w in name_lower for w in ["hipaa", "phi", "baa gap"]):
                    summary["wrong_priority"].append({**task_info, "reason": "HIPAA/PHI related, may need urgent"})

        # Truncate lists if too long (keep it manageable for LLM)
        if len(summary["unassigned"]) > 30:
            summary["unassigned_total"] = len(summary["unassigned"])
            summary["unassigned"] = summary["unassigned"][:30]
            summary["unassigned_truncated"] = True
        if len(summary["no_story_points"]) > 30:
            summary["no_sp_total"] = len(summary["no_story_points"])
            summary["no_story_points"] = summary["no_story_points"][:30]
            summary["no_sp_truncated"] = True
        if len(summary["sla_at_risk"]) > 20:
            summary["sla_total"] = len(summary["sla_at_risk"])
            summary["sla_at_risk"] = summary["sla_at_risk"][:20]

    except Exception as e:
        summary["error"] = str(e)

    return json.dumps(summary, indent=2)


@tool("Execute Triage Actions")
def execute_triage_actions(actions_json: str) -> str:
    """
    Executes triage actions decided by the AI agent. Takes a JSON string
    with arrays of actions to perform.

    Expected format:
    {
      "set_priority": [{"task_id": "xxx", "priority": 1, "reason": "..."}],
      "assign": [{"task_id": "xxx", "user_id": "12345", "reason": "..."}],
      "set_sp": [{"task_id": "xxx", "points": 5}],
      "create_alerts": [{"name": "...", "description": "...", "priority": 1, "tags": ["compliance", "hipaa"]}]
    }

    ALERT TAGS: Always include relevant tags on alerts for filtering.
    Common tags: compliance, hipaa, soc2, security, frontend, backend,
    mobile, infra, github, vanta, urgent.
    Alerts do NOT get story points — they are notifications, not work items.

    priority: 1=urgent, 2=high, 3=normal, 4=low
    user_id: ClickUp user ID string

    Common user IDs:
    - 118004891: Luis Freitas (compliance)
    - 49000180: andreCarespace (frontend)
    - 49000181: fabiano-carespace (backend)
    - 93908270: YeddulaBharath (mobile)
    - 93908266: bhavyasaurabh (ai-cv, security)
    - 111928715: sandeep (infra)
    """
    try:
        actions = json.loads(actions_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON in actions_json"})

    stats = {
        "priorities_set": 0, "tasks_assigned": 0,
        "sp_set": 0, "alerts_created": 0, "errors": 0,
    }

    # Set priorities
    for action in actions.get("set_priority", []):
        try:
            _clickup_api(f"task/{action['task_id']}", method="PUT",
                        payload={"priority": action["priority"]})
            stats["priorities_set"] += 1
        except Exception as e:
            stats["errors"] += 1
            if "first_error" not in stats:
                stats["first_error"] = f"set_priority: {str(e)[:200]}"

    # Assign tasks
    for action in actions.get("assign", []):
        try:
            _clickup_api(f"task/{action['task_id']}", method="PUT",
                        payload={"assignees": {"add": [int(action["user_id"])]}})
            stats["tasks_assigned"] += 1
        except Exception as e:
            stats["errors"] += 1
            if "first_assign_error" not in stats:
                stats["first_assign_error"] = f"{action.get('task_id')}: {str(e)[:200]}"

    # Set story points (uses _set_sp which falls back to sp-N tags)
    for action in actions.get("set_sp", []):
        if _set_sp(action["task_id"], action["points"]):
            stats["sp_set"] += 1
        else:
            stats["errors"] += 1

    # Create alerts (with dedup — check if similar alert already exists)
    existing_alerts = []
    try:
        alert_data = _clickup_api(f"list/{L['alerts']}/task?archived=false")
        existing_alerts = [t["name"].lower() for t in alert_data.get("tasks", [])]
    except Exception:
        pass  # if we can't load alerts, create anyway

    for action in actions.get("create_alerts", []):
        alert_name = action["name"]
        # Enforce naming: always start with [ALERT]
        if not alert_name.startswith("[ALERT]"):
            alert_name = f"[ALERT] {alert_name}"
        # Check if a similar alert already exists (fuzzy match on key words)
        alert_words = set(alert_name.lower().split())
        already_exists = any(
            len(alert_words & set(existing.split())) >= 3
            for existing in existing_alerts
        )
        if already_exists:
            stats["alerts_skipped"] = stats.get("alerts_skipped", 0) + 1
            continue

        try:
            payload = {
                "name": alert_name,
                "priority": action.get("priority", 1),
                "description": action.get("description", ""),
            }
            if action.get("tags"):
                payload["tags"] = action["tags"]
            _clickup_api(
                f"list/{L['alerts']}/task", method="POST",
                payload=payload,
            )
            stats["alerts_created"] += 1
            existing_alerts.append(alert_name.lower())  # add to cache
        except Exception:
            stats["errors"] += 1

    stats["total_actions"] = (
        stats["priorities_set"] + stats["tasks_assigned"] +
        stats["sp_set"] + stats["alerts_created"]
    )
    return json.dumps(stats, indent=2)


def _set_sp(task_id: str, points: int) -> bool:
    """Set story points via the SP custom field (free, unlimited, visible as column).
    Custom field ID from context.py SP_CUSTOM_FIELD_ID."""
    try:
        _clickup_api(f"task/{task_id}/field/{SP_CUSTOM_FIELD_ID}",
                     method="POST", payload={"value": points})
        return True
    except Exception:
        return False


@tool("Scan Backlog For Sprint Planning")
def scan_backlog_for_sprint() -> str:
    """
    Loads ALL backlog tasks and returns a structured summary for the AI
    sprint planner to analyze. Groups by type (bugs, features, tasks,
    compliance) with SP, priority, assignee, and age for each.

    The AI decides what goes in the sprint. This tool just presents the data.
    """
    summary = {
        "total_tasks": 0,
        "carryovers": [],  # from previous sprint — pick these FIRST
        "bugs": [], "features": [], "tasks": [], "compliance": [], "other": [],
        "by_priority": {}, "by_assignee": {}, "total_sp_available": 0,
    }

    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}")
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        summary["total_tasks"] = len(all_tasks)
        from datetime import datetime
        now_ms = int(datetime.utcnow().timestamp() * 1000)

        for t in all_tasks:
            tags = [tag["name"] for tag in t.get("tags", [])]
            pri = t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal"
            assignees = [a.get("username", "") for a in t.get("assignees", [])]
            created_ms = int(t.get("date_created", "0"))
            age_days = round((now_ms - created_ms) / (1000 * 3600 * 24), 1) if created_ms else 0

            cf_sp = next((cf.get("value") for cf in t.get("custom_fields", [])
                         if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
            sp = int(cf_sp) if cf_sp is not None else _estimate_sp(t["name"], pri)

            item = {
                "id": t["id"],
                "name": t["name"][:100],
                "sp": sp,
                "priority": pri,
                "assignees": assignees,
                "age_days": age_days,
                "tags": tags,
            }

            summary["total_sp_available"] += sp
            summary["by_priority"][pri] = summary["by_priority"].get(pri, 0) + 1
            for a in assignees:
                summary["by_assignee"][a] = summary["by_assignee"].get(a, 0) + 1

            # Categorize — carryovers go in their own priority group
            is_carryover = "carryover" in tags
            is_compliance = "compliance" in tags or "vanta" in tags

            if is_carryover:
                summary["carryovers"].append(item)
            elif is_compliance:
                summary["compliance"].append(item)
            elif "bug" in tags:
                summary["bugs"].append(item)
            elif "feature" in tags:
                summary["features"].append(item)
            else:
                summary["tasks"].append(item)

        # Sort each group by priority (urgent first) then age (oldest first)
        pri_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3, "none": 4}
        for group in ["carryovers", "bugs", "features", "tasks", "compliance"]:
            summary[group].sort(key=lambda x: (pri_order.get(x["priority"], 4), -x["age_days"]))

        # Truncate for LLM context — show top items per category
        # Carryovers are NEVER truncated — always show all (usually <10)
        summary["carryovers_total"] = len(summary["carryovers"])
        summary["bugs_total"] = len(summary["bugs"])
        summary["features_total"] = len(summary["features"])
        summary["tasks_total"] = len(summary["tasks"])
        summary["compliance_total"] = len(summary["compliance"])
        summary["bugs"] = summary["bugs"][:15]
        summary["features"] = summary["features"][:15]
        summary["tasks"] = summary["tasks"][:15]
        summary["compliance"] = summary["compliance"][:10]

    except Exception as e:
        summary["error"] = str(e)

    return json.dumps(summary, indent=2)


@tool("Execute Sprint Selection")
def execute_sprint_selection(sprint_list_id: str, task_ids_json: str) -> str:
    """
    Moves selected tasks from the Master Backlog into the sprint list.
    Takes a JSON array of task IDs chosen by the AI sprint planner.

    For each task: copies to sprint (with all metadata: name, description,
    assignees, tags, SP) and closes the backlog original.

    task_ids_json: JSON array of task ID strings, e.g. ["86ag8gpt1", "86ag8fehm"]
    """
    try:
        task_ids = json.loads(task_ids_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON in task_ids_json"})

    stats = {"tasks_moved": 0, "total_sp": 0, "errors": 0, "moved_tasks": []}

    for task_id in task_ids:
        new_id = _move_task_to_sprint(task_id, sprint_list_id)
        if new_id:
            stats["tasks_moved"] += 1
            # Get SP from the new task
            try:
                new_task = _clickup_api(f"task/{new_id}")
                cf_sp = next((cf.get("value") for cf in new_task.get("custom_fields", [])
                             if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
                sp = int(cf_sp) if cf_sp is not None else 0
                stats["total_sp"] += sp
                stats["moved_tasks"].append({
                    "name": new_task.get("name", "")[:80],
                    "sp": sp,
                    "assignees": [a.get("username", "") for a in new_task.get("assignees", [])],
                })
            except Exception:
                stats["moved_tasks"].append({"id": new_id, "sp": 0})
        else:
            stats["errors"] += 1

        # Rate limit
        if stats["tasks_moved"] % 5 == 0 and stats["tasks_moved"] > 0:
            time.sleep(0.5)

    stats["sprint_list_id"] = sprint_list_id
    return json.dumps(stats, indent=2)


@tool("Move Task To Sprint")
def move_task_to_list(task_id: str, target_list_id: str) -> str:
    """
    Move a single task to a sprint list. Creates a full copy in the sprint
    (preserving name, description, assignees, tags, SP) and closes the
    backlog original. ClickUp API does not support direct moves.
    """
    new_id = _move_task_to_sprint(task_id, target_list_id)
    if new_id:
        return json.dumps({"task_id": task_id, "new_task_id": new_id,
                          "moved_to": target_list_id, "success": True})
    else:
        return json.dumps({"error": "Failed to move task"})


@tool("create_or_get_sprint_list")
def create_sprint_list() -> str:
    """
    Smart sprint management. Checks if a current sprint exists and is active.

    - If an active sprint exists (end date hasn't passed): returns it.
      Does NOT create a new one. The AI should update it or skip.
    - If the last sprint ended: creates the next sprint.
    - If no sprints exist: creates Sprint 1.

    Returns: list_id, sprint_name, sprint_number, dates, and
    'status' = 'active' (existing) or 'created' (new).
    """
    import re
    try:
        data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        existing = data.get("lists", [])
        today = date.today()

        # Parse existing sprints to find the latest one
        latest_sprint = None
        latest_number = 0
        for lst in existing:
            name = lst.get("name", "")
            # Extract sprint number
            num = 0
            for sep in ["—", "--"]:
                if sep in name:
                    prefix = name.split(sep)[0].strip()
                    for p in prefix.split():
                        if p.isdigit():
                            num = max(num, int(p))

            # Extract start and end dates from name (e.g., "Sprint 1 — Mar 23 to Apr 05")
            months = ["Jan","Feb","Mar","Apr","May","Jun",
                      "Jul","Aug","Sep","Oct","Nov","Dec"]
            start_date = None
            end_date = None
            date_match = re.search(r'(\w+\s+\d+)\s+to\s+(\w+\s+\d+)', name)
            if date_match:
                try:
                    s = date_match.group(1).split()
                    start_date = date(today.year, months.index(s[0][:3]) + 1, int(s[1]))
                except (ValueError, IndexError):
                    start_date = None
                try:
                    e = date_match.group(2).split()
                    end_date = date(today.year, months.index(e[0][:3]) + 1, int(e[1]))
                except (ValueError, IndexError):
                    end_date = None

            if num > latest_number:
                latest_number = num
                latest_sprint = {
                    "list_id": lst["id"],
                    "name": name,
                    "number": num,
                    "start_date": start_date,
                    "end_date": end_date,
                }

        # Decision: active sprint exists?
        if latest_sprint and latest_sprint["end_date"] and latest_sprint["end_date"] >= today:
            # Sprint is still active — return it with pre-calculated timing
            s = latest_sprint.get("start_date")
            e = latest_sprint["end_date"]
            start_iso = s.isoformat() if s else None
            end_iso = e.isoformat()

            # Pre-calculate timing so the agent doesn't need to do date math
            timing = {}
            if s:
                total_days = (e - s).days + 1
                if today < s:
                    days_until_start = (s - today).days
                    timing = {
                        "sprint_started": False,
                        "days_until_start": days_until_start,
                        "total_days": total_days,
                        "timing_display": f"Starts in {days_until_start} day{'s' if days_until_start != 1 else ''} ({s.strftime('%b %d')} — {e.strftime('%b %d')})",
                    }
                else:
                    elapsed = (today - s).days + 1
                    remaining = (e - today).days
                    timing = {
                        "sprint_started": True,
                        "elapsed_days": elapsed,
                        "remaining_days": remaining,
                        "total_days": total_days,
                        "timing_display": f"Day {elapsed} of {total_days} ({remaining} days remaining)",
                    }

            return json.dumps({
                "list_id": latest_sprint["list_id"],
                "sprint_name": latest_sprint["name"],
                "sprint_number": latest_sprint["number"],
                "start_date": start_iso,
                "end_date": end_iso,
                "today": today.isoformat(),
                "timing": timing,
                "status": "active",
                "message": f"Sprint {latest_sprint['number']} is still active (ends {e}). No new sprint created.",
            })

        # No active sprint — create new one
        sprint_number = latest_number + 1 if latest_number > 0 else 1

        days_until_monday = (7 - today.weekday()) % 7
        start = today if days_until_monday == 0 else today + timedelta(days=days_until_monday)
        end = start + timedelta(days=13)

        sprint_name = f"Sprint {sprint_number} — {start.strftime('%b %d')} to {end.strftime('%b %d')}"

        result = _clickup_api(
            f"folder/{SPRINT_FOLDER_ID}/list",
            method="POST",
            payload={"name": sprint_name},
        )

        days_until = (start - today).days
        total_days = (end - start).days + 1
        return json.dumps({
            "list_id": result.get("id"),
            "sprint_name": sprint_name,
            "sprint_number": sprint_number,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "today": today.isoformat(),
            "timing": {
                "sprint_started": False,
                "days_until_start": days_until,
                "total_days": total_days,
                "timing_display": f"Starts in {days_until} day{'s' if days_until != 1 else ''} ({start.strftime('%b %d')} — {end.strftime('%b %d')})",
            },
            "status": "created",
            "message": f"Created {sprint_name}.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Close Sprint and Handle Carryovers")
def close_sprint() -> str:
    """
    Closes the current sprint and handles incomplete tasks:

    1. Finds the active sprint
    2. Identifies incomplete tasks (not 'complete' or 'done')
    3. Moves them back to Master Backlog with:
       - "carryover" tag added (preserves existing tags)
       - Priority bumped by 1 level (normal→high, high→urgent)
       - Description note: "Carried over from Sprint N"
    4. Marks completed tasks count for velocity tracking
    5. Returns summary of what was carried over

    Call this when a sprint ends (retrospective crew or manually).
    The sprint list itself stays for historical reference.
    """
    import re
    try:
        data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        existing = data.get("lists", [])
        today = date.today()

        # Find the latest sprint
        latest_sprint = None
        latest_number = 0
        for lst in existing:
            name = lst.get("name", "")
            num = 0
            for sep in ["—", "--"]:
                if sep in name:
                    prefix = name.split(sep)[0].strip()
                    for p in prefix.split():
                        if p.isdigit():
                            num = max(num, int(p))
            if num > latest_number:
                latest_number = num
                latest_sprint = {"list_id": lst["id"], "name": name, "number": num}

        if not latest_sprint:
            return json.dumps({"error": "No sprint found to close"})

        # Get all tasks from sprint (including closed)
        all_tasks = []
        page = 0
        while True:
            tasks_data = _clickup_api(
                f"list/{latest_sprint['list_id']}/task?archived=false"
                f"&include_closed=true&page={page}"
            )
            tasks = tasks_data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        completed = []
        carryovers = []
        DONE_STATUSES = {"complete", "done", "closed"}

        for task in all_tasks:
            status = task.get("status", {}).get("status", "").lower()
            if status in DONE_STATUSES:
                completed.append(task)
            else:
                carryovers.append(task)

        # Move carryover tasks back to Master Backlog
        moved = []
        errors = []
        for task in carryovers:
            task_id = task["id"]
            task_name = task.get("name", "")
            existing_tags = [t["name"] for t in task.get("tags", [])]

            try:
                # Move task to Master Backlog
                _clickup_api(
                    f"list/{INTAKE_TARGET}/task/{task_id}",
                    method="PUT",
                    payload={"list": INTAKE_TARGET},
                )

                # Add "carryover" tag if not already present
                if "carryover" not in existing_tags:
                    _clickup_api(
                        f"task/{task_id}/tag/carryover",
                        method="POST",
                        payload={},
                    )

                # Bump priority (4→3, 3→2, 2→1, 1 stays 1)
                current_priority = task.get("priority", {})
                if current_priority and current_priority.get("id"):
                    p = int(current_priority["id"])
                    new_p = max(1, p - 1)  # bump up (lower number = higher priority)
                    if new_p != p:
                        _clickup_api(
                            f"task/{task_id}",
                            method="PUT",
                            payload={"priority": new_p},
                        )

                # Add carryover note to description
                current_desc = task.get("description", "") or ""
                carryover_note = f"\n\n---\n⚡ Carried over from {latest_sprint['name']}"
                if "Carried over from" not in current_desc:
                    _clickup_api(
                        f"task/{task_id}",
                        method="PUT",
                        payload={"description": current_desc + carryover_note},
                    )

                moved.append({
                    "name": task_name[:80],
                    "status": task.get("status", {}).get("status", ""),
                    "sp": task.get("points") or 0,
                })
            except Exception as e:
                errors.append({"task": task_name[:50], "error": str(e)})

        # Calculate velocity
        completed_sp = sum(t.get("points") or 0 for t in completed)
        carryover_sp = sum(m.get("sp", 0) for m in moved)

        return json.dumps({
            "sprint_closed": latest_sprint["name"],
            "sprint_number": latest_sprint["number"],
            "completed_tasks": len(completed),
            "completed_sp": completed_sp,
            "carryover_tasks": len(moved),
            "carryover_sp": carryover_sp,
            "velocity": completed_sp,
            "carryovers": moved,
            "errors": errors,
            "message": (
                f"Sprint {latest_sprint['number']} closed. "
                f"{len(completed)} tasks done ({completed_sp} SP), "
                f"{len(moved)} carried over to backlog ({carryover_sp} SP) "
                f"with 'carryover' tag and bumped priority."
            ),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Bulk Assign And Estimate All Tasks")
def bulk_assign_and_estimate() -> str:
    """
    Assigns ALL unassigned tasks and estimates SP for ALL tasks without points.
    Processes the ENTIRE backlog (paginated), not just first 30.

    Assignment rules based on tags:
    - compliance/vanta/hipaa/soc2 → Luis Freitas (118004891)
    - frontend → andreCarespace (49000180)
    - backend → fabiano-carespace (49000181)
    - mobile → YeddulaBharath (93908270)
    - ai-cv/security → bhavyasaurabh (93908266)
    - infra → sandeep (111928715)

    SP estimation uses task name heuristics.
    Call this ONCE — it processes ALL 311+ tasks.
    """
    from shared.config.context import DOMAIN_LEADS

    stats = {
        "total_tasks": 0, "assigned": 0, "sp_set": 0,
        "already_assigned": 0, "already_has_sp": 0, "errors": 0,
    }

    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}")
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        stats["total_tasks"] = len(all_tasks)

        for t in all_tasks:
            task_id = t["id"]
            tags = [tag["name"] for tag in t.get("tags", [])]
            assignees = t.get("assignees", [])
            points = t.get("points")
            pri = t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal"

            # Assign if unassigned
            if not assignees:
                for tag in tags:
                    if tag in DOMAIN_LEADS:
                        try:
                            _clickup_api(f"task/{task_id}", method="PUT",
                                        payload={"assignees": {"add": [int(DOMAIN_LEADS[tag])]}})
                            stats["assigned"] += 1
                        except Exception:
                            stats["errors"] += 1
                        break
            else:
                stats["already_assigned"] += 1

            # Set SP if missing (check native points + custom field)
            cf_sp = next((cf.get("value") for cf in t.get("custom_fields", [])
                         if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
            has_sp = points is not None or cf_sp is not None
            if not has_sp:
                est = _estimate_sp(t["name"], pri)
                if _set_sp(task_id, est):
                    stats["sp_set"] += 1
                else:
                    stats["errors"] += 1
            else:
                stats["already_has_sp"] += 1

            if (stats["assigned"] + stats["sp_set"]) % 25 == 0 and (stats["assigned"] + stats["sp_set"]) > 0:
                time.sleep(0.5)

    except Exception as e:
        stats["error_detail"] = str(e)

    return json.dumps(stats, indent=2)


@tool("compliance_health_check")
def batch_compliance_check() -> str:
    """
    Complete daily compliance health check in one call. Pulls Vanta health
    data AND counts open compliance tasks in the backlog. Returns everything
    the compliance agent needs to make decisions and post status.

    No other tools needed — this does the full check.
    """
    result = {
        "vanta_health": {"health_indicator": "CHECK_MCP", "note": "Use get_vanta_compliance_health_summary MCP tool for live Vanta data"},
        "open_compliance_tasks": 0,
        "task_sample": [],
        "errors": [],
    }

    # 1. Count open compliance tasks in backlog (paginated)
    # Vanta health comes from MCP tool (injected by CrewHub) — the AI agent
    # should call get_vanta_compliance_health_summary separately if needed.
    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}")
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        compliance_tasks = [
            t for t in all_tasks
            if any(tag["name"] == "compliance" for tag in t.get("tags", []))
        ]
        result["open_compliance_tasks"] = len(compliance_tasks)

        # Sample of first 5 for context
        for t in compliance_tasks[:5]:
            result["task_sample"].append({
                "name": t["name"][:80],
                "priority": t.get("priority", {}).get("priority", "none") if t.get("priority") else "none",
                "assigned": len(t.get("assignees", [])) > 0,
            })
    except Exception as e:
        result["errors"].append(f"clickup: {str(e)[:100]}")

    return json.dumps(result, indent=2)


@tool("Dedup Backlog Cleanup")
def dedup_backlog_cleanup(dry_run: bool = True) -> str:
    """
    Scans the Master Backlog for duplicate tasks and deletes them.
    Keeps the OLDEST task (first created), deletes newer duplicates.

    Duplicates detected by matching identifier in title:
    - Engineering: 'repo#N' pattern (e.g. carespace-ui#159)
    - Compliance: '#N' at the end (e.g. #229)

    dry_run=True (default): shows what WOULD be deleted without deleting.
    dry_run=False: actually deletes the duplicate tasks.
    """
    import re

    stats = {
        "total_tasks": 0, "duplicate_groups": 0, "duplicates_found": 0,
        "tasks_deleted": 0, "tasks_kept": 0, "errors": 0, "dry_run": dry_run,
    }
    deleted_tasks = []
    kept_tasks = []

    try:
        # 1. Load ALL tasks (paginated)
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(
                f"list/{L['master_backlog']}/task?archived=false&page={page}"
            )
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        stats["total_tasks"] = len(all_tasks)

        # 2. Group by identifier extracted from title
        groups = defaultdict(list)
        for t in all_tasks:
            name = t["name"]
            match = re.search(r'\(([^)]*#\d+)\)\s*$', name)
            if match:
                key = match.group(1).lower()
            else:
                key = re.sub(r'\s+', ' ', name.lower().strip())
            groups[key].append({
                "id": t["id"],
                "name": t["name"],
                "date_created": t.get("date_created", "0"),
            })

        # 3. Find groups with duplicates — keep oldest, delete rest
        for key, task_group in groups.items():
            if len(task_group) <= 1:
                continue
            stats["duplicate_groups"] += 1
            task_group.sort(key=lambda x: x["date_created"])
            keep = task_group[0]
            dupes = task_group[1:]
            kept_tasks.append({"name": keep["name"][:80], "id": keep["id"]})

            for dupe in dupes:
                stats["duplicates_found"] += 1
                if not dry_run:
                    try:
                        _clickup_api(f"task/{dupe['id']}", method="DELETE")
                        stats["tasks_deleted"] += 1
                        deleted_tasks.append({"name": dupe["name"][:60], "id": dupe["id"], "deleted": True})
                        time.sleep(0.2)
                    except Exception as e:
                        stats["errors"] += 1
                        if "first_error" not in stats:
                            stats["first_error"] = str(e)[:200]
                else:
                    deleted_tasks.append({"name": dupe["name"][:60], "id": dupe["id"], "would_delete": True})

        stats["tasks_kept"] = len(kept_tasks)
    except Exception as e:
        stats["error_detail"] = str(e)

    stats["sample_duplicates"] = deleted_tasks[:20]
    return json.dumps(stats, indent=2)
