from .crew import SprintPlanningCrewCrew


def run():
    SprintPlanningCrewCrew().crew().kickoff(inputs={
        "sprint_number": "",
        "start_date": "",
        "end_date": "",
        "end_date_iso": "",
        "target_sp": 48,
        "human_priorities": "",
    })


if __name__ == "__main__":
    run()
