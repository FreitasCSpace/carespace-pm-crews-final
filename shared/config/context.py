"""
context.py — Single source of truth for the CareSpace AI PM system.
Simplified architecture: 2 spaces, tags for domain visibility, one backlog.

Redesigned 2026-03-17. Previous version had 6 spaces / 150+ lists.
New: 2 spaces, ~16 lists. Domain routing via tags, not separate lists.
"""

WORKSPACE_ID = "31124097"
GITHUB_ORG   = "carespace-ai"

# ======================================================================
# SPACES (2 total — down from 6)
# ======================================================================
SPACES = {
    "engine": "901313687155",      # Everything product, engineering, ops
    "gtm":    "901313687157",      # Sales, marketing, customer success
}

# ======================================================================
# FOLDERS
# ======================================================================
FOLDERS = {
    # CareSpace Engine
    "backlog":          "901317811713",
    "sprint_planning":  "901317852083",
    "sprints":          "901317811717",
    "operations":       "901317811718",
    "playbooks":        "901317811721",
    # GTM & Revenue
    "pipeline":          "901317811738",
    "marketing":         "901317811726",
    "customer_success":  "901317811730",
}

# ======================================================================
# LISTS — The only IDs crews need
# ======================================================================
L = {
    # === CareSpace Engine ===
    # Backlog (single intake point — everything lands here)
    "master_backlog":       "901326439232",

    # Sprints
    "sprint_candidates":    "901326510572",   # Staging area — tasks proposed for next sprint
    # sprint_crew creates: "Sprint N — {start} to {end}" in folder 901317811717

    # Operations
    "alerts":               "901326439234",   # Alerts & Escalations
    "sprint_history":       "901326439238",   # Sprint History & Metrics

    # === GTM & Revenue ===
    # Pipeline
    "active_deals":         "901326439255",
    "at_risk_deals":        "901326439258",

    # Marketing
    "content_campaigns":    "901326439261",   # Content & Campaigns
    "product_launches":     "901326439262",   # Product Launches

    # Customer Success
    "onboarding_accounts":  "901326439266",   # Onboarding & Accounts
    "support_escalations":  "901326439271",   # Support Escalations
}

# ======================================================================
# TAGS — Replace separate lists for domain/type visibility
# ======================================================================
# Crews apply these tags when creating/triaging tasks.
# Team uses saved Views filtered by tags.
DOMAIN_TAGS = [
    "frontend", "backend", "mobile", "sdk",
    "ai-cv", "infra", "bots", "video",
]

TYPE_TAGS = [
    "bug", "feature", "tech-debt", "security",
    "compliance", "pr-review", "ci-fix", "task",
]

SOURCE_TAGS = [
    "github", "vanta", "client-feedback", "internal",
]

VERTICAL_TAGS = [
    "healthcare", "insurance", "employers", "senior-care",
    "sports", "construction", "manufacturing", "corrections",
    "public-services",
]

# ======================================================================
# GITHUB -> TAG ROUTING (replaces BUG_TARGET / FEATURE_TARGET)
# ======================================================================
# intake_crew tags tasks by domain — everything goes to master_backlog
REPO_DOMAIN = {
    "carespace-ui":                        "frontend",
    "carespace-landingpage":               "frontend",
    "carespace-site":                      "frontend",
    "CareSpace-LMS":                       "frontend",
    "meta-web-view":                       "frontend",
    "healthstartiq":                       "frontend",
    "whoop-integrator-react":              "frontend",
    "carespace-admin":                     "backend",
    "carespace-api-gateway":               "backend",
    "carespace-strapi":                    "backend",
    "carespace-strapi-services":           "backend",
    "carespace-mobile-android":            "mobile",
    "carespace-mobile-ios":                "mobile",
    "carespace_mobile":                    "mobile",
    "carespace-sdk":                       "sdk",
    "PoseEstimator":                       "ai-cv",
    "carespace-poseestimation":            "ai-cv",
    "carespace-poseestimation-classifier": "ai-cv",
    "mediapipeAnnotateVideo":              "ai-cv",
    "MetaHumanCoach":                      "ai-cv",
    "carespace-botkit":                    "bots",
    "carespace-chat":                      "bots",
    "acs":                                 "bots",
    "carespace-media-converter":           "video",
    "carespace-video-converter":           "video",
    "Carespace-VirtualCam":                "video",
    "carespace-docker":                    "infra",
    "carespace-fusionauth":               "infra",
    "carespace-monitoring":                "infra",
    "carespace-bug-tracker":               "infra",
}

# Everything routes to master_backlog with tags — no more per-domain lists
INTAKE_TARGET = L["master_backlog"]

# ======================================================================
# COMPLIANCE REPO (VantaCrews creates issues here — we ingest them)
# ======================================================================
COMPLIANCE_REPO = "FreitasCSpace/CareSpace-Compliance-Repo"

