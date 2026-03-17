#!/usr/bin/env python
from daily_pulse_crew.crew import DailyPulseCrew


def run():
    DailyPulseCrew().crew().kickoff(inputs={
        "sprint_list_id": "",  # populated by orchestrator from active sprint
    })


if __name__ == "__main__":
    run()
