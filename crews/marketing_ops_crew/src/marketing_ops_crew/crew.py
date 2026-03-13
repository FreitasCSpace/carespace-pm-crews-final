import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    post,
)


@CrewBase
class MarketingOpsCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def marketing_ops_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["marketing_ops_agent"],
            tools=[
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def monitor(self) -> Task:
        return Task(config=self.tasks_config["monitor"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
