# G2: Path validity classification

## Input
Send only the Case's `public/system_prompt.txt` and `public/user_prompt.txt` to the
evaluated model. Private answers, certificates, oracle values and metadata must
not enter the model request. The public schema is format documentation, not an
additional model message by default.

## Scientific rule
Validate path legality and the reported error type using the original FIRST_MATCH precedence.

## Results
Binary correct/incorrect. Service failures and scoring exceptions are recorded separately from scored outcomes.
Strict scoring preserves the final response. The shared relaxed-scoring entry
uses raw JSON, removes a complete outer JSON code fence, or extracts a unique
task-shaped JSON object from explanatory text. Ambiguous candidates are
format-invalid. See [scoring protocol](../../docs/SCORING_PROTOCOL.md).

## Interface
`grader.py` exports the task adapter `grade(record: dict, final_answer: str) -> dict`.
Use `optinet.scoring.score_answer()` for the complete strict/relaxed policy.
Obtain records through `optinet.data.inventory()` instead of guessing paths.

```shell
python evaluate.py grade --dataset ../dataset --case G2_0001 --answer answer.txt --out score.json
```

Keep the entire evaluation package. Shared frozen code lives under
`optinet/_vendor`; a task folder alone is not a standalone grader.
