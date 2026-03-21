"""
shared/guardrails.py — Validation functions for CrewAI task guardrails.

Each function receives a TaskOutput and returns (bool, Any).
  - (True, result)  → output accepted
  - (False, reason)  → output rejected, agent retries with the reason as feedback

These are imported in crew.py and passed to Task(guardrail=...).
"""
import json
import re


def _parse_json(raw: str):
    """Try to extract JSON from LLM output (handles markdown fences)."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # Try to find JSON object in the text
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# ── Sprint Crew ──────────────────────────────────────────────────────────────

def validate_sprint_plan(result):
    """Ensure sprint plan meets the mandatory mix rules."""
    from shared.config.context import SPRINT_RULES

    raw = result.raw if hasattr(result, "raw") else str(result)
    data = _parse_json(raw)

    if not data:
        # If not JSON, check prose for key indicators
        lower = raw.lower()
        if "zero features" in lower or "no features" in lower:
            return (False, "Sprint MUST include features. Replan with at least "
                    f"{SPRINT_RULES['min_features']} features.")
        return (True, raw)

    tasks_moved = data.get("tasks_moved", 0)
    total_sp = data.get("total_sp", 0)
    budget = SPRINT_RULES["budget_sp"]

    if total_sp > budget * 1.2:
        return (False, f"Sprint is over budget: {total_sp} SP exceeds "
                f"{budget} SP limit. Remove lower-priority items.")

    if tasks_moved == 0 and "status" not in raw.lower():
        return (False, "No tasks were moved to sprint. Either select tasks "
                "or report that the sprint is already active.")

    return (True, raw)


def validate_sprint_sp_coverage(result):
    """Ensure at least 70% of selected sprint tasks have explicit SP
    (not heuristic estimates). Tasks with sp_estimated=true were auto-estimated
    by _estimate_sp and may be inaccurate. The sprint planner should refine
    estimates or confirm them before committing."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    data = _parse_json(raw)

    if not data:
        return (True, raw)  # Can't validate non-JSON output

    # Check moved_tasks for sp_estimated flags if present
    moved = data.get("moved_tasks", [])
    if not moved:
        return (True, raw)  # No task list to validate

    total = len(moved)
    estimated = sum(1 for t in moved if t.get("sp_estimated", False))
    explicit = total - estimated

    if total > 0 and explicit / total < 0.70:
        pct = round(explicit / total * 100)
        return (False,
                f"Only {pct}% of sprint tasks ({explicit}/{total}) have explicit "
                f"story points. At least 70% should have real SP estimates, not "
                f"heuristic guesses. Review tasks marked sp_estimated=true and "
                f"set accurate SP before committing the sprint.")

    return (True, raw)


# ── Triage Crew ──────────────────────────────────────────────────────────────

def validate_triage_actions(result):
    """Ensure triage completed and produced meaningful output."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    # Must have some substance — not empty or error
    if len(raw.strip()) < 20:
        return (False, "Triage output is too short. Include summary of actions taken.")

    # If alerts were created, they should mention tags
    if "[alert]" in lower and "tags" not in lower and "tag" not in lower:
        return (False, "Alerts must include tags for filtering. "
                "Add tags like ['compliance', 'hipaa'] to each alert.")

    return (True, raw)


# ── PR Radar Crew ────────────────────────────────────────────────────────────

def validate_pr_radar_output(result):
    """Ensure PR radar scan collected PR and CI data.

    This guardrail runs on the SCAN task (before posting) so retries
    don't cause duplicate Slack posts.
    """
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    has_pr_data = any(w in lower for w in ["stale", "pr", "pull request",
                                            "total_prs", "stale_prs"])
    has_ci_data = any(w in lower for w in ["ci", "passing", "failing",
                                            "ci_failures", "actions"])

    if not has_pr_data:
        return (False, "Scan must include PR data. "
                "Call get_stale_pull_requests to find stale PRs.")

    if not has_ci_data:
        return (False, "Scan must include CI status. "
                "Call get_ci_status on key repos.")

    return (True, raw)


# ── Compliance Crew ──────────────────────────────────────────────────────────

def validate_compliance_output(result):
    """Ensure compliance check includes both data sources."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    has_vanta = "vanta" in lower or "green" in lower or "red" in lower or "yellow" in lower
    has_tasks = "task" in lower or "compliance" in lower

    if not has_vanta:
        return (False, "Compliance output must include Vanta health status. "
                "Call get_vanta_compliance_health_summary.")

    if not has_tasks:
        return (False, "Compliance output must include open task count. "
                "Call compliance_health_check.")

    return (True, raw)


