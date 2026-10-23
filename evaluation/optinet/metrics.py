"""Uniform decision categories and explicitly denominated benchmark metrics."""
from __future__ import annotations

TASKS_OVERALL = ("G1", "G2", "G3", "X1", "O1-S", "O1-C", "X2", "X3")
SCORED_CATEGORIES = {"CORRECT", "SUBOPTIMAL", "INFEASIBLE", "MISSING"}


def normalize_result(result):
    result = dict(result)
    category = result.get("category", "SCORING_ERROR")
    if category not in SCORED_CATEGORIES and category not in {"SCORING_ERROR", "SERVICE_ERROR"}:
        result["category"] = "SCORING_ERROR"
        result.setdefault("reason", category)
        category = "SCORING_ERROR"
    if category == "MISSING" and result.get("reason") == "INCORRECT_REJECT_NO_ALLOCATION":
        result["category"] = category = "INFEASIBLE"
    scored = category in SCORED_CATEGORIES
    result["scoring_status"] = "SCORED" if scored else "ERROR"
    result["format_compliant"] = (category != "MISSING") if scored else None
    result["decision_success"] = (category in ("CORRECT", "SUBOPTIMAL")) if scored else None
    result["optimal_solution"] = (category == "CORRECT" and not result.get("correct_reject", False)) if scored else None
    return result


def task_metrics(count, task):
    scored = count["scored_cases"]
    fmt = count["format_compliant_responses"]
    pct = lambda n, d: 100.0 * n / d if d else None
    success = pct(count["successful_decisions"], fmt)
    return {
        "corr_percent": pct(count["correct_answers"], scored) if task in ("G1", "G2", "G3") else None,
        "opt_percent": pct(count["optimal_solutions"], fmt) if task not in ("G1", "G2", "G3") else None,
        "succ_percent": success if task not in ("G1", "G2", "G3") else None,
        "decision_failure_percent": 100.0 - success if success is not None and task not in ("G1", "G2", "G3") else None,
        "format_compliant_percent": pct(fmt, scored),
        "e2e_success_percent": pct(count["successful_decisions"], scored),
        "scoring_complete": scored == count["total_samples"],
    }


def overall_metrics(rows):
    models = sorted({r["model"] for r in rows})
    overall = []
    for model in models:
        by_task = {r["task"]: r for r in rows if r["model"] == model}
        missing = [t for t in TASKS_OVERALL if t not in by_task or by_task[t]["e2e_success_percent"] is None]
        unresolved = [t for t in TASKS_OVERALL if t in by_task and not by_task[t]["scoring_complete"]]
        complete = not missing
        overall.append({"model": model, "overall_e2e_percent":
                        sum(by_task[t]["e2e_success_percent"] for t in TASKS_OVERALL) / 8 if complete else None,
                        "missing_tasks": missing, "unresolved_tasks": unresolved})
    return overall
