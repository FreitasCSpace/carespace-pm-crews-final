"""
tools/clickup_helpers.py
Helper tools that wrap ClickUp MCP search to provide list-level task queries
and duplicate detection. These complement the MCP-injected ClickUp tools.
"""

import os, json, time
from datetime import date, timedelta
from collections import defaultdict
from crewai.tools import tool
from shared.config.context import L, WORKSPACE_ID, SP_ESTIMATE, SPRINT_FOLDER_ID


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


@tool("Create Task In List")
def create_clickup_task(list_id: str, name: str, description: str = "",
                        priority: int = 3, assignees: list[int] = None,
                        tags: list[str] = None, points: int = None) -> str:
    """
    Create a new task in a ClickUp list. USE THIS instead of MCP create_click_up_task.
    list_id: target list ID.
    priority: 1=urgent, 2=high, 3=normal, 4=low.
    assignees: list of ClickUp user IDs.
    tags: list of tag name strings.
    points: story points estimate.
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
        if points is not None:
            payload["points"] = points
        result = _clickup_api(f"list/{list_id}/task", method="POST", payload=payload)
        return json.dumps({
            "id": result.get("id"),
            "name": result.get("name"),
            "url": result.get("url"),
            "status": result.get("status", {}).get("status"),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def _move_task(task_id: str, target_list_id: str) -> bool:
    """Move a task to a different list. Returns True on success.
    Uses the correct ClickUp API: PUT /list/{list_id}/task/{task_id}
    """
    try:
        # ClickUp move task API: PUT /list/{target}/task/{task_id}
        _clickup_api(
            f"list/{target_list_id}/task/{task_id}",
            method="PUT",
            payload={},
        )
        return True
    except Exception:
        return False


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
    Scans ALL Master Backlog tasks and returns a structured summary
    for the AI agent to analyze and make decisions on.

    Returns:
    - total_tasks: count
    - unassigned: list of {id, name, tags, priority, age_hours} for tasks with no assignee
    - wrong_priority: list of tasks that may need priority adjustment
    - no_story_points: list of tasks missing SP estimates
    - sla_at_risk: list of tasks approaching or breaching SLA
    - by_tag: count of tasks per tag
    - by_priority: count of tasks per priority level

    The AI agent should analyze this data and decide what actions to take,
    then pass those decisions to execute_triage_actions.
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

            # Unassigned tasks
            if not assignees:
                summary["unassigned"].append(task_info)

            # No story points
            if points is None:
                summary["no_story_points"].append({"id": t["id"], "name": name[:80], "priority": pri})

            # SLA at risk
            sla_hours = BUG_SLA.get(pri, 168)
            if age_hours > sla_hours * 0.8:  # 80% of SLA = at risk
                task_info["sla_hours"] = sla_hours
                task_info["breached"] = age_hours > sla_hours
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
      "create_alerts": [{"name": "...", "description": "...", "priority": 1}]
    }

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

    # Set story points
    for action in actions.get("set_sp", []):
        try:
            _clickup_api(f"task/{action['task_id']}", method="PUT",
                        payload={"points": action["points"]})
            stats["sp_set"] += 1
        except Exception as e:
            stats["errors"] += 1
            if "first_sp_error" not in stats:
                stats["first_sp_error"] = f"{action.get('task_id')}: {str(e)[:200]}"

    # Create alerts
    for action in actions.get("create_alerts", []):
        try:
            _clickup_api(
                f"list/{L['alerts']}/task", method="POST",
                payload={
                    "name": action["name"],
                    "priority": action.get("priority", 1),
                    "description": action.get("description", ""),
                },
            )
            stats["alerts_created"] += 1
        except Exception:
            stats["errors"] += 1

    stats["total_actions"] = (
        stats["priorities_set"] + stats["tasks_assigned"] +
        stats["sp_set"] + stats["alerts_created"]
    )
    return json.dumps(stats, indent=2)


def _set_sp(task_id: str, points: int) -> bool:
    """Set story points on a task. Returns True on success."""
    try:
        _clickup_api(f"task/{task_id}", method="PUT", payload={"points": points})
        return True
    except Exception:
        return False


@tool("Batch Populate Sprint")
def batch_populate_sprint(sprint_list_id: str, max_sp: int = 48) -> str:
    """
    Reads the Master Backlog, scores all tasks, selects the top ones that
    fit within max_sp story points, moves them to the sprint list, estimates
    SP, and assigns to domain leads. Does EVERYTHING in one call.

    Compliance tasks are capped (max 3 per sprint) since they're handled
    by one person (Luis Freitas). Bugs and features get priority.

    Call this ONCE after create_sprint_list. Returns a full summary.
    """
    from shared.config.context import DOMAIN_LEADS, SCORE, MAX_COMPLIANCE_PER_SPRINT

    priority_weight = SCORE["priority_weight"]
    domain_lead_map = DOMAIN_LEADS

    stats = {
        "tasks_scored": 0, "tasks_selected": 0, "tasks_moved": 0,
        "tasks_assigned": 0, "total_sp": 0, "errors": 0,
        "compliance_selected": 0, "engineering_selected": 0,
    }
    sprint_tasks = []

    try:
        # 1. Load all backlog tasks
        data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false")
        tasks = data.get("tasks", [])
        stats["tasks_scored"] = len(tasks)

        # 2. Score each task — separate compliance from engineering
        compliance_tasks = []
        engineering_tasks = []

        for t in tasks:
            pri = t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal"
            tags = [tag["name"] for tag in t.get("tags", [])]
            base = priority_weight.get(pri, 40)
            is_compliance = "compliance" in tags or "vanta" in tags

            # Score: compliance gets lower base multiplier so bugs/features rank higher
            multi = 1.0
            if "security" in tags:
                multi *= 2.0
            if not is_compliance:
                # Boost engineering tasks so they don't get drowned by compliance
                if "bug" in tags:
                    multi *= 1.8
                if "feature" in tags:
                    multi *= 1.3
            score = base * multi

            # Estimate SP
            sp = t.get("points")
            if sp is None:
                sp = _estimate_sp(t["name"], pri)

            item = {
                "id": t["id"],
                "name": t["name"],
                "score": score,
                "sp": sp,
                "priority": pri,
                "tags": tags,
                "is_compliance": is_compliance,
            }

            if is_compliance:
                compliance_tasks.append(item)
            else:
                engineering_tasks.append(item)

        # 3. Sort each group by score
        engineering_tasks.sort(key=lambda x: x["score"], reverse=True)
        compliance_tasks.sort(key=lambda x: x["score"], reverse=True)

        # 4. Select: engineering first (unlimited), then compliance (capped)
        selected = []
        running_sp = 0

        # Engineering tasks first — fill as much as possible
        for item in engineering_tasks:
            if running_sp + item["sp"] > max_sp:
                continue
            selected.append(item)
            running_sp += item["sp"]
            stats["engineering_selected"] += 1

        # Compliance tasks — max N per sprint
        compliance_count = 0
        for item in compliance_tasks:
            if compliance_count >= MAX_COMPLIANCE_PER_SPRINT:
                break
            if running_sp + item["sp"] > max_sp:
                continue
            selected.append(item)
            running_sp += item["sp"]
            compliance_count += 1
            stats["compliance_selected"] += 1

        stats["tasks_selected"] = len(selected)

        # 5. Move (or copy) tasks to sprint, assign, set SP
        for item in selected:
            task_id = item["id"]

            # Try to move first
            if _move_task(task_id, sprint_list_id):
                stats["tasks_moved"] += 1
            else:
                # Move failed — create a copy in the sprint list instead
                try:
                    result = _clickup_api(
                        f"list/{sprint_list_id}/task",
                        method="POST",
                        payload={
                            "name": item["name"],
                            "priority": {"urgent": 1, "high": 2, "normal": 3, "low": 4}.get(item["priority"], 3),
                            "tags": item["tags"],
                            "points": item["sp"],
                            "description": f"From backlog task: https://app.clickup.com/t/{task_id}",
                        },
                    )
                    task_id = result.get("id", task_id)  # use new task ID for assignment
                    stats["tasks_moved"] += 1
                except Exception:
                    stats["errors"] += 1
                    continue

            _set_sp(task_id, item["sp"])

            # Assign to domain lead based on tags
            assigned_to = None
            for tag in item["tags"]:
                if tag in domain_lead_map:
                    if _assign_task(task_id, domain_lead_map[tag]):
                        stats["tasks_assigned"] += 1
                        assigned_to = tag
                    break

            stats["total_sp"] += item["sp"]
            sprint_tasks.append({
                "name": item["name"][:80],
                "sp": item["sp"],
                "priority": item["priority"],
                "score": item["score"],
                "assigned_domain": assigned_to,
                "type": "compliance" if item["is_compliance"] else "engineering",
            })

    except Exception as e:
        stats["error_detail"] = str(e)

    stats["sprint_list_id"] = sprint_list_id
    stats["sprint_tasks"] = sprint_tasks
    return json.dumps(stats, indent=2)


@tool("Move Task To List")
def move_task_to_list(task_id: str, target_list_id: str) -> str:
    """
    Move a single task to a different ClickUp list.
    For bulk moves, use batch_populate_sprint instead.
    """
    try:
        _clickup_api(f"list/{target_list_id}/task/{task_id}", method="PUT", payload={})
        return json.dumps({"task_id": task_id, "moved_to": target_list_id, "success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Create Sprint List")
def create_sprint_list() -> str:
    """
    Creates a new sprint list in the Sprints folder. Auto-detects the next
    sprint number and calculates dates (2-week sprint starting next Monday).
    Returns the new list_id and sprint name. Call this at the start of sprint
    planning — it handles everything.
    """
    try:
        # Detect next sprint number from existing lists
        sprint_number = 1
        data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        existing = data.get("lists", [])
        for lst in existing:
            name = lst.get("name", "")
            for sep in ["—", "--"]:
                if sep in name:
                    prefix = name.split(sep)[0].strip()
                    for p in prefix.split():
                        if p.isdigit():
                            sprint_number = max(sprint_number, int(p) + 1)

        # Calculate dates: next Monday + 2 weeks
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            start = today
        else:
            start = today + timedelta(days=days_until_monday)
        end = start + timedelta(days=13)

        sprint_name = f"Sprint {sprint_number} — {start.strftime('%b %d')} to {end.strftime('%b %d')}"

        # Create the list
        result = _clickup_api(
            f"folder/{SPRINT_FOLDER_ID}/list",
            method="POST",
            payload={"name": sprint_name},
        )

        return json.dumps({
            "list_id": result.get("id"),
            "sprint_name": sprint_name,
            "sprint_number": sprint_number,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        })
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

            # Set SP if missing
            if points is None:
                est = _estimate_sp(t["name"], pri)
                try:
                    _clickup_api(f"task/{task_id}", method="PUT", payload={"points": est})
                    stats["sp_set"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    if "first_sp_error" not in stats:
                        stats["first_sp_error"] = str(e)[:200]
            else:
                stats["already_has_sp"] += 1

            if (stats["assigned"] + stats["sp_set"]) % 25 == 0 and (stats["assigned"] + stats["sp_set"]) > 0:
                time.sleep(0.5)

    except Exception as e:
        stats["error_detail"] = str(e)

    return json.dumps(stats, indent=2)


@tool("Compliance Health Check")
def batch_compliance_check() -> str:
    """
    Complete daily compliance health check in one call. Pulls Vanta health
    data AND counts open compliance tasks in the backlog. Returns everything
    the compliance agent needs to make decisions and post status.

    No other tools needed — this does the full check.
    """
    result = {
        "vanta_health": None,
        "open_compliance_tasks": 0,
        "task_sample": [],
        "errors": [],
    }

    # 1. Try to get Vanta health from MCP (via subprocess)
    try:
        import subprocess
        # The MCP Vanta tool is not callable directly, so we use our vanta.py
        from shared.tools.vanta import get_health_summary as _vanta_health
        health_json = _vanta_health()
        result["vanta_health"] = json.loads(health_json)
    except Exception as e:
        result["errors"].append(f"vanta_health: {str(e)[:100]}")
        # Fallback: return unknown status
        result["vanta_health"] = {"health_indicator": "UNKNOWN", "error": str(e)[:100]}

    # 2. Count open compliance tasks in backlog (paginated)
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
