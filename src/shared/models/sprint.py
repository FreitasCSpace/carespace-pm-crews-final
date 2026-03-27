from pydantic import BaseModel, Field
from typing import List, Optional


class SprintTask(BaseModel):
    name: str
    assignee: str = "unassigned"
    sp: int = 0
    priority: str = "normal"


class SprintPlan(BaseModel):
    """Output model for sprint crew finalize_task."""
    sprint_name: str = ""
    sprint_number: int = 0
    tasks_moved: int = 0
    total_sp: int = 0
    velocity_budget: int = 0
    over_under: int = Field(default=0, description="Positive = over budget")
    tasks: List[SprintTask] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
