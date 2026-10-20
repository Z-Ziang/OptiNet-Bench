# Scoring protocol

## Categories and denominators
G1/G2/G3 report binary correctness and source diagnostic reasons. Feasible X1,
O1-S/O1-C, X2/X3 and Q1 instances report:

| Category | Meaning |
|---|---|
| CORRECT | A legal globally optimal allocation/path, or a correct binary answer |
| SUBOPTIMAL | Legal but below the frozen lexicographic optimum |
| INFEASIBLE | A processable answer violates constraints, or accepts a certified-infeasible instance |
| MISSING | No compliant solution, including invalid JSON/schema or rejection of a feasible instance, following each source adapter |

Certified correct rejection is identified with `truth_feasible=false` and
`correct_reject=true`; it is not an optimal allocation. REVIEW_* indicates
interface/data/oracle review. SCORING_ERROR is a scorer exception. SERVICE_ERROR
is a failed request without an answer. Do not merge these into model mistakes.
Report total selected, returned, scored, reviewed and infrastructure-unresolved
denominators separately.

## Objectives and numerical rules
- X1: source graph shortest path, using HOP_COUNT or TOTAL_LENGTH_KM. Weighted
  validation uses the link lengths actually printed to six significant digits.
- O1-S/O1-C: paths are fixed; recover them from the Case and call the pinned
  X2/X3 validator. Require zero primary gap, then compare fragmentation.
- X2: minimize hops, then WUFR.
- X3: minimize additional spectrum-hop occupancy, then WUFR.
- Q1: all requests are admitted together or rejected together. Validate routing,
  profile compatibility, contiguous spectrum, joint conflicts, ASE-only OSNR and
  accumulated CD. Minimize sum(slots including guard times hops), then fragmentation.

O/X retains the source 1e-9 gap-classification tolerance. Q1 strict correctness
retains exact primary equality and `math.isclose(rel_tol=0, abs_tol=1e-10)` for
the secondary value. A Q1 rejection is correct only with a stored
INFEASIBLE_CERTIFIED proof. Timeout is not an infeasibility certificate.

Q1 `strict_bilevel_correct` reproduces the original strict predicate. Its
four-category view is a presentation layer. A better legal solution triggers
REVIEW_ORACLE. Source exceptions remain SCORING_ERROR rather than being silently
repaired. Secondary gaps are not compared as equal-quality tradeoffs when the
primary objective differs.

## Format policies
Strict grading preserves the raw final answer. Relaxed grading only removes one
outer JSON code fence enclosing the entire answer. Do not extract JSON from
prose, insert fields, repair routes or select a better retry. Q1 historical strict
scores must be compared with the strict column, not silently with relaxed scores.

The original Q1 evaluator aligns by request_id; it does not enforce input order
or reject all extra fields/duplicate JSON keys. Some malformed nested objects can
raise source exceptions. These behaviors are documented and preserved; enforcing
stricter schemas requires a separate protocol version.

## Public information and fairness
Only public system/user messages are model inputs. Keep private truth, oracle
values, certificates and future information out of requests. This release does
not add a WUFR formula to frozen model prompts. Source interface REVIEW flags
remain meaningful; scoring an objective does not prove that its public definition
was fully specified to the model.

Freeze Case UID, message hash, sampling, model/platform version, thinking settings,
temperature, token budgets, timeout, retries and concurrency. Separate physical
model families and strict/relaxed formats. Group graph/Snapshot/Family relations
to prevent development/test leakage. Disclose model-assisted benchmark construction and do not select better
answers by repeated testing; Q1 includes difficulty-based construction. Source-identical task projections are not independent samples.