# VantaCrews labels → our ClickUp tags + priority
COMPLIANCE_LABEL_MAP = {
    # Priority labels
    "P0-critical": {"priority": "urgent"},
    "P1-high":     {"priority": "high"},
    "P2-medium":   {"priority": "normal"},
    "P3-low":      {"priority": "low"},
    # Type labels → tags
    "compliance":      {"tag": "compliance"},
    "soc2":            {"tag": "soc2"},
    "HIPAA":           {"tag": "hipaa"},
    "control-failure": {"tag": "compliance"},
    "evidence-gap":    {"tag": "compliance"},
    "risk":            {"tag": "security"},
    "access-review":   {"tag": "compliance"},
    "vendor-risk":     {"tag": "compliance"},
    "vulnerability":   {"tag": "security"},
    "asset":           {"tag": "infra"},
    "personnel":       {"tag": "compliance"},
    "tests":           {"tag": "compliance"},
    "integration":     {"tag": "infra"},
    "policy":          {"tag": "compliance"},
    "document":        {"tag": "compliance"},
    "trust-center":    {"tag": "compliance"},
    "needs-upload":    {"tag": "compliance"},
    "overdue":         {"tag": "compliance"},
}

DOMAIN_KEYWORDS = {
    "frontend": ["ui","react","css","storybook","design system","kiosk","dashboard","typescript","nextjs","html","component","plumb line","rom scan","onboarding ui"],
    "backend":  ["api","endpoint","gateway","strapi","auth","rbac","guard","middleware","database","prisma","nestjs","node","rest","graphql","webhook"],
    "mobile":   ["android","ios","flutter","mobile","swift","kotlin","wkwebview","offline","push notification","intake screen"],
    "sdk":      ["sdk","native sdk","production readiness","android sdk","ios sdk","sdk v1"],
    "ai-cv":    ["pose","cv","computer vision","model","inference","mediapipe","rom analysis","poseestimator","skeleton","ml","ai","opencv","classifier"],
    "infra":    ["docker","azure","kubernetes","ci","cd","pipeline","monitoring","fusionauth","nginx","ssl","devops","github actions","deployment"],
    "bots":     ["botkit","chat","acs","azure communication","risecx"],
    "video":    ["video","media","converter","virtualcam","webcam","webm"],
}

# ======================================================================
# TEAM
# ======================================================================
TEAM = {
    # Core engineering
    "fusuma":            {"domains": ["ai-cv","sdk","mobile","backend"], "cap_sp": 20, "max_tasks": 4, "cu_id": "48998538"},
    "andreCarespace":    {"domains": ["frontend"],                       "cap_sp": 20, "max_tasks": 4, "cu_id": "49000180"},
    "BMarcano":          {"domains": ["frontend"],                       "cap_sp": 18, "max_tasks": 3, "cu_id": "112101513"},
    "bhavyasaurabh":     {"domains": ["ai-cv","frontend"],              "cap_sp": 18, "max_tasks": 3, "cu_id": "93908266"},
    "Deekshakain":       {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "61019156"},
    "binunexturn":       {"domains": ["frontend","backend"],             "cap_sp": 20, "max_tasks": 4, "cu_id": "61025897"},
    "fabiano-carespace": {"domains": ["backend","infra"],                "cap_sp": 18, "max_tasks": 3, "cu_id": "49000181"},
    "YeddulaBharath":    {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "93908270"},
    "R-Kapil-Kumar":     {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "81941440"},
    # Nexturn extended team
    "harshitdiyora":     {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "81942238"},
    "ratnakumar":        {"domains": ["mobile","backend"],               "cap_sp": 16, "max_tasks": 3, "cu_id": "81941439"},
    "sreenivas":         {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "93908269"},
    "rohithsuri":        {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "93908271"},
    "sandeep":           {"domains": ["backend","infra"],                "cap_sp": 16, "max_tasks": 3, "cu_id": "111928715"},
    "sujanmahapatra":    {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "111951799"},
    "shubhamsanjog":     {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "112029068"},
    "mubinashaikh":      {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "111980875"},
    "kishorkumar":       {"domains": ["backend"],                        "cap_sp": 16, "max_tasks": 3, "cu_id": "254678220"},
}

# Domain leads — for auto-assignment fallback
DOMAIN_LEADS = {
    "frontend":   "49000180",   # andreCarespace
    "backend":    "49000181",   # fabiano-carespace
    "mobile":     "93908270",   # YeddulaBharath
    "ai-cv":      "93908266",   # bhavyasaurabh
    "sdk":        "93908270",   # YeddulaBharath
    "infra":      "111928715",  # sandeep
    "bots":       "49000181",   # fabiano-carespace
    "video":      "93908266",   # bhavyasaurabh
    "security":   "93908266",   # bhavyasaurabh
    "compliance": "118004891",  # luis freitas — sole compliance owner
    "vanta":      "118004891",  # luis freitas
    "hipaa":      "118004891",  # luis freitas
    "soc2":       "118004891",  # luis freitas
}

