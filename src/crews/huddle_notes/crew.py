from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from shared.tools import fetch_huddle_notes
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

        ctx = crew_context()
        ctx.update({k: v for k, v in (inputs or {}).items() if v})

        # ── Pre-fetch huddle notes (no LLM needed) ──
        try:
            result = fetch_huddle_notes.run(channel="#carespace-team", lookback_hours=24)
            huddle_data = json.loads(result) if isinstance(result, str) else result
            log.info("huddle: fetched %d huddles", huddle_data.get("huddles_found", 0))
        except Exception as e:
            huddle_data = {"huddles_found": 0, "error": str(e)}
            log.warning("huddle: fetch failed: %s", e)

        ctx["huddle_data"] = json.dumps(huddle_data, indent=2)
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
