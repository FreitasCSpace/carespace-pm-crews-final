---
name: pm-context
description: CareSpace PM system context — team roster, repos, ClickUp structure, Slack channels. Use for any task that needs organizational context.
metadata:
  author: CareSpace
  version: "1.0"
---

# CareSpace PM Context

## Organization
CareSpace is a healthcare SaaS platform with 18 engineers across 6 countries.
The PM system is fully automated via 9 AI crews running on CrewHub.

## Team Structure

### Engineering
- **Frontend**: Andre Dutra, Brayan Marcano, Bhavya Saurabh, Deeksha Kain, Binu G, Harshit Diyora, Rohith Suri, Sujan, Shubham, Mubina
- **Backend**: Fabiano Fiorentin, Sandeep Pulichinthala, Kishorkumar
- **Mobile/SDK**: Flavio Fusuma, Bharath Yeddula, R. Kapil Kumar, Sreenivas, Ratnakumar
- **AI/CV**: Bhavya Saurabh, Flavio Fusuma

### Leadership
- **CEO / Compliance Owner**: Luis Freitas
- **CareSpace**: Flavio Garcia, David Richards, Willian Schaitel, Dr. Neha Narula
- **Buena (Design)**: Doug (Founder), Lucas, Bianca Oliveira, Camila Collazos

## Domain Leads
- Frontend → Andre Dutra
- Backend → Fabiano Fiorentin
- Mobile → Bharath Yeddula
- AI/CV → Bhavya Saurabh
- Infra → Sandeep Pulichinthala
- Compliance → Luis Freitas (sole owner)

## GitHub Organization: carespace-ai
Key repos: carespace-ui, carespace-admin, carespace-api-gateway, carespace-sdk,
carespace-mobile-android, carespace-mobile-ios, PoseEstimator

## ClickUp Structure
- 2 spaces: CareSpace Engine + GTM & Revenue
- Master Backlog: single intake point for all tasks
- Sprint Candidates: staging area for next sprint
- Alerts & Escalations: SLA breaches and urgent items

## Slack Channels
- #pm-standup — daily sprint digest
- #pm-sprint-board — sprint plans and retros
- #pm-engineering — triage reports, intake summaries
- #pm-alerts — SLA breaches, escalations
- #pm-exec-updates — weekly executive report
- #pm-compliance — daily compliance health

## Task Naming Convention
All tasks follow: `[TYPE] Title (source#number)`
Types: FEATURE, BUG, TASK, SECURITY, COMPLIANCE
Sources: github (from GitHub issues), design (from Buena team), vanta (from compliance)

## Vault
Crew outputs are persisted to carespace-pm-vault GitHub repo.
Context files in vault/context/ provide rolling state for cross-crew context.
