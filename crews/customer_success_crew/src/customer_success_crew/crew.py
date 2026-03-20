from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    get_tasks_by_list,
    check_duplicate_task,
    create_clickup_task,
    update_clickup_task,
    post_cs_alert,
    post_cs_summary,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_cs_output


@CrewBase
class CustomerSuccessCrew:
    """Customer success monitor — runs daily 08:00."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def customer_success_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["customer_success_agent"]),
            tools=[
                get_tasks_by_list,
                check_duplicate_task,
                create_clickup_task,
                update_clickup_task,
                post_cs_alert,
                post_cs_summary,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def scan_accounts(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["scan_accounts"]),
            guardrail=validate_cs_output,
        )

    @task
    def post_cs_summary_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_cs_summary"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
