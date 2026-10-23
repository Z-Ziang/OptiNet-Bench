# Graph-task scoring

G1 checks equivalence of graph representations. G2 checks path-validity labels
and error types. G3 checks shortest paths, link directions and shared links.
G1-G3 use binary correctness. X1 minimizes hop count or total path length,
as specified by the case. Legal paths exceeding the reference optimum are
suboptimal; invalid paths or inconsistent cost declarations fail the decision.
All X1 cases are solvable. A legal solution better than the stored optimum is
a scoring error requiring reference inspection.

Strict scoring checks the raw final response. Relaxed scoring also permits
removing one complete outer JSON code fence or extracting a unique task-shaped
JSON object from explanatory text. It does not repair fields or select candidates
by score. See the [scoring protocol](../../../evaluation/docs/SCORING_PROTOCOL.md).
Private inputs and reference data are accessed only by the grader.
