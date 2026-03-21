import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    batch_import_engineering,
    batch_import_compliance,
    sync_closed_issues,
    post,
)
from shared.config.context import interpolate_config


@CrewBase
class IntakeCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def intake_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["intake_agent"]),
            tools=[
                batch_import_engineering,
                batch_import_compliance,
                sync_closed_issues,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def intake_scan(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["intake_scan"]))

    @task
    def close_sync(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["close_sync"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
