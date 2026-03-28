from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    batch_import_engineering,
    sync_closed_issues,
    post,
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
        return ctx

    # ── Agents ────────────────────────────────────────────────────────────

    @agent
    def backlog_importer_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["backlog_importer_agent"]),
            tools=[
                batch_import_engineering,
                sync_closed_issues,
                post,
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
                dedup_backlog_cleanup,
                normalize_backlog_tasks,
                bulk_assign_and_estimate,
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
    def dedup_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["dedup_task"]))

    @task
    def normalize_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["normalize_task"]))

    @task
    def estimate_sp_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["estimate_sp_task"]))

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
    def post_triage_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_triage_task"]))

    # ── Crew ──────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            planning=True,
            planning_llm="gpt-4o",
            skills=["src/shared/skills"],
            output_log_file=True,
        )
