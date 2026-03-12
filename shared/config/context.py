"""
context.py — Single source of truth for the entire CareSpace ClickUp workspace.
Generated from live workspace analysis 2026-03-12. Update here when structure changes.
"""

WORKSPACE_ID = "31124097"
GITHUB_ORG   = "carespace-ai"

# ======================================================================
# SPACES
# ======================================================================
SPACES = {
    "sprint_engine":       "55072448",
    "gtm_revenue":         "901313672190",
    "product_engineering": "901313673268",
    "infra_devops":        "901313673272",
    "compliance_security": "901313673273",
    "bugs_support":        "901313673276",
}

# ======================================================================
# FOLDERS
# ======================================================================
FOLDERS = {
    # Sprint Engine
    "sprint_ops":      "901317750578",
    "sop":             "901317762375",
    "sprint":          "901317765699",
    # GTM
    "sales_vertical":  "901317762698",
    "marketing_gtm":   "901317762703",
    "customer_success":"901317762705",
    "revenue_analytics":"901317762710",
    # Engineering
    "frontend":        "901317766126",
    "backend":         "901317766127",
    "mobile":          "901317766130",
    "ai_cv":           "901317766132",
    "bots_comms":      "901317766134",
    "video_media":     "901317766254",
    "data_analytics":  "901317766256",
    "docs_content":    "901317766261",
    "dev_tools":       "901317766266",
    # Infra
    "docker_deploy":   "901317766146",
    "auth_identity":   "901317766148",
    "monitoring":      "901317766150",
    "cicd":            "901317766151",
    # Compliance
    "soc2":            "901317766167",
    "hipaa":           "901317766168",
    "vanta":           "901317766173",
    # Bugs
    "bug_reports":     "901317766187",
    "customer_support":"901317766188",
}

# ======================================================================
# ALL LIST IDs
# ======================================================================
L = {
    # Sprint Engine
    "recurring_ops":         "901326336253",
    "automation_registry":   "901326336259",
    "task_templates":        "901326336262",
    "alerts_sla":            "901326336266",
    "product_roadmap":       "901326359641",
    "master_backlog":        "901326359646",
    "sprint_1":              "901326359655",
    "sprint_2":              "901326359660",
    "sprint_3":              "901326359665",
    "sprint_4":              "901326359670",
    "sprint_5":              "901326359674",
    "sprint_6":              "901326359676",

    # GTM / Revenue
    "sales_healthcare":      "901326354881",
    "sales_insurance":       "901326354882",
    "sales_employers":       "901326354886",
    "sales_senior":          "901326354890",
    "sales_sports":          "901326354891",
    "sales_construction":    "901326354896",
    "pipeline_overview":     "901326354900",
    "content_calendar":      "901326354907",
    "marketing_campaigns":   "901326354910",
    "product_launches":      "901326354911",
    "partner_events":        "901326354916",
    "seo_web":               "901326354920",
    "client_onboarding":     "901326354926",
    "account_health":        "901326354930",
    "support_escalations":   "901326354933",
    "client_feedback":       "901326354935",
    "pipeline_metrics":      "901326354940",
    "vertical_performance":  "901326354950",
    "cohort_retention":      "901326354956",

    # Product Engineering -- Frontend
    "carespace_ui":          "901326360336",
    "carespace_landingpage": "901326360339",
    "carespace_site":        "901326360341",
    "carespace_lms":         "901326360343",
    "meta_web_view":         "901326360348",
    "healthstartiq":         "901326360349",

    # Product Engineering -- Backend
    "carespace_admin":       "901326360350",
    "carespace_gateway":     "901326360351",
    "carespace_strapi":      "901326360352",
    "strapi_services":       "901326360354",

    # Product Engineering -- Mobile
    "mobile_android":        "901326360357",
    "mobile_ios":            "901326360360",
    "mobile_flutter":        "901326360361",
    "carespace_sdk":         "901326360362",

    # Product Engineering -- AI & CV
    "pose_estimator":        "901326360363",
    "pose_classifier":       "901326360365",
    "metahuman_coach":       "901326360366",
    "mediapipe_video":       "901326360367",

    # Product Engineering -- Bots & Comms
    "carespace_botkit":      "901326360368",
    "carespace_chat":        "901326360370",
    "azure_comms":           "901326360371",

    # Product Engineering -- Video & Media
    "media_converter":       "901326360572",
    "video_converter":       "901326360573",
    "virtual_cam":           "901326360575",

    # Product Engineering -- Data & Docs
    "population_health":     "901326360580",
    "product_metrics":       "901326360583",
    "carespace_docs":        "901326360586",
    "carespace_docs_turbo":  "901326360588",
    "bug_tracker_repo":      "901326360591",
    "skills_reports":        "901326360593",

    # Infra & DevOps
    "docker_nginx":          "901326360378",
    "azure_infra":           "901326360381",
    "fusionauth":            "901326360382",
    "stealthid":             "901326360386",
    "upass":                 "901326360388",
    "monitoring_status":     "901326360393",
    "github_actions":        "901326360395",
    "github_clickup_sync":   "901326360404",

    # Compliance & Security
    "soc2_controls":         "901326360411",
    "soc2_access_reviews":   "901326360412",
    "soc2_audit":            "901326360413",
    "hipaa_baa":             "901326360416",
    "hipaa_phi":             "901326360417",
    "hipaa_risk":            "901326360419",
    "vanta_failures":        "901326360426",
    "vendor_risk":           "901326360429",
    "security_questionnaires":"901326360432",

    # Bugs & Support
    "frontend_bugs":         "901326360436",
    "backend_bugs":          "901326360437",
    "mobile_bugs":           "901326360441",
    "security_vulns":        "901326360443",
    "support_tickets":       "901326360444",
}

