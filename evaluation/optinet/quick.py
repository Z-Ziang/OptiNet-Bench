"""One-command configuration and deterministic case selection; no grading rules."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from .data import TASKS, inventory, public_messages

OFFICIAL_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
GENERATION_FIELDS = {
    "max_tokens", "temperature", "top_p", "top_k", "seed", "stop_seqs",
    "frequency_penalty", "presence_penalty", "reasoning_effort", "reasoning_tokens",
    "reasoning_mode", "timeout", "attempt_timeout", "max_retries", "extra_body",
}
SELECTION_FIELDS = {"cases", "case_file", "tasks", "scale", "topology", "limit_per_task", "offset_per_task"}


def _integer(value, name, minimum):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Configuration numbers must be finite")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    if isinstance(value, list):
        for item in value:
            _finite(item)


def validate_config(value):
    """Validate before creating outputs or making requests; keep unset options unset."""
    from .cli import reject_secrets
    from inspect_ai.model import GenerateConfig

    if not isinstance(value, dict):
        raise ValueError("Configuration must be a JSON object")
    config = deepcopy(value)
    reject_secrets(config)
    _finite(config)
    comments = config.pop("_comment", None)
    if comments is not None and (not isinstance(comments, dict) or any(not isinstance(v, str) for v in comments.values())):
        raise ValueError("_comment must be an object containing explanatory strings")
    allowed = {"datasets", "model", "base_url", "api_key_env", "model_args", "generation",
               "max_samples", "selection", "output_dir"}
    if set(config) - allowed:
        raise ValueError("Unknown configuration fields: " + ", ".join(sorted(set(config) - allowed)))
    model = config.get("model", "")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_-]+/[^\s]+", model):
        raise ValueError("model must be a provider/model_id string, e.g. deepseek/deepseek-flash")
    if config.get("base_url") is not None:
        url = config["base_url"]
        if not isinstance(url, str):
            raise ValueError("base_url must be an HTTP(S) API base URL")
        parts = urlsplit(url)
        if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("base_url must be HTTP(S), without credentials, query or fragment")
    key_env = config.get("api_key_env")
    if key_env is not None and (not isinstance(key_env, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_env)):
        raise ValueError("api_key_env must name an environment variable, not contain a key")
    config.setdefault("datasets", ["../dataset"])
    if not isinstance(config["datasets"], list) or not config["datasets"] or any(not isinstance(x, str) or not x for x in config["datasets"]):
        raise ValueError("datasets must be a nonempty list of paths")
    config.setdefault("model_args", {})
    if not isinstance(config["model_args"], dict):
        raise ValueError("model_args must be an object")
    if {"base_url", "model", "model_name", "config", "api_key_var", "default_headers", "default_query"} & set(config["model_args"]):
        raise ValueError("model_args cannot override connection, credentials or generation configuration")
    config.setdefault("generation", {})
    generation = config["generation"]
    if not isinstance(generation, dict) or set(generation) - GENERATION_FIELDS:
        raise ValueError("Unsupported generation option; see docs/CONFIGURATION.md")
    for name in ("max_tokens", "top_k"):
        if name in generation:
            _integer(generation[name], "generation." + name, 1)
    if "reasoning_tokens" in generation:
        _integer(generation["reasoning_tokens"], "generation.reasoning_tokens", 0)
    if "max_retries" in generation:
        _integer(generation["max_retries"], "generation.max_retries", 0)
    for name, low, high in (("temperature", 0, 2), ("top_p", 0, 1),
                            ("frequency_penalty", -2, 2), ("presence_penalty", -2, 2)):
        if name in generation:
            item = generation[name]
            if type(item) not in (int, float) or not low <= item <= high:
                raise ValueError(f"generation.{name} must be between {low} and {high}")
    for name in ("timeout", "attempt_timeout"):
        if name in generation and (type(generation[name]) not in (int, float) or generation[name] <= 0):
            raise ValueError(f"generation.{name} must be positive")
    extra = generation.get("extra_body", {})
    reserved = GENERATION_FIELDS | {"model", "messages", "input", "instructions", "system", "tools", "tool_choice",
                                    "stream", "n", "max_completion_tokens", "max_output_tokens", "response_format"}
    if not isinstance(extra, dict) or reserved & set(extra):
        raise ValueError("extra_body cannot override prompts, model, generation limits or output format")
    try:
        GenerateConfig.model_validate(generation, strict=True)
    except ValueError:
        raise ValueError("Invalid generation value; see Inspect GenerateConfig and docs/CONFIGURATION.md") from None
    config.setdefault("max_samples", 1)
    _integer(config["max_samples"], "max_samples", 1)
    if "output_dir" in config and (not isinstance(config["output_dir"], str) or not config["output_dir"]):
        raise ValueError("output_dir must be a nonempty path")
    return config


def model_connection(config):
    """Resolve a key only in memory. Never include this result in run configuration."""
    provider = config["model"].split("/", 1)[0]
    connection = {"base_url": config.get("base_url") or OFFICIAL_URLS.get(provider), **config.get("model_args", {})}
    name = config.get("api_key_env")
    if name:
        key = os.environ.get(name)
        if not key or not key.strip():
            raise ValueError("Set the API key environment variable: " + name)
        connection["api_key"] = key
    return connection


def _selection_options(selection):
    if not isinstance(selection, dict) or set(selection) - SELECTION_FIELDS or "case_file" in selection:
        raise ValueError("Invalid selection fields (case_file must be expanded before selection)")
    cases, tasks = selection.get("cases", []), selection.get("tasks", [])
    for values in (cases, tasks):
        if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
            raise ValueError("selection.cases and selection.tasks must be lists of nonempty strings")
        if len(values) != len(set(values)):
            raise ValueError("Duplicate case/task selector")
    if bool(cases) == bool(tasks):
        raise ValueError("Select either explicit cases or tasks, never both; no implicit full-dataset run")
    if not set(tasks) <= set(TASKS):
        raise ValueError("Unknown task; choose from " + ", ".join(TASKS))
    limit, offset = selection.get("limit_per_task", 0), selection.get("offset_per_task", 0)
    _integer(limit, "selection.limit_per_task", 0)
    _integer(offset, "selection.offset_per_task", 0)
    for key in ("scale", "topology"):
        if key in selection and (not isinstance(selection[key], str) or not selection[key]):
            raise ValueError("selection." + key + " must be a nonempty string")
    if cases and set(selection) - {"cases"}:
        raise ValueError("Exact cases cannot be combined with task filters, limits or offsets")
    return cases, tasks, limit, offset


def select_cases(rows, selection):
    """Exact selectors preserve requested order; task batches preserve catalog order."""
    cases, tasks, limit, offset = _selection_options(selection)
    selected = []
    if cases:
        matches = {name: [] for name in cases}
        for row in rows:
            for name in {row["case_uid"], row["case_id"]} & matches.keys():
                matches[name].append(row)
        seen = set()
        for name in cases:
            if len(matches[name]) != 1:
                raise ValueError("Case selector must match exactly one record: " + name)
            row = matches[name][0]
            if row["case_uid"] in seen:
                raise ValueError("Two selectors identify the same case: " + name)
            seen.add(row["case_uid"])
            selected.append(row)
    else:
        positions, counts = Counter(), Counter()
        for row in rows:
            task = row["task"]
            if task not in tasks or (selection.get("scale") and row.get("scale") != selection["scale"]):
                continue
            if selection.get("topology") and selection["topology"] not in (row.get("topology_id"), row.get("topology_folder")):
                continue
            positions[task] += 1
            if positions[task] <= offset or (limit and counts[task] >= limit):
                continue
            selected.append(row)
            counts[task] += 1
        if set(tasks) - set(counts):
            raise ValueError("No matching cases for tasks: " + ", ".join(sorted(set(tasks) - set(counts))))
    if not selected:
        raise ValueError("No matching cases")
    return selected


def prepare(config, config_path, args):
    """Resolve CLI overrides and bind the same V1 plan consumed by the existing runner."""
    config = validate_config(config)
    parent = Path(config_path).resolve().parent
    selection = deepcopy(config.get("selection", {}))
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    if args.case or args.case_file or args.tasks is not None:
        selection = {}
        if args.case:
            selection["cases"] = args.case
        if args.case_file:
            selection["case_file"] = str(Path(args.case_file).resolve())
        if args.tasks is not None:
            selection["tasks"] = args.tasks.split(",")
    for name in ("limit_per_task", "offset_per_task", "scale", "topology"):
        if getattr(args, name) is not None:
            selection[name] = getattr(args, name)
    if "case_file" in selection:
        path = selection.pop("case_file")
        if not isinstance(path, str) or not path:
            raise ValueError("selection.case_file must be a nonempty path")
        names = (parent / path).read_text(encoding="utf-8-sig").splitlines()
        selection["cases"] = selection.get("cases", []) + [line.strip() for line in names if line.strip() and not line.lstrip().startswith("#")]
    roots = [str((parent / root).resolve()) for root in config["datasets"]]
    cases, tasks, _, _ = _selection_options(selection)
    selected = select_cases(inventory(roots, set(cases) if cases else None,
                                      wanted_tasks=set(tasks) if tasks else None), selection)
    for row in selected:
        public_messages(row)
    plan = {"schema": "OPTINET_NINE_TASKS_PLAN_V1", "datasets": roots,
            "cases": [{key: row[key] for key in ("case_uid", "task", "case_dir", "messages_sha256")} for row in selected],
            "counts": dict(Counter(row["task"] for row in selected)),
            "selection": "Explicit cases or deterministic catalog order; not a representative sampling claim"}
    config["selection"] = selection
    if args.out:
        destination = Path(args.out).resolve()
    elif config.get("output_dir"):
        destination = (parent / config["output_dir"]).resolve()
    else:
        from datetime import datetime, timezone
        from uuid import uuid4
        destination = parent / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    if destination.exists():
        raise ValueError("Output already exists; choose a new directory: " + str(destination))
    return config, plan, destination
