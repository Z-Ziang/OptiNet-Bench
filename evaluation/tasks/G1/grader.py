"""G1: Graph representation conversion. Delegate scientific rules without duplicating them."""
from optinet.eight_tasks import grade_eight_tasks


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "G1":
        raise ValueError("Wrong task routed to G1")
    return grade_eight_tasks(record, final_answer)
