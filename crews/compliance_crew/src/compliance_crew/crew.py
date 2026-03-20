from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    batch_compliance_check,
    create_clickup_task,
    post_compliance,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_compliance_output


@CrewBase
class ComplianceCrew:
    """Compliance health monitor — runs daily 07:00."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def compliance_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["compliance_agent"]),
            tools=[batch_compliance_check, create_clickup_task, post_compliance],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def gather_health(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["gather_health"]),
            guardrail=validate_compliance_output,
        )

    @task
    def post_report(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_report"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
