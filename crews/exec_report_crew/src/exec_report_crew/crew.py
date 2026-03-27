from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, after_kickoff, crew, task

from shared.tools import (
    create_sprint_list, get_tasks_by_list, batch_compliance_check,
    check_duplicate_task, create_clickup_task, post_exec,
    vanta_health_summary, scan_backlog_for_sprint,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_exec_report
from shared.vault_hooks import vault_before_kickoff, vault_after_kickoff


@CrewBase
class ExecReportCrew:
    """Weekly exec report — runs Friday 17:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return vault_before_kickoff("exec_report", ctx)

    @after_kickoff
    def save_to_vault(self, output):
        vault_after_kickoff("exec_report", output)
        return output

    @agent
    def exec_reporter_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["exec_reporter_agent"]),
            tools=[
                create_sprint_list, get_tasks_by_list, batch_compliance_check,
                check_duplicate_task, create_clickup_task, post_exec,
                vanta_health_summary, scan_backlog_for_sprint,
            ],
            verbose=True,
        )

    @task
    def gather(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["gather"]),
            guardrail=validate_exec_report,
        )

    @task
    def write_and_post(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["write_and_post"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
