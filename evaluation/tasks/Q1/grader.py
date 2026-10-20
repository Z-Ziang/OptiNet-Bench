"""Q1: QoT-aware multi-request single-step RMSA. Delegate scientific rules without duplicating them."""
from optinet.q1 import grade_q1


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "Q1":
        raise ValueError("Wrong task routed to Q1")
    return grade_q1(record, final_answer)
