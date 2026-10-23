# RSA scoring

X2 and X3 select routes over the complete directed topology and assign contiguous,
continuous spectrum without conflicting with existing or simultaneous requests.
Requests include their guard slots. X3 accepts or rejects the request group jointly.
X2 minimizes route hops for the fixed request width, equivalently minimizing added
spectrum-slot occupancy; X3 minimizes the sum of requested slots times route hops.
Both then minimize network-wide spectrum fragmentation (WUFR).

The grader accepts different allocations attaining the same reference optimum.
For solvable cases, successful allocations are optimal or feasible but suboptimal.
A rejection of a solvable case is a decision failure. Correct rejection of a
certified unsolvable case is successful but is not an optimal allocation.
Malformed JSON or schema-invalid responses are format-invalid. Service and scoring
errors are recorded separately. The classification gap tolerance is 1e-9;
the underlying WUFR validator tolerance is 1e-12.

Only system and user prompts are sent to the model. References and objective
implementations are used by the grader. Strict scoring checks the raw final
response. Relaxed scoring also permits removing a complete outer JSON code fence
or extracting a unique task-shaped JSON object from explanatory text. Fields
are not repaired and candidates are not selected by score. See the
[scoring protocol](../../../evaluation/docs/SCORING_PROTOCOL.md).
