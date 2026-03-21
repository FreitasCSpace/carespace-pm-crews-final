"""
tools/vanta.py -- Vanta Compliance Platform REST API tools.

Vanta is the source of truth for CareSpace compliance.
These tools pull live data from Vanta directly -- tests, controls, vendors,
people, policies -- and feed it into the compliance crew.

Authentication:
  Set VANTA_CLIENT_ID and VANTA_CLIENT_SECRET in your .env file.
  Vanta uses OAuth2 client credentials (not an API key).
"""

import os
import json
import requests
from datetime import datetime, timedelta, date
from crewai.tools import tool

# -- Auth --

_token: str | None = None
_token_expiry: datetime | None = None

VANTA_TOKEN_URL = "https://api.vanta.com/oauth/token"
VANTA_BASE = "https://api.vanta.com/v1"


def _get_token() -> str:
    global _token, _token_expiry
    now = datetime.utcnow()
    if _token and _token_expiry and now < _token_expiry:
        return _token

    cid = os.environ.get("VANTA_CLIENT_ID")
    csecret = os.environ.get("VANTA_CLIENT_SECRET")
    if not cid or not csecret:
        raise RuntimeError(
            "Missing VANTA_CLIENT_ID or VANTA_CLIENT_SECRET. "
            "Add them to your .env file."
        )

    r = requests.post(
        VANTA_TOKEN_URL,
        json={
            "client_id": cid,
            "client_secret": csecret,
            "grant_type": "client_credentials",
            "scope": "vanta-api.all:read",
        },
    )
    r.raise_for_status()

    if not r.text or "text/html" in r.headers.get("Content-Type", ""):
        raise RuntimeError(
            "Vanta auth returned HTML instead of JSON. "
            "Check VANTA_CLIENT_ID/SECRET and that api.vanta.com is reachable."
        )

    data = r.json()
    _token = data["access_token"]
    _token_expiry = now + timedelta(seconds=data.get("expires_in", 3600) - 60)
    return _token


def _h() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict | None = None) -> dict:
    r = requests.get(f"{VANTA_BASE}{path}", headers=_h(), params=params)
    r.raise_for_status()
    return r.json()


def _paginate(path: str, params: dict | None = None, limit: int = 500) -> list:
    """Paginate Vanta v1 API. Response shape: results.data[] + results.pageInfo."""
    p = dict(params or {})
    p["pageSize"] = min(limit, 100)
    out = []
    while True:
        data = _get(path, p)
        results_wrapper = data.get("results", {})
        items = results_wrapper.get("data", [])
        out.extend(items)
        if len(out) >= limit:
            break
        page_info = results_wrapper.get("pageInfo", {})
        cursor = page_info.get("endCursor")
        if not cursor or not page_info.get("hasNextPage"):
            break
        p["pageCursor"] = cursor
    return out


def _days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
        return (d - date.today()).days
    except Exception:
        return None


def _days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
        return (date.today() - d).days
    except Exception:
        return None


# == TESTS ==
# Tests are the primary compliance signal in Vanta v1 API.
# Status values: OK, NEEDS_ATTENTION, DEACTIVATED

CRITICAL_TEST_KEYWORDS = [
    "encryption", "screenlock", "mfa", "password manager",
    "malware", "offboarding", "access", "phi", "hipaa",
    "incident response", "security training",
]


def _is_critical_test(name: str) -> bool:
    """Flag tests that represent high-risk compliance failures."""
    lower = name.lower()
    return any(kw in lower for kw in CRITICAL_TEST_KEYWORDS)


# -- Internal functions (called by health summary and tools) --

def _fetch_tests(status_filter: str = "") -> list:
    """Fetch all Vanta tests, optionally filtered by status."""
    tests = _paginate("/tests")

    out = []
    for t in tests:
        s = t.get("status", "unknown").upper()
        if status_filter and s != status_filter.upper():
            continue

        owner = t.get("owner") or {}
        out.append({
            "test_id": t.get("id"),
            "name": t.get("name"),
            "status": s,
            "is_critical": _is_critical_test(t.get("name", "")),
            "description": (t.get("description") or "")[:200],
            "category": t.get("category"),
            "owner_email": owner.get("emailAddress", "unowned"),
            "last_run": t.get("lastTestRunDate"),
            "days_since_last_run": _days_since(t.get("lastTestRunDate")),
            "latest_flip": t.get("latestFlipDate"),
            "remediation_hint": (t.get("remediationDescription") or "")[:300],
        })

    return out


def _fetch_controls(domain_filter: str = "") -> list:
    """Fetch all Vanta controls, optionally filtered by domain."""
    controls = _paginate("/controls")

    out = []
    for c in controls:
        domains = c.get("domains", [])
        if domain_filter and domain_filter.upper() not in [d.upper() for d in domains]:
            continue

        owner = c.get("owner") or {}
        out.append({
            "control_id": c.get("id"),
            "external_id": c.get("externalId"),
            "name": c.get("name"),
            "description": (c.get("description") or "")[:200],
            "domains": domains,
            "source": c.get("source"),
            "owner_email": owner.get("emailAddress") if owner else "unowned",
        })

    return out


