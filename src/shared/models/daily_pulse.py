from pydantic import BaseModel, Field
from typing import List, Optional


class SprintProgress(BaseModel):
    sprint_name: str = ""
    done_count: int = 0
    in_progress_count: int = 0
    blocked_count: int = 0
    pending_count: int = 0
    done_sp: int = 0
    total_sp: int = 0
    completion_pct: float = 0.0
    status: str = Field(default="unknown", description="on_track, at_risk, behind, not_started")


class AttentionItem(BaseModel):
    type: str = Field(description="stale_pr, critical_pr, ci_failure, stale_issue, stale_task")
    description: str = ""
    url: str = ""


class PulseData(BaseModel):
    """Output model for daily pulse scan_and_gather task."""
    sprint: SprintProgress
    attention_items: List[AttentionItem] = Field(default_factory=list)
    sprint_risks: List[str] = Field(default_factory=list)
    timing_display: str = ""
