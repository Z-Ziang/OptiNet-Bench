# OptiNet-Bench

**Benchmarking Large Language Model Capabilities for Optical Network Resource Allocation**

OptiNet-Bench comprises **21,356 cases across nine tasks** for evaluating large
language models (LLMs) in optical-network resource allocation. The task design
connects intent understanding, graph reasoning, and combinatorial optimization,
from component tasks to routing and spectrum assignment (RSA) and QoT-aware
routing, modulation, and spectrum assignment (RMSA).

This repository provides the complete dataset and the Inspect AI evaluation
code, including task-specific validators and reference answers.

## Tasks and dataset

| Group | Task | Description | Cases |
|---|---|---|---:|
| Component tasks | G1 | Graph-representation conversion | 2,430 |
| | G2 | Path-validity checking | 2,815 |
| | G3 | Shared directed links between shortest paths | 2,247 |
| | X1 | Shortest-path computation | 1,126 |
| | O1-S | Fixed-route spectrum assignment: single request | 3,618 |
| | O1-C | Fixed-route spectrum assignment: concurrent requests | 1,751 |
| RSA tasks | X2 | Joint routing and spectrum assignment: single request | 3,618 |
| | X3 | Joint routing and spectrum assignment: concurrent requests | 1,751 |
| RMSA task | Q1 | QoT-aware joint routing, modulation, and spectrum assignment | 2,000 |
| **Total** | | | **21,356** |

Graph tasks cover **561 topologies spanning 5–500 nodes**. Resource-allocation tasks use
**5–60-node** topologies with **320 spectrum slots per directed link**; the
smallest topology size differs by task (for example, Q1's smallest topologies
have 10 nodes). Q1 additionally includes physical link lengths, service bit
rates, modulation formats, and transceiver configurations.

All tasks describe the requirements and constraints in natural language. Only
`public/system_prompt.txt` and `public/user_prompt.txt` are sent to a model.
Reference answers and validation data under `private/` are used for scoring;
they are publicly downloadable, but are not model inputs.

## Paper evaluation subset

The paper evaluates **2,200 cases sampled by task and topology size**: 2,000
across G1–X3 and 200 Q1 cases (a stratified sample of the 2,000 Q1 dataset
cases) for the four frontier models. Each model is run once per evaluated case.

All reported metrics are computed as proportions over the cases actually
evaluated and scored for each model. The four frontier models are submitted on
the full 2,000-case G1–X3 sample; cases with no returned answer or no
format-compliant answer are excluded from the corresponding scored/compliant
denominators. For the smaller models, cases whose input alone exceeded the
32K-token context window (typically cases on the largest topologies) were not
fed to the model and have no evaluation record: the published runs contain
1,843 cases for each Qwen3 configuration and 1,824 for Ministral 3 3B.
Per-task denominator counts are listed in `results/task_summary.csv`.

[`evaluation/splits/evaluation_cases.txt`](evaluation/splits/evaluation_cases.txt)
lists the Case UIDs in the paper's sampled evaluation set, with one UID per line.
Use these UIDs to locate the cases in
`dataset/_meta/catalog/case_index.jsonl`. Record the Git commit when downloading
the repository to identify the exact code and dataset revision.

## Metrics

| Metric | Definition |
|---|---|
| **Corr.** — G1–G3 | Correct answers / scored cases × 100% |
| **Opt.** — other tasks | Optimal solutions / format-compliant responses × 100% |
| **Succ.** — other tasks | (Optimal solutions + feasible suboptimal solutions + correct rejections) / format-compliant responses × 100% |
| **Decision-failure rate** | 100% − Succ. |
| **Overall** | Unweighted mean of the eight task-level end-to-end success rates over G1–X3; Q1 is reported separately |

All cases use the same task-specific scoring policy. The export includes
per-task metrics and denominator counts in `summary.json` and `summary.csv`,
with the eight-task macro-average in `overall.csv`.

Format-invalid responses are excluded from Opt. and Succ., but count as
failures in end-to-end success. Correct rejections contribute to Succ., not
Opt. Incorrect acceptances and rejections count as decision failures.
Service-error records (a request with no returned answer) are excluded from
scored-response denominators and are reported separately.

