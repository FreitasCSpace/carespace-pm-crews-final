import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, after_kickoff, crew, task

from shared.tools import (
    fetch_huddle_notes,
    create_clickup_task,
    check_duplicate_task,
    post_huddle_actions,
)
from shared.config.context import interpolate_config
from shared.vault_hooks import vault_before_kickoff, vault_after_kickoff


@CrewBase
class HuddleNotesCrewCrew:
    """Fetches Slack huddle notes, extracts action items, creates ClickUp tasks."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})
        return vault_before_kickoff("huddle_notes", ctx)

    @after_kickoff
    def save_to_vault(self, output):
        vault_after_kickoff("huddle_notes", output)
        return output

    @agent
    def huddle_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["huddle_agent"]),
            tools=[
                fetch_huddle_notes,
                create_clickup_task,
                check_duplicate_task,
                post_huddle_actions,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def extract_actions_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["extract_actions_task"]))

    @task
    def create_tasks_and_post(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["create_tasks_and_post"]))

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
