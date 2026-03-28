"""
tools/github.py
GitHub org tools -- read issues, PRs, CI, contributors, activity
across all carespace-ai repos + compliance repo.

Batch import tools handle the heavy lifting in code (dedup, create, comment)
so the LLM only needs to call one tool and gets a summary back.
"""

import os, json, time
from datetime import datetime, timedelta
from crewai.tools import tool
from github import Github, GithubException
from shared.config.context import (
    REPO_DOMAIN, INTAKE_TARGET,
    WORKSPACE_ID, L,
)

_gh = None
ORG = "carespace-ai"
BATCH_SIZE = 25  # process N issues per batch, pause between batches


def _g():
    global _gh
    if not _gh:
        _gh = Github(os.environ["GITHUB_TOKEN"])
    return _gh

def _repo(name):
    return _g().get_organization(ORG).get_repo(name)

def _priority(title: str, labels: list[str]) -> str:
    tl = title.lower()
    label_map = {
        "critical": "urgent", "security": "urgent", "p0": "urgent", "cve": "urgent",
        "high-priority": "high", "bug": "high", "p1": "high",
        "enhancement": "normal", "feature": "normal", "low": "low",
    }
    for l in labels:
        if l.lower() in label_map:
            return label_map[l.lower()]
    if any(w in tl for w in ["critical", "security", "rbac", "bypass", "injection", "cve", "vulnerability"]):
        return "urgent"
    if any(w in tl for w in ["bug", "fix", "broken", "error", "fail", "crash", "not loading", "missing"]):
        return "high"
    return "normal"

def _itype(title: str) -> str:
    tl = title.lower()
    if any(w in tl for w in ["security", "vulnerability", "cve", "rbac", "bypass"]):
        return "security"
    if any(w in tl for w in ["bug", "fix", "broken", "error", "fail", "crash"]):
        return "bug"
    if any(w in tl for w in ["feature", "add", "implement", "new", "support", "enable"]):
        return "feature"
    if any(w in tl for w in ["tech debt", "refactor", "cleanup", "deprecat"]):
        return "tech_debt"
    return "task"

def _priority_int(pri: str) -> int:
    return {"urgent": 1, "high": 2, "normal": 3, "low": 4}.get(pri, 3)


# ── ClickUp API helpers (inline to avoid circular imports) ────────────────────

def _clickup_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    import urllib.request
    token = os.environ.get("CLICKUP_PERSONAL_TOKEN", os.environ.get("CLICKUP_API_TOKEN", ""))
    url = f"https://api.clickup.com/api/v2/{endpoint}"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _check_duplicate(title_fragment: str) -> bool:
    """Returns True if a matching task already exists in the Master Backlog.
    DEPRECATED: Use _check_duplicate_cached() instead — this makes an API
    call per check and silently allows creation on failure."""
    try:
        data = _clickup_api(f"list/{INTAKE_TARGET}/task?archived=false")
        tasks = data.get("tasks", [])
        fragment_lower = title_fragment.lower()
        return any(fragment_lower in t["name"].lower() for t in tasks)
    except Exception:
        return True  # if search fails, BLOCK creation to prevent duplicates


# Cache backlog tasks to avoid hitting the API for every single issue
_backlog_cache = None

def _load_all_backlog_tasks() -> list[str]:
    """Load ALL task names from Master Backlog (including closed/completed)
    AND active sprint lists. This prevents intake from re-creating tasks
    that were moved to a sprint (copy + close pattern)."""
    from shared.config.context import SPRINT_FOLDER_ID
    names = []

    # 1. Load backlog tasks (including closed — so moved-to-sprint originals are found)
    for include_closed in ["true"]:
        page = 0
        while True:
            try:
                data = _clickup_api(
                    f"list/{INTAKE_TARGET}/task?archived=false&include_closed={include_closed}&page={page}&page_size=100"
                )
                tasks = data.get("tasks", [])
                if not tasks:
                    break
                names.extend(t["name"].lower() for t in tasks)
                if len(tasks) < 100:
                    break
                page += 1
            except Exception:
                break

    # 2. Load sprint list tasks (the copies that were moved there)
    try:
        sprint_data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        for sprint_list in sprint_data.get("lists", []):
            try:
                sprint_tasks = _clickup_api(
                    f"list/{sprint_list['id']}/task?archived=false&page=0"
                )
                names.extend(t["name"].lower() for t in sprint_tasks.get("tasks", []))
            except Exception:
                pass
    except Exception:
        pass

    # 3. Load Sprint Candidates — tasks staged here must not be re-created in backlog
    try:
        from shared.config.context import L
        candidates = _clickup_api(f"list/{L['sprint_candidates']}/task?archived=false&page=0")
        names.extend(t["name"].lower() for t in candidates.get("tasks", []))
    except Exception:
        pass

    return names


