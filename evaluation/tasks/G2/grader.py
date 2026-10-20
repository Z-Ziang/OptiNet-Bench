"""G2: Path validity classification. Delegate scientific rules without duplicating them."""
from optira.legacy import grade_legacy


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "G2":
        raise ValueError("Wrong task routed to G2")
    return grade_legacy(record, final_answer)
