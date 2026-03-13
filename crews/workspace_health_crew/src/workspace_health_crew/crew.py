import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks_by_list,
    post,
)


@CrewBase
class WorkspaceHealthCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def health_monitor_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["health_monitor_agent"],
            tools=[
                get_tasks_by_list,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def health_check_task(self) -> Task:
        return Task(config=self.tasks_config["health_check"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
