# Experimental Results

OptiNet-Bench contains 21,356 cases across nine tasks. The evaluation subset
comprises 2,200 cases selected by stratified sampling over task and topology size:
2,000 cases across G1–X3 and 200 Q1 cases (a stratified sample of the 2,000 Q1
dataset cases). Nine models are evaluated with ten configurations, including
Thinking and Non-Thinking configurations of Qwen3-8B. In a 32K-token context
window, long Q1 inputs can leave limited space for reasoning and final answers.
Q1 evaluation is limited to the four frontier models; smaller-model experiments
use 32K-token context windows.
Each model is run once per evaluated case.

### Evaluation coverage

The four frontier models were submitted on the full 2,000-case G1–X3 sample.
Cases whose request ended in a service error (no returned answer) are excluded
from the scored-response denominators, and cases without a format-compliant
answer are excluded from the Opt./Succ. denominators, so a model's per-task
denominators can be smaller than its number of sampled cases; the exact counts
are listed in `task_summary.csv`.

For the smaller models, cases whose input alone exceeded the 32K-token context
window (typically cases on the largest topologies) could not be fed to the model
and therefore have no evaluation record. The published runs contain 1,843 cases
for each Qwen3 configuration and 1,824 cases for Ministral 3 3B out of the 2,000
G1–X3 sample. All reported metrics are computed as proportions over the cases
actually evaluated and scored for that model.

## Files

| File | Contents |
|---|---|
| `task_summary.csv` | Task-level counts, Corr., Opt., and Succ. |
| `per_case_results.csv` | One row per included model–case evaluation record |
| `evaluation_settings.json` | Experimental Setup |

All percentages in `task_summary.csv` are rounded to one decimal place. Empty
metric cells mean that the metric does not apply. The Case UIDs refer to
`dataset/_meta/catalog/case_index.jsonl`; the sampled case list is
`evaluation/splits/evaluation_cases.txt`.

In `per_case_results.csv`, `case_uid` retains the dataset identifier and
`case_id` provides the unique short name, such as `G1_0001`, `O1-S_0001`, or
`Q1_0001`. Names use the task prefix and a numeric suffix padded to
four digits. The result records are ordered by model, task, and short-name
sequence.

## Experimental Setup

For frontier models, use official APIs with a 32K-token output budget and leave
other parameters at their defaults. For smaller models, use 32K-token context
windows and an 8K-token output budget on four NVIDIA A100 80GB GPUs. Enable
reasoning where supported, except for Qwen3-8B (Non-Thinking). Evaluate outputs
with Inspect AI and task-specific validators. `evaluation_settings.json` defines
the evaluation configuration. Configure API credentials and endpoints separately.

## Scoring policies

This project distinguishes strict and relaxed scoring: strict scoring checks
the raw response directly, while relaxed scoring permits removal of a complete
outer code fence or extraction of a unique task-shaped JSON object from
explanatory text before validation by the same task-specific scorer. Processing
does not complete or modify answers or select candidates by score.
`results/` contains the paper's relaxed-scoring
results, focusing on the solutions themselves while reducing the influence of
output-format differences. The two policies distinguish raw-output
format adherence from task performance after processing, helping assess the
reliability of model outputs for direct use in resource-allocation workflows.
Related evaluation distinctions or output-cleaning practices appear in
[IFEval](https://github.com/google-research/google-research/tree/master/instruction_following_eval)
and [EvalPlus](https://github.com/evalplus/evalplus/blob/master/docs/cli.md).

A response is format-invalid when the applicable policy cannot produce a unique
answer conforming to the task's output structure, for example because of
truncated JSON, missing required fields, incorrect field types, or ambiguous
candidates. Format-compliant answers that violate network constraints or
incorrectly assess request feasibility are decision failures.

See the [scoring protocol](../evaluation/docs/SCORING_PROTOCOL.md#format-policies)
for the evaluator's strict/relaxed rules and task-specific validation scope.

## Metrics

- **Corr. (G1–G3):** correct answers / scored cases × 100%.
- **Opt. (other tasks):** optimal solutions / format-compliant responses × 100%.
- **Succ. (other tasks):** (optimal solutions + feasible suboptimal solutions +
  correct rejections) / format-compliant responses × 100%.
- **Decision-failure rate:** 100% − Succ.
- **Overall:** unweighted mean of the eight task-level end-to-end success rates
  over G1–X3. Format-invalid responses count as end-to-end failures.

Correct rejections contribute to Succ., not Opt. Format-compliant incorrect
acceptances and rejections are decision failures. Format-invalid responses are
excluded from Opt./Succ. Error records are identified separately and excluded
from scored-response denominators; their counts remain visible.

For Qwen3-8B and Qwen3-8B (Non-Thinking), pooling all eight tasks gives 32.6%/10.6%
end-to-end success; averaging the eight task rates equally gives 29.3%/9.3%.

## Offline analysis

From the repository root, run `python evaluation/analyze_results.py` to reproduce
overall, graph-scale and topology statistics from the published tables. Use
`--analysis overall`, `--analysis scale` or `--analysis topology` for one analysis;
`--out statistics.json` saves the output. No model requests are made.

Graph-scale accuracy covers G1/G2/G3/X1 and the four frontier models. Each
model/task/size cell uses correct/scored for G1-G3 and optimal/scored for X1;
model rates are averaged within tasks, then task rates within size bands.

`dataset/_meta/catalog/topology_features.csv` contains one row per distinct
released graph hash. Physical graphs are simple and undirected; mean hops uses
all ordered pairs of distinct nodes, and connectivity is global edge connectivity.
G3 mean-hop comparisons split topology-level accuracy at the median within each
model and size band, require at least five topologies per side, and average
differences equally across eligible bands and then models. Connectivity comparisons
pool scored G3 responses across the four frontier models within each of the
101-200, 201-300, 301-400 and 401-500 node bands, then average band rates equally.

## Per-case fields

`model`, `case_uid`, `case_id`, `task`, and `node_count` identify the evaluated model and
case. `scored` indicates whether a scored response is available.
`format_compliant`, `decision_success`, `optimal_solution`, and
`correct_rejection` supply the indicators used for aggregation. Empty indicators
mean not applicable or unavailable, rather than false.

`outcome` is one of `correct`, `incorrect`, `optimal`, `feasible_suboptimal`,
`correct_rejection`, `decision_failure`, `format_invalid`, or `error`.
`failure_reason` contains the available diagnostic reason; an empty reason does
not imply success. The files contain evaluation records and summaries, without
full model responses or request logs.
