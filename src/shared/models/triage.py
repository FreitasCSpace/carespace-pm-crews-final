from pydantic import BaseModel, Field
from typing import List


class PriorityChange(BaseModel):
    task_id: str
    task_name: str = ""
    old_priority: str = ""
    new_priority: int = Field(description="1=urgent, 2=high, 3=normal, 4=low")
    reason: str = ""


class TriageDecision(BaseModel):
    """Output model for triage decide_and_execute_task."""
    set_priority: List[PriorityChange] = Field(default_factory=list)
    set_sp: List[dict] = Field(default_factory=list, description="[{task_id, points}]")
    patterns_identified: List[str] = Field(default_factory=list)
    aging_items_flagged: int = 0
    reasoning: str = ""
