from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, after_kickoff, crew, task

from shared.tools import (
    batch_compliance_check,
    post_compliance,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_compliance_output
from shared.vault_hooks import vault_before_kickoff, vault_after_kickoff


@CrewBase
class ComplianceCrew:
    """Compliance health monitor — runs Daily 06:30 PDT."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return vault_before_kickoff("compliance", ctx)

    @after_kickoff
    def save_to_vault(self, output):
        vault_after_kickoff("compliance", output)
        return output

    @agent
    def gather_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["gather_agent"]),
            tools=[batch_compliance_check],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def post_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["post_agent"]),
            tools=[post_compliance],
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
