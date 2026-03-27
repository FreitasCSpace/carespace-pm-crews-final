"""
shared/vault_hooks.py
Vault read/write hooks that run at code level — not LLM-optional.

before_kickoff: reads vault context files and injects them into crew inputs.
after_kickoff:  writes the crew's output to the vault as a dated .md file.

Usage in crew.py:
    from shared.vault_hooks import vault_before_kickoff, vault_after_kickoff

    @before_kickoff
    def inject_context(self, inputs):
        ...
        return vault_before_kickoff("daily_pulse", ctx)

    # Call after crew.kickoff() returns:
    vault_after_kickoff("daily_pulse", result)
"""

import json
import logging
from datetime import date
from shared.tools.vault import vault_read, vault_write, vault_list

log = logging.getLogger(__name__)

# ── What each crew reads before running ──────────────────────────────────

CREW_READS: dict[str, list[str]] = {
    "compliance": [
        "context/compliance-trend.md",
    ],
    "intake": [
        # Intake doesn't need prior context — it scans GitHub fresh
    ],
    "daily_pulse": [
        "context/velocity.md",
        # Yesterday's pulse is dynamic — handled in code below
    ],
    "sla": [
        # Previous SLA report is dynamic — handled in code below
    ],
    "triage": [
        "context/backlog-health.md",
        # Latest retro is dynamic — handled in code below
    ],
    "sprint": [
        "context/velocity.md",
        # Latest retro is dynamic — handled in code below
    ],
    "retrospective": [
        "context/velocity.md",
        # Sprint plan is dynamic — handled in code below
    ],
    "exec_report": [
        "context/velocity.md",
        "context/backlog-health.md",
        "context/compliance-trend.md",
    ],
    "huddle_notes": [
        # Previous huddle is dynamic — handled in code below
    ],
}

# Dynamic reads: crew → (vault_dir, how many recent files to read)
CREW_DYNAMIC_READS: dict[str, list[tuple[str, int]]] = {
    "daily_pulse": [("sprints/daily", 1)],
    "sla": [("sla", 1)],
    "triage": [("triage", 1), ("sprints/retros", 1)],
    "sprint": [("sprints/retros", 1)],
    "retrospective": [("sprints/plans", 1)],
    "exec_report": [
        ("sprints/daily", 1),
        ("sla", 1),
        ("sprints/retros", 1),
        ("compliance", 1),
    ],
    "huddle_notes": [("huddles", 1)],
}


def _read_file(path: str) -> str | None:
    """Read a vault file, return content or None."""
    try:
        result = vault_read.run(path)
        if isinstance(result, str) and not result.startswith('{"error'):
            return result
    except Exception as e:
        log.debug("vault read %s failed: %s", path, e)
    return None


def _read_latest_from_dir(directory: str) -> str | None:
    """List a vault directory, read the most recent file."""
    try:
        listing = vault_list.run(directory)
        files = json.loads(listing) if isinstance(listing, str) else listing
        if isinstance(files, list) and files:
            # Files are sorted by name — last one is newest (YYYY-MM-DD or sprint-N)
            latest = files[-1]
            return _read_file(latest["path"])
    except Exception as e:
        log.debug("vault list %s failed: %s", directory, e)
    return None


def vault_before_kickoff(crew_name: str, inputs: dict) -> dict:
    """
    Read vault context and inject it into crew inputs.
    Call this at the END of your @before_kickoff method.
    Returns the enriched inputs dict.
    """
    vault_context = {}

    # Static reads (known paths)
    for path in CREW_READS.get(crew_name, []):
        content = _read_file(path)
        if content:
            # Key = filename without extension: "velocity.md" → "vault_velocity"
            key = "vault_" + path.split("/")[-1].replace(".md", "").replace("-", "_")
            vault_context[key] = content

    # Dynamic reads (latest file from a directory)
    for directory, count in CREW_DYNAMIC_READS.get(crew_name, []):
        content = _read_latest_from_dir(directory)
        if content:
            # Key = directory with slashes replaced: "sprints/daily" → "vault_sprints_daily"
            key = "vault_" + directory.replace("/", "_")
            vault_context[key] = content

    if vault_context:
        log.info("vault: %s loaded %d context files", crew_name, len(vault_context))

    inputs["vault_context"] = json.dumps(vault_context, indent=2) if vault_context else "{}"
    return inputs


# ── What each crew writes after running ──────────────────────────────────

# crew_name → (vault_crew_key, filename_pattern)
# "date" = YYYY-MM-DD.md, "sprint" = needs sprint number (passed in output)
CREW_WRITES: dict[str, tuple[str, str]] = {
    "compliance": ("compliance", "date"),
    "intake": ("intake", "date"),
    "daily_pulse": ("daily_pulse", "date"),
    "sla": ("sla", "date"),
    "triage": ("triage", "date"),
    "sprint": ("sprint_plan", "sprint"),
    "retrospective": ("sprint_retro", "sprint"),
    "exec_report": ("exec_report", "date"),
    "huddle_notes": ("huddle_notes", "date"),
}

# crew_name → context file to overwrite with latest state
CREW_CONTEXT_WRITES: dict[str, str] = {
    "compliance": "compliance-trend.md",
    "triage": "backlog-health.md",
    "retrospective": "velocity.md",
}


def _extract_output_text(result) -> str:
    """Extract text from CrewAI result object."""
    if hasattr(result, "raw"):
        return str(result.raw)
    if hasattr(result, "output"):
        return str(result.output)
    return str(result)


def _build_frontmatter(crew_name: str, extra: dict = None) -> str:
    """Build YAML frontmatter for a vault file."""
    today = date.today().isoformat()
    lines = [
        "---",
        f"date: {today}",
        f"crew: {crew_name}",
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def vault_after_kickoff(crew_name: str, result, sprint_number: int = None):
    """
    Write crew output to the vault. Call this after crew.kickoff() returns.
    For sprint-scoped crews, pass sprint_number.
    """
    write_config = CREW_WRITES.get(crew_name)
    if not write_config:
        return

    vault_key, pattern = write_config
    output_text = _extract_output_text(result)

    # Determine filename
    if pattern == "date":
        filename = f"{date.today().isoformat()}.md"
    elif pattern == "sprint" and sprint_number:
        filename = f"sprint-{sprint_number}.md"
    else:
        filename = f"{date.today().isoformat()}.md"

    # Build content with frontmatter
    frontmatter = _build_frontmatter(crew_name)
    content = f"{frontmatter}\n\n## {crew_name.replace('_', ' ').title()} — {date.today().isoformat()}\n\n{output_text}"

    # Write crew-specific file
    try:
        vault_write.run(crew=vault_key, content=content, filename=filename)
        log.info("vault: %s wrote %s/%s", crew_name, vault_key, filename)
    except Exception as e:
        log.warning("vault write failed for %s: %s", crew_name, e)

    # Write context file if this crew maintains one
    context_file = CREW_CONTEXT_WRITES.get(crew_name)
    if context_file:
        context_frontmatter = _build_frontmatter(crew_name, {"type": "context"})
        context_content = f"{context_frontmatter}\n\n{output_text}"
        try:
            vault_write.run(crew="context", content=context_content, filename=context_file)
            log.info("vault: %s updated context/%s", crew_name, context_file)
        except Exception as e:
            log.warning("vault context write failed for %s: %s", crew_name, e)
