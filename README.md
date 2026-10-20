# OptiNet-Bench

Code and data for **OptiNet-Bench**, a nine-task benchmark for evaluating large
language models in optical-network resource allocation. The `optinet` evaluation
package uses Inspect AI and frozen scientific validators.

## Contents

- `evaluation/`: evaluation program, configuration example, task documentation and tests.
- `dataset/`: **21,356 Cases** in expanded task/topology/Case directories.
  Q1 contains **2,000 Cases** (600 pure-200G; 1,400 mixed-rate).
- Code license: **MIT**. Dataset license: **CC BY 4.0**.

## Download

Install Git and [Git LFS](https://git-lfs.com/) first. Then:

```shell
git lfs install
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench
git lfs pull
git rev-parse HEAD
```

Record the commit printed by the last command for reproducibility. The dataset
is about 4.65 GiB before Git storage. All data directories are checked into this
repository; no ZIP extraction or Hugging Face account is required. Only the
large source-provenance record uses LFS; its original bytes are checked by the
dataset SHA-256 manifest. The repository disables automatic newline conversion.

## Run a free offline pilot

From `OptiNet-Bench/`:

```shell
cd evaluation
python -m venv .venv
```

Activate `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on Linux/macOS. Then:

```shell
python -m pip install -r requirements.txt
python evaluate.py verify
python evaluate.py verify-data --dataset ../dataset
python evaluate.py plan --dataset ../dataset --limit-per-task 2 --out plans/pilot.json
python evaluate.py preflight --plan plans/pilot.json
python evaluate.py offline --plan plans/pilot.json --out runs/offline_pilot
```

These commands make no paid model calls. The complete hash check reads the full
dataset and may take several minutes. Offline replay is a setup/scoring check,
not a model score. Read [the evaluation guide](evaluation/README.md) to configure
and run a real model, save answers, export results and report error denominators.

## Identity and reproducibility

Task directories use task-based numbers; original scientific Case IDs and UIDs
remain in the catalog. Use UIDs and public-message hashes to join results.
References and proofs are publicly available for grading; only the two public
prompt files are sent to models. Shared topologies, difficulty selection, frozen
physical assumptions and source REVIEW limitations are described in the
[dataset card](dataset/README.md) and [scientific scope](evaluation/docs/REVIEW.md).

The original engineering acceptance is [ACCEPTANCE.json](evaluation/ACCEPTANCE.json).
The current naming and integration audit is [MAINTENANCE_AUDIT.json](evaluation/MAINTENANCE_AUDIT.json).
Use `evaluation/FILE_SHA256.json` and `dataset/_meta/SHA256SUMS.json` to verify
code and data. A saved model answer can be regraded; remote model generation is
not guaranteed identical. No historical model runs or credentials are shipped.

## Licenses

[Evaluation code: MIT](LICENSE). [Dataset: CC BY 4.0](dataset/LICENSE).
Retain applicable third-party attributions and source notices; see
[evaluation notices](evaluation/LICENSE_NOTICE.md) and
[dataset notices](dataset/LICENSE_NOTICE.md).
