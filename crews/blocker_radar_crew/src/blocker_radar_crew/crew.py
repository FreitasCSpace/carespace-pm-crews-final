import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks,
    get_tasks_multi,
    get_stale,
    create_alert,
    update_task,
    add_comment,
    post_blocker,
    post,
    log_run,
)


@CrewBase
class BlockerRadarCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def blocker_radar_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["blocker_radar_agent"],
            tools=[
                get_tasks,
                get_tasks_multi,
                get_stale,
                create_alert,
                update_task,
                add_comment,
                post_blocker,
                post,
                log_run,
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
