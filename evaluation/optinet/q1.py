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
FAMILIES = ("PURE_200G", "MIXED_RATES")


def engine(family: str):
    if family not in FAMILIES:
        raise ValueError(f"Unknown physical model family: {family}")
    name = "_optinet_q1_" + family.replace(".", "_")
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



def _output_structure_error(prediction):
    """Check response structure; allocation coverage and paths remain constraints."""
    if not isinstance(prediction, dict):
        return "OUTPUT_NOT_OBJECT"
    if prediction.get("decision") not in ("ACCEPT", "REJECT"):
        return "MISSING_OR_INVALID_DECISION"
    if "allocations" not in prediction or not isinstance(prediction["allocations"], list):
        return "MISSING_OR_INVALID_ALLOCATIONS"
    if prediction["decision"] == "REJECT":
        return None
    required_types = {
        "request_id": str,
        "path_node_ids": list,
        "path_link_ids": list,
        "transponder_profile_id": str,
        "slot_start": int,
    }
    for allocation in prediction["allocations"]:
        if not isinstance(allocation, dict):
            return "ALLOCATION_NOT_OBJECT"
        for field, expected_type in required_types.items():
            if field not in allocation:
                return "MISSING_ALLOCATION_FIELD:" + field
            value = allocation[field]
            if not isinstance(value, expected_type) or (
                expected_type is int and isinstance(value, bool)
            ):
                return "INVALID_ALLOCATION_FIELD_TYPE:" + field
        for field in ("path_node_ids", "path_link_ids"):
            if any(isinstance(value, (dict, list)) for value in allocation[field]):
                return "INVALID_PATH_IDENTIFIER_CONTAINER:" + field
    return None


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
            "strict_bilevel_correct": False}
    try:
        # Parse the final response before checking its required structure.
        prediction = json.loads(text)
    except (ValueError, TypeError):
        return {**base, "category": "MISSING", "reason": "INVALID_JSON"}
    structure_error = _output_structure_error(prediction)
    if structure_error:
        return {**base, "category": "MISSING", "reason": "OUTPUT_SCHEMA_ERROR",
                "detail": structure_error}
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
              "scoring_status": "SCORED"}
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
        return {**result, "category": "SCORING_ERROR", "reason": "REFERENCE_OPTIMUM_CONFLICT"}
    return {**result, "category": "SUBOPTIMAL"}


def grade_q1(row: dict, answer: str) -> dict:
    def safe(relaxed: bool):
        try:
            return classify(row, answer, relaxed)
        except Exception as exc:
            return {"category": "SCORING_ERROR",
                    "reason": type(exc).__name__, "message": str(exc)}
    return {"strict": safe(False), "relaxed": safe(True), "scoring_adapter_version": "Q1_UNIFIED_DECISION_POLICY_V1"}
