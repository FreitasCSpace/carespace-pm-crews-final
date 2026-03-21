from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, scan_backlog_for_sprint,
    execute_sprint_selection, post_sprint_plan, post,
)
from shared.tools.clickup_helpers import (
    suggest_sprint_candidates, add_to_sprint_candidates,
    list_sprint_candidates, finalize_sprint_from_candidates,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_sprint_plan


@CrewBase
class SprintCrew:
    """AI-assisted sprint planning — uses Sprint Candidates as staging area."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def sprint_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["sprint_agent"]),
            tools=[
                create_sprint_list, scan_backlog_for_sprint,
                execute_sprint_selection, post_sprint_plan, post,
                suggest_sprint_candidates, add_to_sprint_candidates,
                list_sprint_candidates, finalize_sprint_from_candidates,
            ],
            verbose=True,
        )

    @task
    def create_sprint_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["create_sprint_task"]))

    @task
    def check_candidates_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["check_candidates_task"]))

    @task
    def plan_and_execute_task(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["plan_and_execute_task"]),
            guardrail=validate_sprint_plan,
        )

    @task
    def post_sprint_plan_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_sprint_plan_task"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
