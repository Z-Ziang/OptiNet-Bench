# G3: Two shortest paths and shared directed links

## Input
Send only the Case's `public/system_prompt.txt` and `public/user_prompt.txt` to the
evaluated model. Private answers, certificates, oracle values and provenance must
not enter the model request. The public schema is format documentation, not an
additional model message by default.

## Scientific rule
Validate both shortest paths and all shared directed link IDs. Separate HOP_COUNT from TOTAL_LENGTH_KM; weighted scoring uses the public six-significant-digit lengths.

## Results
Binary correct/incorrect. Review, service failures and scoring exceptions remain separate.
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
