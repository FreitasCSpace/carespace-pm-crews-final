from .crew import HuddleNotesCrewCrew


def run():
    HuddleNotesCrewCrew().crew().kickoff(inputs={
        "huddle_channel": "",
    })


if __name__ == "__main__":
    run()
