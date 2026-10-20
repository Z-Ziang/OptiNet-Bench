"""O1-C: Concurrent fixed-path spectrum assignment. Delegate scientific rules without duplicating them."""
from optira.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "O1-C":
        raise ValueError("Wrong task routed to O1-C")
    return grade_legacy(record, final_answer)
