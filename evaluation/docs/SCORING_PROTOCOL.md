# Scoring protocol

## Categories and denominators
All cataloged cases are evaluated with the same task-specific scoring policy.
No case cohort or source-state label changes eligibility or weighting.

| Category | Meaning |
|---|---|
| CORRECT | Correct graph answer, optimal feasible solution, or certified correct rejection |
| SUBOPTIMAL | Feasible solution below the reference optimum |
| INFEASIBLE | Format-compliant decision failure, including incorrect acceptance or rejection |
| MISSING | Format-invalid response, including invalid JSON or a source schema failure |

Correct rejection is identified separately by `correct_reject=true` and is not
an optimal solution. G1–G3 use Corr. = correct / scored cases. Other tasks use
Opt. = optimal solutions / format-compliant responses, and Succ. = (optimal +
feasible suboptimal + correct rejection) / format-compliant responses. Rates
are percentages. Decision-failure rate is 100% − Succ.

End-to-end success uses all scored responses, counting format-invalid responses
as failures. Overall is the unweighted mean of the eight task-level end-to-end
success rates over G1–X3; Q1 is separate. A required task without scored
responses leaves Overall undefined. Service/scorer errors are excluded from
scored-response denominators and listed separately; they do not become model
successes or failures. Denominator counts, errors, and format coverage are
exported alongside the rates.

SCORING_ERROR identifies an actual scorer, data-integrity or reference-optimum
conflict. SERVICE_ERROR identifies a failed request without an answer. These
are reported separately rather than relabeled as model failures.

## Objectives and numerical rules
- X1: source graph shortest path, using HOP_COUNT or TOTAL_LENGTH_KM. Weighted
  validation uses the link lengths actually printed to six significant digits.
- O1-S/O1-C: paths are fixed; recover them from the Case and call the pinned
  X2/X3 validator. Require zero primary gap, then compare fragmentation.
- X2: minimize route hops (equivalently, minimize added spectrum-slot occupancy
  for the fixed request width), then WUFR.
- X3: minimize additional spectrum-hop occupancy, then WUFR.
- Q1: all requests are admitted together or rejected together. Validate routing,
  profile compatibility, contiguous spectrum, joint conflicts, ASE-only OSNR and
  accumulated CD. Minimize sum(slots including guard times hops), then fragmentation.

O1-S/O1-C/X2/X3 use a 1e-9 gap-classification tolerance. Q1 optimality
requires exact primary equality and `math.isclose(rel_tol=0, abs_tol=1e-10)` for
the secondary value. A Q1 rejection is correct only with a stored
INFEASIBLE_CERTIFIED proof. Timeout is not an infeasibility certificate.

Q1 `strict_bilevel_correct` indicates whether the answer satisfies the
feasibility and bilevel-optimality conditions. A better legal solution triggers
SCORING_ERROR with a reference-optimum-conflict reason. Source exceptions remain SCORING_ERROR rather than being silently
repaired. Secondary gaps are not compared as equal-quality tradeoffs when the
primary objective differs.

## Format policies
This project distinguishes strict and relaxed scoring. Strict scoring checks
the raw response directly. Relaxed scoring follows predefined rules applied
consistently to all models: it permits removal of a complete outer code fence
or extraction of a unique JSON object matching the task's output structure from
explanatory text, followed by validation with the same task-specific scorer.
Processing neither completes nor modifies the answer and never selects
candidates based on their scores. The two policies
distinguish raw-output format adherence from task performance after permitted
processing, helping assess the reliability of model outputs in
resource-allocation workflows. Related evaluation distinctions or
output-cleaning practices appear in
[IFEval](https://github.com/google-research/google-research/tree/master/instruction_following_eval)
and [EvalPlus](https://github.com/evalplus/evalplus/blob/master/docs/cli.md).

A response is format-invalid when the applicable scoring policy cannot produce
a unique answer conforming to the task's output structure, for example because
of truncated JSON, missing required fields, incorrect field types, or multiple
ambiguous candidates. A structurally valid answer that violates network
constraints or incorrectly assesses request feasibility is a decision failure,
not a format-invalid response. Required fields and types follow each task's
output contract and validator.

The evaluator records both strict and relaxed per-case grades. The
Inspect task's main score and exported summary metrics use relaxed grading.

Relaxed preprocessing follows this fixed order:

1. If the entire response parses as JSON, use it directly, even if it is
   structurally invalid or incorrect. Do not search its nested objects for an
   alternative answer.
2. If one JSON code fence encloses the entire response, remove that fence and
   validate the enclosed text, without searching for another answer.
3. Otherwise, scan complete outer JSON containers in the explanatory text.
   Retain objects matching the task's output fields and types; do not promote
   nested objects or salvage them from a truncated parent. Deduplicate repeated
   JSON values while preserving array order and duplicate-key occurrences.
   Accept exactly one distinct candidate. Multiple candidates are format-invalid
   with reason `AMBIGUOUS_JSON_CANDIDATES`; no candidate leaves the response
   format-invalid. The task validator determines final structural validity,
   feasibility and optimality after selection.

Candidate selection reads only the final visible response and task identifier,
not reference answers, feasibility results or objective values. The selected
text is an exact substring of the original answer. Do not insert fields, repair
routes or select a better retry. Compare results under the same scoring policy.

The relaxed grade records `output_processing`: policy version, method (`raw`,
`single_outer_fence`, `json_extraction`, or `none`), status, distinct candidate
count, selected-text SHA-256, and start/end character offsets. Extracted text is
retained for `json_extraction`; the unmodified original answer remains in the
run log and export. Offsets use Python string indices, not byte offsets.

The [published results](../../results/README.md#scoring-policies) use a relaxed
scoring policy.

Q1 aligns allocations by `request_id`, independently of their input order.
Additional fields and duplicate JSON keys are not universally rejected.
Validator exceptions are reported as `SCORING_ERROR`.

## Public information and fairness
Only public system/user messages are model inputs. Keep private truth, oracle
values, certificates and future information out of requests. WUFR serves solely
as the metric for assessing how well a model minimizes network-wide spectrum
fragmentation; it is not an objective supplied to the model.

Freeze Case UID, message hash, sampling, model/platform version, thinking settings,
temperature, token budgets, timeout, retries and concurrency. Separate physical
model families and strict/relaxed formats. Group graph/Snapshot/Family relations
to prevent development/test leakage. Do not select better answers by repeated
testing. Source-identical task projections are not independent samples.
