import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_contributors,
    get_tasks_by_list,
    post,
)


@CrewBase
class AssignmentCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def task_assigner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["task_assigner_agent"],
            tools=[
                get_contributors,
                get_tasks_by_list,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def read_state(self) -> Task:
        return Task(config=self.tasks_config["read_state"])

    @task
    def assign_all(self) -> Task:
        return Task(config=self.tasks_config["assign_all"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
