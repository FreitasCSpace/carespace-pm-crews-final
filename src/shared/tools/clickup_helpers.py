"""
tools/clickup_helpers.py
Helper tools that wrap ClickUp MCP search to provide list-level task queries
and duplicate detection. These complement the MCP-injected ClickUp tools.
"""

import os, json, time
from datetime import date, timedelta
from collections import defaultdict
from crewai.tools import tool
from shared.config.context import L, WORKSPACE_ID, SP_ESTIMATE, SPRINT_FOLDER_ID, SP_CUSTOM_FIELD_ID, SPRINT_RULES, SPRINT_TEMPLATE_LIST_ID


def _clickup_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    """Direct ClickUp API v2 call for operations MCP doesn't expose.
    Retries up to 3 times on 429 (rate limit) with exponential backoff,
    respecting the Retry-After header when present."""
    import urllib.request, logging
    log = logging.getLogger(__name__)
    token = os.environ.get("CLICKUP_PERSONAL_TOKEN",
            os.environ.get("CLICKUP_API_TOKEN", ""))
    url = f"https://api.clickup.com/api/v2/{endpoint}"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode() if payload else None

    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.request.HTTPError as e:
            if e.code == 429 and attempt < 2:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                wait = float(retry_after) if retry_after else 2 ** (attempt + 1)
                log.warning("ClickUp 429 rate limit (attempt %d/3), waiting %.1fs", attempt + 1, wait)
                time.sleep(wait)
                continue
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {error_body[:200]}")
    # Should not reach here, but safety net
    raise Exception(f"ClickUp API failed after 3 retries: {endpoint}")


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
            import urllib.parse
            params += f"&statuses[]={urllib.parse.quote(status)}"
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


@tool("check_stale_sprint_tasks")
def check_stale_sprint_tasks(task_ids_json: str, days: int = 3) -> str:
    """
    Checks which sprint tasks have NO ClickUp comments for N+ days.
    This detects truly silent tasks — ignores bot updates to date_updated.

    task_ids_json: JSON array of task ID strings, e.g. '["abc123", "def456"]'
    days: number of days without comments to flag (default: 3)

    Returns: JSON array of stale tasks with id, name, days_silent, last_comment_date.
    Tasks with zero comments are always flagged.
    """
    from datetime import datetime, timezone
    task_ids = json.loads(task_ids_json) if isinstance(task_ids_json, str) else task_ids_json
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stale = []

    for task_id in task_ids:
        try:
            comments_data = _clickup_api(f"task/{task_id}/comment")
            comments = comments_data.get("comments", [])
            if not comments:
                # No comments ever — use task creation date from the task itself
                try:
                    task_data = _clickup_api(f"task/{task_id}")
                    created_ts = int(task_data.get("date_created", "0"))
                    created_dt = datetime.fromtimestamp(created_ts / 1000, tz=timezone.utc)
                    days_since = (datetime.now(timezone.utc) - created_dt).days
                except Exception:
                    days_since = 0
                if days_since >= days:
                    stale.append({
                        "task_id": task_id,
                        "days_silent": days_since,
                        "last_comment_date": None,
                        "note": "no comments ever",
                    })
                continue

            # Find the most recent comment date
            last_ts = max(int(c.get("date", "0")) for c in comments)
            last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
            if last_dt < cutoff:
                days_silent = (datetime.now(timezone.utc) - last_dt).days
                stale.append({
                    "task_id": task_id,
                    "days_silent": days_silent,
                    "last_comment_date": last_dt.isoformat(),
                })
        except Exception:
            continue  # Skip tasks we can't check — non-fatal

    return json.dumps(stale, indent=2)


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
        payload = {"name": name, "priority": priority, "status": "to do"}
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

    Orphan protection trade-off: if the copy succeeds but closing the
    original fails, we keep the copy (resulting in a duplicate) rather
    than deleting it. A duplicate is recoverable via dedup; a lost task
    is not.
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
        # If this fails, we intentionally keep the copy — better to have a
        # duplicate than lose the task entirely. Dedup cleanup handles dupes.
        try:
            _clickup_api(f"task/{task_id}", method="PUT", payload={"status": "complete"})
        except Exception as close_err:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to close original task %s after copying to %s: %s "
                "(keeping copy to prevent task loss)",
                task_id, new_id, close_err,
            )

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


