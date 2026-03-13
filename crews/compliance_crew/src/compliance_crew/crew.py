import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from shared.tools import (
    get_health_summary,
    get_controls,
    get_failing_tests,
    get_evidence,
    get_vulnerabilities,
    get_vendors,
    get_baa_gaps,
    get_access_reviews,
    get_people_risks,
    get_policies,
    post_compliance,
    post,
)


@CrewBase
class ComplianceCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def compliance_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["compliance_agent"],
            tools=[
                get_health_summary,
                get_controls,
                get_failing_tests,
                get_evidence,
                get_vulnerabilities,
                get_vendors,
                get_baa_gaps,
                get_access_reviews,
                get_people_risks,
                get_policies,
                post_compliance,
                post,
            ],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def vanta_sweep(self) -> Task:
        return Task(config=self.tasks_config["vanta_sweep"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