def _fetch_vendors() -> list:
    """Fetch all vendors from Vanta."""
    vendors = _paginate("/vendors")

    out = []
    for v in vendors:
        category = v.get("category") or {}
        next_review = v.get("nextSecurityReviewDueDate")
        last_review = v.get("lastSecurityReviewCompletionDate")

        out.append({
            "vendor_id": v.get("id"),
            "name": v.get("name"),
            "website": v.get("websiteUrl"),
            "category": category.get("displayName", "unknown"),
            "is_risk_auto_scored": v.get("isRiskAutoScored", False),
            "is_visible_to_auditors": v.get("isVisibleToAuditors", False),
            "next_security_review_due": next_review,
            "days_until_security_review": _days_until(next_review),
            "review_overdue": (_days_until(next_review) or 1) < 0 if next_review else None,
            "last_security_review": last_review,
            "days_since_review": _days_since(last_review),
            "security_owner_id": v.get("securityOwnerUserId"),
            "business_owner_id": v.get("businessOwnerUserId"),
        })

    return out


def _fetch_people_risks() -> list:
    """Fetch people-related compliance risks from Vanta."""
    people = _paginate("/people")

    risks = []
    for p in people:
        emp = p.get("employment") or {}
        emp_status = emp.get("status", "UNKNOWN").upper()
        name_obj = p.get("name") or {}
        display_name = name_obj.get("display", "Unknown")
        email = p.get("emailAddress", "unknown")
        tasks = p.get("tasksSummary") or {}
        task_status = tasks.get("status", "UNKNOWN")

        # Former employee with incomplete offboarding
        if emp_status == "FORMER" and task_status != "OFFBOARDING_COMPLETE":
            risks.append({
                "name": display_name,
                "email": email,
                "risk_type": "incomplete_offboarding",
                "severity": "critical",
                "description": f"Former employee with offboarding status: {task_status}",
                "action": "Complete offboarding process and revoke all access",
            })

        # Active employee with overdue tasks
        if emp_status == "CURRENT" and task_status == "DUE_SOON":
            details = tasks.get("details", {})
            incomplete = []
            for task_key, task_info in details.items():
                if isinstance(task_info, dict):
                    ts = task_info.get("status", "")
                    if ts in ("DUE_SOON", "OVERDUE"):
                        trainings = task_info.get("incompleteTrainings", [])
                        for tr in trainings:
                            incomplete.append(tr.get("name", task_key))
                        if not trainings:
                            incomplete.append(task_key)

            if incomplete:
                risks.append({
                    "name": display_name,
                    "email": email,
                    "risk_type": "overdue_tasks",
                    "severity": "high",
                    "description": f"Incomplete: {', '.join(incomplete[:5])}",
                    "action": "Complete outstanding compliance tasks",
                })

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda x: sev_order.get(x["severity"], 4))

    return risks


def _fetch_policies(status_filter: str = "") -> list:
    """Fetch all policies from Vanta."""
    policies = _paginate("/policies")

    out = []
    for p in policies:
        s = (p.get("status") or "unknown").lower()
        if status_filter and s != status_filter.lower():
            continue

        owner = p.get("owner") or {}
        out.append({
            "policy_id": p.get("id"),
            "name": p.get("name"),
            "status": s,
            "owner_email": owner.get("emailAddress") if owner else "unowned",
            "last_approved": p.get("lastApprovedAt"),
            "next_review_due": p.get("nextReviewDate"),
            "days_until_review": _days_until(p.get("nextReviewDate")),
            "review_overdue": (_days_until(p.get("nextReviewDate")) or 1) < 0,
        })

    return out


# -- CrewAI tool wrappers --

@tool("Get Vanta Tests")
def get_tests(status_filter: str = "") -> str:
    """
    Returns all Vanta automated tests with their current status.
    status_filter: 'ok' / 'needs_attention' / 'deactivated'. Empty = all.
    """
    return json.dumps(_fetch_tests(status_filter), indent=2)


@tool("Get Vanta Failing Tests")
def get_failing_tests() -> str:
    """
    Returns all Vanta tests that need attention (status != OK).
    These are tests the compliance crew should focus on resolving.
    """
    return json.dumps(_fetch_tests("NEEDS_ATTENTION"), indent=2)


@tool("Get Vanta Controls")
def get_controls(domain_filter: str = "") -> str:
    """
    Returns all Vanta controls (structural compliance requirements).
    domain_filter: filter by domain (e.g. 'ASSET_MANAGEMENT'). Empty = all.
    Controls in Vanta v1 don't have pass/fail status — tests provide that signal.
    """
    return json.dumps(_fetch_controls(domain_filter), indent=2)


@tool("Get Vanta Vendors")
def get_vendors() -> str:
    """Returns all vendors in the Vanta vendor register."""
    return json.dumps(_fetch_vendors(), indent=2)


@tool("Get Vanta People Risks")
def get_people_risks() -> str:
    """
    Returns people-related compliance risks: former employees with
    incomplete offboarding, overdue onboarding tasks, incomplete training.
    """
    return json.dumps(_fetch_people_risks(), indent=2)


