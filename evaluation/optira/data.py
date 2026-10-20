"""Portable catalog access. Only public_messages() constructs model-visible input."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

TASKS = ("G1", "G2", "G3", "X1", "O1-S", "O1-C", "X2", "X3", "Q1")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inside(root: str | Path, relative: str) -> Path:
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Path escapes dataset: {relative}")
    return target


def inventory(roots: list[str], wanted_ids: set[str] | None = None) -> Iterator[dict]:
    seen = set()
    for location in roots:
        root = Path(location).resolve()
        if (root / "_meta/catalog/case_index.jsonl").is_file():
            if root.name != "dataset":
                raise ValueError("Keep the single-folder dataset directory named 'dataset'")
            catalog = root / "_meta/catalog/case_index.jsonl"
            logical_root = root.parent
        elif (root / "dataset/_meta/catalog/case_index.jsonl").is_file():
            catalog = root / "dataset/_meta/catalog/case_index.jsonl"
            logical_root = root
        else:
            catalog = root / "catalog/case_index.jsonl"
            logical_root = root
        with catalog.open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                if wanted_ids is not None and row.get("case_uid") not in wanted_ids:
                    continue
                if row["task"] not in TASKS:
                    raise ValueError(f"Unsupported task: {row['task']}")
                allowed = [logical_root / "dataset"]
                if row["task"] == "Q1":
                    allowed.append(logical_root / "cases")  # compatible with renamed engineering release
                if not any(inside(logical_root, row["case_dir"]).is_relative_to(folder) for folder in allowed):
                    raise ValueError("Only cataloged default Cases are allowed")
                if row["case_uid"] in seen:
                    raise ValueError("Duplicate Case UID across datasets; do not double count")
                seen.add(row["case_uid"])
                yield {**row, "dataset_root": str(logical_root)}


def checked_file(row: dict, relative: str) -> bytes:
    directory = inside(row["dataset_root"], row["case_dir"])
    identity = read_json(directory / "identity.json")
    if identity["case_uid"] != row["case_uid"] or identity["task"] != row["task"]:
        raise ValueError("Case identity mismatch")
    raw = inside(directory, relative).read_bytes()
    expected = identity["files"][relative]
    if len(raw) != expected["bytes"] or sha256(raw) != expected["sha256"]:
        raise ValueError(f"Case file hash mismatch: {relative}")
    return raw


def public_messages(row: dict) -> list[dict[str, str]]:
    messages = [
        {"role": role, "content": checked_file(row, "public/" + name).decode("utf-8")}
        for role, name in (("system", "system_prompt.txt"), ("user", "user_prompt.txt"))
    ]
    encoded = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if sha256(encoded) != row["messages_sha256"]:
        raise ValueError("Public message identity mismatch")
    return messages


def reference(row: dict) -> dict:
    filename = "evaluation_reference_output.json" if row["task"] in ("G1", "G2", "G3", "X1") else "reference_output.json"
    return json.loads(checked_file(row, "private/" + filename))


def plan_rows(path: str | Path) -> list[dict]:
    plan = read_json(path)
    if plan.get("schema") != "OPTIRA_NINE_TASKS_PLAN_V1":
        raise ValueError("Unsupported plan schema")
    wanted = plan["cases"]
    if len({item["case_uid"] for item in wanted}) != len(wanted):
        raise ValueError("Duplicate Case in plan")
    identifiers = {item["case_uid"] for item in wanted}
    rows = {row["case_uid"]: row for row in inventory(plan["datasets"], identifiers)}
    selected = []
    for item in wanted:
        row = rows[item["case_uid"]]
        for key in ("task", "case_dir", "messages_sha256"):
            if row[key] != item[key]:
                raise ValueError(f"Plan and current catalog disagree: {key}")
        selected.append(row)
    return selected
