# O1-C: Concurrent fixed-path spectrum assignment

## Input
Send only the Case's `public/system_prompt.txt` and `public/user_prompt.txt` to the
evaluated model. Private answers, certificates, oracle values and provenance must
not enter the model request. The public schema is format documentation, not an
additional model message by default.

## Scientific rule
Recover each fixed path, check joint resource conflicts with the pinned X3 validator, and evaluate secondary fragmentation. Model allocations contain request_id and slot_start only.

## Results
Four categories for feasible instances; certified correct rejection is separate. Review, service failures and scoring exceptions remain separate.
Strict scoring preserves the final response; relaxed scoring only removes a
single outer JSON code fence. See `docs/SCORING_PROTOCOL.md`.

## Interface
`grader.py` exports `grade(record: dict, final_answer: str) -> dict`.
Obtain records through `optira.data.inventory()` instead of guessing paths.

```shell
python evaluate.py grade --config config.json --case FULL_CASE_UID --answer answer.txt --out score.json
```

Keep the entire evaluation package. Shared frozen code lives under
`optira/_vendor`; a task folder alone is not a standalone grader.
