from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import fetch_huddle_notes
from shared.tools.vault import vault_list
from shared.config.context import interpolate_config


@CrewBase
class HuddleNotesCrew:
    """Fetches Slack huddle notes and produces structured vault summaries."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def inject_context(self, inputs):
        import json, logging
        from shared.config.context import crew_context
        log = logging.getLogger(__name__)

        print("[HUDDLE_DEBUG] before_kickoff ENTERED — commit c011221+", flush=True)

        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── Pre-fetch huddle notes — 7 day window to catch missed runs ──
        try:
            print("[HUDDLE_DEBUG] calling fetch_huddle_notes with lookback_hours=168", flush=True)
            result = fetch_huddle_notes.run(channel="#carespace-team", lookback_hours=168)
            print(f"[HUDDLE_DEBUG] raw result type={type(result).__name__} len={len(str(result))}", flush=True)
            print(f"[HUDDLE_DEBUG] raw result preview: {str(result)[:500]}", flush=True)
            huddle_data = json.loads(result) if isinstance(result, str) else result
            print(f"[HUDDLE_DEBUG] huddles_found={huddle_data.get('huddles_found', 'MISSING')}", flush=True)
            log.info("huddle: fetched %d huddles from last 7 days", huddle_data.get("huddles_found", 0))
            for h in huddle_data.get("huddles", []):
                log.info("huddle: found — date=%s source=%s", h.get("date", "?"), h.get("source", "?"))
        except Exception as e:
            print(f"[HUDDLE_DEBUG] EXCEPTION: {type(e).__name__}: {e}", flush=True)
            huddle_data = {"huddles_found": 0, "error": str(e)}
            log.warning("huddle: fetch failed: %s", e)

        # Guard: no huddles found or fetch failed — skip the LLM entirely
        if huddle_data.get("huddles_found", 0) == 0:
            reason = huddle_data.get("error", "No huddles in lookback period")
            log.info("huddle: nothing to process — %s", reason)
            ctx["huddle_data"] = json.dumps({"huddles_found": 0, "status": "skipped", "reason": reason})
            return ctx

        # Skip vault dedup for now — vault_list was hanging on CrewHub.
        # Vault write_vault will just overwrite if duplicate.
        print(f"[HUDDLE_DEBUG] passing {huddle_data.get('huddles_found')} huddles straight to agent (no dedup)", flush=True)
        ctx["huddle_data"] = json.dumps(huddle_data, indent=2)
        print(f"[HUDDLE_DEBUG] ctx huddle_data set, length={len(ctx['huddle_data'])}", flush=True)
        return ctx

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