@tool("Normalize Backlog Tasks")
def normalize_backlog_tasks() -> str:
    """
    Finds backlog tasks created directly in ClickUp (not from GitHub).
    Differentiates between two sources:

    1. Vanta/Compliance tasks — have 'compliance' tag or start with '[Vanta]'.
       These are SKIPPED — they're already properly tagged and named.

    2. Design tasks (Buena team) — no GitHub link, no compliance tag.
       These get normalized: 'design' source tag + [TYPE] prefix + domain tag.

    Detection logic:
    - Has github.com URL in description → GitHub task, skip
    - Has 'compliance' tag or starts with '[Vanta]' → Vanta task, skip
    - Everything else without GitHub link → design task, normalize

    Returns: {tasks_scanned, tasks_normalized, vanta_skipped, details: [...]}
    """
    import re
    from shared.config.context import DOMAIN_TAGS, DOMAIN_KEYWORDS

    _GITHUB_URL_RE = re.compile(r"github\.com/", re.IGNORECASE)

    stats = {"tasks_scanned": 0, "tasks_normalized": 0, "already_normalized": 0,
             "skipped_has_github": 0, "vanta_skipped": 0, "details": []}

    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}&page_size=100")
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        stats["tasks_scanned"] = len(all_tasks)

        for t in all_tasks:
            tags = [tag["name"] for tag in t.get("tags", [])]
            name = t["name"]
            desc = t.get("description", "") or ""
            task_id = t["id"]

            # If description contains a GitHub URL, this is a GitHub-sourced task — skip
            if _GITHUB_URL_RE.search(desc):
                stats["skipped_has_github"] += 1
                continue

            # Vanta/compliance tasks — already properly tagged, skip
            if "compliance" in tags or name.startswith("[Vanta]") or name.startswith("[COMPLIANCE]"):
                stats["vanta_skipped"] += 1
                continue

            # Already normalized: has 'design' tag and [TYPE] prefix
            has_design_tag = "design" in tags
            has_prefix = name.startswith("[")
            has_domain = any(tag in DOMAIN_TAGS for tag in tags)

            if has_design_tag and has_prefix and has_domain:
                stats["already_normalized"] += 1
                continue

            # This is a design task that needs normalization
            updates_made = []
            tags_to_add = []

            # 1. Add 'design' source tag
            if not has_design_tag:
                tags_to_add.append("design")
                updates_made.append("added 'design' source tag")

            # 2. Rename to [TYPE] prefix if missing
            if not has_prefix:
                nl = name.lower()
                if any(w in nl for w in ["bug", "fix", "broken", "error", "crash", "not working"]):
                    itype = "BUG"
                elif any(w in nl for w in ["feature", "add", "implement", "new", "create", "build", "enable"]):
                    itype = "FEATURE"
                elif any(w in nl for w in ["security", "vulnerability", "cve", "rbac"]):
                    itype = "SECURITY"
                elif any(w in nl for w in ["compliance", "hipaa", "soc2", "vanta", "audit"]):
                    itype = "COMPLIANCE"
                else:
                    itype = "TASK"
                new_name = f"[{itype}] {name}"
                try:
                    _clickup_api(f"task/{task_id}", method="PUT", payload={"name": new_name})
                    updates_made.append(f"renamed to [{itype}]")
                except Exception:
                    updates_made.append("rename failed")

            # 3. Infer domain tag if missing
            if not has_domain:
                nl = name.lower()
                matched_domain = None
                for domain, keywords in DOMAIN_KEYWORDS.items():
                    if any(kw in nl for kw in keywords):
                        matched_domain = domain
                        break
                if matched_domain:
                    tags_to_add.append(matched_domain)
                    updates_made.append(f"added '{matched_domain}' domain tag")

            # Apply tags
            for tag in tags_to_add:
                try:
                    from urllib.parse import quote
                    _clickup_api(f"task/{task_id}/tag/{quote(tag)}", method="POST")
                except Exception:
                    pass

            if updates_made:
                stats["tasks_normalized"] += 1
                stats["details"].append({
                    "id": task_id,
                    "original_name": name[:80],
                    "updates": updates_made,
                })

        # Truncate details for LLM context
        if len(stats["details"]) > 20:
            stats["details_total"] = len(stats["details"])
            stats["details"] = stats["details"][:20]

    except Exception as e:
        stats["error"] = str(e)

    return json.dumps(stats, indent=2)


