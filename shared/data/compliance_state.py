"""
Compliance state persistence for delta-based daily reporting.

Stores a snapshot after each successful run so the next run can compute
what changed (new failures, resolved tests, health trend).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STATE_FILE = Path(__file__).parent / "compliance_state.json"


def load_previous_state() -> dict | None:
    """Load yesterday's compliance snapshot. Returns None on first run."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return None


def save_current_state(snapshot: dict) -> None:
    """Persist today's snapshot for tomorrow's delta computation."""
    try:
        STATE_FILE.write_text(json.dumps(snapshot, indent=2))
    except Exception:
        pass  # Non-fatal — next run just won't have delta


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
