from .crew import AssignmentCrewCrew


def run():
    AssignmentCrewCrew().crew().kickoff(inputs={
        "list_id": "",
    })


if __name__ == "__main__":
    run()
