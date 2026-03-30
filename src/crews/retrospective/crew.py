from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, get_tasks_by_list, post_retro,
    close_sprint,
)
from shared.config.context import interpolate_config


@CrewBase
class RetrospectiveCrew:
    """Sprint retrospective — 100% Python in before_kickoff.

    Checks sprint dates, tasks, runs retro if ready, posts to Slack.
    If sprint is active or empty, does NOTHING — no Slack, no vault.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        import json, logging
        from datetime import date
        from shared.config.context import crew_context, SP_CUSTOM_FIELD_ID

        log = logging.getLogger(__name__)
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── 1. Get sprint ──
        try:
            sprint_result = create_sprint_list.run()
            sprint = json.loads(sprint_result) if isinstance(sprint_result, str) else sprint_result
        except Exception as e:
            log.warning("retro: sprint lookup failed: %s", e)
            ctx["retro_result"] = f"Sprint lookup failed: {e}"
            return ctx

        sprint_name = sprint.get("sprint_name", "Unknown")
        end_date_str = sprint.get("end_date", "")
        list_id = sprint.get("list_id", "")
        status = sprint.get("status", "")

        log.info("retro: %s (status=%s, end=%s, list=%s)", sprint_name, status, end_date_str, list_id)

        # ── 2. Sprint must have ended ──
        if status == "created":
            log.info("retro: no sprint to review — skipping silently")
            ctx["retro_result"] = "No completed sprint."
            return ctx

        try:
            end_date = date.fromisoformat(end_date_str)
            if date.today() <= end_date:
                log.info("retro: sprint still active (ends %s) — skipping silently", end_date_str)
                ctx["retro_result"] = f"Sprint still active (ends {end_date_str}). Skipped."
                return ctx
        except Exception:
            pass

        # ── 3. Get tasks ──
        tasks = []
        try:
            tasks_result = get_tasks_by_list.run(list_id=list_id, status="", include_closed=True)
            tasks = json.loads(tasks_result) if isinstance(tasks_result, str) else tasks_result
            if isinstance(tasks, dict):
                tasks = []
        except Exception:
            pass

        if not tasks:
            log.info("retro: sprint empty — skipping silently")
            ctx["retro_result"] = "Sprint empty. Skipped."
            return ctx

        # ── 4. Calculate metrics ──
        done_tasks, carryover_tasks = [], []
        total_sp, done_sp = 0, 0
        DONE = {"complete", "done", "closed"}

        for t in tasks:
            task_status = (t.get("status") or "").lower()
            sp = t.get("points") or 0
            total_sp += sp
            if task_status in DONE:
                done_tasks.append(t)
                done_sp += sp
            else:
                carryover_tasks.append(t)

        completion_pct = round(len(done_tasks) / len(tasks) * 100, 1) if tasks else 0
        sprint_number = sprint.get("sprint_number", 1)

        log.info("retro: %d tasks, %d done (%s%%), %d SP, %d carryovers",
                 len(tasks), len(done_tasks), completion_pct, done_sp, len(carryover_tasks))

        # ── 5. Close sprint (move carryovers to Sprint Candidates) ──
        try:
            close_result = close_sprint.run()
            close_data = json.loads(close_result) if isinstance(close_result, str) else close_result
            log.info("retro: close_sprint result: %s", str(close_data)[:200])
        except Exception as e:
            log.error("retro: close_sprint failed: %s", e)

        # ── 6. Post retro to Slack ──
        try:
            post_retro.run(
                sprint_name=sprint_name,
                completion_pct=completion_pct,
                velocity_sp=done_sp,
                carry_over=len(carryover_tasks),
                doc_url="N/A",
            )
            log.info("retro: posted to Slack")
        except Exception as e:
            log.error("retro: Slack post failed: %s", e)

        ctx["retro_result"] = (
            f"Retro complete: {sprint_name} — {completion_pct}% completion, "
            f"{done_sp} SP velocity, {len(carryover_tasks)} carryovers."
        )
        return ctx

    # ── Minimal crew — just confirms ──

    @agent
    def retrospective_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["retrospective_agent"]),
            tools=[],
            verbose=True,
        )

    @task
    def confirm_task(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["confirm_task"]))

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
