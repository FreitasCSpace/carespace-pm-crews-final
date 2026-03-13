import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_stale_prs,
    get_ci,
    get_activity,
    get_tasks_by_list,
    post_retro,
    post,
)


@CrewBase
class RetrospectiveCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def retrospective_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["retrospective_agent"],
            tools=[
                get_stale_prs,
                get_ci,
                get_activity,
                get_tasks_by_list,
                post_retro,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def measure(self) -> Task:
        return Task(config=self.tasks_config["measure"])

    @task
    def write_retro(self) -> Task:
        return Task(config=self.tasks_config["write_retro"])

    @task
    def post_and_log(self) -> Task:
        return Task(config=self.tasks_config["post_and_log"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
