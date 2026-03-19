from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, scan_backlog_for_sprint,
    execute_sprint_selection, post_sprint_plan, post,
)


@CrewBase
class SprintCrew:
    """AI-driven sprint planning — runs bi-weekly Sunday 18:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def sprint_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sprint_agent"],
            tools=[
                create_sprint_list, scan_backlog_for_sprint,
                execute_sprint_selection, post_sprint_plan, post,
            ],
            verbose=True,
        )

    @task
    def create_sprint_task(self) -> Task:
        return Task(config=self.tasks_config["create_sprint_task"])

    @task
    def scan_backlog_task(self) -> Task:
        return Task(config=self.tasks_config["scan_backlog_task"])

    @task
    def plan_and_execute_task(self) -> Task:
        return Task(config=self.tasks_config["plan_and_execute_task"])

    @task
    def post_sprint_plan_task(self) -> Task:
        return Task(config=self.tasks_config["post_sprint_plan_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