def _check_duplicate_cached(title_fragment: str) -> bool:
    """Cached version — loads full backlog once (paginated), checks in memory."""
    global _backlog_cache
    if _backlog_cache is None:
        _backlog_cache = _load_all_backlog_tasks()
    return any(title_fragment.lower() in name for name in _backlog_cache)


def _create_task(list_id: str, name: str, description: str, priority: int,
                 tags: list[str]) -> dict | None:
    """Create a ClickUp task. Returns task dict or None on failure."""
    try:
        payload = {
            "name": name,
            "description": description,
            "priority": priority,
            "tags": tags,
            "status": "to do",
        }
        result = _clickup_api(f"list/{list_id}/task", method="POST", payload=payload)
        return result
    except Exception as e:
        return None


def _comment_github_issue(repo_full_name: str, issue_number: int, comment: str):
    """Post a comment on a GitHub issue. Fails silently."""
    try:
        _g().get_repo(repo_full_name).get_issue(issue_number).create_comment(comment)
    except Exception:
        pass


# ── Batch import: Engineering repos ───────────────────────────────────────────

@tool("Batch Import Engineering Issues")
def batch_import_engineering() -> str:
    """
    Scans ALL open issues across all carespace-ai GitHub repos and imports
    them into the ClickUp Master Backlog in batches. Handles dedup, task
    creation, and GitHub cross-linking automatically.

    Call this ONCE — it processes everything and returns a summary.
    No need to call check_duplicate_task or create_clickup_task separately.
    """
    # Discover ALL repos in the org dynamically (not just hardcoded list)
    try:
        org = _g().get_organization(ORG)
        repos = [r.name for r in org.get_repos(type="all")]
    except Exception:
        repos = list(REPO_DOMAIN.keys())  # fallback to hardcoded list
    stats = {
        "repos_scanned": 0, "issues_found": 0, "tasks_created": 0,
        "duplicates_skipped": 0, "errors": 0, "by_domain": {}, "by_type": {},
    }
    created_tasks = []

    for rname in repos:
        stats["repos_scanned"] += 1
        try:
            r = _repo(rname)
            for issue in r.get_issues(state="open"):
                if issue.pull_request:
                    continue

                stats["issues_found"] += 1
                labels = [l.name for l in issue.labels]
                domain = REPO_DOMAIN.get(rname, "frontend")
                pri = _priority(issue.title, labels)
                itype = _itype(issue.title)
                dedup_key = f"{rname}#{issue.number}"

                # Dedup check (only against Master Backlog, not old spaces)
                if _check_duplicate_cached(dedup_key):
                    stats["duplicates_skipped"] += 1
                    continue

                # Create task
                title = f"[{itype.upper()}] {issue.title} ({dedup_key})"
                desc = f"GitHub: {issue.html_url}\n\n{(issue.body or '')[:500]}"
                tags = [domain, itype, "github"]

                result = _create_task(INTAKE_TARGET, title, desc, _priority_int(pri), tags)
                if result:
                    stats["tasks_created"] += 1
                    stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1
                    stats["by_type"][itype] = stats["by_type"].get(itype, 0) + 1
                    created_tasks.append({"title": title[:80], "priority": pri})
                    # Add to cache so we don't create duplicates within same run
                    if _backlog_cache is not None:
                        _backlog_cache.append(title.lower())

                    # Cross-link back to GitHub
                    task_url = result.get("url", "")
                    if task_url:
                        _comment_github_issue(
                            f"{ORG}/{rname}", issue.number,
                            f"Tracked in ClickUp: {task_url}"
                        )
                else:
                    stats["errors"] += 1

                # Pause between batches to avoid rate limits
                if stats["tasks_created"] % BATCH_SIZE == 0 and stats["tasks_created"] > 0:
                    time.sleep(1)

        except GithubException as e:
            stats["errors"] += 1
        except Exception as e:
            stats["errors"] += 1

    stats["sample_created"] = created_tasks[:10]  # show first 10 for context
    return json.dumps(stats, indent=2)


