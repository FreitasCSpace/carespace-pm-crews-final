import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_issues,
    get_prs,
    get_contributors,
    get_tasks_by_list,
    check_duplicate_task,
    comment_issue,
    post,
)


@CrewBase
class IntakeCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def intake_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["intake_agent"],
            tools=[
                get_issues,
                get_prs,
                get_contributors,
                get_tasks_by_list,
                check_duplicate_task,
                comment_issue,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def intake_scan(self) -> Task:
        return Task(config=self.tasks_config["intake_scan"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
