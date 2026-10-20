# O1-S: Single-request fixed-path spectrum assignment

## Input
Send only the Case's `public/system_prompt.txt` and `public/user_prompt.txt` to the
evaluated model. Private answers, certificates, oracle values and provenance must
not enter the model request. The public schema is format documentation, not an
additional model message by default.

## Scientific rule
Recover the fixed path from the Case; the model only selects a starting slot. Call the pinned X2 validator, require zero primary gap and evaluate secondary fragmentation.

## Results
Four categories for feasible instances; certified correct rejection is separate. Review, service failures and scoring exceptions remain separate.
Strict scoring preserves the final response; relaxed scoring only removes a
single outer JSON code fence. See [scoring protocol](../../docs/SCORING_PROTOCOL.md).

## Interface
`grader.py` exports `grade(record: dict, final_answer: str) -> dict`.
Obtain records through `optinet.data.inventory()` instead of guessing paths.

```shell
python evaluate.py grade --dataset ../dataset --case FULL_CASE_UID --answer answer.txt --out score.json
```

Keep the entire evaluation package. Shared frozen code lives under
`optinet/_vendor`; a task folder alone is not a standalone grader.
