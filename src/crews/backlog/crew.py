from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    batch_import_engineering,
    sync_closed_issues,
    dedup_backlog_cleanup,
    bulk_assign_and_estimate,
    normalize_backlog_tasks,
    scan_backlog_for_triage,
    execute_triage_actions,
    post_triage_summary,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_triage_actions
from shared.models.triage import TriageDecision


@CrewBase
class BacklogCrew:
    """Backlog import + triage — runs every 3 hours."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── Deterministic backlog hygiene (no LLM needed) ──
        import json, logging
        log = logging.getLogger(__name__)

        # 1. Dedup
        try:
            result = dedup_backlog_cleanup.run(dry_run=False)
            dedup_stats = json.loads(result) if isinstance(result, str) else result
            log.info("backlog: dedup — %s duplicates removed", dedup_stats.get("tasks_deleted", 0))
        except Exception as e:
            dedup_stats = {"error": str(e)}
            log.warning("backlog: dedup failed: %s", e)

        # 2. Normalize
        try:
            result = normalize_backlog_tasks.run()
            normalize_stats = json.loads(result) if isinstance(result, str) else result
            log.info("backlog: normalize — %s tasks normalized", normalize_stats.get("tasks_normalized", 0))
        except Exception as e:
            normalize_stats = {"error": str(e)}
            log.warning("backlog: normalize failed: %s", e)

        # 3. Estimate SP
        try:
            result = bulk_assign_and_estimate.run()
            estimate_stats = json.loads(result) if isinstance(result, str) else result
            log.info("backlog: estimate — %s tasks got SP", estimate_stats.get("sp_set", 0))
        except Exception as e:
            estimate_stats = {"error": str(e)}
            log.warning("backlog: estimate failed: %s", e)

        # Guard: if ALL hygiene ops failed, bail — don't let the LLM hallucinate
        all_failed = all(
            "error" in stats
            for stats in (dedup_stats, normalize_stats, estimate_stats)
        )
        if all_failed:
            log.error("backlog: all hygiene operations failed — aborting crew")
            ctx["hygiene_stats"] = json.dumps({"status": "all_failed", "note": "All hygiene checks failed. Nothing to report."})
            return ctx

        # Strip error entries so the agent only sees real data
        hygiene = {}
        if "error" not in dedup_stats:
            hygiene["dedup"] = dedup_stats
        if "error" not in normalize_stats:
            hygiene["normalize"] = normalize_stats
        if "error" not in estimate_stats:
            hygiene["estimate"] = estimate_stats

        ctx["hygiene_stats"] = json.dumps(hygiene)

        return ctx

    # ── Agents ────────────────────────────────────────────────────────────

    @agent
    def backlog_importer_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["backlog_importer_agent"]),
            tools=[
                batch_import_engineering,
                sync_closed_issues,
            ],
            verbose=True,
            allow_delegation=False,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @agent
    def backlog_analyst_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["backlog_analyst_agent"]),
            tools=[
                scan_backlog_for_triage,
                execute_triage_actions,
            ],
            verbose=True,
            reasoning=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @agent
    def backlog_post_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["backlog_post_agent"]),
            tools=[post_triage_summary],
            verbose=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    # ── Tasks ─────────────────────────────────────────────────────────────

    @task
    def intake_scan(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["intake_scan"]))

    @task
    def close_sync(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["close_sync"]))

    @task
    def scan_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["scan_task"]))

    @task
    def decide_and_execute_task(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["decide_and_execute_task"]),
            guardrail=validate_triage_actions,
            output_pydantic=TriageDecision,
        )

    @task
    def post_report(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_report"]))

    # ── Crew ──────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            planning=False,
            memory=False,
        )