# ── Customer Success Crew ────────────────────────────────────────────────────

def validate_cs_output(result):
    """Ensure CS monitoring checked both lists."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    has_onboarding = "onboarding" in lower or "account" in lower
    has_support = "support" in lower or "ticket" in lower or "escalation" in lower

    if not has_onboarding and not has_support:
        return (False, "CS output must cover both Onboarding & Accounts "
                "and Support Escalations lists.")

    return (True, raw)


# ── Exec Report Crew ─────────────────────────────────────────────────────────

def validate_exec_report(result):
    """Ensure gather step collected data across all 5 dimensions.

    This guardrail runs on the GATHER task (before posting) so retries
    don't cause duplicate Slack posts.
    """
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    dimensions = {
        "engineering": any(w in lower for w in ["sprint", "engineering", "velocity", "task"]),
        "gtm": any(w in lower for w in ["gtm", "deal", "pipeline", "active_deals"]),
        "compliance": any(w in lower for w in ["compliance", "vanta", "hipaa", "control"]),
        "customer_success": any(w in lower for w in ["customer", "onboarding", "churn", "support"]),
        "bugs": any(w in lower for w in ["bug", "sla", "defect", "backlog"]),
    }

    missing = [d for d, found in dimensions.items() if not found]
    if len(missing) >= 3:
        return (False, f"Gathered data missing dimensions: {missing}. "
                "Collect data for engineering, GTM, compliance, CS, and bug health "
                "before proceeding to post.")

    return (True, raw)


# ── Daily Pulse Crew ─────────────────────────────────────────────────────────

def validate_standup_data(result):
    """Ensure scan collected sprint + attention data before posting.

    This guardrail runs on the SCAN task (before posting) so retries
    don't cause duplicate Slack posts.
    """
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    has_sprint = any(w in lower for w in ["sprint", "task", "status", "progress"])
    has_attention = any(w in lower for w in ["stale", "ci", "alert", "blocker", "pr"])

    if not has_sprint:
        return (False, "Scan data must include sprint task status. "
                "Call get_tasks_by_list for the active sprint.")

    if not has_attention:
        return (False, "Scan data must include attention items. "
                "Check stale PRs, CI status, and alerts.")

    return (True, raw)


# ── Deal Intel Crew ──────────────────────────────────────────────────────────

def validate_deal_intel(result):
    """Ensure pipeline analysis includes vertical breakdown.

    This guardrail runs on the ANALYZE task (before posting) so retries
    don't cause duplicate Slack posts.
    """
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    if "vertical" not in lower and "healthcare" not in lower and "pipeline" not in lower:
        return (False, "Deal intel must include pipeline analysis by vertical. "
                "Group deals by vertical tags and identify coverage gaps.")

    return (True, raw)


# ── Retrospective Crew ──────────────────────────────────────────────────────

def validate_retro_metrics(result):
    """Ensure retro measurement collected key metrics before posting.

    This guardrail runs on the MEASURE task (before posting) so retries
    don't cause duplicate Slack posts.
    """
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    has_velocity = any(w in lower for w in ["velocity", "sp", "story point",
                                             "completed", "done"])
    has_completion = any(w in lower for w in ["completion", "rate", "percent",
                                               "progress"])

    if not has_velocity:
        return (False, "Retro must include velocity data (SP completed). "
                "Pull sprint tasks with include_closed=True and sum points.")

    if not has_completion:
        return (False, "Retro must include completion rate. "
                "Calculate done tasks / total tasks as a percentage.")

    return (True, raw)
