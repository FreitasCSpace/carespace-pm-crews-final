from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    batch_triage_backlog, dedup_backlog_cleanup, post,
)


@CrewBase
class TriageCrew:
    """Bug triage + rules enforcement + dedup — runs every 6 hours."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @agent
    def triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["triage_agent"],
            tools=[batch_triage_backlog, dedup_backlog_cleanup, post],
            verbose=True,
        )

    @task
    def dedup_task(self) -> Task:
        return Task(config=self.tasks_config["dedup_task"])

    @task
    def triage_task(self) -> Task:
        return Task(config=self.tasks_config["triage_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
