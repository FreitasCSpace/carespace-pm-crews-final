from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    dedup_backlog_cleanup, bulk_assign_and_estimate,
    scan_backlog_for_triage, execute_triage_actions,
    post_triage_summary, post,
)


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
            config=self.agents_config["triage_agent"],
            tools=[
                dedup_backlog_cleanup, bulk_assign_and_estimate,
                scan_backlog_for_triage, execute_triage_actions,
                post_triage_summary, post,
            ],
            verbose=True,
        )

    @task
    def dedup_task(self) -> Task:
        return Task(config=self.tasks_config["dedup_task"])

    @task
    def bulk_assign_task(self) -> Task:
        return Task(config=self.tasks_config["bulk_assign_task"])

    @task
    def scan_task(self) -> Task:
        return Task(config=self.tasks_config["scan_task"])

    @task
    def decide_and_execute_task(self) -> Task:
        return Task(config=self.tasks_config["decide_and_execute_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
