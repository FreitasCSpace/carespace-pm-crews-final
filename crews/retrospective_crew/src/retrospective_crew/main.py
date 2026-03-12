from .crew import RetrospectiveCrewCrew


def run():
    RetrospectiveCrewCrew().crew().kickoff(inputs={
        "sprint_number": "",
        "sprint_list_id": "",
        "sprint_name": "",
    })


if __name__ == "__main__":
    run()
