import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks_by_list,
    create_clickup_task,
    post_compliance,
    post,
)


@CrewBase
class ComplianceCrew:
    """Compliance health monitor — runs daily 07:00.
    Uses MCP Vanta tools (injected by CrewHub) for health data.
    Our custom tools only handle ClickUp and Slack.
    """
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def compliance_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["compliance_agent"],
            tools=[
                get_tasks_by_list,
                create_clickup_task,
                post_compliance,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def health_check(self) -> Task:
        return Task(config=self.tasks_config["health_check"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
