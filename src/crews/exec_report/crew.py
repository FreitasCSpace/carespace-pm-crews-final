from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from src.shared.tools import (
    create_sprint_list, get_tasks_by_list, batch_compliance_check,
    check_duplicate_task, create_clickup_task, post_exec,
    vanta_health_summary, scan_backlog_for_sprint,
)
from src.shared.config.context import interpolate_config
from src.shared.guardrails import validate_exec_report
from src.shared.models.exec_report import ExecGatherData


@CrewBase
class ExecReportCrew:
    """Weekly exec report — runs Friday 17:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from src.shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return ctx

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
            reasoning=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @task
    def gather(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["gather"]),
            guardrail=validate_exec_report,
            output_pydantic=ExecGatherData,
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
            planning=True,
            planning_llm="gpt-4o",
            skills=["src/shared/skills"],
            output_log_file=True,
        )