Validators first check feasibility and then compare against precomputed
reference optima. X1 minimizes hop count or total path length; O1-S/O1-C
minimize network-wide spectrum fragmentation; X2/X3/Q1 use lexicographic
objectives for additional spectrum occupancy and fragmentation. Fragmentation
is evaluated using the network-wide wasted-unusable-free ratio (WUFR).

## Repository structure

```text
OptiNet-Bench/
├── README.md
├── LICENSE
├── dataset/
│   ├── G1/ G2/ G3/ X1/ O1-S/ O1-C/ X2/ X3/ Q1/
│   ├── _meta/catalog/      # Case and file-identity indexes
│   ├── _meta/contracts/    # Shared output formats and task specifications
│   ├── LICENSE
│   └── LICENSE_NOTICE.md
├── results/
└── evaluation/
    ├── evaluate.py
    ├── inspect_tasks.py
    ├── config.example.json
    ├── requirements.txt
    ├── optinet/
    ├── tasks/
    ├── splits/evaluation_cases.txt
    └── docs/
```

## Download

Install [Git](https://git-scm.com/), then run:

```shell
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench
git rev-parse HEAD
```

The dataset is distributed as ordinary files. No separate archive
extraction or Hugging Face account is required.

## Install and run

Use Python **3.11 or newer** and keep `evaluation/` and `dataset/` side by side.

```shell
cd evaluation
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```shell
# Linux or macOS
source .venv/bin/activate
```

Install dependencies and check the files:

```shell
python -m pip install -r requirements.txt
python evaluate.py verify
python evaluate.py verify-data --dataset ../dataset
```

Run a small offline reference replay without calling a model:

```shell
python evaluate.py plan --dataset ../dataset --limit-per-task 2 --out plans/pilot.json
python evaluate.py preflight --plan plans/pilot.json
python evaluate.py offline --plan plans/pilot.json --out runs/offline_pilot
```

The pilot checks setup and scoring; it does not measure model performance.
Its deterministic selection is separate from the paper's sampled evaluation set.

To evaluate a model, copy `config.example.json` to `config.json`, configure the
model/API connection, optional generation settings and case selection, and
provide API credentials through environment variables. The example uses
DeepSeek with `DEEPSEEK_API_KEY` and selects one G1 case. Then run:

```shell
python evaluate.py quick --config config.json
```

This one command validates the cases, calls the model, grades the answers and
exports results. Override selection with repeated `--case` options, or use a
task batch such as `--tasks X2 --limit-per-task 10`. Omitting the limit with
`--tasks X2` selects all X2 cases. Use `--dry-run` to validate without model
calls. See the [configuration guide](evaluation/docs/CONFIGURATION.md).

Model requests may incur provider charges. The configuration example is a
starting point; record the actual model, context and output budgets, reasoning
settings, and generation parameters used in an experiment.

Runs save final answers, grading results, timing, token usage when available,
and code/configuration identity. See the
[evaluation guide](evaluation/README.md) and
[scoring protocol](evaluation/docs/SCORING_PROTOCOL.md) for the interfaces and
task-specific rules.

## Use and reproducibility

- Cases can share topologies and resource snapshots; case counts are not counts
  of independent network topologies.
- Use the declared constraints and physical model for each task. Q1 evaluates
  QoT under its specified ASE-noise and chromatic-dispersion assumptions.
- Preserve Case UIDs, prompt files, reference answers, and validator definitions
  when reporting benchmark results.
- Record the code/data revision and evaluation settings. Saved answers can be
  regraded; remote model generation need not be identical across repeated calls.

## Experimental results

The [results directory](results/README.md) provides experimental settings,
per-case outcomes and task-level summaries.

## Citation

```bibtex
@misc{optinetbench,
  author = {Ziang Zhang and Rentao Gu and Zuhe Song and Yuefeng Ji},
  title = {{OptiNet-Bench}: Benchmarking Large Language Model Capabilities for Optical Network Resource Allocation},
  year = {2026},
  howpublished = {GitHub repository},
  url = {https://github.com/Z-Ziang/OptiNet-Bench}
}
```

## License

Evaluation code: **MIT** — see [LICENSE](LICENSE).

Dataset: **CC BY 4.0** — see [dataset/LICENSE](dataset/LICENSE).

Retain applicable source attributions and third-party notices. See
[evaluation/LICENSE_NOTICE.md](evaluation/LICENSE_NOTICE.md) and
[dataset/LICENSE_NOTICE.md](dataset/LICENSE_NOTICE.md).