# Sprint compliance cap — max compliance tasks per sprint
# Compliance is handled by one person (Luis Freitas), so we cap it
# to avoid filling the entire sprint with compliance work.
MAX_COMPLIANCE_PER_SPRINT = 3

# ======================================================================
# SPRINT CONFIG
# ======================================================================
SPRINT_FOLDER_ID = FOLDERS["sprints"]  # sprint_crew creates lists here (901317811717)
SPRINT_TEMPLATE_LIST_ID = "901326512991"  # template list to duplicate for new sprints

# Custom field ID for Story Points (Number field, space-level)
SP_CUSTOM_FIELD_ID = "1662e3e7-b018-47b7-8881-e30f6831c674"

SCORE = {
    "priority_weight":  {"urgent": 100, "high": 70, "normal": 40, "low": 10},
    "security_multi":   2.0,
    "blocker_multi":    1.8,
    "compliance_multi": 1.5,
    "client_multi":     1.3,
    "age_per_week":     0.5,
    "velocity_buffer":  0.80,
    "default_velocity": 60,
}

SP_ESTIMATE = {
    "security":        8,
    "bug_low":         2,
    "bug_medium":      5,
    "bug_high":        8,
    "feature_small":   5,
    "feature_medium":  13,
    "feature_large":   21,
    "pr_review":       2,
    "ci_fix":          3,
}

# ======================================================================
# BUG SLA (hours until escalation)
# ======================================================================
BUG_SLA = {"urgent": 4, "high": 24, "normal": 72, "low": 168}

# ======================================================================
# SLACK CHANNELS (simplified — fewer, clearer)
# ======================================================================
SLACK = {
    "standup":     "#pm-standup",
    "sprint":      "#pm-sprint-board",
    "engineering": "#pm-engineering",
    "alerts":      "#pm-alerts",
    "gtm":         "#pm-gtm",
    "exec":        "#pm-exec-updates",
    "compliance":  "#pm-compliance",
    "cs":          "#pm-customer-success",
}

# ======================================================================
# CREW SCHEDULE (reference — actual scheduling via CrewHub)
# ======================================================================
CREW_SCHEDULE = {
    # Times in America/Los_Angeles (Oregon) — PDT = UTC-7, PST = UTC-8
    # CrewHub server runs UTC — crons adjusted for PDT (March-November)
    "compliance_crew":        "Daily 06:30 PDT (cron: 30 13 * * *)",
    "intake_crew":            "Daily 07:00 PDT (cron: 0 14 * * *)",
    "daily_pulse_crew":       "Mon-Fri 07:45 PDT (cron: 45 14 * * 1-5)",
    "customer_success_crew":  "Daily 08:30 PDT (cron: 30 15 * * *)",
    "pr_radar_crew":          "Daily 10:00 PDT (cron: 0 17 * * *)",
    "triage_crew":            "Every 6 hours (cron: 0 */6 * * *)",
    "deal_intel_crew":        "Monday 07:00 PDT (cron: 0 14 * * 1)",
    "exec_report_crew":       "Friday 17:00 PDT (cron: 0 0 * * 6)",
    "retrospective_crew":     "Bi-weekly Friday 16:00 PDT (cron: 0 23 * * 5)",
    "sprint_crew":            "Bi-weekly Sunday 18:00 PDT (cron: 0 1 * * 1)",
}

# ======================================================================
# CLICKUP DOCS (for AI-written reports)
# ======================================================================
DOCS = {
    "sprint_engine":    "xnum1-4273",
    "ai_system":        "xnum1-9333",
    "crew_dashboard":   "xnum1-9353",
    "config_manual":    "xnum1-9593",
    "crews_handbook":   "xnum1-9613",
}

# ======================================================================
# THRESHOLDS — Tunable values injected into crew YAML via {variables}
# ======================================================================
THRESHOLDS = {
    # PR & code health
    "stale_pr_days":           7,
    "critical_stale_pr_days":  30,
    "stale_task_days":         3,

    # Customer success
    "onboarding_sla_days":     30,
    "stale_onboarding_days":   7,
    "churn_no_login_days":     14,
    "churn_open_tickets":      3,
    "churn_renewal_days":      60,
    "ticket_unresponded_hours": 24,
    "ticket_stale_hours":      48,

    # Deal intel
    "at_risk_deal_days":       7,

    # Exec report
    "launch_alert_days":       14,
}

# Key repos for CI health checks (daily_pulse, pr_radar)
CI_CHECK_REPOS = [
    "carespace-ui",
    "carespace-admin",
    "carespace-api-gateway",
    "carespace-sdk",
]