# ── Sync: close ClickUp tasks when GitHub issues close ────────────────────────

import re

_GITHUB_REF_RE = re.compile(r"\(([a-zA-Z0-9_.-]+#\d+)\)\s*$")
def _extract_github_ref(task: dict) -> dict | None:
    """Extract GitHub repo + issue number from a ClickUp task title."""
    name = task.get("name", "")

    # Engineering: title ends with (repo#123)
    m = _GITHUB_REF_RE.search(name)
    if m:
        ref = m.group(1)
        repo_name, issue_num = ref.rsplit("#", 1)
        return {
            "task_id": task["id"],
            "task_name": name,
            "task_status": task.get("status", {}).get("status", "").lower(),
            "repo": f"{ORG}/{repo_name}",
            "issue_number": int(issue_num),
        }

    return None


@tool("Sync GitHub Issues to ClickUp")
def sync_closed_issues() -> str:
    """
    Two-way sync between GitHub issues and ClickUp tasks.
    GitHub is the source of truth:

    1. GitHub closed + ClickUp open → close ClickUp task (status: complete)
    2. GitHub open + ClickUp complete → reopen ClickUp task (status: to do)

    Call this ONCE per intake run — it handles all repos automatically.
    """
    stats = {
        "backlog_scanned": 0, "github_tasks_found": 0,
        "closed_on_github": 0, "clickup_closed": 0,
        "reopened_from_github": 0, "clickup_reopened": 0,
        "errors": 0,
    }
    closed_tasks = []
    reopened_tasks = []

    # Load ALL backlog tasks (open + closed) with GitHub refs
    try:
        all_tasks = []
        page = 0
        while True:
            data = _clickup_api(
                f"list/{INTAKE_TARGET}/task?archived=false&include_closed=true&page={page}&page_size=100"
            )
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:
                break
            page += 1
        stats["backlog_scanned"] = len(all_tasks)
    except Exception as e:
        stats["errors"] += 1
        stats["error_detail"] = f"Failed to load backlog: {e}"
        return json.dumps(stats, indent=2)

    # Also scan sprint lists — tasks moved to sprint are no longer in backlog
    # but still need GitHub sync (merged PR → task done)
    try:
        from shared.config.context import SPRINT_FOLDER_ID
        sprint_folder = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        sprint_tasks_found = 0
        for sprint_list in sprint_folder.get("lists", []):
            page = 0
            while True:
                sprint_data = _clickup_api(
                    f"list/{sprint_list['id']}/task?archived=false&include_closed=true&page={page}&page_size=100"
                )
                batch = sprint_data.get("tasks", [])
                if not batch:
                    break
                all_tasks.extend(batch)
                sprint_tasks_found += len(batch)
                if len(batch) < 100:
                    break
                page += 1
        stats["sprint_tasks_scanned"] = sprint_tasks_found
    except Exception as sprint_e:
        stats["sprint_scan_error"] = str(sprint_e)

    # Extract GitHub refs from all tasks
    github_tasks = []
    for t in all_tasks:
        ref = _extract_github_ref(t)
        if ref:
            github_tasks.append(ref)

    stats["github_tasks_found"] = len(github_tasks)

    # Sync each task against GitHub source of truth
    checked = 0
    for gt in github_tasks:
        try:
            repo = _g().get_repo(gt["repo"])
            issue = repo.get_issue(gt["issue_number"])
            clickup_is_closed = gt["task_status"] in ("complete", "done", "closed")

            if issue.state == "closed" and not clickup_is_closed:
                # GitHub closed, ClickUp open → close ClickUp
                stats["closed_on_github"] += 1
                try:
                    _clickup_api(
                        f"task/{gt['task_id']}", method="PUT",
                        payload={"status": "complete"}
                    )
                    stats["clickup_closed"] += 1
                    closed_tasks.append({
                        "task": gt["task_name"][:80],
                        "issue": f"{gt['repo']}#{gt['issue_number']}",
                    })
                except Exception:
                    stats["errors"] += 1

            elif issue.state == "open" and clickup_is_closed:
                # GitHub open, ClickUp closed → reopen ClickUp
                stats["reopened_from_github"] += 1
                try:
                    _clickup_api(
                        f"task/{gt['task_id']}", method="PUT",
                        payload={"status": "to do"}
                    )
                    stats["clickup_reopened"] += 1
                    reopened_tasks.append({
                        "task": gt["task_name"][:80],
                        "issue": f"{gt['repo']}#{gt['issue_number']}",
                    })
                except Exception:
                    stats["errors"] += 1

        except Exception:
            stats["errors"] += 1

        checked += 1
        if checked % BATCH_SIZE == 0:
            time.sleep(1)

    stats["sample_closed"] = closed_tasks[:10]
    stats["sample_reopened"] = reopened_tasks[:10]
    return json.dumps(stats, indent=2)


