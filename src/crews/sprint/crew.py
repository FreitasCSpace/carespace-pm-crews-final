from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, post_sprint_plan, post_sprint_status, get_last_sprint_velocity,
)
from shared.tools.clickup_helpers import (
    list_sprint_candidates, finalize_sprint_from_candidates,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_sprint_plan
from shared.models.sprint import SprintPlan


@CrewBase
class SprintCrew:
    """Sprint finalization — moves Sprint Candidates into the sprint."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return ctx

    @agent
    def sprint_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["sprint_agent"]),
            tools=[
                create_sprint_list, get_last_sprint_velocity,
                list_sprint_candidates, finalize_sprint_from_candidates,
            ],
            verbose=True,
            reasoning=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @agent
    def sprint_post_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["sprint_post_agent"]),
            tools=[post_sprint_plan, post_sprint_status],
            verbose=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @task
    def check_candidates_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["check_candidates_task"]))

    @task
    def finalize_task(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["finalize_task"]),
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
            planning=False,
            memory=False,
        )
