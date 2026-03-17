from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_health_summary, get_tasks_by_list, check_duplicate_task,
    create_clickup_task, post_exec, post,
)


@CrewBase
class ExecReportCrew:
    """Weekly exec report + crew health + marketing ops — runs Friday 17:00."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @agent
    def exec_reporter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["exec_reporter_agent"],
            tools=[
                get_health_summary, get_tasks_by_list, check_duplicate_task,
                create_clickup_task, post_exec, post,
            ],
            verbose=True,
        )

    @task
    def gather(self) -> Task:
        return Task(config=self.tasks_config["gather"])

    @task
    def write_and_post(self) -> Task:
        return Task(config=self.tasks_config["write_and_post"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
