from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import fetch_huddle_notes
from shared.tools.vault import vault_write
from shared.config.context import interpolate_config


@CrewBase
class HuddleNotesCrew:
    """Fetches Slack huddle notes and writes raw canvas content to vault — one file per day.

    100% Python — no LLM involved. before_kickoff fetches huddles,
    writes each one directly to vault, and the crew's single task
    just returns a confirmation.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        import json, logging, re
        from datetime import datetime
        from shared.config.context import crew_context
        log = logging.getLogger(__name__)

        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── 1. Fetch huddle notes — 7 day lookback ──
        try:
            result = fetch_huddle_notes.run(channel="#carespace-team", lookback_hours=168)
            huddle_data = json.loads(result) if isinstance(result, str) else result
            log.info("huddle: fetched %d huddles from last 7 days", huddle_data.get("huddles_found", 0))
        except Exception as e:
            huddle_data = {"huddles_found": 0, "error": str(e)}
            log.warning("huddle: fetch failed: %s", e)

        # Guard: nothing found
        if huddle_data.get("huddles_found", 0) == 0:
            reason = huddle_data.get("error", "No huddles in lookback period")
            log.info("huddle: nothing to process — %s", reason)
            ctx["huddle_result"] = f"No huddles found. {reason}"
            return ctx

        # ── 2. Write each huddle directly to vault — raw canvas content ──
        huddles = huddle_data.get("huddles", [])
        written = []
        skipped = []

        for h in huddles:
            canvas = h.get("canvas_content", "").strip()
            huddle_date = h.get("date", "")  # "2026-03-30 16:54"

            # Skip empty canvases (no real content)
            if not canvas or len(canvas) < 50:
                log.info("huddle: skipping %s — canvas too short (%d chars)", huddle_date, len(canvas))
                skipped.append(huddle_date)
                continue

            # Parse date for filename: "2026-03-30 16:54" → "2026-03-30-1654"
            try:
                dt = datetime.strptime(huddle_date, "%Y-%m-%d %H:%M")
                filename = dt.strftime("%Y-%m-%d-%H%M") + ".md"
                date_iso = dt.strftime("%Y-%m-%d")
            except Exception:
                filename = huddle_date.replace(" ", "-").replace(":", "") + ".md"
                date_iso = huddle_date[:10] if len(huddle_date) >= 10 else "unknown"

            # Build vault file — raw canvas content with frontmatter
            content = f"""---
date: {date_iso}
crew: huddle_notes
---

{canvas}
"""

            # Write to vault
            try:
                vault_write.run(crew="huddle_notes", content=content, filename=filename)
                log.info("huddle: wrote vault huddles/%s", filename)
                written.append(filename)
            except Exception as e:
                log.warning("huddle: vault write failed for %s: %s", filename, e)

        # ── 3. Summary for the crew output ──
        summary_parts = []
        if written:
            summary_parts.append(f"Wrote {len(written)} huddle(s) to vault: {', '.join(written)}")
        if skipped:
            summary_parts.append(f"Skipped {len(skipped)} huddle(s) with empty content")
        if not written and not skipped:
            summary_parts.append("No huddles to process")

        ctx["huddle_result"] = " | ".join(summary_parts)
        log.info("huddle: %s", ctx["huddle_result"])
        return ctx

    # ── Minimal crew — just returns confirmation ──

    @agent
    def huddle_agent(self) -> Agent:
        return Agent(
            config=interpolate_config(self.agents_config["huddle_agent"]),
            tools=[],
            verbose=True,
            allow_delegation=False,
            inject_date=True,
            function_calling_llm="gpt-4o-mini",
        )

    @task
    def fetch_and_summarize(self) -> Task:
        return Task(config=interpolate_config(self.tasks_config["fetch_and_summarize"]))

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
