import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    post_gtm,
    post,
)


@CrewBase
class DealIntelCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def deal_intel_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["deal_intel_agent"],
            tools=[
                post_gtm,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def analyze(self) -> Task:
        return Task(config=self.tasks_config["analyze"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
