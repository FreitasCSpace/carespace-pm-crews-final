from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import (
    create_sprint_list, post_sprint_plan, post_sprint_status, get_last_sprint_velocity,
)
from shared.tools.clickup_helpers import (
    list_sprint_candidates, finalize_sprint_from_candidates,
)
from shared.config.context import interpolate_config


@CrewBase
class SprintCrew:
    """Sprint finalization — 100% Python logic in before_kickoff.

    Checks candidates, finalizes sprint if ready, posts to Slack.
    LLM only confirms the result.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        import json, logging
        from shared.config.context import crew_context

        log = logging.getLogger(__name__)
        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── 1. Check if a sprint is active ──
        try:
            sprint_result = create_sprint_list.run()
            sprint = json.loads(sprint_result) if isinstance(sprint_result, str) else sprint_result
        except Exception as e:
            log.error("sprint: lookup failed: %s", e)
            ctx["sprint_result"] = f"Sprint lookup failed: {e}"
            return ctx

        list_id = sprint.get("list_id", "")
        sprint_name = sprint.get("sprint_name", "Unknown")
        status = sprint.get("status", "")
        timing = sprint.get("timing", {})
        end_date = timing.get("end_date", "")
        sprint_started = timing.get("sprint_started", False)

        log.info("sprint: %s (status=%s, list_id=%s)", sprint_name, status, list_id)

        # ── 2. If sprint is already active, check if candidates are for next sprint ──
        if status == "active" and sprint_started:
            # Sprint is running — candidates are for the NEXT sprint
            try:
                candidates_result = list_sprint_candidates.run()
                candidates = json.loads(candidates_result) if isinstance(candidates_result, str) else candidates_result
                candidate_count = len(candidates) if isinstance(candidates, list) else 0
            except Exception:
                candidate_count = 0

            msg_detail = f"{candidate_count} Sprint Candidates being collected for the next sprint.\nCurrent sprint ends {end_date}."
            log.info("sprint: active — %d candidates for next sprint", candidate_count)

            try:
                post_sprint_status.run(
                    headline=f"{sprint_name} — Active until {end_date}",
                    detail=msg_detail,
                )
                log.info("sprint: posted status to Slack")
            except Exception as e:
                log.error("sprint: Slack post failed: %s", e)

            ctx["sprint_result"] = f"Sprint active. {candidate_count} candidates for next sprint."
            return ctx

        # ── 3. Sprint was just created (or no active sprint) — check candidates ──
        try:
            candidates_result = list_sprint_candidates.run()
            candidates = json.loads(candidates_result) if isinstance(candidates_result, str) else candidates_result
            if isinstance(candidates, dict):
                candidates = candidates.get("tasks", [])
            candidate_count = len(candidates) if isinstance(candidates, list) else 0
        except Exception as e:
            log.warning("sprint: candidates check failed: %s", e)
            candidate_count = 0

        log.info("sprint: %d candidates found", candidate_count)

        if candidate_count == 0:
            # No candidates — nothing to finalize
            try:
                post_sprint_status.run(
                    headline="Sprint Planning — Not Ready",
                    detail="No active sprint. Sprint Candidates is empty.\nTeam needs to add tasks before the next sprint can start.",
                )
            except Exception as e:
                log.error("sprint: Slack post failed: %s", e)

            ctx["sprint_result"] = "No candidates — sprint not planned."
            return ctx

        # ── 4. Finalize: move candidates into the sprint ──
        try:
            finalize_result = finalize_sprint_from_candidates.run(sprint_list_id=list_id)
            result = json.loads(finalize_result) if isinstance(finalize_result, str) else finalize_result
            tasks_moved = result.get("tasks_moved", 0)
            total_sp = result.get("total_sp", 0)
            warnings = result.get("warnings", [])
            log.info("sprint: finalized — %d tasks, %d SP, %d warnings", tasks_moved, total_sp, len(warnings))
        except Exception as e:
            log.error("sprint: finalization failed: %s", e)
            ctx["sprint_result"] = f"Finalization failed: {e}"
            return ctx

        # ── 5. Post sprint plan to Slack ──
        try:
            post_sprint_plan.run(sprint_list_id=list_id)
            log.info("sprint: posted sprint plan to Slack")
        except Exception as e:
            log.error("sprint: Slack post failed: %s", e)

        ctx["sprint_result"] = f"Sprint finalized: {tasks_moved} tasks, {total_sp} SP."
        if warnings:
            ctx["sprint_result"] += f" Warnings: {'; '.join(str(w) for w in warnings[:3])}"
        return ctx

    # ── Minimal crew — just confirms ──

    @agent
    def sprint_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["sprint_agent"]),
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
