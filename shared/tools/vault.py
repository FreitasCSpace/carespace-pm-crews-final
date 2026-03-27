"""
tools/vault.py
Read/write .md files to the carespace-pm-vault GitHub repo.
Acts as a shared knowledge base across all PM crew runs.

Uses the GitHub API directly (no local clone needed).
Requires GITHUB_TOKEN in environment with repo write access.
"""

import os, json, base64
from datetime import date
from crewai.tools import tool

VAULT_REPO = "FreitasCSpace/carespace-pm-vault"

# Map crew names to vault directories
CREW_DIRS = {
    "compliance": "compliance",
    "intake": "intake",
    "daily_pulse": "sprints/daily",
    "sla": "sla",
    "triage": "triage",
    "sprint_plan": "sprints/plans",
    "sprint_retro": "sprints/retros",
    "exec_report": "exec",
    "huddle_notes": "huddles",
    "context": "context",
}


def _gh_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    """GitHub API v3 call."""
    import urllib.request
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://api.github.com/repos/{VAULT_REPO}/{endpoint}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.request.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}", "detail": body[:300]}


def _get_file_sha(path: str) -> str | None:
    """Get the SHA of an existing file (needed for updates)."""
    result = _gh_api(f"contents/{path}")
    if "sha" in result:
        return result["sha"]
    return None


@tool("vault_write")
def vault_write(crew: str, content: str, filename: str = "") -> str:
    """
    Writes a markdown file to the PM vault repo (carespace-pm-vault).
    Each crew run should write its output here for cross-crew context.

    crew: which crew is writing. One of:
      compliance, intake, daily_pulse, sla, triage,
      sprint_plan, sprint_retro, exec_report, huddle_notes, context
    content: markdown content to write (include frontmatter)
    filename: optional override. Default: YYYY-MM-DD.md for daily crews,
      or must be provided for sprint-scoped files (e.g. 'sprint-1.md')

    The content MUST include YAML frontmatter:
    ---
    date: YYYY-MM-DD
    crew: crew_name
    type: daily|sprint|weekly
    ---

    Returns: {ok: true, path: "dir/file.md"} or {error: "..."}
    """
    directory = CREW_DIRS.get(crew)
    if not directory:
        return json.dumps({"error": f"Unknown crew '{crew}'. Valid: {list(CREW_DIRS.keys())}"})

    if not filename:
        filename = f"{date.today().isoformat()}.md"

    path = f"{directory}/{filename}"
    encoded = base64.b64encode(content.encode()).decode()

    # Check if file already exists (need SHA for update)
    sha = _get_file_sha(path)

    payload = {
        "message": f"vault: {crew} — {filename}",
        "content": encoded,
        "committer": {"name": "CareSpace PM AI", "email": "pm-ai@carespace.com"},
    }
    if sha:
        payload["sha"] = sha  # update existing file

    result = _gh_api(f"contents/{path}", method="PUT", payload=payload)

    if "content" in result:
        return json.dumps({"ok": True, "path": path, "sha": result["content"].get("sha", "")})
    return json.dumps({"ok": False, "error": result.get("error", "unknown"), "detail": result.get("detail", "")})


@tool("vault_read")
def vault_read(path: str) -> str:
    """
    Reads a markdown file from the PM vault repo.
    Use this to get context from previous crew runs.

    path: file path relative to vault root.
      Examples:
        'context/velocity.md' — latest velocity data
        'triage/2026-03-27.md' — specific triage report
        'sprints/retros/sprint-1.md' — sprint 1 retrospective
        'compliance/2026-03-27.md' — compliance health for that day

    Returns the raw markdown content, or {error: "..."} if not found.
    """
    result = _gh_api(f"contents/{path}")

    if "content" in result:
        decoded = base64.b64decode(result["content"]).decode()
        return decoded
    if result.get("error") == "HTTP 404":
        return json.dumps({"error": f"File not found: {path}"})
    return json.dumps({"error": result.get("error", "unknown"), "detail": result.get("detail", "")})


@tool("vault_list")
def vault_list(directory: str) -> str:
    """
    Lists files in a vault directory. Use to find what data is available.

    directory: path relative to vault root.
      Examples: 'triage', 'sprints/daily', 'context', 'compliance'

    Returns: JSON array of {name, path, size} sorted by name (newest last
    for date-named files).
    """
    result = _gh_api(f"contents/{directory}")

    if isinstance(result, list):
        files = [
            {"name": f["name"], "path": f["path"], "size": f.get("size", 0)}
            for f in result
            if f.get("type") == "file" and f["name"] != ".gitkeep"
        ]
        files.sort(key=lambda f: f["name"])
        return json.dumps(files, indent=2)

    if isinstance(result, dict) and result.get("error"):
        return json.dumps({"error": result.get("error"), "detail": result.get("detail", "")})

    return json.dumps({"error": "Unexpected response", "detail": str(result)[:300]})