# Sprint planning rules
SPRINT_RULES = {
    "budget_sp":      int(SCORE["default_velocity"] * SCORE["velocity_buffer"]),
    "min_features":   3,
    "max_compliance": MAX_COMPLIANCE_PER_SPRINT,
    "target_items":   "10-12",
    "mix": "1-2 bugs + 3-5 features + 2-3 tasks + 2-3 compliance",
}

# Verticals for GTM pipeline (deal_intel_crew)
GTM_VERTICALS = [
    "Healthcare & Rehab", "Insurance & Workers Comp",
    "Employers & Occupational", "Senior & Long-Term Care",
    "Sports Performance", "Construction", "Manufacturing",
    "Corrections", "Public Services",
]


# ======================================================================
# crew_context() — Flat dict injected into every crew via kickoff(inputs)
# ======================================================================
def crew_context(**overrides) -> dict:
    """Build the template variables dict for CrewAI YAML interpolation.

    Every {variable} in agents.yaml / tasks.yaml is resolved from this dict.
    The orchestrator calls this once and passes it to all crews.
    """
    # -- List IDs --
    ctx = {
        "master_backlog_id":       L["master_backlog"],
        "alerts_id":               L["alerts"],
        "sprint_history_id":       L["sprint_history"],
        "active_deals_id":         L["active_deals"],
        "at_risk_deals_id":        L["at_risk_deals"],
        "content_campaigns_id":    L["content_campaigns"],
        "product_launches_id":     L["product_launches"],
        "onboarding_id":           L["onboarding_accounts"],
        "support_escalations_id":  L["support_escalations"],
        "sprint_candidates_id":    L["sprint_candidates"],
    }

    # -- Thresholds --
    ctx.update(THRESHOLDS)

    # -- CI repos --
    ctx["ci_check_repos"] = ", ".join(CI_CHECK_REPOS)

    # -- Sprint rules --
    ctx["sprint_budget_sp"]    = SPRINT_RULES["budget_sp"]
    ctx["min_features"]        = SPRINT_RULES["min_features"]
    ctx["max_compliance"]      = SPRINT_RULES["max_compliance"]
    ctx["sprint_target_items"] = SPRINT_RULES["target_items"]
    ctx["sprint_mix"]          = SPRINT_RULES["mix"]

    # -- Slack channels --
    for key, channel in SLACK.items():
        ctx[f"slack_{key}"] = channel

    # -- GTM verticals --
    ctx["verticals"] = ", ".join(GTM_VERTICALS)

    # -- Domain assignments (formatted for triage/sprint backstories) --
    _id_to_name = {t["cu_id"]: name for name, t in TEAM.items()}
    assignments = []
    for domain in ["compliance", "frontend", "backend", "mobile",
                    "ai-cv", "security", "infra"]:
        cu_id = DOMAIN_LEADS.get(domain, "")
        name = _id_to_name.get(cu_id, cu_id)
        assignments.append(f"- {domain.title()} → {name} ({cu_id})")
    ctx["domain_assignments"] = "\n".join(assignments)

    # -- Team roster (formatted for sprint backstory) --
    roster = []
    for name, info in TEAM.items():
        domains = ", ".join(info["domains"])
        roster.append(f"- {name}: {domains} ({info['cap_sp']} SP, max {info['max_tasks']} tasks)")
    ctx["team_roster"] = "\n".join(roster)

    # -- SP estimation rules (formatted for triage backstory) --
    sp_lines = []
    for label, sp in SP_ESTIMATE.items():
        sp_lines.append(f"- {label.replace('_', ' ').title()}: {sp} SP")
    ctx["sp_estimates"] = "\n".join(sp_lines)

    # -- Bug SLA (formatted) --
    sla_lines = []
    for pri, hours in BUG_SLA.items():
        sla_lines.append(f"- {pri}: {hours}h")
    ctx["bug_sla"] = "\n".join(sla_lines)

    # -- Overrides (sprint_list_id, sprint_number, etc.) --
    ctx.update(overrides)
    return ctx


def interpolate_config(config: dict) -> dict:
    """Pre-interpolate {variables} in a CrewAI config dict.

    Call this in crew.py agent/task methods so variables are resolved
    regardless of whether the caller passes inputs (CrewHub doesn't).
    """
    ctx = crew_context()
    out = {}
    for key, value in config.items():
        if isinstance(value, str):
            try:
                out[key] = value.format_map(ctx)
            except (KeyError, ValueError):
                out[key] = value
        else:
            out[key] = value
    return out


# ======================================================================
# SPACES TO ARCHIVE (old structure — manual cleanup)
# ======================================================================
# These spaces are no longer used. Archive them in ClickUp:
# - Product Engineering:    901313673268
# - Infrastructure & DevOps: 901313673272
# - Compliance & Security:  901313673273
# - Bugs & Support:         901313673276
