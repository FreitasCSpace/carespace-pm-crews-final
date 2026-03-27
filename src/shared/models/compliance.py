from pydantic import BaseModel, Field
from typing import List, Optional


class VantaHealth(BaseModel):
    health_indicator: str = Field(description="RED, YELLOW, or GREEN")
    pass_rate: float = Field(description="Test pass rate as percentage")
    critical_failing: int = Field(description="Number of critical tests failing")
    total_tests: int = 0


class ComplianceDelta(BaseModel):
    has_previous: bool = False
    new_failures: List[str] = Field(default_factory=list)
    resolved: List[str] = Field(default_factory=list)
    consecutive_red_days: int = 0


class ComplianceHealth(BaseModel):
    """Output model for compliance crew gather_health task."""
    vanta: VantaHealth
    delta: ComplianceDelta
    needs_action: List[str] = Field(default_factory=list, description="Critical items without owners")
    open_compliance_tasks: int = 0
    sprint_compliance_tasks: int = 0