# ── Lightweight read-only tools (for other crews) ────────────────────────────

@tool("Get Open GitHub Issues")
def get_issues(repo: str = "", label: str = "") -> str:
    """
    Fetches open GitHub issues from the carespace-ai org (read-only scan).
    repo: specific repo name, or empty for ALL repos.
    Returns summary: repo, domain, number, title, priority, issue_type.
    Limited to 20 per repo to keep LLM context manageable.
    """
    repos = [repo] if repo else list(REPO_DOMAIN.keys())
    out = []
    for rname in repos:
        try:
            r = _repo(rname)
            kwargs: dict = {"state": "open"}
            if label: kwargs["labels"] = [label]
            count = 0
            for issue in r.get_issues(**kwargs):
                if count >= 20:
                    break
                if issue.pull_request:
                    continue
                labels = [l.name for l in issue.labels]
                domain = REPO_DOMAIN.get(rname, "frontend")
                out.append({
                    "repo": rname, "domain": domain, "number": issue.number,
                    "title": issue.title,
                    "priority": _priority(issue.title, labels),
                    "issue_type": _itype(issue.title),
                    "url": issue.html_url,
                })
                count += 1
        except Exception:
            pass
    return json.dumps(out, indent=2)


def _get_prs_impl(repo: str = "") -> str:
    repos = [repo] if repo else list(REPO_DOMAIN.keys())
    now = datetime.utcnow()
    out = []
    for rname in repos:
        try:
            r = _repo(rname)
            count = 0
            for pr in r.get_pulls(state="open"):
                if count >= 20:
                    break
                age = (now - pr.created_at.replace(tzinfo=None)).days
                ci = "unknown"
                try:
                    runs = list(r.get_commit(pr.head.sha).get_check_runs())
                    if runs:
                        ci = "failing" if any(x.conclusion == "failure" for x in runs) else "passing"
                except: pass
                out.append({
                    "repo": rname, "number": pr.number, "title": pr.title,
                    "author": pr.user.login, "branch": pr.head.ref,
                    "age_days": age, "stale": age >= 7, "critical_stale": age >= 30,
                    "ci_status": ci, "url": pr.html_url,
                })
                count += 1
        except GithubException as e:
            out.append({"repo": rname, "error": str(e)})
    return json.dumps(out, indent=2)


@tool("Get Open Pull Requests")
def get_prs(repo: str = "") -> str:
    """
    Fetches open PRs from the carespace-ai org.
    repo: specific repo name, or empty for all repos.
    Returns: number, title, author, branch, age_days, stale (>7d), ci_status, url.
    """
    return _get_prs_impl(repo)


