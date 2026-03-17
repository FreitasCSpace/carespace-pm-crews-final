from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_stale_prs, get_ci, get_tasks_by_list,
    post_standup, post_blocker, post,
)


@CrewBase
class DailyPulseCrew:
    """Daily standup + blocker detection — runs Mon-Fri 08:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @agent
    def daily_pulse_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["daily_pulse_agent"],
            tools=[
                get_stale_prs, get_ci, get_tasks_by_list,
                post_standup, post_blocker, post,
            ],
            verbose=True,
        )

    @task
    def scan_and_gather(self) -> Task:
        return Task(config=self.tasks_config["scan_and_gather"])

    @task
    def post_and_escalate(self) -> Task:
        return Task(config=self.tasks_config["post_and_escalate"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
