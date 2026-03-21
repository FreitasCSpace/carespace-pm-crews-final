import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    get_tasks_by_list,
    check_duplicate_task,
    create_clickup_task,
    update_clickup_task,
    post_gtm,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_deal_intel


@CrewBase
class DealIntelCrew:
    """GTM pipeline intelligence — runs Monday 07:00 PDT."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def deal_intel_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["deal_intel_agent"]),
            tools=[
                get_tasks_by_list,
                check_duplicate_task,
                create_clickup_task,
                update_clickup_task,
                post_gtm,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def analyze_pipeline(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["analyze_pipeline"]),
            guardrail=validate_deal_intel,
        )

    @task
    def post_pipeline_report(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_pipeline_report"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
