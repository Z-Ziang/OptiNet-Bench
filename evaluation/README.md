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
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench/evaluation
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
next to each other and retain `_meta`. Dataset files are ordinary Git files. No Hugging Face account or ZIP
extraction is needed. See `docs/DATASET.md`.

## 2. Install

Use Python 3.11 or newer in a virtual environment.
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

Copy `config.example.json` to `config.json`. It has three configurable parts:
model/API connection, optional generation parameters, and case selection. The
example uses `deepseek/deepseek-flash`, an explicit 8192-token output cap and one
G1 case. Set `DEEPSEEK_API_KEY` in your environment, then run:

```shell
python evaluate.py quick --config config.json
```

This single command validates public inputs, saves an exact plan, calls the
model, grades the answers and exports results to a new timestamped `runs/`
directory. It makes real API requests and can incur charges. Selection must be
explicit; omitting it does not evaluate the full dataset. No key is saved in
the JSON configuration. Omitted generation fields retain Inspect/provider
defaults; the example output cap is not a universal benchmark setting.

```shell
python evaluate.py quick --config config.json --case X2_0001 --case X2_0002
python evaluate.py quick --config config.json --tasks X2 --limit-per-task 10
python evaluate.py quick --config config.json --tasks X2
python evaluate.py quick --config config.json --dry-run --out runs/check_selection
python evaluate.py quick --config config.json --offline --out runs/reference_check
```

The third command selects **all X2 cases**. Dry-run and offline modes make no
model requests. Official OpenAI, Anthropic and DeepSeek addresses are used when
`base_url` is omitted in `quick`. See `docs/CONFIGURATION.md` for key variables,
custom endpoints, budgets, temperature, batch lists and path rules. The existing
explicit-plan workflow also remains available:

```shell
python evaluate.py run --config config.json --plan plans/pilot.json --out runs/my_model_pilot
```

## 5. Read the results

Each run saves Inspect logs, the final visible answers, strict/relaxed grades,
model/configuration identity, time and provider-reported token usage. The
`export/` directory contains `answers_and_scores.jsonl`, `summary.json` and
`summary.csv`. Unknown usage stays unknown; hidden reasoning is not the answer.

Both strict and relaxed per-case grades are retained; the main score and
exported summary metrics use relaxed grading. Relaxed preprocessing uses a raw
JSON response directly, removes a complete outer JSON code fence, or extracts
one unique task-shaped JSON object from explanatory text, in that order.
Ambiguous candidates are format-invalid; answers are never repaired or selected
by score. Run exports retain the raw answer and preprocessing metadata. See the
[published-results notes](../results/README.md#scoring-policies) for the paper's
scoring scope.

The [scoring protocol](docs/SCORING_PROTOCOL.md#format-policies) defines the
strict/relaxed policies and format-invalid responses.

The export reports Corr., Opt., Succ., decision-failure rate, end-to-end success,
format coverage, and denominator counts. `overall.csv` gives the macro-average
end-to-end success over G1–X3 when all eight tasks have scored responses. Q1 is
reported separately. Correct rejections contribute to Succ., not Opt. All cases
use the same task-specific policy. See `docs/SCORING_PROTOCOL.md` for details.

To grade a saved final answer without another model request:

```shell
python evaluate.py grade --dataset ../dataset --case X2_0001 --answer answer.txt --out score.json
```

Directory names such as `X2_001` are presentation labels. Use the catalog's
64-character hexadecimal Case UID or canonical Case ID (for example, `X2_0001`) for `--case`; do not infer identity from a
directory number. `docs/INTERFACES.md` describes the Python API and retry/export.

## Reproducibility and release scope

- Only `public/system_prompt.txt` and `public/user_prompt.txt` are sent to models.
  Private answers, proofs and metadata are used for grading, not prompting.
- The public dataset also distributes grading references. It is an open
  benchmark, not a secret test set. Q1's 2,000 Cases are selected by stratified
  sampling; the paper's 200 evaluated Q1 Cases are a stratified sample of them.
- Freeze the code/data revisions and hashes. The same saved answer can be
  regraded deterministically; remote model generation is not guaranteed identical.
- Keep the whole evaluator: `optinet/_vendor` contains required frozen scientific
  code and contracts. The task folders are adapters, not standalone graders.
- The `results/` directory contains per-case outcomes, task summaries and experimental settings.
  Scientific scope and physical assumptions are documented in `docs/SCIENTIFIC_SCOPE.md`.
- Code and documentation: **MIT** (see `LICENSE`). Dataset: **CC BY 4.0**.
  Retain applicable third-party notices; see `LICENSE_NOTICE.md`.

See `docs/SCORING_PROTOCOL.md` for metric definitions and
`docs/SCIENTIFIC_SCOPE.md` for physical assumptions and interpretation.
