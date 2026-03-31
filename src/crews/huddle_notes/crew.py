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

        # ── Deduplicate against vault — only keep new huddles ──
        existing_dates = set()
        try:
            print("[HUDDLE_DEBUG] calling vault_list for huddles dir", flush=True)
            vault_files = vault_list.run(directory="huddles")
            print(f"[HUDDLE_DEBUG] vault_list raw: {str(vault_files)[:500]}", flush=True)
            vault_entries = json.loads(vault_files) if isinstance(vault_files, str) else vault_files
            import re
            for entry in vault_entries if isinstance(vault_entries, list) else []:
                name = entry.get("name", "") if isinstance(entry, dict) else str(entry)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
                if date_match:
                    existing_dates.add(date_match.group(1))
            print(f"[HUDDLE_DEBUG] existing vault dates ({len(existing_dates)}): {sorted(existing_dates)[-5:]}", flush=True)
        except Exception as e:
            print(f"[HUDDLE_DEBUG] vault_list EXCEPTION: {type(e).__name__}: {e}", flush=True)

        all_huddles = huddle_data.get("huddles", [])
        huddle_dates = [h.get("date", "")[:10] for h in all_huddles]
        print(f"[HUDDLE_DEBUG] huddle dates from Slack: {huddle_dates}", flush=True)

        if existing_dates:
            new_huddles = [
                h for h in all_huddles
                if h.get("date", "")[:10] not in existing_dates
            ]
            print(f"[HUDDLE_DEBUG] after dedup: {len(new_huddles)} new out of {len(all_huddles)}", flush=True)

            if not new_huddles:
                print("[HUDDLE_DEBUG] ALL FILTERED — returning skipped", flush=True)
                ctx["huddle_data"] = json.dumps({"huddles_found": 0, "status": "skipped", "reason": "All huddles already processed"})
                return ctx

            huddle_data = {"huddles_found": len(new_huddles), "huddles": new_huddles}

        final_json = json.dumps(huddle_data, indent=2)
        print(f"[HUDDLE_DEBUG] FINAL huddle_data length={len(final_json)} huddles_found={huddle_data.get('huddles_found')}", flush=True)
        ctx["huddle_data"] = final_json
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
