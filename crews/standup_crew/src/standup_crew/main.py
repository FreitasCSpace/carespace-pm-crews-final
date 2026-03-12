from .crew import StandupCrewCrew


def run():
    StandupCrewCrew().crew().kickoff(inputs={
        "sprint_list_id": "",
    })


if __name__ == "__main__":
    run()
