"""Q1 presentation adapter. The source evaluate() and correctness predicate are preserved.

Physics families use separate Python package namespaces, including their frozen WUFR
dependencies. They never overwrite the eight-task ``src`` package in sys.modules.
"""
from __future__ import annotations

import importlib
import math
import re
import sys
import types
from pathlib import Path

from .data import checked_file, read_json, sha256
import json

SECONDARY_ABS_TOL = 1e-10
FAMILIES = ("LEGACY_V0.2", "MIXED_V0.3")


def engine(family: str):
    if family not in FAMILIES:
        raise ValueError(f"Unknown physical model family: {family}")
    name = "_optira_q1_" + family.replace(".", "_")
    if name not in sys.modules:
        vendor = Path(__file__).parent / "_vendor/q1"
        for relative, expected in read_json(vendor / "FILE_SHA256.json").items():
            path = (vendor / relative).resolve()
            if not path.is_relative_to(vendor.resolve()) or sha256(path.read_bytes()) != expected:
                raise ValueError("Frozen Q1 scientific runtime hash mismatch: " + relative)
        package = types.ModuleType(name)
        package.__path__ = [str(Path(__file__).parent / "_vendor/q1" / family / "src")]
        sys.modules[name] = package
    return importlib.import_module(name + ".q1")


def classify(row: dict, answer: str, allow_single_fence: bool) -> dict:
    text = answer
    removed = False
    if allow_single_fence:
        match = re.fullmatch(r"```(?:json)?\s*\r?\n(.*?)\r?\n```", text.strip(), re.I | re.S)
        if match:
            text, removed = match.group(1), True
    root = json.loads(checked_file(row, "private/root_case.json"))
    proof = json.loads(checked_file(row, "private/oracle_proof.json"))
    truth = json.loads(checked_file(row, "private/reference_output.json"))
    evaluator = engine(row["model_version"])
    if root["physics"]["model_id"] != evaluator.MODEL_ID:
        raise ValueError("Case physics model does not match its cataloged engine")
    feasible = truth["decision"] == "ACCEPT"
    base = {"task": "Q1", "grading_version": "Q1_SOURCE_STRICT_PREDICATE_V1",
            "model_version": row["model_version"], "truth_feasible": feasible,
            "single_outer_fence_removed": removed, "correct_reject": False,
            "source_interface_status": row.get("interface_status", "UNKNOWN"),
            "strict_bilevel_correct": False}
    try:
        # Preserve the original JSON parser; do not silently tighten source schemas.
        prediction = json.loads(text)
    except (ValueError, TypeError):
        return {**base, "category": "MISSING", "reason": "INVALID_JSON", "formal_eligible": True}
    validation = evaluator.evaluate(root, prediction)
    valid = bool(validation.get("valid"))
    decision_match = isinstance(prediction, dict) and prediction.get("decision") == truth["decision"]
    correct = False
    if valid and decision_match:
        if truth["decision"] == "REJECT":
            correct = proof["status"] == "INFEASIBLE_CERTIFIED"
        else:
            correct = validation["primary"] == proof["primary"] and math.isclose(
                float(validation["secondary"]), float(proof["secondary"]), rel_tol=0, abs_tol=SECONDARY_ABS_TOL)
    result = {**base, "validator": validation, "submission_valid": valid,
              "decision_correct": bool(decision_match), "strict_bilevel_correct": bool(correct),
              "certified_primary": proof.get("primary"), "certified_secondary": proof.get("secondary"),
              "submission_primary": validation.get("primary"), "submission_secondary": validation.get("secondary"),
              "formal_eligible": True}
    if correct:
        return {**result, "category": "CORRECT", "correct_reject": not feasible,
                "result_kind": "ALLOCATION" if feasible else "CERTIFIED_REJECT"}
    if isinstance(prediction, dict) and prediction.get("decision") == "REJECT" and feasible:
        return {**result, "category": "MISSING", "reason": "INCORRECT_REJECT_NO_ALLOCATION"}
    if not valid or not feasible:
        return {**result, "category": "INFEASIBLE"}
    primary_gap = validation["primary"] - proof["primary"]
    secondary_gap = validation["secondary"] - proof["secondary"]
    result["metrics"] = {"primary_gap": primary_gap,
                         "secondary_gap": secondary_gap if primary_gap == 0 else None}
    if primary_gap < 0 or (primary_gap == 0 and secondary_gap < -SECONDARY_ABS_TOL):
        return {**result, "category": "REVIEW_ORACLE", "formal_eligible": False}
    return {**result, "category": "SUBOPTIMAL"}


def grade_q1(row: dict, answer: str) -> dict:
    def safe(relaxed: bool):
        try:
            return classify(row, answer, relaxed)
        except Exception as exc:
            return {"category": "SCORING_ERROR", "formal_eligible": False,
                    "reason": type(exc).__name__, "message": str(exc)}
    return {"strict": safe(False), "relaxed": safe(True), "scoring_adapter_version": "Q1_RENAME_ONLY_R1"}
