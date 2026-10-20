"""Offline regression checks for the published package and plan identity."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class PackageIdentityTests(unittest.TestCase):
    def test_public_package_and_cli_use_current_name(self):
        package = importlib.import_module("optinet")
        self.assertIn("OptiNet-Bench", package.__doc__)
        result = subprocess.run([sys.executable, str(ROOT / "evaluate.py"), "--help"],
                                text=True, capture_output=True, check=True)
        self.assertIn("OptiNet-Bench", result.stdout)

    def test_new_plans_use_current_schema(self):
        cli = importlib.import_module("optinet.cli")
        row = {"task": "G1", "case_uid": "case", "case_dir": "dataset/G1/case",
               "messages_sha256": "hash"}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            argv = ["evaluate.py", "plan", "--dataset", directory, "--out", str(output)]
            with patch.object(sys, "argv", argv), patch.object(cli, "inventory", return_value=iter([row])):
                cli.main()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["schema"],
                             "OPTINET_NINE_TASKS_PLAN_V1")

    def test_existing_plan_identity_is_still_checked(self):
        data = importlib.import_module("optinet.data")
        row = {"task": "G1", "case_uid": "case", "case_dir": "dataset/G1/case",
               "messages_sha256": "hash"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            for schema in ("OPTINET_NINE_TASKS_PLAN_V1", "OPTIRA_NINE_TASKS_PLAN_V1"):
                path.write_text(json.dumps({"schema": schema, "datasets": [], "cases": [row]}), encoding="utf-8")
                with patch.object(data, "inventory", return_value=iter([row])):
                    self.assertEqual(data.plan_rows(path), [row])
                with patch.object(data, "inventory", return_value=iter([{**row, "messages_sha256": "changed"}])):
                    with self.assertRaisesRegex(ValueError, "Plan and current catalog disagree"):
                        data.plan_rows(path)


if __name__ == "__main__":
    unittest.main()
