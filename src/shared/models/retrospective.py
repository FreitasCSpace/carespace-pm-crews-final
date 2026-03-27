from pydantic import BaseModel, Field
from typing import List, Optional


class EngineerStats(BaseModel):
    name: str
    tasks_completed: int = 0
    sp_delivered: int = 0


class CarryoverTask(BaseModel):
    name: str
    assignee: str = ""
    sp: int = 0
    reason: str = ""


class RetroMetrics(BaseModel):
    """Output model for retrospective crew measure task."""
    sprint_name: str = ""
    completion_rate: float = Field(description="Percentage 0-100")
    velocity_sp: int = Field(description="Total SP completed")
    planned_sp: int = 0
    per_engineer: List[EngineerStats] = Field(default_factory=list)
    carry_overs: List[CarryoverTask] = Field(default_factory=list)
    recommended_next_sp: int = Field(description="velocity_sp * 0.80")
    stale_prs: int = 0
    ci_status: str = "unknown"
