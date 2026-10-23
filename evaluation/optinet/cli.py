"""Command-line orchestration. No scientific grading formulas live in this module."""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .data import TASKS, inventory, plan_rows, public_messages, read_json, sha256
from .scoring import score_answer
from .metrics import normalize_result, task_metrics, overall_metrics, SCORED_CATEGORIES

HERE = Path(__file__).resolve().parents[1]


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=serialize)


def serialize(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else str(value)


def reject_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower().replace("-", "_") in (
                "api_key", "authorization", "access_token", "password", "azure_ad_token",
                "api_token", "bearer_token", "token", "secret", "client_secret",
                "credential", "credentials",
            ):
                raise ValueError("Put credentials in environment variables, not configuration files")
            reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            reject_secrets(item)


def load_config(path):
    path = Path(path).resolve()
    config = read_json(path)
    reject_secrets(config)
    if config.get("base_url") and urlsplit(config["base_url"]).username:
        raise ValueError("Do not embed credentials in a platform URL")
    return config, path


def dataset_roots(args):
    if args.dataset:
        return [str(Path(root).resolve()) for root in args.dataset]
    config, path = load_config(args.config)
    return [str((path.parent / root).resolve()) for root in config["datasets"]]


def export_logs(paths, destination):
    """Export final answers, raw grading fields and per-model/task category counts."""
    from inspect_ai.log import read_eval_log

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    seen, groups, logs = set(), {}, []
    with (destination / "answers_and_scores.jsonl").open("x", encoding="utf-8") as stream:
        for path in paths:
            log = read_eval_log(path)
            logs.append({"path": str(path), "status": log.status})
            for sample in log.samples or []:
                key = (log.eval.model, str(sample.id))
                if key in seen:
                    raise ValueError("Overlapping model/Case in logs; do not sum retries or different settings")
                seen.add(key)
                row = (sample.metadata or {}).get("case_record", {})
                score = next(iter((sample.scores or {}).values()), None)
                grading = dict(score.metadata) if score and score.metadata else {}
                for policy in ("strict", "relaxed"):
                    if grading.get(policy):
                        grading[policy] = normalize_result(grading[policy])
                result = normalize_result(grading.get("relaxed", {})) if grading.get("relaxed") else {}
                returned = bool(sample.output and sample.output.choices)
                error = sample.error.model_dump(mode="json") if sample.error else None
                category = result.get("category", ("SCORING_ERROR" if returned else "SERVICE_ERROR") if error else "UNSCORED")
                record = {
                    "model": log.eval.model, "case_uid": str(sample.id), "case_id": row.get("case_id"),
                    "task": row.get("task", "UNKNOWN"), "topology": row.get("topology_folder"),
                    "node_count": row.get("node_count"), "scale": row.get("scale"),
                    "model_version": row.get("model_version"), "messages_sha256": row.get("messages_sha256"),
                    "public_input_characters": row.get("public_input_characters"),
                    "returned_answer": returned, "answer": sample.output.completion if sample.output else "",
                    "category": category, "strict_category": grading.get("strict", {}).get("category"),
                    "truth_feasible": result.get("truth_feasible"), "correct_reject": result.get("correct_reject", False),
                    "format_compliant": result.get("format_compliant"),
                    "decision_success": result.get("decision_success"),
                    "optimal_solution": result.get("optimal_solution"), "grading": grading,
                    "usage": sample.model_usage, "total_time": sample.total_time, "error": error,
                    "inspect_log": str(path),
                }
                stream.write(json.dumps(record, ensure_ascii=False, default=serialize) + "\n")
                count = groups.setdefault((log.eval.model, record["task"]), collections.Counter())
                count["total_samples"] += 1
                count["returned_answers"] += returned
                count["service_errors"] += bool(error) and not returned
                count["category_" + category] += 1
                if result.get("binary_label"):
                    count["binary_" + result["binary_label"].lower()] += 1
                if result.get("truth_feasible") is True and row.get("task") not in ("G1", "G2", "G3"):
                    count["feasible_truth_" + category] += 1
                if result.get("truth_feasible") is False:
                    count["infeasible_truth_" + category] += 1
                if result.get("correct_reject"):
                    count["correct_reject"] += 1
                if category in SCORED_CATEGORIES:
                    count["scored_cases"] += 1
                    count["format_compliant_responses"] += bool(result.get("format_compliant"))
                    count["format_invalid_responses"] += not result.get("format_compliant")
                    count["successful_decisions"] += bool(result.get("decision_success"))
                    count["optimal_solutions"] += bool(result.get("optimal_solution"))
                    count["correct_answers"] += category == "CORRECT"
    rows = []
    for (model, task), count in groups.items():
        rows.append({"model": model, "task": task, **dict(count), **task_metrics(count, task)})
    overall = overall_metrics(rows)
    write_new(destination / "summary.json", {"logs": logs, "rows": rows, "overall": overall,
              "note": "All cases use one scoring policy. Percentages use explicit per-task denominators; infrastructure errors remain unresolved."})
    with (destination / "overall.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("model", "overall_e2e_percent", "missing_tasks", "unresolved_tasks"))
        writer.writeheader()
        writer.writerows(overall)
    fields = ["model", "task"] + sorted({key for row in rows for key in row if key not in ("model", "task")})
    with (destination / "summary.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return {"samples": len(seen), "rows": rows, "overall": overall}


def parser():
    root = argparse.ArgumentParser(description="Nine-task OptiNet-Bench evaluation with frozen scientific grading")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="Verify shipped code and frozen-runtime hashes; no model calls")
    data_check = sub.add_parser("verify-data", help="Verify every payload file against the dataset manifest; no model calls")
    data_check.add_argument("--dataset", required=True)
    sub.add_parser("tasks", help="List the nine supported tasks")
    quick = sub.add_parser("quick", help="Select, validate, run and export from one configuration")
    quick.add_argument("--config", default="config.json")
    quick.add_argument("--case", action="append", help="Exact canonical case ID or full UID; repeat for multiple cases")
    quick.add_argument("--case-file", help="UTF-8 text file containing one canonical ID or UID per line")
    quick.add_argument("--tasks", help="Comma-separated tasks, e.g. X2 or G1,G2")
    quick.add_argument("--limit-per-task", type=int, help="0 means all matching cases in each selected task")
    quick.add_argument("--offset-per-task", type=int)
    quick.add_argument("--scale")
    quick.add_argument("--topology")
    quick.add_argument("--out", help="New output directory; otherwise use config output_dir or a timestamped runs folder")
    mode = quick.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate and save the exact plan; no model calls")
    mode.add_argument("--offline", action="store_true", help="Run stored reference answers through the existing graders; no model calls")
    plan = sub.add_parser("plan", help="Freeze a batch; source order is not stratified random sampling")
    plan.add_argument("--config", default="config.json")
    plan.add_argument("--dataset", action="append", help="Dataset root; repeat only for disjoint catalogs")
    plan.add_argument("--tasks", default=",".join(TASKS))
    plan.add_argument("--scale", default="")
    plan.add_argument("--topology", default="")
    plan.add_argument("--limit-per-task", type=int, default=0)
    plan.add_argument("--offset-per-task", type=int, default=0)
    plan.add_argument("--out", required=True)
    for command in ("preflight", "offline", "run"):
        item = sub.add_parser(command)
        item.add_argument("--plan", required=True)
        if command != "preflight":
            item.add_argument("--out", required=True)
        if command == "run":
            item.add_argument("--config", default="config.json")
    grade = sub.add_parser("grade", help="Score a saved final answer without an API call")
    grade.add_argument("--config", default="config.json")
    grade.add_argument("--dataset", action="append")
    grade.add_argument("--case", required=True, help="Full Case UID or unique Case ID")
    grade.add_argument("--answer", required=True)
    grade.add_argument("--out")
    export = sub.add_parser("export")
    export.add_argument("--logs", nargs="+", required=True)
    export.add_argument("--out", required=True)
    retry = sub.add_parser("retry")
    retry.add_argument("--log", required=True)
    retry.add_argument("--out", required=True)
    return root


def main():
    args = parser().parse_args()
    if args.command == "tasks":
        print("\n".join(TASKS))
        return
    if args.command == "verify":
        manifest = read_json(HERE / "FILE_SHA256.json")
        for rel, expected in manifest.items():
            path = (HERE / rel).resolve()
            if not path.is_relative_to(HERE) or sha256(path.read_bytes()) != expected:
                raise ValueError("Program hash mismatch: " + rel)
        print(json.dumps({"status": "PASS", "files": len(manifest), "API_calls": 0}))
        return
    if args.command == "verify-data":
        import concurrent.futures
        root = Path(args.dataset).resolve()
        manifest_path = root / "SHA256SUMS.json"
        if not manifest_path.is_file():
            manifest_path = root / "_meta/SHA256SUMS.json"
        manifest = read_json(manifest_path)
        def check(item):
            relative, expected = item
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or sha256(path.read_bytes()) != expected:
                raise ValueError("Dataset payload hash mismatch: " + relative)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for index, _ in enumerate(pool.map(check, manifest.items()), 1):
                if index % 20000 == 0:
                    print(json.dumps({"verified_files": index, "total": len(manifest)}), flush=True)
        print(json.dumps({"status": "PASS", "verified_files": len(manifest), "API_calls": 0}))
        return
    if args.command == "plan":
        tasks = args.tasks.split(",")
        if not set(tasks) <= set(TASKS) or min(args.limit_per_task, args.offset_per_task) < 0:
            raise ValueError("Invalid tasks, limit or offset")
        roots = dataset_roots(args)
        counts, positions, selected = collections.Counter(), collections.Counter(), []
        for row in inventory(roots):
            task = row["task"]
            if task not in tasks or (args.scale and row["scale"] != args.scale):
                continue
            if args.topology and args.topology not in (row["topology_id"], row["topology_folder"]):
                continue
            positions[task] += 1
            if positions[task] <= args.offset_per_task or (args.limit_per_task and counts[task] >= args.limit_per_task):
                continue
            selected.append({key: row[key] for key in ("case_uid", "task", "case_dir", "messages_sha256")})
            counts[task] += 1
        if not selected:
            raise ValueError("No matching Cases")
        write_new(args.out, {"schema": "OPTINET_NINE_TASKS_PLAN_V1", "datasets": roots, "cases": selected,
                            "counts": dict(counts), "selection": "Deterministic source order for batching; not a representative sampling claim"})
        print(json.dumps({"cases": len(selected), "counts": dict(counts)}))
        return
    if args.command == "grade":
        rows = [row for row in inventory(dataset_roots(args)) if args.case in (row["case_uid"], row["case_id"])]
        if len(rows) != 1:
            raise ValueError("Case ID must identify exactly one catalog record; use a full UID")
        result = score_answer(rows[0], Path(args.answer).read_text(encoding="utf-8-sig"))
        if args.out:
            write_new(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "preflight":
        rows = plan_rows(args.plan)
        for row in rows:
            public_messages(row)
        print(json.dumps({"status": "PASS", "cases": len(rows), "API_calls": 0}))
        return
    if args.command == "export":
        print(json.dumps(export_logs(args.logs, args.out), ensure_ascii=False))
        return
    quick_config, runtime_model = None, None
    if args.command == "quick":
        from .quick import prepare, model_connection
        quick_config, bound_plan, destination = prepare(*load_config(args.config), args)
        # Resolve the key and construct the model before creating any output.
        # The key is passed directly to Inspect, never added to the saved config.
        if not args.dry_run and not args.offline:
            from inspect_ai.model import get_model
            connection = model_connection(quick_config)
            runtime_model = get_model(quick_config["model"], **connection)
            if connection.get("base_url"):
                quick_config["base_url"] = connection["base_url"]
        destination.mkdir(parents=True, exist_ok=False)
        args.plan = str(destination / "plan.json")
        write_new(args.plan, bound_plan)
        print(json.dumps({"cases": len(bound_plan["cases"]), "counts": bound_plan["counts"],
                          "output": str(destination), "mode": "dry-run" if args.dry_run else "offline" if args.offline else "live"}), flush=True)
        if args.dry_run:
            print(json.dumps({"status": "PASS", "API_calls": 0, "plan": args.plan}))
            return
        args.out = str(destination)
        args.command = "offline" if args.offline else "run"
    from inspect_ai import eval, eval_retry
    destination = Path(args.out).resolve()
    if quick_config is None:
        destination.mkdir(parents=True, exist_ok=False)
    if args.command == "retry":
        from inspect_ai.log import read_eval_log
        old = read_eval_log(args.log)
        if any(sample.error and sample.output and sample.output.choices for sample in old.samples or []):
            raise ValueError("A failed sample already has an answer; preserve it and score offline")
        if old.status == "success" and not any(sample.error for sample in old.samples or []):
            raise ValueError("Completed log; no retry needed")
        logs = eval_retry(args.log, log_dir=str(destination / "logs"), display="none", log_model_api=False)
    else:
        rows = plan_rows(args.plan)
        for row in rows:
            public_messages(row)
        config = (quick_config or {}) if args.command == "offline" else (quick_config if quick_config is not None else load_config(args.config)[0])
        generation = config.get("generation", {})
        protected = {"tasks", "task_args", "solver", "model", "model_base_url", "model_args", "log_dir", "log_samples", "log_model_api", "score", "max_samples", "display", "fail_on_error"}
        if protected & set(generation):
            raise ValueError("Generation config overrides protected orchestration settings")
        import importlib.metadata
        manifest = HERE / "FILE_SHA256.json"
        if not manifest.is_file():
            raise FileNotFoundError("Required program manifest is missing")
        write_new(destination / "run_identity.json", {"plan": read_json(args.plan), "config": config,
                  "offline": args.command == "offline", "framework": "Inspect AI",
                  "python": sys.version,
                  "versions": {name: importlib.metadata.version(name) for name in ("inspect-ai", "openai", "jsonschema")},
                  "program_manifest_sha256": sha256(manifest.read_bytes())})
        logs = eval(str(HERE / "inspect_tasks.py") + "@optinet_cases",
                    model="mockllm/model" if args.command == "offline" else (runtime_model if runtime_model is not None else config["model"]),
                    task_args={"plan_path": str(Path(args.plan).resolve()), "offline_reference": args.command == "offline"},
                    model_base_url=None if runtime_model is not None else config.get("base_url"),
                    model_args={} if runtime_model is not None else config.get("model_args", {}),
                    log_dir=str(destination / "logs"), display="none", log_samples=True, log_model_api=False,
                    fail_on_error=False, max_samples=config.get("max_samples", 1), **({"epochs": 1} if quick_config is not None else {}), **generation)
    paths = [log.location for log in logs]
    write_new(destination / "inspect_logs.json", paths)
    print(json.dumps(export_logs(paths, destination / "export"), ensure_ascii=False))
    if any(log.status != "success" or any(sample.error for sample in log.samples or []) for log in logs):
        sys.exit(2)
