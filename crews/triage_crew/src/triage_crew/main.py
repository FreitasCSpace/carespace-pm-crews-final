#!/usr/bin/env python
from triage_crew.crew import TriageCrew


def run():
    TriageCrew().crew().kickoff(inputs={
        "sprint_list_id": "",  # populated by orchestrator from active sprint
    })


if __name__ == "__main__":
    run()
