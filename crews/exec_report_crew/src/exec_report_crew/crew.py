import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks,
    get_tasks_multi,
    get_stale,
    get_velocity,
    get_health_summary,
    write_doc_page,
    post_exec,
    post,
    log_run,
)


@CrewBase
class ExecReportCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def exec_reporter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["exec_reporter_agent"],
            tools=[
                get_tasks,
                get_tasks_multi,
                get_stale,
                get_velocity,
                get_health_summary,
                write_doc_page,
                post_exec,
                post,
                log_run,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def gather(self) -> Task:
        return Task(config=self.tasks_config["gather"])

    @task
    def write_and_post(self) -> Task:
        return Task(config=self.tasks_config["write_and_post"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
