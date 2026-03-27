#!/usr/bin/env python3
"""Parallel Orchestrator — run CareSpace PM crews concurrently.

Usage:
    python orchestrator.py                          # run all crews
    python orchestrator.py --crews intake,triage    # run specific crews
    python orchestrator.py --daily                  # run daily schedule only
    python orchestrator.py --sprint                 # run sprint cycle crews
    python orchestrator.py --weekly                 # run weekly report crews
    python orchestrator.py --bootstrap              # cold start: intake → triage → sprint (sequential)

All crews are independent — no dependency ordering required.
Crews run in parallel via CrewAI akickoff() + asyncio.gather().
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ── Crew registry ────────────────────────────────────────────────────────────

PM_CREWS: dict[str, dict[str, Any]] = {
    "compliance": {
        "module": "compliance_crew.crew",
        "class": "ComplianceCrew",
        "schedule": "daily",
        "cron": "0 7 * * *",
        "description": "Vanta compliance sweep → backlog tasks",
        "inputs": {},
    },
    "intake": {
        "module": "intake_crew.crew",
        "class": "IntakeCrew",
        "schedule": "daily",
        "cron": "0 8 * * *",
        "description": "GitHub issues/PRs → Master Backlog",
        "inputs": {},
    },
    "daily_pulse": {
        "module": "daily_pulse_crew.crew",
        "class": "DailyPulseCrew",
        "schedule": "daily",
        "cron": "0 8 * * 1-5",
        "description": "Standup + blocker detection",
        "inputs": {"sprint_list_id": ""},  # set by active sprint lookup
    },
    "sla": {
        "module": "sla_crew.crew",
        "class": "SlaCrew",
        "schedule": "6h",
        "cron": "0 */6 * * *",
        "description": "Sprint SLA enforcement + alerts",
        "inputs": {},
    },
    "triage": {
        "module": "triage_crew.crew",
        "class": "TriageCrew",
        "schedule": "6h",
        "cron": "0 */6 * * *",
        "description": "SLA enforcement + rules + auto-assign",
        "inputs": {"sprint_list_id": ""},
    },
    "sprint": {
        "module": "sprint_crew.crew",
        "class": "SprintCrew",
        "schedule": "biweekly",
        "cron": "0 18 * * 0",
        "description": "Score backlog + fill sprint + assign",
        "inputs": {
            "sprint_number": 1,
            "start_date": "",
            "end_date": "",
            "human_priorities": "",
            "target_sp": 48,
        },
    },
    "retrospective": {
        "module": "retrospective_crew.crew",
        "class": "RetrospectiveCrew",
        "schedule": "biweekly",
        "cron": "0 16 * * 5",
        "description": "Sprint metrics + retro doc",
        "inputs": {"sprint_list_id": ""},
    },
    "exec_report": {
        "module": "exec_report_crew.crew",
        "class": "ExecReportCrew",
        "schedule": "weekly",
        "cron": "0 17 * * 5",
        "description": "Exec dashboard + crew health + marketing",
        "inputs": {},
    },
}

# Schedule groups
SCHEDULE_GROUPS = {
    "daily": ["compliance", "intake", "daily_pulse", "sla", "triage"],
    "weekly": ["exec_report"],
    "sprint": ["sprint", "retrospective"],
    "all": list(PM_CREWS.keys()),
}


@dataclass
class CrewResult:
    """Result of a single crew run."""
    crew_name: str
    success: bool
    duration_s: float
    output: Any = None
    error: str | None = None


@dataclass
class OrchestratorResult:
    """Aggregate result from the full orchestration run."""
    crews: list[CrewResult] = field(default_factory=list)

    @property
    def wall_clock_s(self) -> float:
        return max((r.duration_s for r in self.crews), default=0)

    @property
    def sequential_s(self) -> float:
        return sum(r.duration_s for r in self.crews)

    def summary(self) -> str:
        lines = ["\n╔══════════════════════════════════════════════════╗"]
        lines.append("║      CareSpace PM Crews — Orchestrator Report    ║")
        lines.append("╚══════════════════════════════════════════════════╝\n")

        successes = sum(1 for r in self.crews if r.success)
        failures = len(self.crews) - successes
        lines.append(
            f"  Crews: {successes} succeeded, {failures} failed "
            f"({len(self.crews)} total, ran in parallel)\n"
        )

        for r in sorted(self.crews, key=lambda x: x.crew_name):
            status = "OK" if r.success else "FAIL"
            lines.append(f"  [{status}] {r.crew_name:<24s} ({r.duration_s:.1f}s)")
            if not r.success:
                lines.append(f"        Error: {r.error}")

        wall = self.wall_clock_s
        seq = self.sequential_s
        lines.append(f"\n  Wall-clock time:  {wall:.1f}s")
        lines.append(f"  Sequential equiv: {seq:.1f}s")
        if wall > 0:
            lines.append(f"  Speedup:          {seq / wall:.1f}x")

        return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _import_crew_class(module_path: str, class_name: str):
    """Dynamically import a crew class by module path and class name."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def _resolve_active_sprint() -> str:
    """Look up the most recent sprint list in the Sprints folder.
    Returns the list_id of the active sprint, or empty string if none found.
    """
    try:
        from shared.config.context import SPRINT_FOLDER_ID
        from shared.tools.clickup_helpers import _clickup_api
        data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        lists = data.get("lists", [])
        if lists:
            return lists[-1]["id"]  # most recently created sprint
    except Exception:
        pass
    return ""


