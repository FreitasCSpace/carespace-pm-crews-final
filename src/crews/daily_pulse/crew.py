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

        # ── Pre-gather AND pre-format sprint digest (no LLM needed) ──

        # 1. Get active sprint
        try:
            sprint_result = create_sprint_list.run()
            sprint = json.loads(sprint_result) if isinstance(sprint_result, str) else sprint_result
            list_id = sprint.get("list_id", "")
        except Exception as e:
            log.warning("daily_pulse: sprint lookup failed: %s", e)
            sprint = {"error": str(e)}
            list_id = ""

        # 2. Get sprint tasks
        tasks = []
        log.info("daily_pulse: sprint=%s list_id=%s", sprint.get("sprint_name", "?"), list_id)
        if list_id:
            try:
                tasks_result = get_tasks_by_list.run(
                    list_id=list_id, status="", include_closed=True,
                )
                tasks = json.loads(tasks_result) if isinstance(tasks_result, str) else tasks_result
                if isinstance(tasks, dict) and "error" in tasks:
                    tasks = []
                log.info("daily_pulse: fetched %d tasks from list %s: %s",
                         len(tasks), list_id,
                         [t.get("name", "?")[:50] for t in tasks[:5]])
            except Exception as e:
                log.warning("daily_pulse: tasks fetch failed: %s", e)

        # 3. Check stale sprint tasks
        stale_tasks = []
        non_done_ids = [t["id"] for t in tasks if t.get("status") not in ("complete", "done")]
        if non_done_ids:
            try:
                stale_result = check_stale_sprint_tasks.run(
                    task_ids_json=json.dumps(non_done_ids), days=3,
                )
                stale_tasks = json.loads(stale_result) if isinstance(stale_result, str) else stale_result
            except Exception:
                pass
        stale_ids = {s.get("task_id") for s in stale_tasks}

        # 4. Get open PRs
        open_prs = []
        try:
            prs_result = get_prs.run(repo="")
            open_prs = json.loads(prs_result) if isinstance(prs_result, str) else prs_result
        except Exception:
            pass

        # ── Build formatted digest sections ──
        timing = sprint.get("timing", {})
        sprint_name = sprint.get("sprint_name", "Unknown Sprint")
        timing_display = timing.get("timing_display", "")

        # Classify tasks by status
        done, in_progress, blocked, pending = [], [], [], []
        total_sp, done_sp = 0, 0
        for t in tasks:
            status = (t.get("status") or "").lower()
            sp = t.get("points") or 0
            total_sp += sp
            assignees = [a.get("username", "?") for a in t.get("assignees", [])]
            assignee = assignees[0] if assignees else "unassigned"
            url = t.get("url", "")
            # Clean name: drop [TYPE] prefix
            name = t.get("name", "")
            if name.startswith("[") and "]" in name:
                name = name[name.index("]") + 1:].strip()
            line = f"<{url}|{name}>" if url else name
            line += f" — @{assignee} · {sp} SP"

            if status in ("complete", "done"):
                done.append(line)
                done_sp += sp
            elif status == "in progress":
                in_progress.append(line)
            elif status == "blocked":
                blocked.append(line)
            else:
                pending.append(line)

        pct = round(done_sp / total_sp * 100, 1) if total_sp > 0 else 0

        # Sprint status
        if timing.get("sprint_started"):
            elapsed = timing.get("elapsed_days", 0)
            total_days = timing.get("total_days", 14)
            time_pct = elapsed / total_days if total_days > 0 else 0
            done_pct = done_sp / total_sp if total_sp > 0 else 0
            if done_pct >= time_pct - 0.05:
                health = "🟢 On Track"
            elif done_pct >= time_pct - 0.15:
                health = "🟡 At Risk"
            else:
                health = "🔴 Behind"
        else:
            health = "🟢 Not yet started"

        # Executive summary
        exec_lines = [
            f"• {sprint_name} — {timing_display}",
            f"• Progress: {pct}% complete ({done_sp}/{total_sp} SP delivered)",
            f"• Status: {health}",
        ]
        issues_count = len(blocked) + len([t for t in tasks if t["id"] in stale_ids])
        if issues_count > 0:
            exec_lines.append(f"• {issues_count} task(s) need attention")
        ctx["digest_executive_summary"] = "\n".join(exec_lines)

        ctx["digest_done"] = "\n".join(f"• {l}" for l in done) if done else ""
        ctx["digest_in_progress"] = "\n".join(f"• {l}" for l in in_progress) if in_progress else ""
        ctx["digest_blocked"] = "\n".join(f"• {l}" for l in blocked) if blocked else ""
        ctx["digest_pending"] = "\n".join(f"• {l}" for l in pending) if pending else ""

        # Task health — each problematic task once with all issues
        health_lines = []
        for t in tasks:
            status = (t.get("status") or "").lower()
            if status in ("complete", "done"):
                continue
            issues = []
            tid = t["id"]
            sp = t.get("points") or 0
            assignees = [a.get("username", "?") for a in t.get("assignees", [])]
            assignee = assignees[0] if assignees else "unassigned"
            url = t.get("url", "")
            name = t.get("name", "")
            if name.startswith("[") and "]" in name:
                name = name[name.index("]") + 1:].strip()

            if tid in stale_ids:
                s = next((x for x in stale_tasks if x.get("task_id") == tid), {})
                days = s.get("days_silent", "?")
                issues.append(f"No comments for {days}d")
            if not assignees:
                issues.append("Unassigned — needs owner")
            if status == "in progress":
                # Check PR coverage
                has_pr = any(
                    name.lower()[:30] in (pr.get("title", "") + pr.get("branch", "")).lower()
                    for pr in open_prs if isinstance(pr, dict) and "title" in pr
                )
                if not has_pr:
                    issues.append("No PR opened (in progress)")
            if status == "blocked":
                issues.append("Blocked")
            if sp >= 8 and timing.get("sprint_started"):
                issues.append(f"High SP ({sp}), still {status}")

            if issues:
                header = f"<{url}|{name}>" if url else name
                header += f" — @{assignee} · {sp} SP · {status}"
                health_lines.append(f"• {header}")
                for issue in issues:
                    health_lines.append(f"  - {issue}")

        ctx["digest_attention"] = "\n".join(health_lines) if health_lines else "All tasks healthy ✅"

        # Meeting mode
        if health_lines:
            ctx["digest_meeting_mode"] = f"🔴 STANDUP MODE: {len([l for l in health_lines if l.startswith('•')])} task(s) need attention. 15-min focused session."
        else:
            ctx["digest_meeting_mode"] = "🟢 OPEN SLOT: Sprint healthy. Available for strategic discussion."

        log.info("daily_pulse: digest pre-built — %d tasks, %d health issues", len(tasks), len(health_lines))
        log.info("daily_pulse: exec_summary=%s", ctx["digest_executive_summary"][:200])
        log.info("daily_pulse: done=%s", ctx.get("digest_done", "")[:200])
        log.info("daily_pulse: in_progress=%s", ctx.get("digest_in_progress", "")[:200])
        log.info("daily_pulse: pending=%s", ctx.get("digest_pending", "")[:200])
        log.info("daily_pulse: attention=%s", ctx.get("digest_attention", "")[:200])
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
