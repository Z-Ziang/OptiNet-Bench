"""Call the unchanged eight-task adapters through their original path contract."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

VENDOR = Path(__file__).parent / "_vendor/eight_tasks"
_core = None


def grade_legacy(row: dict, answer: str) -> dict:
    global _core
    if _core is None:
        sys.path.insert(0, str(VENDOR))
        spec = importlib.util.spec_from_file_location("_optira_eight_task_core", VENDOR / "core.py")
        _core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_core)
    return _core.score_answer(row["dataset_root"], row, answer)
