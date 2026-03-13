import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_stale_prs,
    get_ci,
    post_standup,
    post_blocker,
    post,
)


@CrewBase
class StandupCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def standup_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["standup_agent"],
            tools=[
                get_stale_prs,
                get_ci,
                post_standup,
                post_blocker,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def gather(self) -> Task:
        return Task(config=self.tasks_config["gather"])

    @task
    def post_and_escalate(self) -> Task:
        return Task(config=self.tasks_config["post_and_escalate"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
