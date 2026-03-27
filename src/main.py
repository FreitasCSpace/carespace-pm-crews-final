"""CareSpace PM Crews Flow — CrewHub entry point.

CrewHub detects this as a Flow (via [tool.crewai] type = "flow" in pyproject.toml)
and calls PMCrewsFlow().kickoff(). Inputs arrive via CREWHUB_INPUT_KWARGS env var.

Usage from CrewHub:
    crew_name: "triage"        (required)
    ... plus any crew-specific inputs

The flow reads vault context, runs the requested crew, and writes output to vault.
"""

import importlib
import json
import os

from crewai.flow.flow import Flow, start

from src.shared.vault_hooks import vault_before_kickoff, vault_after_kickoff
from src.shared.config.context import crew_context


# crew_name → (module_path, class_name)
CREW_REGISTRY = {
    "compliance":    ("src.crews.compliance.crew",    "ComplianceCrew"),
    "intake":        ("src.crews.intake.crew",         "IntakeCrew"),
    "daily_pulse":   ("src.crews.daily_pulse.crew",   "DailyPulseCrew"),
    "sla":           ("src.crews.sla.crew",           "SlaCrew"),
    "triage":        ("src.crews.triage.crew",        "TriageCrew"),
    "sprint":        ("src.crews.sprint.crew",        "SprintCrew"),
    "retrospective": ("src.crews.retrospective.crew", "RetrospectiveCrew"),
    "exec_report":   ("src.crews.exec_report.crew",   "ExecReportCrew"),
    "huddle_notes":  ("src.crews.huddle_notes.crew",  "HuddleNotesCrew"),
}


class PMCrewsFlow(Flow):
    """Orchestrates all 9 CareSpace PM crews.

    CrewHub passes inputs via CREWHUB_INPUT_KWARGS env var (JSON).
    Required key: crew_name. Remaining keys are passed to the crew.
    """

    @start()
    def dispatch(self):
        """Route to the correct crew with vault context."""
        # Read inputs from CrewHub env var
        raw = os.environ.get("CREWHUB_INPUT_KWARGS", "{}")
        inputs = json.loads(raw) if raw else {}

        crew_name = inputs.pop("crew_name", "")

        if not crew_name:
            available = ", ".join(sorted(CREW_REGISTRY.keys()))
            raise ValueError(
                f"crew_name is required. Available crews: {available}"
            )

        if crew_name not in CREW_REGISTRY:
            available = ", ".join(sorted(CREW_REGISTRY.keys()))
            raise ValueError(
                f"Unknown crew '{crew_name}'. Available: {available}"
            )

        # 1. Vault read — load context from previous crew runs
        ctx = crew_context()
        ctx.update(inputs)
        enriched = vault_before_kickoff(crew_name, ctx)

        # 2. Run crew
        module_path, cls_name = CREW_REGISTRY[crew_name]
        module = importlib.import_module(module_path)
        crew_cls = getattr(module, cls_name)
        result = crew_cls().crew().kickoff(inputs=enriched)

        # 3. Vault write — persist crew output
        sprint_num = enriched.get("sprint_number")
        vault_after_kickoff(crew_name, result, sprint_number=sprint_num)

        print(f"[{crew_name}] Complete.", flush=True)
        return result


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
