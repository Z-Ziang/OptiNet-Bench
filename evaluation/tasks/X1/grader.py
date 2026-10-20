"""X1: Graph shortest path. Delegate scientific rules without duplicating them."""
from optira.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "X1":
        raise ValueError("Wrong task routed to X1")
    return grade_legacy(record, final_answer)
