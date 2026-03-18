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
    "backlog":    "901317811713",
    "sprints":    "901317811717",
    "operations": "901317811718",
    "playbooks":  "901317811721",
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

    # Sprints (auto-created by sprint_crew — folder starts empty)
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
    "standup":     "#standup",
    "sprint":      "#sprint-board",
    "engineering": "#engineering",
    "alerts":      "#alerts",
    "gtm":         "#gtm",
    "exec":        "#exec-updates",
    "compliance":  "#compliance",
    "cs":          "#customer-success",
}

# ======================================================================
# CREW SCHEDULE (reference — actual scheduling via CrewHub)
# ======================================================================
CREW_SCHEDULE = {
    "compliance_crew":        "Daily 07:00",
    "intake_crew":            "Daily 08:00 + webhooks",
    "daily_pulse_crew":       "Mon-Fri 08:00",
    "pr_radar_crew":          "Daily 10:00",
    "triage_crew":            "Every 6 hours",
    "sprint_crew":            "Bi-weekly Sunday 18:00",
    "retrospective_crew":     "Bi-weekly Friday 16:00",
    "deal_intel_crew":        "Monday 07:00",
    "customer_success_crew":  "Daily 08:30",
    "exec_report_crew":       "Friday 17:00",
}

# ======================================================================
# CLICKUP DOCS (for AI-written reports)
# ======================================================================
DOCS = {
    "sprint_engine":    "xnum1-4273",
    "ai_system":        "xnum1-9333",
    "crew_dashboard":   "xnum1-9353",
}

# ======================================================================
# SPACES TO ARCHIVE (old structure — manual cleanup)
# ======================================================================
# These spaces are no longer used. Archive them in ClickUp:
# - Product Engineering:    901313673268
# - Infrastructure & DevOps: 901313673272
# - Compliance & Security:  901313673273
# - Bugs & Support:         901313673276
