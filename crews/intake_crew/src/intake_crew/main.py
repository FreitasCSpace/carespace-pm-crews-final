from .crew import IntakeCrewCrew


def run():
    IntakeCrewCrew().crew().kickoff(inputs={
        "repo": "",
        "issue_number": "",
    })


if __name__ == "__main__":
    run()
