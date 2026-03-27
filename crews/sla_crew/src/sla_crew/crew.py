import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    scan_sprint_sla, create_clickup_task, check_duplicate_task,
    notify_task_assignee, post_sla_breach, post,
)
from shared.config.context import interpolate_config


@CrewBase
class SlaCrew:
    """Sprint SLA Monitor — checks sprint items for SLA breaches."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def sla_monitor_agent(self) -> Agent:
        """Data agent — scans sprint, creates alerts, DMs assignees."""
        return Agent(
            config=interpolate_config(self.agents_config["sla_monitor_agent"]),
            tools=[
                scan_sprint_sla, create_clickup_task, check_duplicate_task,
                notify_task_assignee,
            ],
            verbose=True,
        )

    @agent
    def sla_post_agent(self) -> Agent:
        """Post agent — Slack only, no data collection."""
        return Agent(
            config=interpolate_config(self.agents_config["sla_post_agent"]),
            tools=[post_sla_breach, post],
            verbose=True,
        )

    @task
    def scan_sprint_sla_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["scan_sprint_sla_task"]))

    @task
    def post_sla_report_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_sla_report_task"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
