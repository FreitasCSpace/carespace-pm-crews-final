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
from datetime import date, datetime
from shared.tools.vault import vault_read, vault_write, vault_list

log = logging.getLogger(__name__)

# ── What each crew reads before running ──────────────────────────────────

CREW_READS: dict[str, list[str]] = {
    "intake": [],
    "daily_pulse": [
        "context/velocity.md",
    ],
    "triage": [
        "context/backlog-health.md",
    ],
    "sprint": [
        "context/velocity.md",
    ],
    "retrospective": [
        "context/velocity.md",
    ],
    "huddle_notes": [],
}

# Dynamic reads: crew → (vault_dir, how many recent files to read)
CREW_DYNAMIC_READS: dict[str, list[tuple[str, int]]] = {
    "daily_pulse": [("sprint/daily", 1)],
    "triage": [("backlog", 1), ("sprint/retros", 1)],
    "sprint": [("sprint/retros", 1)],
    "retrospective": [("sprint/plans", 1)],
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
    "intake": ("intake", "datetime"),
    "daily_pulse": ("daily_pulse", "date"),
    "triage": ("triage", "datetime"),
    "sprint": ("sprint_plan", "sprint"),
    "retrospective": ("sprint_retro", "sprint"),
    "huddle_notes": ("huddle_notes", "datetime"),
}

# crew_name → context file to overwrite with latest state
CREW_CONTEXT_WRITES: dict[str, str] = {
    "triage": "backlog-health.md",
    "retrospective": "velocity.md",
}


def _extract_output_text(result) -> str:
    """Extract ALL task outputs from a CrewAI result — not just the final task.

    CrewOutput.tasks_output contains every task's output. We combine them
    into a structured document so the vault file has useful context,
    not just "Confirmation of report posted to Slack."
    """
    sections = []

    # Try to get all task outputs (CrewOutput has tasks_output list)
    if hasattr(result, "tasks_output") and result.tasks_output:
        for i, task_output in enumerate(result.tasks_output, 1):
            task_desc = ""
            task_raw = ""
            if hasattr(task_output, "description"):
                # First 80 chars of description as section header
                task_desc = str(task_output.description or "")[:80].strip()
            if hasattr(task_output, "raw"):
                task_raw = str(task_output.raw or "")
            elif hasattr(task_output, "output"):
                task_raw = str(task_output.output or "")
            else:
                task_raw = str(task_output)

            # Skip empty or trivial confirmation outputs
            if task_raw.strip() and len(task_raw.strip()) > 20:
                header = task_desc if task_desc else f"Task {i}"
                sections.append(f"### {header}\n\n{task_raw}")

    if sections:
        return "\n\n---\n\n".join(sections)

    # Fallback: single raw output (for string results passed from Flow)
    if hasattr(result, "raw") and result.raw:
        raw = str(result.raw)
        if len(raw.strip()) > 20:
            return raw
    if hasattr(result, "output") and result.output:
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
    now = datetime.now()
    if pattern == "datetime":
        filename = f"{now.strftime('%Y-%m-%d-%H%M')}.md"
    elif pattern == "date":
        filename = f"{date.today().isoformat()}.md"
    elif pattern == "sprint" and sprint_number:
        filename = f"sprint-{sprint_number}.md"
    else:
        filename = f"{date.today().isoformat()}.md"

    # Build content with frontmatter
    timestamp = now.strftime("%Y-%m-%d %H:%M") if pattern == "datetime" else date.today().isoformat()
    frontmatter = _build_frontmatter(crew_name)
    content = f"{frontmatter}\n\n## {crew_name.replace('_', ' ').title()} — {timestamp}\n\n{output_text}"

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
