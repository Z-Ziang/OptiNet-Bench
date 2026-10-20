# Interfaces

```python
from optinet.data import inventory, public_messages
from optinet.scoring import score_answer

record = next(inventory(["/absolute/path/to/dataset"]))
messages = public_messages(record)  # exactly public system and user
result = score_answer(record, final_visible_response)
```

Every task folder exports grade(record, final_answer). Use the shared loader:
it binds dataset location, UID, task and public-message hashes. The returned
strict and relaxed objects preserve source validator diagnostics and metrics.
Never substitute reference-string equality for feasibility/optimality checks.

CLI: verify, verify-data, tasks, plan, preflight, offline, run, grade, export,
retry. Run `python evaluate.py --help` for arguments. New outputs use exclusive
creation to protect old experiments. Export rejects overlapping model/Case pairs.

Run artifacts include code/configuration identity, Inspect logs,
answers_and_scores.jsonl, summary.csv and summary.json. JSONL retains final
visible answers, grading, input identity, model family, usage, time and errors.
The evaluator does not use hidden reasoning as the submitted answer. Inspect
logs can contain provider-specific content and should be reviewed before sharing.

Read order: README, task README, task grader, shared adapter, frozen implementation.
The entire evaluation directory is required; do not distribute isolated task
folders without their shared runtime. JSON and source files use UTF-8; CSV exports
use UTF-8 BOM for Windows spreadsheet compatibility.
