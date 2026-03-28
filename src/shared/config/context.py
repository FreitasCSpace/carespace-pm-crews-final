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
    "carespace-posture-engine":            "ai-cv",
}

# Everything routes to master_backlog with tags — no more per-domain lists
INTAKE_TARGET = L["master_backlog"]


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
    # Engineers who can be assigned sprint tasks.
    # slack_name = Slack display name for DM notifications (resolved to ID at runtime)
    # ── CareSpace core ──────────────────────────────────────────────────────────
    "fusuma":            {"domains": ["ai-cv","sdk","mobile","backend"], "cap_sp": 20, "max_tasks": 4, "cu_id": "48998538",  "slack_name": "Flavio Fusuma"},
    "andreCarespace":    {"domains": ["frontend"],                       "cap_sp": 20, "max_tasks": 4, "cu_id": "49000180",  "slack_name": "Andre Dutra"},
    "fabiano-carespace": {"domains": ["backend","infra"],                "cap_sp": 18, "max_tasks": 3, "cu_id": "49000181",  "slack_name": "Fabiano"},
    # ── Buena / mixed ───────────────────────────────────────────────────────────
    "BMarcano":          {"domains": ["frontend"],                       "cap_sp": 18, "max_tasks": 3, "cu_id": "112101513", "slack_name": "Brayan Marcano"},
    # ── Nexturn core ────────────────────────────────────────────────────────────
    "bhavyasaurabh":     {"domains": ["ai-cv","frontend"],              "cap_sp": 18, "max_tasks": 3, "cu_id": "93908266",  "slack_name": "Bhavya Saurabh"},
    "Deekshakain":       {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "61019156",  "slack_name": "Deeksha Kain"},
    "binunexturn":       {"domains": ["frontend","backend"],             "cap_sp": 20, "max_tasks": 4, "cu_id": "61025897",  "slack_name": "Binu G"},
    "YeddulaBharath":    {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "93908270",  "slack_name": "Bharath"},
    "R-Kapil-Kumar":     {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "81941440",  "slack_name": "R. Kapil Kumar"},
    "harshitdiyora":     {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "81942238",  "slack_name": "Harshit Diyora"},
    "ratnakumar":        {"domains": ["mobile","backend"],               "cap_sp": 16, "max_tasks": 3, "cu_id": "81941439",  "slack_name": "Ratnakumar A"},
    "sreenivas":         {"domains": ["mobile","sdk"],                   "cap_sp": 16, "max_tasks": 3, "cu_id": "93908269",  "slack_name": "Sreenivas"},
    "rohithsuri":        {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "93908271",  "slack_name": "Sai Rohith Suri"},
    "sandeep":           {"domains": ["backend","infra"],                "cap_sp": 16, "max_tasks": 3, "cu_id": "111928715", "slack_name": "Sandeep Pulichinthala"},
    "sujanmahapatra":    {"domains": ["frontend","backend"],             "cap_sp": 16, "max_tasks": 3, "cu_id": "111951799", "slack_name": "Sujan"},
    "shubhamsanjog":     {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "112029068", "slack_name": "Shubham Sanjog"},
    "mubinashaikh":      {"domains": ["frontend"],                       "cap_sp": 16, "max_tasks": 3, "cu_id": "111980875", "slack_name": "Mubina Shaikh"},
    "kishorkumar":       {"domains": ["backend"],                        "cap_sp": 16, "max_tasks": 3, "cu_id": "254678220", "slack_name": "Kishorkumar"},
}

# Non-engineering workspace members — stakeholders, leadership, ops.
# Included in DM notification system but NOT in sprint capacity planning.
# NOTE: Ben Clark is in Slack but has no ClickUp account — cannot DM via this system.
STAKEHOLDERS = {
    # ── CareSpace leadership ─────────────────────────────────────────────────
    "luis":      {"cu_id": "118004891", "slack_name": "Luis Freitas",      "role": "CEO / Compliance"},
    "flavio_g":  {"cu_id": "61019146",  "slack_name": "Flavio Garcia",     "role": "CareSpace"},
    "david":     {"cu_id": "54169952",  "slack_name": "David Richards",    "role": "CareSpace exec"},
    "willian":   {"cu_id": "49057990",  "slack_name": "Willian Schaitel",  "role": "CareSpace"},
    "neha":      {"cu_id": "61019162",  "slack_name": "Dr. Neha Narula",   "role": "Clinical"},
    # ── Buena team ───────────────────────────────────────────────────────────
    "lucas":     {"cu_id": "112078562", "slack_name": "Lucas",             "role": "Buena"},
    "bianca":    {"cu_id": "87354299",  "slack_name": "Bianca Oliveira",   "role": "Buena"},
    "camila":    {"cu_id": "81580212",  "slack_name": "Camila Collazos",   "role": "Buena"},
    "doug":      {"cu_id": "4492088",   "slack_name": "Doug",              "role": "Buena Founder"},
    # ── External / contractors (no Slack workspace access) ───────────────────
    "anton":     {"cu_id": "112086736", "slack_name": "",                  "role": "External"},
    "vladyslava":{"cu_id": "266535001", "slack_name": "",                  "role": "External"},
}

# Combined ClickUp ID → Slack display name mapping (engineers + stakeholders)
# Used by notify_task_assignee to DM anyone assigned a task in ClickUp.
CU_TO_SLACK_NAME: dict[str, str] = {
    info["cu_id"]: info["slack_name"]
    for info in list(TEAM.values()) + list(STAKEHOLDERS.values())
    if info.get("slack_name")
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
}

# ======================================================================
# CREW SCHEDULE (reference — actual scheduling via CrewHub)
# ======================================================================
CREW_SCHEDULE = {
    # All crons in America/Los_Angeles (PDT) timezone
    "backlog_crew":           "Every 3 hours (cron: 0 */3 * * *)",
    "daily_pulse_crew":       "Mon-Fri 07:45 (cron: 45 7 * * 1-5)",
    "huddle_notes_crew":      "Daily 11:00 (cron: 0 11 * * *)",
    "retrospective_crew":     "Bi-weekly Friday 16:00 (cron: 0 16 * * 5)",
    "sprint_crew":            "Bi-weekly Sunday 18:00 (cron: 0 18 * * 0)",
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