# ── Parallel execution ────────────────────────────────────────────────────────

async def _run_crew_async(crew_name: str, crew_info: dict) -> CrewResult:
    """Run a single crew asynchronously using akickoff()."""
    print(f"  >> Starting {crew_name}...")
    t0 = time.perf_counter()
    try:
        crew_cls = _import_crew_class(crew_info["module"], crew_info["class"])
        crew_instance = crew_cls().crew()
        inputs = dict(crew_info.get("inputs", {}))
        result = await crew_instance.akickoff(inputs=inputs)
        duration = time.perf_counter() - t0
        print(f"  [OK]   {crew_name} ({duration:.1f}s)")
        return CrewResult(crew_name=crew_name, success=True, duration_s=duration, output=result)
    except Exception as e:
        duration = time.perf_counter() - t0
        print(f"  [FAIL] {crew_name} ({duration:.1f}s): {e}")
        return CrewResult(crew_name=crew_name, success=False, duration_s=duration, error=str(e))


async def run_crews(crew_names: list[str]) -> OrchestratorResult:
    """Run selected crews in parallel."""
    active = {k: v for k, v in PM_CREWS.items() if k in crew_names}

    if not active:
        print("  No crews selected.")
        return OrchestratorResult()

    # Build shared context from context.py — all {variables} in YAML resolve from this
    from shared.config.context import crew_context
    sprint_id = _resolve_active_sprint()
    base_ctx = crew_context(sprint_list_id=sprint_id)

    # Merge base context into each crew's inputs (crew-specific inputs take precedence)
    for info in active.values():
        merged = dict(base_ctx)
        merged.update(info.get("inputs", {}))
        if "sprint_list_id" in info.get("inputs", {}):
            merged["sprint_list_id"] = sprint_id
        info["inputs"] = merged

    print(f"\n  Running {len(active)} crews in parallel...")
    print("  " + "-" * 48)

    tasks = [_run_crew_async(name, info) for name, info in active.items()]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    return OrchestratorResult(crews=list(results))


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CareSpace PM Crews — Parallel Orchestrator",
    )
    parser.add_argument(
        "--crews", type=str, default=None,
        help="Comma-separated crew names (default: all 10)",
    )
    parser.add_argument("--daily", action="store_true", help="Run daily schedule crews only")
    parser.add_argument("--weekly", action="store_true", help="Run weekly crews only")
    parser.add_argument("--sprint", action="store_true", help="Run sprint cycle crews only")
    parser.add_argument(
        "--bootstrap", action="store_true",
        help="Cold start: intake → triage → sprint (sequential). "
        "Use this when starting from scratch with existing GitHub issues.",
    )
    return parser.parse_args()


async def run_bootstrap() -> OrchestratorResult:
    """Cold-start sequence: intake → triage → sprint (sequential).

    Use when starting from scratch with existing GitHub issues.
    1. intake_crew: scans all GitHub repos, populates Master Backlog
    2. triage_crew: enforces SLAs, assigns priorities, estimates SP
    3. sprint_crew: scores backlog, creates sprint, fills & assigns

    These run sequentially because each depends on the previous output.
    """
    all_results = []
    sequence = ["intake", "triage", "sprint"]

    print("\n  BOOTSTRAP MODE — importing existing work into first sprint")
    print("  " + "=" * 48)

    for crew_name in sequence:
        print(f"\n  Phase: {crew_name}")
        print("  " + "-" * 48)
        result = await run_crews([crew_name])
        all_results.extend(result.crews)

        # Stop if a phase fails
        if any(not r.success for r in result.crews):
            print(f"\n  Bootstrap stopped: {crew_name} failed.")
            break

    return OrchestratorResult(crews=all_results)


def main() -> None:
    args = parse_args()

    if args.bootstrap:
        result = asyncio.run(run_bootstrap())
    elif args.crews:
        crew_list = args.crews.split(",")
        result = asyncio.run(run_crews(crew_list))
    elif args.daily:
        result = asyncio.run(run_crews(SCHEDULE_GROUPS["daily"]))
    elif args.weekly:
        result = asyncio.run(run_crews(SCHEDULE_GROUPS["weekly"]))
    elif args.sprint:
        result = asyncio.run(run_crews(SCHEDULE_GROUPS["sprint"]))
    else:
        result = asyncio.run(run_crews(SCHEDULE_GROUPS["all"]))

    print(result.summary())

    if any(not r.success for r in result.crews):
        sys.exit(1)


if __name__ == "__main__":
    main()
