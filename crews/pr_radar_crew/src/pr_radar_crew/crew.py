import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_prs, get_ci, get_stale_prs, get_contributors,
    get_tasks_by_list, check_duplicate_task, create_clickup_task,
    post_blocker, post_pr_radar, post,
)


@CrewBase
class PrRadarCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def pr_radar_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["pr_radar_agent"],
            tools=[
                get_prs, get_ci, get_stale_prs, get_contributors,
                get_tasks_by_list, check_duplicate_task, create_clickup_task,
                post_blocker, post_pr_radar, post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def scan(self) -> Task:
        return Task(config=self.tasks_config["scan"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
