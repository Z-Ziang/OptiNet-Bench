"""X3: Concurrent autonomous RSA. Delegate scientific rules without duplicating them."""
from optinet.eight_tasks import grade_eight_tasks


def grade(record: dict, final_answer: str) -> dict:
    """Score one final visible response using the pinned task adapter."""
    if record["task"] != "X3":
        raise ValueError("Wrong task routed to X3")
    return grade_eight_tasks(record, final_answer)
