# Experimental Results

OptiNet-Bench contains 21,356 cases across nine tasks. The evaluation subset
comprises 2,200 cases selected by stratified sampling over task and topology size:
2,000 cases across G1–X3 and 200 Q1 cases. Nine models are evaluated with ten
configurations, including Thinking and Non-Thinking configurations of Qwen3-8B.
Q1 results are included for the four frontier models. Each model is run once per
evaluated case.

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
`case_name` provides the unique short name, such as `G1_001`, `O1-S_001`, or
`Q1_001`. Names use the task prefix and a numeric suffix padded to at least
three digits. The result records are ordered by model, task, and short-name
sequence.

## Experimental Setup

For frontier models, use official APIs with a 32K-token output budget and leave
other parameters at their defaults. For smaller models, use 32K-token context
windows and an 8K-token output budget on four NVIDIA A100 80GB GPUs. Enable
reasoning where supported, except for Qwen3-8B (Non-Thinking). Evaluate outputs
with Inspect AI and task-specific validators. `evaluation_settings.json` defines
the evaluation configuration. Configure API credentials and endpoints separately.

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

## Per-case fields

`model`, `case_uid`, `case_name`, `task`, and `node_count` identify the evaluated model and
case. `scored` indicates whether a scored response is available.
`format_compliant`, `decision_success`, `optimal_solution`, and
`correct_rejection` supply the indicators used for aggregation. Empty indicators
mean not applicable or unavailable, rather than false.

`outcome` is one of `correct`, `incorrect`, `optimal`, `feasible_suboptimal`,
`correct_rejection`, `decision_failure`, `format_invalid`, or `error`.
`failure_reason` contains the available diagnostic reason; an empty reason does
not imply success. The files contain evaluation records and summaries, without
full model responses or request logs.
