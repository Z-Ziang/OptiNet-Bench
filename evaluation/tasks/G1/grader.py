"""G1: Graph representation conversion. Delegate scientific rules without duplicating them."""
from optira.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "G1":
        raise ValueError("Wrong task routed to G1")
    return grade_legacy(record, final_answer)
