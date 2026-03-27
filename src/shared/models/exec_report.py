from pydantic import BaseModel, Field
from typing import List, Optional


class DimensionHealth(BaseModel):
    name: str
    status: str = Field(description="GREEN, YELLOW, or RED")
    headline: str = ""


class ExecGatherData(BaseModel):
    """Output model for exec report crew gather task."""
    health_dimensions: List[DimensionHealth] = Field(default_factory=list)
    sprint_completion_pct: float = 0.0
    sprint_velocity_sp: int = 0
    compliance_pass_rate: float = 0.0
    open_bugs: int = 0
    total_backlog: int = 0
    top_risks: List[str] = Field(default_factory=list)
    wins: List[str] = Field(default_factory=list)
    decisions_needed: List[str] = Field(default_factory=list)
