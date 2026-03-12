"""
tools/vanta.py -- Vanta Compliance Platform REST API tools.

Vanta is the source of truth for CareSpace compliance.
These tools pull live data from Vanta directly -- controls, tests, risks, vendors,
access reviews, vulnerabilities -- and feed it into the compliance crew.

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
        "https://app.vanta.com/oauth/token",
        json={
            "client_id": cid,
            "client_secret": csecret,
            "grant_type": "client_credentials",
            "scope": "vanta-api.all:read",
        },
    )
    r.raise_for_status()
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

def _paginate(path: str, params: dict | None = None, limit: int = 100) -> list:
    p = dict(params or {})
    p["pageSize"] = min(limit, 100)
    out = []
    while True:
        data = _get(path, p)
        results = data.get("data", {}).get("results", [])
        out.extend(results)
        cursor = data.get("data", {}).get("pageInfo", {}).get("endCursor")
        if not cursor or not results:
            break
        p["pageCursor"] = cursor
    return out

def _days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
        return (d - date.today()).days
    except:
        return None

def _days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
        return (date.today() - d).days
    except:
        return None


# == CONTROLS & TESTS ==

@tool("Get Vanta Controls")
def get_controls(framework: str = "", status_filter: str = "") -> str:
    """
    Returns all Vanta controls with their test status.
    framework: filter by framework slug (e.g. 'soc2', 'hipaa'). Empty = all.
    status_filter: 'failing' / 'passing' / 'disabled' / 'needs_attention'. Empty = all.
    """
    params: dict = {}
    if framework:
        params["frameworkSlugs"] = framework

    controls = _paginate("/controls", params)

    out = []
    for c in controls:
        s = c.get("status", "unknown").lower()
        if status_filter and s != status_filter.lower():
            continue

        failing = sum(
            1 for t in c.get("tests", [])
            if t.get("status", "").lower() in ("failing", "fail")
        )

        out.append({
            "control_id": c.get("id"),
            "name": c.get("name"),
            "description": c.get("description", "")[:200],
            "framework": c.get("frameworkSlug", ""),
            "status": s,
            "failing_tests_count": failing,
            "total_tests": len(c.get("tests", [])),
            "owner_email": (c.get("owner") or {}).get("email"),
            "last_tested": c.get("lastTestedAt"),
            "days_since_tested": _days_since(c.get("lastTestedAt")),
        })

    return json.dumps(out, indent=2)


@tool("Get Vanta Failing Tests")
def get_failing_tests(framework: str = "") -> str:
    """
    Returns all currently failing Vanta automated tests.
    framework: 'soc2' / 'hipaa'. Empty = all failing tests across all frameworks.
    """
    params: dict = {"status": "FAILING"}
    if framework:
        params["frameworkSlugs"] = framework

    tests = _paginate("/tests", params)

    out = []
    for t in tests:
        out.append({
            "test_id": t.get("id"),
            "name": t.get("name"),
            "description": t.get("description", "")[:300],
            "control_name": (t.get("control") or {}).get("name"),
            "framework": t.get("frameworkSlug", ""),
            "severity": t.get("severity", "medium").lower(),
            "status": t.get("status", "").lower(),
            "failing_resources": t.get("failingResourceCount", 0),
            "owner_email": (t.get("owner") or {}).get("email"),
            "remediation_hint": t.get("remediationGuide", "")[:300],
            "failing_since": t.get("firstFailedAt"),
            "days_failing": _days_since(t.get("firstFailedAt")),
        })

    return json.dumps(out, indent=2)


@tool("Get Vanta Control Evidence")
def get_evidence(control_id: str) -> str:
    """
    Returns the evidence items attached to a specific Vanta control.
    control_id: from get_controls().
    """
    data = _get(f"/controls/{control_id}/evidence")
    evidence = data.get("data", {}).get("results", [])

    return json.dumps([{
        "evidence_id": e.get("id"),
        "name": e.get("name"),
        "type": e.get("type"),
        "status": e.get("status", "").lower(),
        "uploader_email": (e.get("uploader") or {}).get("email"),
        "uploaded_at": e.get("uploadedAt"),
        "due_date": e.get("dueDate"),
        "days_until_due": _days_until(e.get("dueDate")),
        "is_overdue": (_days_until(e.get("dueDate")) or 1) < 0,
    } for e in evidence], indent=2)


# == VULNERABILITIES ==

@tool("Get Vanta Vulnerabilities")
def get_vulnerabilities(severity: str = "", status: str = "open") -> str:
    """
    Returns security vulnerabilities tracked in Vanta.
    severity: 'critical' / 'high' / 'medium' / 'low'. Empty = all.
    status: 'open' (default) / 'fixed' / 'ignored'.
    """
    params: dict = {}
    if severity:
        params["severity"] = severity.upper()
    if status:
        params["status"] = status.upper()

    vulns = _paginate("/vulnerabilities", params)

    SLA = {"critical": 7, "high": 30, "medium": 90, "low": 180}

    out = []
    for v in vulns:
        sev = v.get("severity", "medium").lower()
        first_detected = v.get("firstDetectedAt")
        days_open = _days_since(first_detected) or 0
        sla_days = SLA.get(sev, 90)
        days_until_sla = sla_days - days_open

        out.append({
            "vuln_id": v.get("id"),
            "title": v.get("title"),
            "severity": sev,
            "cve_ids": v.get("cveIds", []),
            "affected_resource": v.get("resourceName"),
            "resource_type": v.get("resourceType"),
            "first_detected": first_detected,
            "days_open": days_open,
            "sla_days": sla_days,
            "days_until_sla": days_until_sla,
            "sla_breached": days_until_sla < 0,
            "description": v.get("description", "")[:300],
        })

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    out.sort(key=lambda x: (sev_order.get(x["severity"], 4), -x.get("days_open", 0)))

    return json.dumps(out, indent=2)


# == VENDORS & RISK ==

@tool("Get Vanta Vendors")
def get_vendors(risk_level: str = "") -> str:
    """
    Returns all vendors in the Vanta vendor risk register.
    risk_level: 'high' / 'medium' / 'low'. Empty = all.
    """
    vendors = _paginate("/vendors")

    out = []
    for v in vendors:
        rl = v.get("riskLevel", "").lower()
        if risk_level and rl != risk_level.lower():
            continue

        baa = v.get("baa") or {}
        q = v.get("securityQuestionnaire") or {}
        q_due = q.get("dueDate")

        has_phi = v.get("receivesPHI", False) or v.get("storesPHI", False)

        out.append({
            "vendor_id": v.get("id"),
            "name": v.get("name"),
            "risk_level": rl,
            "risk_tier": v.get("riskTier"),
            "processes_phi": has_phi,
            "has_baa": baa.get("signed", False),
            "baa_status": baa.get("status", "none").lower(),
            "baa_expiry": baa.get("expiresAt"),
            "baa_days_until_expiry": _days_until(baa.get("expiresAt")),
            "missing_baa_and_phi": has_phi and not baa.get("signed", False),
            "questionnaire_status": q.get("status", "none").lower(),
            "questionnaire_due": q_due,
            "questionnaire_days_until_due": _days_until(q_due),
            "last_reviewed": v.get("lastReviewedAt"),
            "days_since_review": _days_since(v.get("lastReviewedAt")),
        })

    return json.dumps(out, indent=2)


@tool("Get Vanta BAA Gaps")
def get_baa_gaps() -> str:
    """
    Returns vendors that process PHI but have no signed BAA.
    This is a critical HIPAA violation -- every result here needs immediate action.
    """
    vendors = json.loads(get_vendors(""))
    gaps = [v for v in vendors if v.get("missing_baa_and_phi")]

    return json.dumps([{
        "vendor_id": v["vendor_id"],
        "vendor_name": v["name"],
        "risk_level": v["risk_level"],
        "questionnaire_status": v["questionnaire_status"],
        "action": (
            "CRITICAL: Vendor processes PHI without signed BAA. "
            "Obtain BAA immediately or revoke PHI access."
        ),
    } for v in gaps], indent=2)


# == ACCESS REVIEWS ==

@tool("Get Vanta Access Reviews")
def get_access_reviews(status: str = "") -> str:
    """
    Returns Vanta access reviews.
    status: 'pending' / 'completed' / 'overdue'. Empty = all.
    """
    reviews = _paginate("/accessReviews")

    out = []
    for r in reviews:
        s = r.get("status", "").lower()
        if status and s != status.lower():
            continue

        due = r.get("dueDate")
        days_until = _days_until(due)
        is_overdue = (days_until is not None and days_until < 0) or s == "overdue"

        out.append({
            "review_id": r.get("id"),
            "name": r.get("name"),
            "status": s,
            "reviewer_email": (r.get("reviewer") or {}).get("email"),
            "due_date": due,
            "days_until_due": days_until,
            "is_overdue": is_overdue,
            "completed_at": r.get("completedAt"),
            "scope": r.get("scope"),
            "resources_count": r.get("resourcesCount", 0),
        })

    return json.dumps(out, indent=2)


# == PEOPLE & USER ACCOUNTS ==

@tool("Get Vanta People Risks")
def get_people_risks() -> str:
    """
    Returns people-related compliance risks: offboarded users with active access,
    users without MFA, users with excessive permissions.
    """
    people = _paginate("/people")

    risks = []
    for p in people:
        email = p.get("email", "unknown")

        if p.get("isOffboarded") and p.get("hasActiveAccess"):
            risks.append({
                "email": email,
                "risk_type": "offboarded_with_access",
                "severity": "critical",
                "description": "User is offboarded but still has active system access",
                "soc2_control": "CC6.2",
                "action": "Immediately revoke all access for this user",
            })

        if not p.get("mfaEnabled") and not p.get("isOffboarded"):
            risks.append({
                "email": email,
                "risk_type": "missing_mfa",
                "severity": "high",
                "description": "Active user has no MFA enabled",
                "soc2_control": "CC6.1",
                "action": "Require MFA enrollment within 24 hours",
            })

        last_active = p.get("lastActiveAt")
        days_inactive = _days_since(last_active) or 0
        if days_inactive > 90 and not p.get("isOffboarded"):
            risks.append({
                "email": email,
                "risk_type": "inactive_active_user",
                "severity": "medium",
                "description": f"Active user account with no login in {days_inactive} days",
                "soc2_control": "CC6.2",
                "action": "Review and deactivate if no longer needed",
            })

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda x: sev_order.get(x["severity"], 4))

    return json.dumps(risks, indent=2)


# == COMPREHENSIVE COMPLIANCE HEALTH SNAPSHOT ==

@tool("Get Vanta Compliance Health Summary")
def get_health_summary() -> str:
    """
    Returns a complete compliance health snapshot across all dimensions.
    Use this as the PRIMARY ENTRY POINT for the compliance crew.
    """
    try:
        failing_controls = json.loads(get_controls(status_filter="failing"))
    except: failing_controls = []

    try:
        failing_tests = json.loads(get_failing_tests())
    except: failing_tests = []

    try:
        critical_vulns = json.loads(get_vulnerabilities(severity="critical"))
        high_vulns     = json.loads(get_vulnerabilities(severity="high"))
    except: critical_vulns = high_vulns = []

    try:
        baa_gaps = json.loads(get_baa_gaps())
    except: baa_gaps = []

    try:
        overdue_reviews = [r for r in json.loads(get_access_reviews()) if r.get("is_overdue")]
    except: overdue_reviews = []

    try:
        people_risks = json.loads(get_people_risks())
        critical_people = [r for r in people_risks if r.get("severity") == "critical"]
    except: people_risks = critical_people = []

    try:
        vendors = json.loads(get_vendors())
        urgent_questionnaires = [
            v for v in vendors
            if v.get("questionnaire_days_until_due") is not None
            and 0 <= v.get("questionnaire_days_until_due", 99) <= 7
        ]
    except: urgent_questionnaires = []

    critical_issues = (
        len([c for c in failing_controls if c.get("framework") in ("soc2", "hipaa")]) +
        len(critical_vulns) + len(baa_gaps) + len(critical_people)
    )
    health = "GREEN" if critical_issues == 0 else ("YELLOW" if critical_issues <= 2 else "RED")

    soc2_failing = len([c for c in failing_controls if c.get("framework") == "soc2"])
    hipaa_failing = len([c for c in failing_controls if c.get("framework") == "hipaa"])

    summary = {
        "health_indicator": health,
        "critical_issues_total": critical_issues,
        "as_of": date.today().isoformat(),
        "controls": {
            "soc2_failing": soc2_failing,
            "hipaa_failing": hipaa_failing,
            "total_failing": len(failing_controls),
            "top_failing": [c["name"] for c in failing_controls[:5]],
        },
        "tests": {
            "total_failing": len(failing_tests),
            "critical_severity": len([t for t in failing_tests if t.get("severity") == "critical"]),
            "high_severity": len([t for t in failing_tests if t.get("severity") == "high"]),
        },
        "vulnerabilities": {
            "critical_open": len(critical_vulns),
            "high_open": len(high_vulns),
            "sla_breached": len([v for v in critical_vulns + high_vulns if v.get("sla_breached")]),
        },
        "hipaa": {
            "baa_gaps": len(baa_gaps),
            "vendors_missing_baa": [v["vendor_name"] for v in baa_gaps],
        },
        "access_reviews": {
            "overdue": len(overdue_reviews),
            "overdue_names": [r["name"] for r in overdue_reviews],
        },
        "people": {
            "offboarded_with_access": len(critical_people),
            "missing_mfa": len([r for r in people_risks if r.get("risk_type") == "missing_mfa"]),
            "inactive_active": len([r for r in people_risks if r.get("risk_type") == "inactive_active_user"]),
        },
        "upcoming_deadlines": {
            "questionnaires_due_7d": len(urgent_questionnaires),
            "questionnaire_vendors": [v["name"] for v in urgent_questionnaires],
        },
    }

    return json.dumps(summary, indent=2)


# == POLICY DOCUMENTS ==

@tool("Get Vanta Policies")
def get_policies(status: str = "") -> str:
    """
    Returns all policies tracked in Vanta.
    status: 'approved' / 'needs_review' / 'draft'. Empty = all.
    """
    policies = _paginate("/policies")

    out = []
    for p in policies:
        s = p.get("status", "").lower()
        if status and s != status.lower():
            continue

        next_review = p.get("nextReviewDate")

        out.append({
            "policy_id": p.get("id"),
            "name": p.get("name"),
            "status": s,
            "owner_email": (p.get("owner") or {}).get("email"),
            "last_approved": p.get("lastApprovedAt"),
            "next_review_due": next_review,
            "days_until_review": _days_until(next_review),
            "review_overdue": (_days_until(next_review) or 1) < 0,
        })

    return json.dumps(out, indent=2)
