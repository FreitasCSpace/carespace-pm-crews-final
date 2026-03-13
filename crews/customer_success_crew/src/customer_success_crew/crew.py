import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks_by_list,
    check_duplicate_task,
    post_cs_alert,
    post,
)


@CrewBase
class CustomerSuccessCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def customer_success_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["customer_success_agent"],
            tools=[
                get_tasks_by_list,
                check_duplicate_task,
                post_cs_alert,
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
