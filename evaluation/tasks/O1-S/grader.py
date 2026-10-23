"""O1-S: Single-request fixed-path spectrum assignment. Delegate scientific rules without duplicating them."""
from optinet.eight_tasks import grade_eight_tasks


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "O1-S":
        raise ValueError("Wrong task routed to O1-S")
    return grade_eight_tasks(record, final_answer)
