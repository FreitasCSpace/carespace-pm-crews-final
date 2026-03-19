"""
shared/guardrails.py — Validation functions for CrewAI task guardrails.

Each function receives a TaskOutput and returns (bool, Any).
  - (True, result)  → output accepted
  - (False, reason)  → output rejected, agent retries with the reason as feedback

These are imported in crew.py and passed to Task(guardrail=...).
"""
from __future__ import annotations

import json
import re
from typing import Any, Tuple


def _parse_json(raw: str) -> dict | None:
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

def validate_sprint_plan(result) -> Tuple[bool, Any]:
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


# ── Triage Crew ──────────────────────────────────────────────────────────────

def validate_triage_actions(result) -> Tuple[bool, Any]:
    """Ensure triage output includes reasoning and proper alert format."""
    raw = result.raw if hasattr(result, "raw") else str(result)

    # Must include reasoning — this is a thinking crew, not a mechanical one
    lower = raw.lower()
    if "reason" not in lower and "because" not in lower and "decision" not in lower:
        return (False, "Triage output must include REASONING for decisions. "
                "Explain WHY you escalated, assigned, or skipped items.")

    # Check for alerts without tags (common mistake)
    if "[alert]" in lower and "tags" not in lower:
        return (False, "Alerts must include tags for filtering. "
                "Add tags like ['compliance', 'hipaa'] to each alert.")

    return (True, raw)


# ── PR Radar Crew ────────────────────────────────────────────────────────────

def validate_pr_radar_output(result) -> Tuple[bool, Any]:
    """Ensure PR radar output has required metrics."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    data = _parse_json(raw)

    if data:
        required = ["total_prs", "stale_prs"]
        missing = [k for k in required if k not in data]
        if missing:
            return (False, f"PR radar output missing required fields: {missing}. "
                    "Include total_prs and stale_prs counts.")

    # If not JSON, check that a summary was posted
    if "post_pr_radar" not in raw.lower() and "posted" not in raw.lower():
        if "slack" not in raw.lower() and "summary" not in raw.lower():
            return (False, "PR radar must post a summary to Slack. "
                    "Use post_pr_radar_report tool before finishing.")

    return (True, raw)


# ── Compliance Crew ──────────────────────────────────────────────────────────

def validate_compliance_output(result) -> Tuple[bool, Any]:
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

def validate_cs_output(result) -> Tuple[bool, Any]:
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

def validate_exec_report(result) -> Tuple[bool, Any]:
    """Ensure exec report covers all 5 dimensions."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    dimensions = {
        "engineering": any(w in lower for w in ["sprint", "engineering", "velocity"]),
        "gtm": any(w in lower for w in ["gtm", "deal", "pipeline"]),
        "compliance": any(w in lower for w in ["compliance", "vanta", "hipaa"]),
        "customer_success": any(w in lower for w in ["customer", "onboarding", "churn"]),
        "bugs": any(w in lower for w in ["bug", "sla", "defect"]),
    }

    missing = [d for d, found in dimensions.items() if not found]
    if len(missing) >= 3:
        return (False, f"Exec report missing dimensions: {missing}. "
                "Must cover engineering, GTM, compliance, CS, and bug health.")

    return (True, raw)


# ── Daily Pulse Crew ─────────────────────────────────────────────────────────

def validate_standup_posted(result) -> Tuple[bool, Any]:
    """Ensure standup was actually posted to Slack."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    if "post_standup" not in lower and "posted" not in lower and "confirmation" not in lower:
        return (False, "Standup must be posted to Slack. "
                "Use the post_standup tool to post the digest.")

    return (True, raw)


# ── Deal Intel Crew ──────────────────────────────────────────────────────────

def validate_deal_intel(result) -> Tuple[bool, Any]:
    """Ensure pipeline analysis includes vertical breakdown."""
    raw = result.raw if hasattr(result, "raw") else str(result)
    lower = raw.lower()

    if "vertical" not in lower and "healthcare" not in lower and "pipeline" not in lower:
        return (False, "Deal intel must include pipeline analysis by vertical. "
                "Group deals by vertical tags and identify coverage gaps.")

    return (True, raw)
