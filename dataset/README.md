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

The catalog contains 21,356 Cases across nine tasks. The four graph tasks span
561 topologies (5–500 nodes). Q1 contains 2,000 certified
Cases: 600 pure-200G and 1,400 mixed-rate (1,950 solvable, 50 certified
infeasible). These 2,000 Cases are selected by stratified sampling over the
joint quota strata described below; the paper's evaluated 200 Q1 Cases are a
stratified sample drawn from these 2,000. The other eight tasks retain their
19,356 scientific Cases; their directories use task-based numbers, with current
location metadata updated accordingly. Case counts describe problem instances,
not independent topologies.

## Repository layout

The dataset is published alongside the evaluation program at
https://github.com/Z-Ziang/OptiNet-Bench.
Clone the repository; `evaluation/` and `dataset/` stay side by side.
Use `git rev-parse HEAD` to record the exact release revision. No archive
extraction or Hugging Face account is required.

```text
dataset/
  Q1/<topology_name>_n<nodes>_TB<id>/Q1_<number>/
    metadata.json
    public/system_prompt.txt
    public/user_prompt.txt
    private/root_case.json
    private/oracle_proof.json
    private/reference_output.json
    private/reference_validation.json
    private/difficulty_and_lineage.json
  G1/ G2/ G3/ X1/ O1-S/ O1-C/ X2/ X3/
  _meta/catalog/case_index.jsonl
  _meta/catalog/case_identity.jsonl
  _meta/SHA256SUMS.json
```

Q1 case IDs run from `Q1_0001` to `Q1_2000`, using four numeric digits.
Directory labels locate files; use the catalog's `case_id` or `case_uid` to identify a case.
The catalog is authoritative. The case identity index
(`_meta/catalog/case_identity.jsonl`) binds every payload file by SHA-256 and
byte length. Model messages consist of the two `public` files only. `private`
denotes the grading role; those files contain reference answers and proofs and
are also downloadable from a public dataset repository.

Each case has one formal reference answer at `private/reference_output.json`.
The catalog and offline reference replay use this same file.

Optional X2/X3 `private/features.json` files provide auxiliary instance statistics
and reference-algorithm diagnostics.

The 2,000 Q1 Cases are drawn by stratified sampling over 53 joint quota strata
based on exact node count, rate mode, frozen physical contract, request count
and Oracle decision. Each Case carries a certified oracle proof
(EXACT_CERTIFIED or INFEASIBLE_CERTIFIED) in `private/oracle_proof.json`;
network structures can be shared across Cases. This stratified construction
does not represent a uniform random topology sample.

## Download and evaluate

```shell
git clone https://github.com/Z-Ziang/OptiNet-Bench.git
cd OptiNet-Bench/evaluation
python -m pip install -r requirements.txt
python evaluate.py verify
python evaluate.py verify-data --dataset ../dataset
python evaluate.py plan --dataset ../dataset --tasks Q1 --out plans/q1_2000.json
python evaluate.py preflight --plan plans/q1_2000.json
```

Use a virtual environment as explained in the repository README. These commands
make no model requests. The evaluation guide explains model configuration and
Inspect AI execution. The dataset is stored as ordinary files.
Git attributes preserve original newline bytes for all scientific payloads.

## License

Dataset: **CC BY 4.0**. Evaluation code: **MIT**. See LICENSE and
LICENSE_NOTICE.md. Preserve source credit and indicate modifications.


## Directory names and stable identity

Within each task, Case directories use task-based numbers such as `G1_001`,
`O1-S_001` and `Q1_001`. Stable Case UIDs, public messages, private scientific
inputs, proofs and reference answers identify every Case; directory names are
presentation labels, and current paths and metadata integrity bindings are the
only location-dependent fields. Use stable UIDs for result joins. Regenerate
evaluation plans after relocation or a data revision.

## Intended use and limitations

This benchmark evaluates graph reasoning and optical-network resource allocation.
It does not certify production network safety or device-level optical performance.
Q1 uses frozen ASE-only/CD assumptions; its 2,000 Cases are selected by the
stratified sampling described above. Related task projections, shared graphs
and snapshot variants are not independent samples. References and certificates
are publicly downloadable: this is an open benchmark, not a secret held-out
test set.

## Licensing and publication identifiers

The dataset is licensed under **CC BY 4.0**; the evaluation code uses **MIT**.
Retain source attributions and applicable third-party notices. See LICENSE and
LICENSE_NOTICE.md for the license terms and scope. The repository URL above is the official code/data location. Record the Git
commit for exact version binding.
