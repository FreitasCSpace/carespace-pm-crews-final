import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    batch_compliance_check,
    create_clickup_task,
    post_compliance,
    post,
)
from shared.config.context import interpolate_config


@CrewBase
class ComplianceCrew:
    """Compliance health monitor — runs daily 07:00."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def compliance_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["compliance_agent"]),
            tools=[batch_compliance_check, create_clickup_task, post_compliance, post],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def health_check(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["health_check"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
