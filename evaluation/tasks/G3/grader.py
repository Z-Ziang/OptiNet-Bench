"""G3: Two shortest paths and shared directed links. Delegate scientific rules without duplicating them."""
from optira.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "G3":
        raise ValueError("Wrong task routed to G3")
    return grade_legacy(record, final_answer)