@tool("Scan Backlog For Triage")
def scan_backlog_for_triage() -> str:
    """
    Scans Master Backlog tasks for hygiene issues.

    Returns:
    - unassigned: tasks with no assignee
    - wrong_priority: tasks that may need priority adjustment
    - no_story_points: tasks missing SP estimates
    - aging: tasks with no update in >21 days
    - by_tag / by_priority: distribution counts

    Only scans the Master Backlog — sprint items are handled by daily pulse.
    """
    from datetime import datetime

    now_ms = int(datetime.utcnow().timestamp() * 1000)

    summary = {
        "total_tasks": 0,
        "bugs": 0,
        "features": 0,
        "compliance": 0,
        "design": 0,
        "tasks": 0,
        "unassigned": [],
        "wrong_priority": [],
        "no_story_points": [],
        "aging": [],
        "by_tag": {},
        "by_priority": {},
    }

    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}&page_size=100")
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
            cf_sp = next((cf.get("value") for cf in t.get("custom_fields", [])
                         if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
            points = t.get("points") or cf_sp  # check both native and custom field
            created_ms = int(t.get("date_created", "0"))
            age_hours = round((now_ms - created_ms) / (1000 * 3600), 1) if created_ms else 0
            name = t["name"]

            # Count by tag and priority
            for tag in tags:
                summary["by_tag"][tag] = summary["by_tag"].get(tag, 0) + 1
            summary["by_priority"][pri] = summary["by_priority"].get(pri, 0) + 1

            # Count by type (from tags or title prefix)
            name_upper = name.upper()
            if "bug" in tags or name_upper.startswith("[BUG]"):
                summary["bugs"] += 1
            elif "compliance" in tags or name_upper.startswith("[COMPLIANCE]") or name_upper.startswith("[VANTA]"):
                summary["compliance"] += 1
            elif "feature" in tags or name_upper.startswith("[FEATURE]"):
                summary["features"] += 1
            elif "design" in tags or name_upper.startswith("[DESIGN]"):
                summary["design"] += 1
            else:
                summary["tasks"] += 1

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

            # No story points
            if points is None:
                summary["no_story_points"].append({"id": t["id"], "name": name[:80], "priority": pri})

            # Aging items — no update in >21 days (504 hours)
            updated_ms = int(t.get("date_updated", "0"))
            if updated_ms:
                hours_since_update = round((now_ms - updated_ms) / (1000 * 3600), 1)
                if hours_since_update > 504:  # 21 days
                    summary["aging"].append({
                        "id": t["id"],
                        "name": name[:100],
                        "priority": pri,
                        "days_since_update": round(hours_since_update / 24),
                        "tags": tags[:3],
                    })

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
        if len(summary["aging"]) > 20:
            summary["aging_total"] = len(summary["aging"])
            summary["aging"] = summary["aging"][:20]
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
        "priority_details": [],
    }

    pri_names = {1: "urgent", 2: "high", 3: "normal", 4: "low"}

    # Set priorities
    for action in actions.get("set_priority", []):
        try:
            _clickup_api(f"task/{action['task_id']}", method="PUT",
                        payload={"priority": action["priority"]})
            stats["priorities_set"] += 1
            stats["priority_details"].append({
                "task_id": action["task_id"],
                "new_priority": pri_names.get(action["priority"], str(action["priority"])),
                "reason": action.get("reason", ""),
                "clickup_url": f"https://app.clickup.com/t/{action['task_id']}",
            })
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


# ── Sprint Candidates (staging area between backlog and sprint) ──────────────

@tool("List Sprint Candidates")
def list_sprint_candidates() -> str:
    """
    Returns all tasks currently in the Sprint Candidates list with their
    assignees, SP, priority, and tags. Use this to review what's been
    proposed for the next sprint before finalizing.
    """
    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(
                f"list/{L['sprint_candidates']}/task?archived=false&page={page}&page_size=100"
            )
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1

        result = {
            "total_candidates": len(all_tasks),
            "total_sp": 0,
            "unassigned": 0,
            "tasks": [],
        }

        for t in all_tasks:
            assignees = [a.get("username", "") for a in t.get("assignees", [])]
            cf_sp = next((cf.get("value") for cf in t.get("custom_fields", [])
                         if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
            sp = int(cf_sp) if cf_sp is not None else _estimate_sp(t["name"], "normal")

            if not assignees:
                result["unassigned"] += 1

            result["total_sp"] += sp
            result["tasks"].append({
                "id": t["id"],
                "name": t["name"][:100],
                "sp": sp,
                "priority": t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal",
                "assignees": assignees,
                "tags": [tag["name"] for tag in t.get("tags", [])],
                "url": t.get("url", ""),
            })

        result["budget_sp"] = SPRINT_RULES["budget_sp"]
        result["over_budget"] = result["total_sp"] > SPRINT_RULES["budget_sp"]

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("Finalize Sprint From Candidates")
def finalize_sprint_from_candidates(sprint_list_id: str) -> str:
    """
    Moves all tasks from Sprint Candidates into the actual Sprint list.
    This is the final step in sprint planning — called AFTER the team
    has reviewed and approved the candidates.

    Validates:
    - All candidates have assignees (warns if not)
    - Total SP doesn't exceed budget (warns if over)
    - At least 1 task exists

    Then: copies each candidate to sprint, deletes from candidates,
    and closes the backlog original.
    """
    # Load candidates
    candidates_data = json.loads(list_sprint_candidates.run())
    tasks = candidates_data.get("tasks", [])

    if not tasks:
        return json.dumps({"error": "No tasks in Sprint Candidates. Add tasks first."})

    # Warnings
    warnings = []
    unassigned = [t for t in tasks if not t["assignees"]]
    if unassigned:
        warnings.append(f"{len(unassigned)} task(s) have no assignee: {', '.join(t['name'][:40] for t in unassigned)}")
    if candidates_data.get("over_budget"):
        warnings.append(f"Over budget: {candidates_data['total_sp']} SP vs {candidates_data['budget_sp']} SP budget")

    stats = {"tasks_moved": 0, "total_sp": 0, "errors": 0, "warnings": warnings, "moved": []}

    for task in tasks:
        task_id = task["id"]
        try:
            # Get full task data
            full_task = _clickup_api(f"task/{task_id}")

            # Build sprint task payload from full task data
            pri = full_task.get("priority")
            description = full_task.get("description", "") or ""

            tags = [t["name"] for t in full_task.get("tags", [])]

            # If candidate has no description or tags, pull from backlog original
            if not description.strip() or not tags:
                import re as _re
                github_ref = _re.search(r'\(([^)]+#\d+)\)', full_task.get("name", ""))
                if github_ref:
                    ref = github_ref.group(1)  # e.g. "carespace-ui#64"
                    try:
                        bl_data = _clickup_api(
                            f"list/{L['master_backlog']}/task?archived=false&include_closed=true&page_size=100"
                        )
                        for bl_task in bl_data.get("tasks", []):
                            if ref.lower() in bl_task.get("name", "").lower():
                                bl_full = _clickup_api(f"task/{bl_task['id']}")
                                if not description.strip():
                                    description = bl_full.get("description", "") or ""
                                if not tags:
                                    tags = [t["name"] for t in bl_full.get("tags", [])]
                                break
                    except Exception:
                        pass

            payload = {
                "name": full_task.get("name", ""),
                "description": description,
                "assignees": [a["id"] for a in full_task.get("assignees", [])],
                "tags": tags,
            }
            if isinstance(pri, dict) and pri.get("id"):
                payload["priority"] = int(pri["id"])

            result = _clickup_api(
                f"list/{sprint_list_id}/task",
                method="POST", payload=payload,
            )
            new_id = result.get("id", "")

            # Copy SP
            cf_sp = next((cf.get("value") for cf in full_task.get("custom_fields", [])
                         if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
            if cf_sp is not None:
                _set_sp(new_id, int(cf_sp))

            # Delete from candidates
            try:
                _clickup_api(f"task/{task_id}", method="DELETE")
            except Exception:
                pass  # orphan protection — sprint copy exists

            # Close backlog original
            desc = full_task.get("description", "")
            backlog_closed = False

            # Method 1: explicit link in description
            if "Backlog task: https://app.clickup.com/t/" in desc:
                backlog_id = desc.split("Backlog task: https://app.clickup.com/t/")[-1].strip().split()[0]
                try:
                    _clickup_api(f"task/{backlog_id}", method="PUT",
                                payload={"status": "complete"})
                    backlog_closed = True
                except Exception:
                    pass

            # Method 2: match by title in backlog (fallback for manually created candidates)
            if not backlog_closed:
                task_name = full_task.get("name", "").lower()[:60]
                try:
                    bl_page = 0
                    while not backlog_closed:
                        bl_data = _clickup_api(
                            f"list/{L['master_backlog']}/task?archived=false&include_closed=false&page={bl_page}&page_size=100"
                        )
                        bl_tasks = bl_data.get("tasks", [])
                        if not bl_tasks:
                            break
                        for bl_task in bl_tasks:
                            if task_name in bl_task["name"].lower():
                                _clickup_api(f"task/{bl_task['id']}", method="PUT",
                                            payload={"status": "complete"})
                                backlog_closed = True
                                break
                        bl_page += 1
                except Exception:
                    pass

            stats["tasks_moved"] += 1
            stats["total_sp"] += task.get("sp", 0)
            assignee_names = [a.get("username", a.get("id", "?")) if isinstance(a, dict) else str(a)
                              for a in full_task.get("assignees", [])]
            stats["moved"].append({
                "name": task["name"],
                "assignee": ", ".join(assignee_names) if assignee_names else "unassigned",
                "story_points": task.get("sp", "?"),
                "priority": task.get("priority", "normal"),
            })
        except Exception as e:
            stats["errors"] += 1
            if "error_details" not in stats:
                stats["error_details"] = []
            stats["error_details"].append(f"{task.get('name', task_id)[:50]}: {str(e)[:100]}")

        if stats["tasks_moved"] % 5 == 0 and stats["tasks_moved"] > 0:
            time.sleep(0.5)

    stats["sprint_list_id"] = sprint_list_id
    # Pre-format for post_sprint_plan — agent passes this directly as tasks_json
    stats["tasks_json"] = json.dumps(stats["moved"])
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


@tool("get_last_sprint_velocity")
def get_last_sprint_velocity() -> str:
    """
    Reads Sprint History to find the last sprint's actual velocity.
    Returns the recommended SP budget for the next sprint.

    Recommended budget = last_velocity × 0.80 (conservative buffer).
    Falls back to 48 SP if no history exists yet.
    """
    import re
    try:
        data = _clickup_api(
            f"list/{L['sprint_history']}/task?archived=false"
            f"&order_by=created&reverse=true&page_size=10"
        )
        tasks = data.get("tasks", [])
        for task in tasks:
            name = task.get("name", "")
            m = re.search(r'Velocity:\s*(\d+)\s*SP', name, re.IGNORECASE)
            if m:
                last_velocity = int(m.group(1))
                recommended = max(20, int(last_velocity * 0.80))
                return json.dumps({
                    "source": name,
                    "last_velocity_sp": last_velocity,
                    "recommended_budget_sp": recommended,
                    "note": f"{last_velocity} SP delivered last sprint × 0.80 = {recommended} SP budget",
                })
        return json.dumps({
            "source": "default",
            "last_velocity_sp": None,
            "recommended_budget_sp": 48,
            "note": "No sprint history yet — using default 48 SP budget",
        })
    except Exception as e:
        return json.dumps({"source": "error", "recommended_budget_sp": 48, "error": str(e)})


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

        # Parse existing sprints to find the latest one (skip template)
        latest_sprint = None
        latest_number = 0
        for lst in existing:
            if lst.get("id") == SPRINT_TEMPLATE_LIST_ID:
                continue
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

        # No active sprint — create new one by duplicating template
        sprint_number = latest_number + 1 if latest_number > 0 else 1

        days_until_monday = (7 - today.weekday()) % 7
        start = today if days_until_monday == 0 else today + timedelta(days=days_until_monday)
        end = start + timedelta(days=13)

        sprint_name = f"Sprint {sprint_number} — {start.strftime('%b %d')} to {end.strftime('%b %d')}"

        # Create new list in sprint folder
        result = _clickup_api(
            f"folder/{SPRINT_FOLDER_ID}/list",
            method="POST",
            payload={"name": sprint_name},
        )

        new_list_id = result.get("id")

        days_until = (start - today).days
        total_days = (end - start).days + 1
        return json.dumps({
            "list_id": new_list_id,
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
                f"&include_closed=true&page={page}&page_size=100"
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
        # ClickUp API does NOT support moving tasks between lists.
        # Must use copy + close approach (same as _move_task_to_sprint).
        moved = []
        errors = []
        pri_map = {"urgent": 1, "high": 2, "normal": 3, "low": 4}

        for task in carryovers:
            task_id = task["id"]
            task_name = task.get("name", "")
            existing_tags = [t["name"] for t in task.get("tags", [])]

            try:
                # Get full task details (sprint task may have limited fields)
                src = _clickup_api(f"task/{task_id}")
                pri = src.get("priority", {}).get("priority", "normal") if src.get("priority") else "normal"
                assignee_ids = [a["id"] for a in src.get("assignees", [])]
                tag_names = [t["name"] for t in src.get("tags", [])]

                # Add "carryover" tag
                if "carryover" not in tag_names:
                    tag_names.append("carryover")

                # Bump priority (4→3, 3→2, 2→1, 1 stays 1)
                pri_int = pri_map.get(pri, 3)
                bumped_pri = max(1, pri_int - 1)

                # Build description with carryover note
                desc = src.get("description", "") or ""
                carryover_note = f"\n\n---\n⚡ Carried over from {latest_sprint['name']}"
                if "Carried over from" not in desc:
                    desc += carryover_note

                # 1. Create copy in Master Backlog
                new_task = _clickup_api(
                    f"list/{L['master_backlog']}/task",
                    method="POST",
                    payload={
                        "name": task_name,
                        "description": desc,
                        "priority": bumped_pri,
                        "assignees": assignee_ids,
                        "tags": tag_names,
                    },
                )
                new_id = new_task.get("id")
                if not new_id:
                    errors.append({"task": task_name[:50], "error": "Failed to create copy"})
                    continue

                # 2. Copy SP custom field
                src_sp = next((cf.get("value") for cf in src.get("custom_fields", [])
                               if cf.get("id") == SP_CUSTOM_FIELD_ID and cf.get("value") is not None), None)
                sp = int(src_sp) if src_sp is not None else 0
                if sp:
                    _set_sp(new_id, sp)

                # 3. Delete sprint original (it's now in backlog, not "complete")
                # Orphan protection: if delete fails, keep the backlog copy.
                # Better to have a duplicate than lose the task entirely.
                try:
                    _clickup_api(f"task/{task_id}", method="DELETE")
                except Exception as del_err:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to delete sprint task %s after copying to backlog %s: %s "
                        "(keeping backlog copy to prevent task loss)",
                        task_id, new_id, del_err,
                    )
                    errors.append({"task": task_name[:50], "error": f"delete failed: {str(del_err)[:100]}"})

                moved.append({
                    "name": task_name[:80],
                    "new_task_id": new_id,
                    "status": task.get("status", {}).get("status", ""),
                    "sp": sp,
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
def bulk_estimate_sp() -> str:
    """
    Processes the ENTIRE backlog (paginated):
    1. Removes assignees from any assigned tasks (backlog must be unassigned)
    2. Estimates story points for tasks that don't have SP yet

    Assignees are selected during sprint planning, not in the backlog.
    Call this ONCE — it processes all tasks.
    """
    stats = {
        "total_tasks": 0, "sp_set": 0, "unassigned": 0,
        "already_has_sp": 0, "already_unassigned": 0, "errors": 0,
    }

    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(f"list/{L['master_backlog']}/task?archived=false&page={page}&page_size=100")
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
            assignees = t.get("assignees", [])
            points = t.get("points")
            pri = t.get("priority", {}).get("priority", "normal") if t.get("priority") else "normal"

            # Remove assignees — backlog items must be unassigned
            if assignees:
                assignee_ids = [a["id"] for a in assignees]
                try:
                    _clickup_api(f"task/{task_id}", method="PUT",
                                payload={"assignees": {"rem": assignee_ids}})
                    stats["unassigned"] += 1
                except Exception:
                    stats["errors"] += 1
            else:
                stats["already_unassigned"] += 1

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

            changes = stats["unassigned"] + stats["sp_set"]
            if changes % 25 == 0 and changes > 0:
                time.sleep(0.5)

    except Exception as e:
        stats["error_detail"] = str(e)

    return json.dumps(stats, indent=2)


# Keep old name as alias for backwards compatibility
bulk_assign_and_estimate = bulk_estimate_sp


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
                f"list/{L['master_backlog']}/task?archived=false&page={page}&page_size=100"
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
