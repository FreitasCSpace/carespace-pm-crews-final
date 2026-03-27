from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from src.shared.tools import (
    create_sprint_list, get_stale_prs, get_ci, get_activity,
    get_tasks_by_list, create_clickup_task, post_retro, post,
    close_sprint,
)
from src.shared.config.context import interpolate_config
from src.shared.guardrails import validate_retro_metrics


@CrewBase
class RetrospectiveCrew:
    """Sprint retrospective — runs bi-weekly Friday 16:00."""
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from src.shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return ctx

    @agent
    def retrospective_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["retrospective_agent"]),
            tools=[
                create_sprint_list, get_stale_prs, get_ci, get_activity,
                get_tasks_by_list, create_clickup_task, post_retro, post,
                close_sprint,
            ],
            verbose=True,
            allow_delegation=False,
            reasoning=True,
        )

    @task
    def find_sprint_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["find_sprint_task"]))

    @task
    def measure(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["measure"]),
            guardrail=validate_retro_metrics,
        )

    @task
    def close_and_carryover(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["close_and_carryover"]))

    @task
    def post_and_log(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["post_and_log"]))

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
        )
