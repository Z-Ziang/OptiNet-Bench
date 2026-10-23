"""Configuration and selection checks for one-command evaluation; no paid calls."""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optinet.quick import validate_config, select_cases, model_connection
from optinet.cli import main, parser


class QuickTests(unittest.TestCase):
    def config(self):
        return {"model": "deepseek/deepseek-flash", "selection": {"cases": ["G1_0001"]}}

    def rows(self):
        return [{"task": task, "case_id": f"{task}_{n:04d}", "case_uid": f"{i:064x}",
                 "case_dir": f"dataset/{task}/{n}", "messages_sha256": "a" * 64,
                 "scale": "small", "topology_folder": "topology", "topology_id": "TB_REAL::TOP_1_TEST"}
                for i, (task, n) in enumerate([("G1", 1), ("X2", 1), ("X2", 2)], 1)]

    def test_omitted_generation_stays_empty_and_input_is_unchanged(self):
        original = self.config()
        saved = copy.deepcopy(original)
        config = validate_config(original)
        self.assertEqual(config["generation"], {})
        self.assertEqual(config["max_samples"], 1)
        self.assertEqual(original, saved)

    def test_comment_block_does_not_change_effective_configuration(self):
        value = {**self.config(), "_comment": {"model": "Provider/model ID", "generation": "Optional settings"}}
        self.assertEqual(validate_config(value), validate_config(self.config()))
        self.assertIn("_comment", value)

    def test_official_endpoint_and_custom_key_reference(self):
        config = validate_config({**self.config(), "api_key_env": "MY_TEST_KEY"})
        with patch.dict(os.environ, {"MY_TEST_KEY": "test-secret"}):
            connection = model_connection(config)
        self.assertEqual(connection["base_url"], "https://api.deepseek.com")
        self.assertEqual(connection["api_key"], "test-secret")
        self.assertNotIn("test-secret", str(config))

    def test_custom_endpoint_preserved(self):
        config = validate_config({**self.config(), "base_url": "http://localhost:8000/v1"})
        self.assertEqual(model_connection(config)["base_url"], "http://localhost:8000/v1")

    def test_missing_custom_key_is_an_error(self):
        config = validate_config({**self.config(), "api_key_env": "ABSENT_TEST_KEY"})
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "ABSENT_TEST_KEY"):
            model_connection(config)

    def test_invalid_configuration_rejected(self):
        invalid = [{"generation": {"max_tokens": 0}}, {"generation": {"max_tokens": True}},
                   {"generation": {"temperature": -1}}, {"generation": {"temperature": float("nan")}},
                   {"generation": {"max_retries": -1}}, {"generation": {"temprature": 0}},
                   {"generation": {"system_message": "replace prompt"}},
                   {"generation": {"extra_body": {"messages": []}}},
                   {"generation": {"extra_headers": {"Authorization": "secret"}}},
                   {"max_samples": 0}, {"max_samples": True}, {"model": "no-provider"},
                   {"api_key_env": "not valid"}, {"api_key": "secret"},
                   {"base_url": "https://user:secret@example.com/v1"},
                   {"base_url": "https://example.com/v1?api_key=secret"},
                   {"base_url": "file:///tmp/service"}, {"unknown": 1}]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                validate_config({**self.config(), **fields})

    def test_explicit_options_pass_through(self):
        options = {"max_tokens": 2048, "temperature": 0, "top_p": .9, "max_retries": 0,
                   "extra_body": {"thinking": {"type": "disabled"}}}
        self.assertEqual(validate_config({**self.config(), "generation": options})["generation"], options)

    def test_provider_credential_aliases_are_rejected(self):
        for name in ("azure_ad_token", "api-token", "client_secret", "credentials", "token"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_config({**self.config(), "model_args": {name: "sentinel-secret"}})

    def test_zero_reasoning_budget_is_allowed_for_providers_that_support_it(self):
        self.assertEqual(validate_config({**self.config(), "generation": {"reasoning_tokens": 0}})["generation"], {"reasoning_tokens": 0})

    def test_exact_ids_and_uids_in_requested_order(self):
        rows = self.rows()
        selected = select_cases(rows, {"cases": [rows[2]["case_uid"], "G1_0001"]})
        self.assertEqual([r["case_id"] for r in selected], ["X2_0002", "G1_0001"])

    def test_task_batch_limit_and_offset(self):
        selected = select_cases(self.rows(), {"tasks": ["X2"], "limit_per_task": 1, "offset_per_task": 1})
        self.assertEqual([r["case_id"] for r in selected], ["X2_0002"])
        self.assertEqual(len(select_cases(self.rows(), {"tasks": ["X2"]})), 2)

    def test_selection_must_be_explicit_and_unambiguous(self):
        invalid = [{}, {"tasks": []}, {"tasks": ["XX"]}, {"cases": ["missing"]},
                   {"cases": ["X2_0001"], "tasks": ["X2"]}, {"tasks": ["X2"], "limit_per_task": -1},
                   {"tasks": ["X2"], "limit_per_task": True}, {"tasks": ["X2"], "typo": 2},
                   {"cases": ["X2_0001", "X2_0001"]},
                   {"cases": ["X2_0001", self.rows()[1]["case_uid"]]},
                   {"cases": ["X2_0001"], "limit_per_task": 1}]
        for selection in invalid:
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                select_cases(self.rows(), selection)

    def test_filters_never_silently_remove_exact_cases(self):
        with self.assertRaises(ValueError):
            select_cases(self.rows(), {"cases": ["X2_0001"], "scale": "large"})

    def test_ambiguous_case_id_rejected(self):
        rows = self.rows()
        duplicate = {**rows[1], "case_uid": "f" * 64}
        with self.assertRaises(ValueError):
            select_cases(rows + [duplicate], {"cases": ["X2_0001"]})

    def test_quick_cli_dry_run_writes_bound_plan_without_model_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.json"
            config.write_text(json.dumps(self.config()), encoding="utf-8")
            out = root / "out"
            with patch("optinet.quick.inventory", return_value=iter(self.rows())), \
                 patch("optinet.quick.public_messages", return_value=[]), \
                 patch("inspect_ai.model.get_model") as get_model, \
                 patch.object(sys, "argv", ["evaluate.py", "quick", "--config", str(config), "--out", str(out), "--dry-run"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                main()
            get_model.assert_not_called()
            plan = json.loads((out / "plan.json").read_text())
            self.assertEqual(plan["counts"], {"G1": 1})
            self.assertEqual(plan["cases"][0]["case_uid"], self.rows()[0]["case_uid"])

    def test_quick_live_passes_options_and_keeps_key_out_of_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.json"
            value = {**self.config(), "api_key_env": "TEST_RUN_KEY", "generation": {"max_tokens": 32}}
            config.write_text(json.dumps(value), encoding="utf-8")
            out = root / "out"
            with patch("optinet.quick.inventory", return_value=iter(self.rows())), \
                 patch("optinet.quick.public_messages", return_value=[]), \
                 patch("optinet.cli.plan_rows", return_value=[]), \
                 patch("inspect_ai.model.get_model", return_value="runtime-model") as get_model, \
                 patch("inspect_ai.eval", return_value=[]) as evaluate, \
                 patch("optinet.cli.export_logs", return_value={}), \
                 patch.dict(os.environ, {"TEST_RUN_KEY": "sentinel-secret"}), \
                 patch.object(sys, "argv", ["evaluate.py", "quick", "--config", str(config), "--out", str(out)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                main()
            self.assertEqual(get_model.call_args.kwargs["api_key"], "sentinel-secret")
            self.assertEqual(evaluate.call_args.kwargs["max_tokens"], 32)
            self.assertNotIn("temperature", evaluate.call_args.kwargs)
            self.assertNotIn("sentinel-secret", (out / "run_identity.json").read_text())

    def test_cli_selector_replaces_config_selector_and_case_file_is_relative(self):
        from optinet.quick import prepare
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cases.txt").write_text("# chosen IDs\nX2_0001\nX2_0002\n", encoding="utf-8")
            args = parser().parse_args(["quick", "--tasks", "X2", "--limit-per-task", "1"])
            with patch("optinet.quick.inventory", return_value=iter(self.rows())), patch("optinet.quick.public_messages"):
                _, plan, _ = prepare(self.config(), root / "config.json", args)
            self.assertEqual(plan["counts"], {"X2": 1})
            args = parser().parse_args(["quick"])
            with patch("optinet.quick.inventory", return_value=iter(self.rows())), patch("optinet.quick.public_messages"):
                _, plan, _ = prepare({**self.config(), "selection": {"case_file": "cases.txt"}}, root / "config.json", args)
            self.assertEqual(plan["counts"], {"X2": 2})


if __name__ == "__main__":
    unittest.main()
