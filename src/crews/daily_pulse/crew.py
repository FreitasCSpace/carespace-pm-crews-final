from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from src.shared.tools import (
    create_sprint_list, get_stale_prs, get_ci, get_tasks_by_list,
    get_prs, get_contributors, get_stale_issues,
    post_standup,
)
from src.shared.config.context import interpolate_config
from src.shared.guardrails import validate_standup_data


@CrewBase
class DailyPulseCrew:
    """Daily sprint intelligence digest — runs Mon-Fri 07:45 PDT."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from src.shared.config.context import crew_context
        ctx = crew_context()
        ctx.update(inputs or {})
        return ctx

    @agent
    def daily_pulse_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["daily_pulse_agent"]),
            tools=[
                create_sprint_list, get_stale_prs, get_ci, get_tasks_by_list,
                get_prs, get_contributors, get_stale_issues,
                post_standup,
            ],
            verbose=True,
        )

    @task
    def find_sprint_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["find_sprint_task"]))

    @task
    def scan_and_gather(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["scan_and_gather"]),
            guardrail=validate_standup_data,
        )

    @task
    def compile_and_post(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["compile_and_post"]))

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
