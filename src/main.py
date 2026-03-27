"""CareSpace PM Crews Flow — CrewHub entry point.

CrewHub detects this as a Flow (via [tool.crewai] type = "flow" in pyproject.toml)
and calls kickoff(). Inputs arrive via CREWHUB_INPUT_KWARGS env var.

Usage from CrewHub:
    crew_name: "triage"        (required)
    ... plus any crew-specific inputs

Architecture:
    @start  → load_inputs (parse CrewHub env, validate crew_name)
    @listen → read_vault  (load context from previous crew runs)
    @listen → run_crew    (execute the requested crew with enriched inputs)
    @listen → write_vault (persist crew output to vault repo)
"""

import importlib
import json
import logging
import os
from typing import Optional

from crewai.flow.flow import Flow, start, listen
from crewai.flow.persistence import persist
from pydantic import BaseModel, Field

from shared.vault_hooks import vault_before_kickoff, vault_after_kickoff
from shared.config.context import crew_context

log = logging.getLogger(__name__)


# ── Pydantic Flow State ─────────────────────────────────────────────────────

class PMFlowState(BaseModel):
    """Typed state for the PM Crews Flow. Persisted between steps."""
    # Inputs
    crew_name: str = ""
    crew_inputs: dict = Field(default_factory=dict)
    sprint_number: Optional[int] = None

    # Vault context (loaded before crew runs)
    vault_context: str = "{}"

    # Crew result (populated after crew runs)
    crew_raw_output: str = ""
    crew_success: bool = False
    crew_error: Optional[str] = None

    # Vault write status
    vault_written: bool = False


# ── Crew Registry ────────────────────────────────────────────────────────────

CREW_REGISTRY = {
    "compliance":    ("crews.compliance.crew",    "ComplianceCrew"),
    "intake":        ("crews.intake.crew",        "IntakeCrew"),
    "daily_pulse":   ("crews.daily_pulse.crew",   "DailyPulseCrew"),
    "sla":           ("crews.sla.crew",           "SlaCrew"),
    "triage":        ("crews.triage.crew",        "TriageCrew"),
    "sprint":        ("crews.sprint.crew",        "SprintCrew"),
    "retrospective": ("crews.retrospective.crew", "RetrospectiveCrew"),
    "exec_report":   ("crews.exec_report.crew",   "ExecReportCrew"),
    "huddle_notes":  ("crews.huddle_notes.crew",  "HuddleNotesCrew"),
}


# ── Flow ─────────────────────────────────────────────────────────────────────

@persist
class PMCrewsFlow(Flow[PMFlowState]):
    """Orchestrates all 9 CareSpace PM crews with typed state and persistence.

    Steps:
        1. load_inputs  — parse CrewHub env, validate crew_name
        2. read_vault   — load context from previous crew runs into state
        3. run_crew     — execute the requested crew with enriched inputs
        4. write_vault  — persist crew output to vault repo
    """

    @start()
    def load_inputs(self):
        """Parse CrewHub env var and validate crew_name."""
        raw = os.environ.get("CREWHUB_INPUT_KWARGS", "{}")
        inputs = json.loads(raw) if raw else {}

        self.state.crew_name = inputs.pop("crew_name", "")
        self.state.crew_inputs = inputs
        self.state.sprint_number = inputs.get("sprint_number")

        if not self.state.crew_name:
            available = ", ".join(sorted(CREW_REGISTRY.keys()))
            raise ValueError(f"crew_name is required. Available: {available}")

        if self.state.crew_name not in CREW_REGISTRY:
            available = ", ".join(sorted(CREW_REGISTRY.keys()))
            raise ValueError(f"Unknown crew '{self.state.crew_name}'. Available: {available}")

        log.info("[%s] Inputs loaded", self.state.crew_name)

    @listen(load_inputs)
    def read_vault(self):
        """Load vault context from previous crew runs."""
        ctx = crew_context()
        ctx.update(self.state.crew_inputs)
        enriched = vault_before_kickoff(self.state.crew_name, ctx)
        self.state.crew_inputs = enriched
        self.state.vault_context = enriched.get("vault_context", "{}")
        log.info("[%s] Vault context loaded", self.state.crew_name)

    @listen(read_vault)
    def run_crew(self):
        """Execute the requested crew with enriched inputs."""
        module_path, cls_name = CREW_REGISTRY[self.state.crew_name]
        module = importlib.import_module(module_path)
        crew_cls = getattr(module, cls_name)

        try:
            result = crew_cls().crew().kickoff(inputs=self.state.crew_inputs)
            # Store full CrewOutput for vault (has tasks_output with all task results)
            self._crew_result = result
            self.state.crew_raw_output = result.raw if hasattr(result, "raw") else str(result)
            self.state.crew_success = True
            log.info("[%s] Crew completed successfully", self.state.crew_name)
        except Exception as e:
            self._crew_result = None
            self.state.crew_error = str(e)
            self.state.crew_success = False
            log.error("[%s] Crew failed: %s", self.state.crew_name, e)
            raise

    @listen(run_crew)
    def write_vault(self):
        """Persist crew output to the vault repo.

        Passes the full CrewOutput object (not just .raw) so vault_after_kickoff
        can extract ALL task outputs — not just the final confirmation message.
        """
        # Use full CrewOutput if available, fall back to raw string
        result_to_save = getattr(self, "_crew_result", None) or self.state.crew_raw_output
        try:
            vault_after_kickoff(
                self.state.crew_name,
                result_to_save,
                sprint_number=self.state.sprint_number,
            )
            self.state.vault_written = True
            log.info("[%s] Output saved to vault", self.state.crew_name)
        except Exception as e:
            log.warning("[%s] Vault write failed: %s", self.state.crew_name, e)

        # Use Flow memory to remember this run
        self.remember(
            f"{self.state.crew_name} completed. "
            f"Success: {self.state.crew_success}. "
            f"Output length: {len(self.state.crew_raw_output)} chars.",
            scope=f"/crew/{self.state.crew_name}",
        )

        print(f"[{self.state.crew_name}] Complete.", flush=True)
        return self.state.crew_raw_output


# ── Entry Points ─────────────────────────────────────────────────────────────

def kickoff():
    """Entry point for CrewHub and `crewai run`."""
    PMCrewsFlow().kickoff()


def plot():
    """Generate HTML flow visualization."""
    PMCrewsFlow().plot("pm_crews_flow")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: python -m src.main <crew_name> [inputs_json]")
        print(f"Crews: {', '.join(sorted(CREW_REGISTRY.keys()))}")
        sys.exit(1)

    crew_name = sys.argv[1]
    extra = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    extra["crew_name"] = crew_name

    os.environ["CREWHUB_INPUT_KWARGS"] = json.dumps(extra)

    flow = PMCrewsFlow()
    result = flow.kickoff()
    print(result)
