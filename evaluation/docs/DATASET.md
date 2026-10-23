# Dataset layout

Keep `evaluation/` and `dataset/` next to each other. Set the dataset path in
`config.json` or pass it to `--dataset`. The loader uses
`dataset/_meta/catalog/case_index.jsonl`. File identities are stored in
`dataset/_meta/catalog/case_identity.jsonl`.

Each case has a stable UID and a readable name. Names are unique within each task.
Use UIDs to join the evaluation subset, model outputs and results.
Only the system and user prompts are sent to the evaluated model.
Private network states, reference outputs and certificates are used for scoring.

The dataset contains 21,356 cases. Q1 contains 600 pure-200G cases and 1,400
mixed-rate cases, with 1,950 solvable and 50 certified unsolvable cases.
Physical-model identifiers select the corresponding grading engines.
Case counts do not imply independent topology counts.

Run `verify-data` to validate dataset file checksums. Run `verify` to validate
program checksums. Dataset prompts, constraints and references must agree with
their catalog and identity bindings.
