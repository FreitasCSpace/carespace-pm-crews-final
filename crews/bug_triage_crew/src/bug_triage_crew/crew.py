import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks,
    get_unassigned,
    get_stale,
    get_workload,
    get_members,
    update_task,
    add_comment,
    create_alert,
    post_sla_breach,
    post_blocker,
    post,
    log_run,
)


@CrewBase
class BugTriageCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def bug_triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["bug_triage_agent"],
            tools=[
                get_tasks,
                get_unassigned,
                get_stale,
                get_workload,
                get_members,
                update_task,
                add_comment,
                create_alert,
                post_sla_breach,
                post_blocker,
                post,
                log_run,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def triage(self) -> Task:
        return Task(config=self.tasks_config["triage"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
