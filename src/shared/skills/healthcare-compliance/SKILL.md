---
name: healthcare-compliance
description: HIPAA and SOC 2 compliance domain knowledge. Use when handling compliance tasks, Vanta health data, or regulatory risk assessment.
metadata:
  author: CareSpace
  version: "1.0"
---

# Healthcare Compliance Context

## Frameworks
- **HIPAA**: Health Insurance Portability and Accountability Act — governs PHI handling
- **SOC 2 Type II**: Service Organization Control — audit for security, availability, processing integrity

## Key Concepts
- **PHI** (Protected Health Information): any health data linked to an individual
- **BAA** (Business Associate Agreement): required contract before sharing PHI with vendors
- **Evidence**: documentation proving compliance controls are in place
- **Control**: a security/compliance measure (e.g., "encryption at rest")
- **Test**: automated check in Vanta that validates a control

## Vanta Health Indicators
- **GREEN**: pass rate >= 80%, no critical failures
- **YELLOW**: pass rate 60-80%, some critical failures
- **RED**: pass rate < 60%, or any critical unowned test failing

## Critical Test Keywords
Tests containing these keywords are flagged as critical:
access, encrypt, backup, mfa, incident, termination, risk, vulnerability,
audit, training, data retention, breach, phi, hipaa

## SLA by Priority (hours)
- Urgent (P0): 4 hours
- High (P1): 24 hours
- Normal (P2): 72 hours
- Low (P3): 168 hours (1 week)

## Risk Framing
When reporting compliance issues, always frame in business terms:
- "SOC 2 controls failing" → "Enterprise sales blocked until audit-ready"
- "BAA gap with Azure" → "PHI processing legally blocked — HIPAA violation exposure"
- "Evidence overdue" → "Breach notification risk if audited"

## Compliance Owner
Luis Freitas is the sole compliance owner. All compliance tasks route to him.
Maximum 3 compliance tasks per sprint to avoid overloading one person.
