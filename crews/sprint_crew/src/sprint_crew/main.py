#!/usr/bin/env python
"""Sprint crew entry point — auto-detects sprint number and dates.

Can be run standalone or via orchestrator. Handles cold-start (first sprint
ever) and ongoing sprints (detects last sprint number from Sprints folder).
"""
from datetime import date, timedelta
from sprint_crew.crew import SprintCrew


def _detect_sprint_info() -> dict:
    """Auto-detect sprint number and dates from existing Sprints folder."""
    sprint_number = 1
    try:
        from shared.config.context import SPRINT_FOLDER_ID
        from shared.tools.clickup_helpers import _clickup_api
        data = _clickup_api(f"folder/{SPRINT_FOLDER_ID}/list")
        lists = data.get("lists", [])
        if lists:
            # Extract highest sprint number from existing list names
            for lst in lists:
                name = lst.get("name", "")
                # Parse "Sprint N — ..." or "Sprint N -- ..."
                for sep in ["—", "--"]:
                    if sep in name:
                        prefix = name.split(sep)[0].strip()
                        parts = prefix.split()
                        for p in parts:
                            if p.isdigit():
                                sprint_number = max(sprint_number, int(p) + 1)
    except Exception:
        pass  # cold start — use defaults

    # Sprint dates: starts today (or next Monday), runs 2 weeks
    today = date.today()
    # Align to Monday if not already Monday
    days_until_monday = (7 - today.weekday()) % 7
    start = today if days_until_monday == 0 else today + timedelta(days=days_until_monday)
    end = start + timedelta(days=13)  # 2-week sprint

    return {
        "sprint_number": sprint_number,
        "start_date": start.strftime("%b %d"),
        "end_date": end.strftime("%b %d"),
        "end_date_iso": end.isoformat(),
        "human_priorities": "",
        "target_sp": 48,
    }


def run():
    inputs = _detect_sprint_info()
    print(f"  Sprint {inputs['sprint_number']}: {inputs['start_date']} to {inputs['end_date']}")
    SprintCrew().crew().kickoff(inputs=inputs)


if __name__ == "__main__":
    run()
