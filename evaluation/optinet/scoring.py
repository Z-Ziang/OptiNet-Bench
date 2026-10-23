"""One interface for nine task folders; classification rules stay in source adapters."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from .data import TASKS
from .metrics import normalize_result
from .output_processing import prepare_relaxed_answer

_modules = {}


def score_answer(row: dict, answer: str) -> dict:
    task = row["task"]
    if task not in TASKS:
        raise ValueError(f"Unsupported task: {task}")
    if not isinstance(answer, str):
        raise TypeError("Answer must be the final visible response text")
    if task not in _modules:
        path = Path(__file__).resolve().parents[1] / "tasks" / task / "grader.py"
        spec = importlib.util.spec_from_file_location("_optinet_task_" + task.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _modules[task] = module
    processing = prepare_relaxed_answer(task, answer)
    grading = _modules[task].grade(row, answer)
    relaxed = grading["relaxed"]
    if processing["method"] == "json_extraction" and relaxed.get("category") != "SCORING_ERROR":
        # Candidate discovery never sees grader outcomes or reference answers.
        relaxed = _modules[task].grade(row, processing["text"])["strict"]
    elif processing["status"] == "ambiguous" and relaxed.get("category") != "SCORING_ERROR":
        relaxed = {**relaxed, "category": "MISSING", "reason": "AMBIGUOUS_JSON_CANDIDATES"}
    # Store extracted text only when extraction occurred; raw answers stay in logs.
    metadata = dict(processing)
    if processing["method"] != "json_extraction":
        metadata.pop("text")
    grading["relaxed"] = {**relaxed, "output_processing": metadata}
    for policy in ("strict", "relaxed"):
        grading[policy] = normalize_result(grading[policy])
    return grading
