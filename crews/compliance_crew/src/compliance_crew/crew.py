from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    batch_compliance_check,
    create_clickup_task,
    post_compliance,
    vanta_health_summary,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_compliance_output


@CrewBase
class ComplianceCrew:
    """Compliance health monitor — runs Daily 06:30 PDT."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def gather_agent(self) -> Agent:
        """Data-only agent for gather step — no Slack tools to prevent early posting."""
        return Agent(
            config=interpolate_config(self.agents_config["gather_agent"]),
            tools=[batch_compliance_check, vanta_health_summary],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def post_agent(self) -> Agent:
        """Post agent — has Slack + alert tools, runs only after gather completes."""
        return Agent(
            config=interpolate_config(self.agents_config["post_agent"]),
            tools=[post_compliance, create_clickup_task],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def gather_health(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["gather_health"]),
            agent=self.gather_agent(),
            guardrail=validate_compliance_output,
        )

    @task
    def post_report(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["post_report"]),
            agent=self.post_agent(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
