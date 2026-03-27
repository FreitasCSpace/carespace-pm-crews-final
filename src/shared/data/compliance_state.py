"""
Compliance state persistence for delta-based daily reporting.

Stores a snapshot in the vault (GitHub repo) after each successful run
so the next run can compute what changed (new failures, resolved tests,
health trend).

Previous approach used a local file — broken on Azure where the venv
is disposable. Now uses the vault GitHub API directly.
"""
from __future__ import annotations

import base64
import json
import logging
import os

log = logging.getLogger(__name__)

VAULT_REPO = "FreitasCSpace/carespace-pm-vault"
STATE_PATH = "context/compliance-state.json"


def _gh_api(endpoint: str, method: str = "GET", payload: dict | None = None) -> dict:
    """GitHub API v3 call (duplicated from vault.py to avoid circular imports)."""
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


def load_previous_state() -> dict | None:
    """Load the previous compliance snapshot from the vault."""
    try:
        result = _gh_api(f"contents/{STATE_PATH}")
        if "content" in result:
            decoded = base64.b64decode(result["content"]).decode()
            return json.loads(decoded)
    except Exception as e:
        log.debug("compliance state load failed: %s", e)
    return None


def save_current_state(snapshot: dict) -> None:
    """Persist the current snapshot to the vault for the next run's delta."""
    try:
        encoded = base64.b64encode(json.dumps(snapshot, indent=2).encode()).decode()

        # Get existing SHA for update
        sha = None
        existing = _gh_api(f"contents/{STATE_PATH}")
        if "sha" in existing:
            sha = existing["sha"]

        payload = {
            "message": f"compliance-state: {snapshot.get('date', 'unknown')}",
            "content": encoded,
            "committer": {"name": "CareSpace PM AI", "email": "pm-ai@carespace.com"},
        }
        if sha:
            payload["sha"] = sha

        _gh_api(f"contents/{STATE_PATH}", method="PUT", payload=payload)
        log.info("compliance state saved to vault")
    except Exception as e:
        log.warning("compliance state save failed: %s", e)


def compute_delta(current: dict, previous: dict | None) -> dict:
    """
    Deterministic delta between two compliance snapshots.

    Returns:
        {
            "has_previous": bool,
            "consecutive_red_days": int,
            "new_failures": [{"test_id": str, "name": str, "is_critical": bool}],
            "resolved": [{"test_id": str, "name": str}],
            "net_change": int,
            "pass_rate_change": str,  # e.g. "+2%" or "-1%"
            "task_count_change": int,
        }
    """
    if previous is None:
        return {
            "has_previous": False,
            "consecutive_red_days": 1 if current.get("health_indicator") == "RED" else 0,
            "new_failures": [],
            "resolved": [],
            "net_change": 0,
            "pass_rate_change": "",
            "task_count_change": 0,
        }

    # Failing test sets
    cur_ids = set(current.get("failing_test_ids", []))
    prev_ids = set(previous.get("failing_test_ids", []))
    cur_names = current.get("failing_test_names", {})
    prev_names = previous.get("failing_test_names", {})
    cur_critical = current.get("critical_test_ids", set())
    if isinstance(cur_critical, list):
        cur_critical = set(cur_critical)

    new_ids = cur_ids - prev_ids
    resolved_ids = prev_ids - cur_ids

    new_failures = [
        {"test_id": tid, "name": cur_names.get(tid, "Unknown"),
         "is_critical": tid in cur_critical}
        for tid in sorted(new_ids)
    ]
    resolved = [
        {"test_id": tid, "name": prev_names.get(tid, "Unknown")}
        for tid in sorted(resolved_ids)
    ]

    # Consecutive RED days
    prev_consecutive = previous.get("consecutive_red_days", 0)
    if current.get("health_indicator") == "RED":
        consecutive = prev_consecutive + 1 if previous.get("health_indicator") == "RED" else 1
    else:
        consecutive = 0

    # Pass rate change
    cur_rate = current.get("pass_rate_pct", 0)
    prev_rate = previous.get("pass_rate_pct", 0)
    rate_diff = cur_rate - prev_rate
    if rate_diff > 0:
        pass_rate_change = f"+{rate_diff}%"
    elif rate_diff < 0:
        pass_rate_change = f"{rate_diff}%"
    else:
        pass_rate_change = "0%"

    # Task count change
    cur_tasks = current.get("open_compliance_tasks", 0)
    prev_tasks = previous.get("open_compliance_tasks", 0)

    return {
        "has_previous": True,
        "consecutive_red_days": consecutive,
        "new_failures": new_failures,
        "resolved": resolved,
        "net_change": len(new_ids) - len(resolved_ids),
        "pass_rate_change": pass_rate_change,
        "task_count_change": cur_tasks - prev_tasks,
    }
