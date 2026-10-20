---
license: cc-by-4.0
language:
- en
task_categories:
- text-generation
tags:
- benchmark
- optical-networks
- resource-allocation
pretty_name: OptiNet-Bench
---

# OptiNet-Bench dataset

The catalog contains 21,356 Cases across nine tasks. Q1 contains 2,000 certified
Cases: 600 pure-200G and 1,400 mixed-rate. Its original 200 Cases are retained
byte-for-byte, with 1,800 additional Cases. The other eight tasks retain their 19,356 scientific Cases; their directories
use task-based numbers, with current location metadata updated accordingly. Case counts describe problem instances, not independent topologies.

## Repository layout

The expanded dataset is published alongside the evaluation program at
https://github.com/Z-Ziang/OptiNet-Bench.
Clone with Git LFS installed; `evaluation/` and `dataset/` stay side by side.
Use `git rev-parse HEAD` to record the exact release revision. No archive
extraction or Hugging Face account is required.

```text
dataset/
  Q1/<topology_name>_n<nodes>_TB<id>/Q1_<number>/
    identity.json
    public/system_prompt.txt
    public/user_prompt.txt
    private/root_case.json
    private/oracle_proof.json
    private/reference_output.json
    private/reference_validation.json
    private/difficulty_and_lineage.json
  G1/ G2/ G3/ X1/ O1-S/ O1-C/ X2/ X3/
  _meta/catalog/case_index.jsonl
  _meta/SHA256SUMS.json
```

Q1 IDs run from `Q1_001` to `Q1_2000`, with a minimum of three numeric digits.
The catalog is authoritative. Per-Case identity files bind all seven payload
files by SHA-256 and byte length. Model messages consist of the two `public`
files only. `private` denotes the grading role; those files contain reference
answers and proofs and are also downloadable from a public dataset repository.

Q1 uses 53 joint quota strata based on exact node count, rate mode, frozen
physical contract, request count and Oracle decision. Each stratum is ten times
the reviewed 200-Case seed population. New Cases include explicitly documented,
seeded spectrum-snapshot variants; network structures can be shared. Source
lineage and full production certification evidence are retained under
`dataset/_meta/release/Q1_2000/`. This construction uses certification and
difficulty selection and does not represent a uniform random topology sample.

## Download and evaluate

```shell
git lfs install
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench/evaluation
git lfs pull
python -m pip install -r requirements.txt
python evaluate.py verify
python evaluate.py verify-data --dataset ../dataset
python evaluate.py plan --dataset ../dataset --tasks Q1 --out plans/q1_2000.json
python evaluate.py preflight --plan plans/q1_2000.json
```

Use a virtual environment as explained in the repository README. These commands
make no model requests. The evaluation guide explains model configuration and
Inspect AI execution. Only the large source-provenance record uses Git LFS;
Git attributes preserve original newline bytes for all scientific payloads.

## License

Dataset: **CC BY 4.0**. Evaluation code: **MIT**. See LICENSE and
LICENSE_NOTICE.md. Preserve source credit and indicate modifications.


## Directory names and stable identity

The eight non-Q1 tasks use TASK_001, TASK_002, ... across their topology folders.
Original scientific Case IDs, stable UIDs, public messages, private scientific
inputs, proofs and reference answers are unchanged. Only current paths and
metadata integrity bindings change. The complete mapping is
`_meta/catalog/DIRECTORY_NAME_MAPPING.jsonl`; the verification summary is
`_meta/release/DIRECTORY_NAMING_ACCEPTANCE.json`. Use stable UIDs for result joins.
Historical provenance paths are retained as source evidence, not runtime paths.
Regenerate evaluation plans after relocation or a data revision.

## Intended use and limitations

This benchmark evaluates graph reasoning and optical-network resource allocation.
It does not certify production network safety or device-level optical performance.
Q1 uses frozen ASE-only/CD assumptions and disclosed difficulty selection. Related
task projections, shared graphs and snapshot variants are not independent samples.
References and certificates are publicly downloadable: this is an open benchmark,
not a secret held-out test set. Prior model-assisted selection must be disclosed.
Source REVIEW flags and oracle-audit limitations are retained by the evaluator.

## Licensing and publication identifiers

The dataset is licensed under **CC BY 4.0**; the evaluation code uses **MIT**.
Retain source attributions and applicable third-party notices. See LICENSE and
LICENSE_NOTICE.md for the license terms and scope. The repository URL above is the official code/data location. Record the Git
commit for exact version binding.
