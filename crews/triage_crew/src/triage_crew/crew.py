from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks_by_list, check_duplicate_task, auto_estimate_sp,
    update_clickup_task, add_tag_to_task, create_clickup_task,
    post_sla_breach, post_blocker, post,
)


@CrewBase
class TriageCrew:
    """Bug triage + rules enforcement — runs every 6 hours."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @agent
    def triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["triage_agent"],
            tools=[
                get_tasks_by_list, check_duplicate_task, auto_estimate_sp,
                update_clickup_task, add_tag_to_task, create_clickup_task,
                post_sla_breach, post_blocker, post,
            ],
            verbose=True,
        )

    @task
    def triage_and_enforce(self) -> Task:
        return Task(config=self.tasks_config["triage_and_enforce"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
