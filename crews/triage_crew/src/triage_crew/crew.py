from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    dedup_backlog_cleanup, bulk_assign_and_estimate,
    scan_backlog_for_triage, execute_triage_actions,
    post_triage_summary,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_triage_actions


@CrewBase
class TriageCrew:
    """Bug triage + rules enforcement + dedup — runs every 6 hours."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def triage_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["triage_agent"]),
            tools=[
                dedup_backlog_cleanup, bulk_assign_and_estimate,
                scan_backlog_for_triage, execute_triage_actions,
                post_triage_summary,
            ],
            verbose=True,
        )

    @task
    def dedup_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["dedup_task"]))

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
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
