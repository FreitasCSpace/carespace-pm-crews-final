from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, get_stale_prs, get_ci, get_activity,
    get_tasks_by_list, create_clickup_task, post_retro,
    close_sprint,
)
from shared.config.context import interpolate_config


@CrewBase
class RetrospectiveCrew:
    """Sprint retrospective — 100% Python guards in before_kickoff.

    Checks sprint dates and task count before running. If sprint is
    still active or empty, returns silently with no Slack post.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        import json, logging
        from datetime import date
        from shared.config.context import crew_context

        log = logging.getLogger(__name__)
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── 1. Check sprint status ──
        try:
            sprint_result = create_sprint_list.run()
            sprint = json.loads(sprint_result) if isinstance(sprint_result, str) else sprint_result
        except Exception as e:
            log.warning("retro: sprint lookup failed: %s", e)
            ctx["retro_skip"] = "true"
            ctx["retro_result"] = f"Sprint lookup failed: {e}"
            return ctx

        sprint_name = sprint.get("sprint_name", "Unknown")
        end_date_str = sprint.get("end_date", "")
        list_id = sprint.get("list_id", "")
        status = sprint.get("status", "")

        log.info("retro: %s (status=%s, end_date=%s)", sprint_name, status, end_date_str)

        # ── 2. Sprint must have ended ──
        if status == "created":
            log.info("retro: no sprint to review (just created)")
            ctx["retro_skip"] = "true"
            ctx["retro_result"] = "No completed sprint to review."
            return ctx

        try:
            end_date = date.fromisoformat(end_date_str)
            today = date.today()
            if today <= end_date:
                log.info("retro: sprint still active (ends %s) — skipping silently", end_date_str)
                ctx["retro_skip"] = "true"
                ctx["retro_result"] = f"Sprint still active (ends {end_date_str}). Skipped."
                return ctx
        except Exception:
            pass  # If date parsing fails, proceed anyway

        # ── 3. Sprint must have tasks ──
        tasks = []
        try:
            tasks_result = get_tasks_by_list.run(list_id=list_id, status="", include_closed=True)
            tasks = json.loads(tasks_result) if isinstance(tasks_result, str) else tasks_result
            if isinstance(tasks, dict):
                tasks = []
        except Exception:
            pass

        if not tasks:
            log.info("retro: sprint is empty — skipping silently")
            ctx["retro_skip"] = "true"
            ctx["retro_result"] = "Sprint is empty. Skipped."
            return ctx

        # ── Sprint is ready for retro — pass data for the LLM tasks ──
        log.info("retro: sprint ready — %d tasks, proceeding with retro", len(tasks))
        ctx["retro_skip"] = "false"
        ctx["retro_sprint_name"] = sprint_name
        ctx["retro_list_id"] = list_id
        ctx["retro_task_count"] = str(len(tasks))
        return ctx

    @agent
    def retrospective_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["retrospective_agent"]),
            tools=[
                create_sprint_list, get_stale_prs, get_ci, get_activity,
                get_tasks_by_list, create_clickup_task, post_retro,
                close_sprint,
            ],
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @task
    def find_sprint_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["find_sprint_task"]))

    @task
    def measure(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["measure"]))

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
            planning=False,
            memory=False,
        )
