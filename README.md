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

Graph tasks cover **5–500-node** topologies. Resource-allocation tasks use
**5–60-node** topologies with **320 spectrum slots per directed link**. Q1
additionally includes physical link lengths, service bit rates, modulation
formats, and transceiver configurations.

All tasks describe the requirements and constraints in natural language. Only
`public/system_prompt.txt` and `public/user_prompt.txt` are sent to a model.
Reference answers and validation data under `private/` are used for scoring;
they are publicly downloadable, but are not model inputs.

## Paper evaluation subset

The paper evaluates **2,200 cases sampled by task and topology size**: 2,000
across G1–X3 for nine LLMs and 200 Q1 cases for four frontier models, owing to
context-window limits. Each model is run once per evaluated case.

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

Format-invalid responses are excluded from Opt. and Succ., but count as
failures in end-to-end success. Correct rejections contribute to Succ., not
Opt. Incorrect acceptances and rejections count as decision failures.

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
│   ├── _meta/
│   ├── LICENSE
│   └── LICENSE_NOTICE.md
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

Install [Git](https://git-scm.com/) and [Git LFS](https://git-lfs.com/), then run:

```shell
git lfs install
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench
git lfs pull
git rev-parse HEAD
```

The expanded dataset occupies approximately **4.65 GiB**. No separate archive
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
served model and generation settings, and provide API credentials through
environment variables. Then run:

```shell
python evaluate.py run --config config.json --plan plans/pilot.json --out runs/my_model
```

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
