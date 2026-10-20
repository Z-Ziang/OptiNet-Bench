"""One interface for nine task folders; classification rules stay in source adapters."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from .data import TASKS

_modules = {}


def score_answer(row: dict, answer: str) -> dict:
    task = row["task"]
    if task not in TASKS:
        raise ValueError(f"Unsupported task: {task}")
    if not isinstance(answer, str):
        raise TypeError("Answer must be the final visible response text")
    if task not in _modules:
        path = Path(__file__).resolve().parents[1] / "tasks" / task / "grader.py"
        spec = importlib.util.spec_from_file_location("_optira_task_" + task.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _modules[task] = module
    return _modules[task].grade(row, answer)