# ======================================================================
# ACTIVE SPRINT -- update after each retro
# ======================================================================
ACTIVE_SPRINT = {
    "number":  1,
    "name":    "Sprint 1 -- Mar 16-Mar 30",
    "start":   "2026-03-16",
    "end":     "2026-03-30",
    "list_id": "901326359655",
}

# ======================================================================
# GITHUB -> CLICKUP ROUTING
# ======================================================================
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
    "PoseEstimator":                       "ai_cv",
    "carespace-poseestimation":            "ai_cv",
    "carespace-poseestimation-classifier": "ai_cv",
    "mediapipeAnnotateVideo":              "ai_cv",
    "MetaHumanCoach":                      "ai_cv",
    "carespace-botkit":                    "bots",
    "carespace-chat":                      "bots",
    "acs":                                 "bots",
    "carespace-media-converter":           "video",
    "carespace-video-converter":           "video",
    "Carespace-VirtualCam":                "video",
    "carespace-docker":                    "infra",
    "carespace-fusionauth":                "infra",
    "carespace-monitoring":                "infra",
    "carespace-bug-tracker":               "infra",
}

BUG_TARGET = {
    "frontend": L["frontend_bugs"],
    "backend":  L["backend_bugs"],
    "mobile":   L["mobile_bugs"],
    "sdk":      L["security_vulns"],
    "ai_cv":    L["frontend_bugs"],
    "bots":     L["backend_bugs"],
    "video":    L["frontend_bugs"],
    "infra":    L["backend_bugs"],
}

FEATURE_TARGET = {
    "frontend": L["carespace_ui"],
    "backend":  L["carespace_admin"],
    "mobile":   L["mobile_ios"],
    "sdk":      L["carespace_sdk"],
    "ai_cv":    L["pose_estimator"],
    "bots":     L["carespace_botkit"],
    "video":    L["media_converter"],
    "infra":    L["docker_nginx"],
}

# ======================================================================
# TEAM
# ======================================================================
TEAM = {
    "fusuma":            {"domains": ["ai_cv","sdk","mobile","backend"], "cap_sp": 20, "max_tasks": 4, "cu_id": None},
    "andreCarespace":    {"domains": ["frontend"],                        "cap_sp": 20, "max_tasks": 4, "cu_id": None},
    "BMarcano":          {"domains": ["frontend"],                        "cap_sp": 18, "max_tasks": 3, "cu_id": None},
    "bhavyasaurabh":     {"domains": ["ai_cv","frontend"],               "cap_sp": 18, "max_tasks": 3, "cu_id": None},
    "Deekshakain":       {"domains": ["frontend"],                        "cap_sp": 16, "max_tasks": 3, "cu_id": None},
    "binunexturn":       {"domains": ["frontend","backend"],              "cap_sp": 20, "max_tasks": 4, "cu_id": None},
    "fabiano-carespace": {"domains": ["backend","infra"],                 "cap_sp": 18, "max_tasks": 3, "cu_id": None},
    "YeddulaBharath":    {"domains": ["mobile","sdk"],                    "cap_sp": 16, "max_tasks": 3, "cu_id": None},
    "R-Kapil-Kumar":     {"domains": ["mobile","sdk"],                    "cap_sp": 16, "max_tasks": 3, "cu_id": None},
}

DOMAIN_KEYWORDS = {
    "frontend": ["ui","react","css","storybook","design system","kiosk","dashboard","typescript","nextjs","html","component","plumb line","rom scan","onboarding ui"],
    "backend":  ["api","endpoint","gateway","strapi","auth","rbac","guard","middleware","database","prisma","nestjs","node","rest","graphql","webhook"],
    "mobile":   ["android","ios","flutter","mobile","swift","kotlin","wkwebview","offline","push notification","intake screen"],
    "sdk":      ["sdk","native sdk","production readiness","android sdk","ios sdk","sdk v1"],
    "ai_cv":    ["pose","cv","computer vision","model","inference","mediapipe","rom analysis","poseestimator","skeleton","ml","ai","opencv","classifier"],
    "infra":    ["docker","azure","kubernetes","ci","cd","pipeline","monitoring","fusionauth","nginx","ssl","devops","github actions","deployment"],
    "bots":     ["botkit","chat","acs","azure communication","risecx"],
    "video":    ["video","media","converter","virtualcam","webcam","webm"],
}

# ======================================================================
# SPRINT SCORING
# ======================================================================
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
# SLACK CHANNELS
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
# CLICKUP DOCS (for AI-written reports)
# ======================================================================
DOCS = {
    "sprint_engine": "xnum1-4273",
    "ai_system":     "xnum1-9333",
}
