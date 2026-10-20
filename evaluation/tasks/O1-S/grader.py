"""O1-S: Single-request fixed-path spectrum assignment. Delegate scientific rules without duplicating them."""
from optinet.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "O1-S":
        raise ValueError("Wrong task routed to O1-S")
    return grade_legacy(record, final_answer)
