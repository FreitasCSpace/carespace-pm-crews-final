import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, get_stale_prs, get_ci, get_activity,
    get_tasks_by_list, create_clickup_task, post_retro, post,
)
from shared.config.context import interpolate_config


@CrewBase
class RetrospectiveCrewCrew:
    """Sprint retrospective — runs bi-weekly Friday 16:00."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def retrospective_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["retrospective_agent"]),
            tools=[
                create_sprint_list, get_stale_prs, get_ci, get_activity,
                get_tasks_by_list, create_clickup_task, post_retro, post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def find_sprint_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["find_sprint_task"]))

    @task
    def measure(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["measure"]))

    @task
    def post_and_log(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_and_log"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
