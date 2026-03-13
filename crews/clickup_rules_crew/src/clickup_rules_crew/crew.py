import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_tasks_by_list,
    check_duplicate_task,
    auto_estimate_sp,
    update_clickup_task,
    add_tag_to_task,
    create_clickup_task,
    post_sla_breach,
)


@CrewBase
class ClickupRulesCrewCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def rules_enforcer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["rules_enforcer_agent"],
            tools=[
                get_tasks_by_list,
                check_duplicate_task,
                auto_estimate_sp,
                update_clickup_task,
                add_tag_to_task,
                create_clickup_task,
                post_sla_breach,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def enforce_guard_rules(self) -> Task:
        return Task(config=self.tasks_config["enforce_guard_rules"])

    @task
    def enforce_flow_and_signal_rules(self) -> Task:
        return Task(config=self.tasks_config["enforce_flow_and_signal_rules"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
