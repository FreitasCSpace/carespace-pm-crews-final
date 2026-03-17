#!/usr/bin/env python
from sprint_crew.crew import SprintCrew


def run():
    SprintCrew().crew().kickoff(inputs={
        "sprint_number": 1,
        "start_date": "Mar 16",
        "end_date": "Mar 30",
        "human_priorities": "",
        "target_sp": 48,
    })


if __name__ == "__main__":
    run()
