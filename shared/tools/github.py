"""
tools/github.py
GitHub org tools -- read issues, PRs, CI, contributors, activity
across all 59 carespace-ai repos.
"""

import os, json
from datetime import datetime, timedelta
from crewai.tools import tool
from github import Github, GithubException
from shared.config.context import REPO_DOMAIN, INTAKE_TARGET, COMPLIANCE_REPO, COMPLIANCE_LABEL_MAP

_gh = None
ORG = "carespace-ai"

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


@tool("Get Open GitHub Issues")
def get_issues(repo: str = "", label: str = "") -> str:
    """
    Fetches ALL open GitHub issues from the carespace-ai org.
    repo: specific repo name, or empty string for ALL repos.
    label: optional label filter (e.g. 'bug').
    Returns: repo, domain, number, title, body_preview, labels, assignee,
             priority, issue_type, target_list_id, suggested_title, url, created_at.
    """
    repos = [repo] if repo else list(REPO_DOMAIN.keys())
    out = []
    for rname in repos:
        try:
            r = _repo(rname)
            kwargs: dict = {"state": "open"}
            if label: kwargs["labels"] = [label]
            for issue in r.get_issues(**kwargs):
                if issue.pull_request:
                    continue
                labels = [l.name for l in issue.labels]
                domain = REPO_DOMAIN.get(rname, "frontend")
                pri = _priority(issue.title, labels)
                itype = _itype(issue.title)
                out.append({
                    "repo": rname, "domain": domain, "number": issue.number,
                    "title": issue.title,
                    "body_preview": (issue.body or "")[:300],
                    "labels": labels,
                    "assignee": issue.assignee.login if issue.assignee else None,
                    "priority": pri, "issue_type": itype,
                    "target_list_id": INTAKE_TARGET,
                    "suggested_tags": [domain, itype],
                    "suggested_title": f"[{itype.upper()}] {issue.title} ({rname}#{issue.number})",
                    "url": issue.html_url,
                    "created_at": issue.created_at.isoformat(),
                })
        except GithubException as e:
            out.append({"repo": rname, "error": str(e)})
        except Exception as e:
            out.append({"repo": rname, "error": f"Unexpected: {e}"})
    return json.dumps(out, indent=2)


def _get_prs_impl(repo: str = "") -> str:
    """Internal helper for fetching PRs — callable from other tool functions."""
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


@tool("Get CI Status")
def get_ci(repo: str, branch: str = "main") -> str:
    """
    Returns latest CI check run results for a given branch.
    Returns: overall (passing/failing), failing_checks, total.
    """
    try:
        r = _repo(repo)
        sha = r.get_branch(branch).commit.sha
        checks = list(r.get_commit(sha).get_check_runs())
        failing = [c.name for c in checks if c.conclusion == "failure"]
        return json.dumps({
            "repo": repo, "branch": branch,
            "overall": "failing" if failing else "passing",
            "failing_checks": failing, "total_checks": len(checks),
        })
    except Exception as e:
        return json.dumps({"repo": repo, "branch": branch, "error": str(e)})


@tool("Get Stale Pull Requests")
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


@tool("Get Repo Activity")
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


@tool("Get Compliance Issues from VantaCrews")
def get_compliance_issues() -> str:
    """
    Fetches ALL open issues from the CareSpace Compliance Repo (created by VantaCrews).
    Maps VantaCrews labels to ClickUp tags and priorities. No limit — gets every
    open issue. Currently 500+ issues across SOC 2, HIPAA, control failures,
    evidence gaps, vulnerabilities, access reviews, vendor risks, etc.
    Returns: number, title, body_preview, labels, priority, suggested_tags,
             suggested_title, url, created_at, issue_type.
    """
    try:
        repo = _g().get_repo(COMPLIANCE_REPO)
        out = []
        for issue in repo.get_issues(state="open", sort="created", direction="desc"):
            if issue.pull_request:
                continue

            labels = [l.name for l in issue.labels]

            # Map VantaCrews labels → priority
            priority = "normal"
            for lbl in labels:
                mapped = COMPLIANCE_LABEL_MAP.get(lbl, {})
                if "priority" in mapped:
                    priority = mapped["priority"]
                    break

            # Map VantaCrews labels → tags
            tags = {"compliance", "vanta"}  # always tagged as compliance + vanta source
            for lbl in labels:
                mapped = COMPLIANCE_LABEL_MAP.get(lbl, {})
                if "tag" in mapped:
                    tags.add(mapped["tag"])

            # Determine issue type from VantaCrews label patterns
            issue_type = "compliance"
            for lbl in labels:
                if lbl in ("vulnerability", "risk"):
                    issue_type = "security"
                    break
                if lbl == "access-review":
                    issue_type = "compliance"
                    break

            repo_short = COMPLIANCE_REPO.split("/")[-1]
            out.append({
                "repo": repo_short,
                "number": issue.number,
                "title": issue.title,
                "body_preview": (issue.body or "")[:500],
                "labels": labels,
                "priority": priority,
                "issue_type": issue_type,
                "target_list_id": INTAKE_TARGET,
                "suggested_tags": sorted(tags),
                "suggested_title": f"[COMPLIANCE] {issue.title} (#{issue.number})",
                "url": issue.html_url,
                "created_at": issue.created_at.isoformat(),
                "source": "vantacrews",
            })
        return json.dumps(out, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


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
