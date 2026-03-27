from pydantic import BaseModel, Field
from typing import List


class SlaItem(BaseModel):
    task_name: str
    assignee: str = ""
    priority: str = ""
    age_hours: float = 0
    sla_hours: int = 0
    url: str = ""


class SlaReport(BaseModel):
    """Output model for SLA crew scan_sprint_sla_task."""
    sprint_name: str = ""
    tasks_checked: int = 0
    breached: List[SlaItem] = Field(default_factory=list)
    at_risk: List[SlaItem] = Field(default_factory=list)
    alerts_created: int = 0
    dms_sent: int = 0
