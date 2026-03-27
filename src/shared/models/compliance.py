from pydantic import BaseModel, Field, field_validator
from typing import Any, List, Optional


class VantaHealth(BaseModel):
    health_indicator: str = Field(description="RED, YELLOW, or GREEN")
    pass_rate: float = Field(description="Test pass rate as percentage")
    critical_failing: int = Field(description="Number of critical tests failing")
    total_tests: int = 0

    @field_validator("pass_rate", mode="before")
    @classmethod
    def strip_percent(cls, v):
        if isinstance(v, str):
            return float(v.replace("%", "").strip())
        return v


class ComplianceDelta(BaseModel):
    has_previous: bool = False
    new_failures: List[str] = Field(default_factory=list)
    resolved: List[str] = Field(default_factory=list)
    consecutive_red_days: int = 0


class ComplianceHealth(BaseModel):
    """Output model for compliance crew gather_health task."""
    vanta: VantaHealth
    delta: ComplianceDelta
    needs_action: List[Any] = Field(default_factory=list, description="Critical items without owners")
    open_compliance_tasks: int = 0
    sprint_compliance_tasks: int = 0
