from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    create_sprint_list, batch_populate_sprint,
    post_sprint_plan, post,
)


@CrewBase
class SprintCrew:
    """Sprint planning + assignment crew — runs bi-weekly Sunday 18:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @agent
    def sprint_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sprint_agent"],
            tools=[
                create_sprint_list, batch_populate_sprint,
                post_sprint_plan, post,
            ],
            verbose=True,
        )

    @task
    def create_sprint_task(self) -> Task:
        return Task(config=self.tasks_config["create_sprint_task"])

    @task
    def populate_sprint_task(self) -> Task:
        return Task(config=self.tasks_config["populate_sprint_task"])

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