@tool("get_ci_status")
def get_ci(repo: str, branch: str = "main") -> str:
    """
    Returns latest CI check run results for a given branch.
    Auto-falls back: main → master → develop if branch not found.
    Returns: overall (passing/failing), failing_checks, total.
    """
    r = _repo(repo)
    branches_to_try = [branch]
    if branch == "main":
        branches_to_try = ["main", "master", "develop"]

    for b in branches_to_try:
        try:
            sha = r.get_branch(b).commit.sha
            checks = list(r.get_commit(sha).get_check_runs())
            failing = [c.name for c in checks if c.conclusion == "failure"]
            return json.dumps({
                "repo": repo, "branch": b,
                "overall": "failing" if failing else "passing",
                "failing_checks": failing, "total_checks": len(checks),
            })
        except Exception:
            continue

    return json.dumps({
        "repo": repo, "branch": branch,
        "overall": "unknown",
        "error": f"No branch found (tried: {', '.join(branches_to_try)})",
    })


@tool("get_stale_pull_requests")
def get_stale_prs(days: int = 7) -> str:
    """
    Returns all PRs open longer than N days across all repos.
    Fast path for standup and PR radar -- pre-filters for stale only.
    """
    all_prs = json.loads(_get_prs_impl(""))
    return json.dumps(
        [p for p in all_prs if isinstance(p, dict) and p.get("age_days", 0) >= days],
        indent=2,
    )


@tool("Get Repo Contributors")
def get_contributors(repo: str) -> str:
    """
    Returns top contributors for a repo by commit count.
    Use when assigning repo-specific tasks -- prefer the people who know the codebase.
    """
    try:
        r = _repo(repo)
        return json.dumps([
            {"login": c.login, "commits": c.contributions}
            for c in r.get_contributors()[:10]
        ], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("get_repo_activity")
def get_activity(repo: str, days: int = 14) -> str:
    """
    Returns commit count, open PR count, and last push for a repo over N days.
    Used by retrospective crew to summarize sprint engineering activity.
    """
    try:
        r = _repo(repo)
        since = datetime.utcnow() - timedelta(days=days)
        commits = sum(1 for _ in r.get_commits(since=since))
        return json.dumps({
            "repo": repo, "days": days, "commits": commits,
            "open_prs": r.get_pulls(state="open").totalCount,
            "open_issues": r.get_issues(state="open").totalCount,
            "last_push": r.pushed_at.isoformat() if r.pushed_at else None,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("get_stale_github_issues")
def get_stale_issues(days: int = 3) -> str:
    """
    Returns GitHub issues with no comments for N+ days across all repos.
    Flags issues that may need follow-up — nobody has responded or updated.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    out = []
    for rname in REPO_DOMAIN.keys():
        try:
            r = _repo(rname)
            for issue in r.get_issues(state="open", sort="updated", direction="asc"):
                if issue.pull_request:
                    continue
                # Check last comment date
                comments = list(issue.get_comments())
                if comments:
                    last_comment = max(c.created_at.replace(tzinfo=None) for c in comments)
                else:
                    last_comment = issue.created_at.replace(tzinfo=None)
                if last_comment < cutoff:
                    days_silent = (now - last_comment).days
                    out.append({
                        "repo": rname,
                        "number": issue.number,
                        "title": issue.title,
                        "days_no_comments": days_silent,
                        "last_activity": last_comment.isoformat(),
                        "url": issue.html_url,
                    })
                if len(out) >= 30:
                    break
        except Exception:
            pass
        if len(out) >= 30:
            break
    return json.dumps(out, indent=2)


@tool("Comment on GitHub Issue")
def comment_issue(repo: str, issue_number: int, comment: str) -> str:
    """
    Posts a comment on a GitHub issue.
    Primary use: cross-link the ClickUp task URL back to the GitHub issue.
    """
    try:
        _repo(repo).get_issue(issue_number).create_comment(comment)
        return f"Comment posted on {repo}#{issue_number}"
    except Exception as e:
        return f"Error: {e}"
