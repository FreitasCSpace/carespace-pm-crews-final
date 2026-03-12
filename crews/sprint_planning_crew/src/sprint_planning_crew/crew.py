import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks,
    get_workload,
    get_issues,
    get_stale_prs,
    get_ci,
    create_sprint_list,
    move_task,
    create_task,
    update_task,
    add_comment,
    post_sprint_plan,
    post,
    log_run,
)


@CrewBase
class SprintPlanningCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def sprint_planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sprint_planner_agent"],
            tools=[
                get_tasks,
                get_workload,
                get_issues,
                get_stale_prs,
                get_ci,
                create_sprint_list,
                move_task,
                create_task,
                update_task,
                add_comment,
                post_sprint_plan,
                post,
                log_run,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def create_sprint_list_task(self) -> Task:
        return Task(config=self.tasks_config["create_sprint_list_task"])

    @task
    def score_and_select_task(self) -> Task:
        return Task(config=self.tasks_config["score_and_select_task"])

    @task
    def populate_sprint_task(self) -> Task:
        return Task(config=self.tasks_config["populate_sprint_task"])

    @task
    def post_and_log_task(self) -> Task:
        return Task(config=self.tasks_config["post_and_log_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
