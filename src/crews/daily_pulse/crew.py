from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, get_stale_prs, get_tasks_by_list,
    get_prs, get_contributors, get_stale_issues, check_stale_sprint_tasks,
    post_standup,
)
from shared.config.context import interpolate_config
from shared.guardrails import validate_standup_data
from shared.models.daily_pulse import PulseData


@CrewBase
class DailyPulseCrew:
    """Daily sprint intelligence digest — runs Mon-Fri 07:45 PDT."""

    agents_config  = "config/agents.yaml"
    tasks_config   = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        from shared.config.context import crew_context
        import json, logging

        log = logging.getLogger(__name__)
        ctx = crew_context()
        ctx.update(inputs or {})

        # ── Pre-gather sprint data (no LLM needed) ──
        sprint_data = {}

        # 1. Get active sprint
        try:
            sprint_result = create_sprint_list.run()
            sprint = json.loads(sprint_result) if isinstance(sprint_result, str) else sprint_result
            sprint_data["sprint"] = sprint
            list_id = sprint.get("list_id", "")
        except Exception as e:
            log.warning("daily_pulse: sprint lookup failed: %s", e)
            sprint_data["sprint"] = {"error": str(e)}
            list_id = ""

        # 2. Get sprint tasks
        tasks = []
        if list_id:
            try:
                tasks_result = get_tasks_by_list.run(
                    list_id=list_id, status="", include_closed=True,
                )
                tasks = json.loads(tasks_result) if isinstance(tasks_result, str) else tasks_result
                if isinstance(tasks, dict) and "error" in tasks:
                    tasks = []
            except Exception as e:
                log.warning("daily_pulse: tasks fetch failed: %s", e)
        sprint_data["tasks"] = tasks

        # 3. Check stale sprint tasks (by ClickUp comments)
        if tasks:
            non_done_ids = [
                t["id"] for t in tasks
                if t.get("status") not in ("complete", "done")
            ]
            if non_done_ids:
                try:
                    stale_result = check_stale_sprint_tasks.run(
                        task_ids_json=json.dumps(non_done_ids), days=3,
                    )
                    sprint_data["stale_tasks"] = (
                        json.loads(stale_result)
                        if isinstance(stale_result, str)
                        else stale_result
                    )
                except Exception as e:
                    log.warning("daily_pulse: stale check failed: %s", e)
                    sprint_data["stale_tasks"] = []
            else:
                sprint_data["stale_tasks"] = []
        else:
            sprint_data["stale_tasks"] = []

        # 4. Get open PRs (for PR coverage)
        try:
            prs_result = get_prs.run(repo="")
            sprint_data["open_prs"] = (
                json.loads(prs_result)
                if isinstance(prs_result, str)
                else prs_result
            )
        except Exception as e:
            log.warning("daily_pulse: PRs fetch failed: %s", e)
            sprint_data["open_prs"] = []

        # 5. Get stale PRs
        try:
            stale_prs_result = get_stale_prs.run(days=7)
            sprint_data["stale_prs"] = (
                json.loads(stale_prs_result)
                if isinstance(stale_prs_result, str)
                else stale_prs_result
            )
        except Exception as e:
            log.warning("daily_pulse: stale PRs failed: %s", e)
            sprint_data["stale_prs"] = []

        # 6. Get stale GitHub issues
        try:
            stale_issues_result = get_stale_issues.run(days=3)
            sprint_data["stale_issues"] = (
                json.loads(stale_issues_result)
                if isinstance(stale_issues_result, str)
                else stale_issues_result
            )
        except Exception as e:
            log.warning("daily_pulse: stale issues failed: %s", e)
            sprint_data["stale_issues"] = []

        ctx["sprint_data"] = json.dumps(sprint_data, indent=2)
        return ctx

    @agent
    def daily_pulse_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["daily_pulse_agent"]),
            tools=[post_standup],
            verbose=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @task
    def analyze_sprint(self) -> Task:
        return Task(
            config=interpolate_config(self.tasks_config["analyze_sprint"]),
            guardrail=validate_standup_data,
            output_pydantic=PulseData,
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
            output_log_file=True,
        )
