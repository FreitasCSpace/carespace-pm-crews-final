import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks,
    get_velocity,
    get_stale_prs,
    get_ci,
    get_activity,
    write_doc_page,
    post_retro,
    post,
    log_run,
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
                get_tasks,
                get_velocity,
                get_stale_prs,
                get_ci,
                get_activity,
                write_doc_page,
                post_retro,
                post,
                log_run,
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