@tool("Get Vanta Policies")
def get_policies(status_filter: str = "") -> str:
    """
    Returns all policies tracked in Vanta.
    status_filter: filter by status. Empty = all.
    """
    return json.dumps(_fetch_policies(status_filter), indent=2)


# == COMPREHENSIVE COMPLIANCE HEALTH SNAPSHOT ==

@tool("Get Vanta Compliance Health Summary")
def get_health_summary() -> str:
    """
    Returns a complete compliance health snapshot across all dimensions.
    Use this as the PRIMARY ENTRY POINT for the compliance crew.

    Health indicator logic:
      RED    — test pass rate < 70% OR any critical test failing and unowned
      YELLOW — test pass rate < 90% OR critical test failing (owned)
      GREEN  — >= 90% tests passing, no critical unowned failures
    """
    errors = []

    # -- Tests (primary signal) --
    try:
        all_tests = _fetch_tests()
    except Exception as e:
        all_tests = []
        errors.append(f"Failed to fetch tests: {e}")

    active_tests = [t for t in all_tests if t.get("status") != "DEACTIVATED"]
    ok_tests = [t for t in active_tests if t.get("status") == "OK"]
    failing_tests = [t for t in active_tests if t.get("status") == "NEEDS_ATTENTION"]
    total_active = len(active_tests)
    pass_rate = len(ok_tests) / total_active if total_active > 0 else 0

    critical_failing = [t for t in failing_tests if t.get("is_critical")]
    critical_unowned = [t for t in critical_failing
                        if t.get("owner_email") in ("unowned", None, "")]

    # -- People risks --
    try:
        people_risks = _fetch_people_risks()
    except Exception as e:
        people_risks = []
        errors.append(f"Failed to fetch people: {e}")

    critical_people = [r for r in people_risks if r.get("severity") == "critical"]
    high_people = [r for r in people_risks if r.get("severity") == "high"]

    # -- Vendors --
    try:
        vendors = _fetch_vendors()
        overdue_reviews = [v for v in vendors if v.get("review_overdue")]
    except Exception as e:
        vendors = []
        overdue_reviews = []
        errors.append(f"Failed to fetch vendors: {e}")

    # -- Policies --
    try:
        policies = _fetch_policies()
        overdue_policies = [p for p in policies if p.get("review_overdue")]
    except Exception as e:
        policies = []
        overdue_policies = []
        errors.append(f"Failed to fetch policies: {e}")

    # -- Health indicator --
    if errors and total_active == 0:
        health = "UNKNOWN"
        health_reason = f"Could not fetch Vanta data: {'; '.join(errors)}"
    elif pass_rate < 0.70 or len(critical_unowned) > 0 or len(critical_people) > 0:
        health = "RED"
        reasons = []
        if pass_rate < 0.70:
            reasons.append(f"test pass rate {pass_rate:.0%} (< 70%)")
        if critical_unowned:
            reasons.append(f"{len(critical_unowned)} critical unowned test(s) failing")
        if critical_people:
            reasons.append(f"{len(critical_people)} critical people risk(s)")
        health_reason = "; ".join(reasons)
    elif pass_rate < 0.90 or len(critical_failing) > 0 or len(high_people) > 3:
        health = "YELLOW"
        reasons = []
        if pass_rate < 0.90:
            reasons.append(f"test pass rate {pass_rate:.0%} (< 90%)")
        if critical_failing:
            reasons.append(f"{len(critical_failing)} critical test(s) failing (owned)")
        if len(high_people) > 3:
            reasons.append(f"{len(high_people)} people with overdue tasks")
        health_reason = "; ".join(reasons)
    else:
        health = "GREEN"
        health_reason = f"test pass rate {pass_rate:.0%}, no critical failures"

    summary = {
        "health_indicator": health,
        "health_reason": health_reason,
        "as_of": date.today().isoformat(),
        "tests": {
            "total_active": total_active,
            "passing": len(ok_tests),
            "needs_attention": len(failing_tests),
            "pass_rate": f"{pass_rate:.0%}",
            "critical_failing": len(critical_failing),
            "critical_unowned": len(critical_unowned),
            "top_failing": [
                {"name": t["name"], "owner": t.get("owner_email", "unowned"),
                 "is_critical": t.get("is_critical", False)}
                for t in failing_tests[:10]
            ],
        },
        "people": {
            "critical_risks": len(critical_people),
            "high_risks": len(high_people),
            "total_risks": len(people_risks),
            "top_risks": [
                {"name": r["name"], "risk_type": r["risk_type"],
                 "severity": r["severity"]}
                for r in people_risks[:5]
            ],
        },
        "vendors": {
            "total": len(vendors),
            "overdue_reviews": len(overdue_reviews),
            "vendor_names": [v["name"] for v in vendors],
        },
        "policies": {
            "total": len(policies),
            "overdue_reviews": len(overdue_policies),
            "overdue_names": [p["name"] for p in overdue_policies],
        },
        "errors": errors if errors else None,
    }

    return json.dumps(summary, indent=2)
