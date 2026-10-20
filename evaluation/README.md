# OptiNet-Bench evaluation

Use this program to send benchmark questions to a model and grade its final
answers. Inspect AI runs the model calls; the bundled scientific validators
check the answers. The expanded dataset is included in the same GitHub repository.

## What is included?

| Task | Question | Cases |
|---|---|---:|
| G1 | Convert graph representations | 2,430 |
| G2 | Check whether a path is valid | 2,815 |
| G3 | Find shortest paths and shared directed links | 2,247 |
| X1 | Find an optimal path | 1,126 |
| O1-S | Allocate spectrum on a fixed path | 3,618 |
| O1-C | Allocate spectrum for concurrent requests on fixed paths | 1,751 |
| X2 | Route and allocate spectrum for a request | 3,618 |
| X3 | Route and allocate spectrum for concurrent requests | 1,751 |
| Q1 | Jointly admit and allocate a batch of requests | 2,000 |

There are **21,356 Cases**. Q1 contains 600 pure-200G and 1,400 mixed-rate Cases.
These are problem-instance counts, not counts of independent topologies.
See each `tasks/<task>/README.md` for its exact frozen scoring contract.

## 1. Clone code and data together

```shell
git lfs install
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench/evaluation
git lfs pull
```

Record `git rev-parse HEAD` as your exact code/data revision.

```text
OptiNet-Bench/                 # cloned repository
  evaluation/                  # evaluation program
    evaluate.py
    config.example.json
    optinet/
    tasks/
  dataset/                     # included benchmark files
    G1/ G2/ G3/ X1/ O1-S/ O1-C/ X2/ X3/ Q1/
    _meta/
```

The enclosing directory can have any name. Keep `evaluation/` and `dataset/`
next to each other and retain `_meta`. Git LFS restores the one large source
record; all other files are ordinary Git files. No Hugging Face account or ZIP
extraction is needed. See `docs/DATASET.md`.

## 2. Install

Use Python 3.11 or newer in a virtual environment. The recorded acceptance
environment is Windows with Python 3.13; other systems are not claimed as tested.
Run these commands from `evaluation/`:

```shell
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on Linux/macOS. Then:

```shell
python -m pip install -r requirements.txt
python evaluate.py tasks
python evaluate.py verify
python evaluate.py verify-data --dataset ../dataset
```

`verify` checks the shipped program; `verify-data` reads and hashes the full
dataset and can take several minutes. Neither command calls a model.

## 3. Try a free offline check

```shell
python evaluate.py plan --dataset ../dataset --limit-per-task 2 --out plans/pilot.json
python evaluate.py preflight --plan plans/pilot.json
python evaluate.py offline --plan plans/pilot.json --out runs/offline_pilot
```

This selects two Cases per task and grades stored reference answers. It makes
no external model requests and is **not a model performance measurement**.
Existing output directories are protected: choose a new name for another run.

To evaluate all Q1 Cases instead, make a plan with `--tasks Q1` and omit
`--limit-per-task`. Plans select a deterministic catalog order; a small prefix
is not a representative random sample. Regenerate plans after relocating data.

## 4. Evaluate your model

Copy `config.example.json` to `config.json`. Set your actual served model ID,
API base URL, generation limits and concurrency. Put the API key in an
environment variable, never in the JSON file. For an OpenAI-compatible service,
set `OPENAI_API_KEY` using your shell or secret manager.

```shell
python evaluate.py run --config config.json --plan plans/pilot.json --out runs/my_model_pilot
```

This command makes real API requests and can incur charges. The example
generation limit is not a universal benchmark setting. Freeze and report
temperature, thinking settings, context/output budgets, retries and concurrency
for your actual service. See `docs/CONFIGURATION.md`.

## 5. Read the results

Each run saves Inspect logs, the final visible answers, strict/relaxed grades,
model/configuration identity, time and provider-reported token usage. The
`export/` directory contains `answers_and_scores.jsonl`, `summary.json` and
`summary.csv`. Unknown usage stays unknown; hidden reasoning is not the answer.

For optimization tasks, report `CORRECT`, `SUBOPTIMAL`, `INFEASIBLE` and
`MISSING`. G1/G2/G3 use binary correctness. Certified correct rejection has its
own flag. Keep REVIEW states, scorer errors and service failures separate from
ordinary model mistakes. See `docs/SCORING_PROTOCOL.md` for denominators.

To grade a saved final answer without another model request:

```shell
python evaluate.py grade --dataset ../dataset --case FULL_CASE_UID --answer answer.txt --out score.json
```

Directory names such as `X2_001` are presentation labels. Use the catalog's
stable Case UID or original Case ID for `--case`; do not infer identity from a
directory number. `docs/INTERFACES.md` describes the Python API and retry/export.

## Reproducibility and release scope

- Only `public/system_prompt.txt` and `public/user_prompt.txt` are sent to models.
  Private answers, proofs and metadata are used for grading, not prompting.
- The public dataset also distributes grading references. It is an open
  benchmark, not a secret test set. Q1 includes disclosed difficulty selection.
- Freeze the code/data revisions and hashes. The same saved answer can be
  regraded deterministically; remote model generation is not guaranteed identical.
- Keep the whole evaluator: `optinet/_vendor` contains required frozen scientific
  code and contracts. The task folders are adapters, not standalone graders.
- This repository contains no production jobs or historical model runs.
  Source REVIEW flags and scientific limitations remain documented in
  `docs/REVIEW.md`; a successful replay does not re-prove every oracle optimum.
- Code and documentation: **MIT** (see `LICENSE`). Dataset: **CC BY 4.0**.
  Retain applicable third-party notices; see `LICENSE_NOTICE.md`.

See `docs/RELEASE_CHECKLIST.md` for the public-release criteria and
`MAINTENANCE_AUDIT.json` for the current audit and `ACCEPTANCE.json` for
the original engineering acceptance.
