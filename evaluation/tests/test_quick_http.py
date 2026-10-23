"""End-to-end compatible-API check using a local HTTP fixture, never a paid API."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from optinet.cli import main
from optinet.data import inventory, public_messages, reference


class QuickHTTPTests(unittest.TestCase):
    def test_request_grading_export_and_secret_boundary(self):
        data = ROOT.parent / "dataset"
        if not (data / "_meta/catalog/case_index.jsonl").is_file():
            self.skipTest("This integration check requires the bundled dataset")
        uid = "0cd2bc24e25e2c78691d680f703a48369f88de7bac34585d449f8e7e8f7518f1"
        row = next(inventory([str(data)], {uid}))
        solution = json.dumps(reference(row))
        answer = "Here is the answer:\n" + solution + "\nEnd."
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append({"path": self.path, "body": body})
                raw = json.dumps({"id": "fixture", "object": "chat.completion", "created": 0,
                    "model": "fixture-model", "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                config = {"datasets": [str(data)], "model": "openai-api/fixture/fixture-model",
                          "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                          "api_key_env": "OPTINET_FIXTURE_KEY", "model_args": {"responses_api": False, "stream": False},
                          "generation": {"max_tokens": 64, "temperature": 0, "max_retries": 0},
                          "selection": {"cases": [uid]}}
                path = folder / "config.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                out = folder / "out"
                with patch.dict(os.environ, {"OPTINET_FIXTURE_KEY": "fixture-secret-123"}), \
                     patch.object(sys, "argv", ["evaluate.py", "quick", "--config", str(path), "--out", str(out)]), \
                     contextlib.redirect_stdout(io.StringIO()):
                    main()
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["path"], "/v1/chat/completions")
                body = requests[0]["body"]
                self.assertEqual(body["messages"], public_messages(row))
                self.assertEqual(body["temperature"], 0)
                self.assertEqual(body.get("max_tokens", body.get("max_completion_tokens")), 64)
                exported = [json.loads(line) for line in (out / "export/answers_and_scores.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(exported), 1)
                self.assertEqual(exported[0]["case_uid"], uid)
                self.assertEqual(exported[0]["category"], "CORRECT")
                self.assertEqual(exported[0]["answer"], answer)
                self.assertEqual(exported[0]["strict_category"], "MISSING")
                processing = exported[0]["grading"]["relaxed"]["output_processing"]
                self.assertEqual(processing["method"], "json_extraction")
                self.assertEqual(processing["text"], solution)
                self.assertTrue((out / "export/summary.csv").is_file())
                from inspect_ai.log import read_eval_log
                locations = json.loads((out / "inspect_logs.json").read_text())
                log = read_eval_log(locations[0])
                self.assertEqual(log.samples[0].output.stop_reason, "stop")
                self.assertNotIn("fixture-secret-123", log.model_dump_json())
                self.assertNotIn("fixture-secret-123", (out / "run_identity.json").read_text())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
