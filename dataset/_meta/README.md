# Dataset metadata

The dataset contains 21,356 cases across nine tasks, including 2,000 Q1 cases.
Use `catalog/case_index.jsonl` to select cases and
`catalog/case_identity.jsonl` for file identities and integrity bindings.
`SHA256SUMS.json` lists dataset file checksums.
Only `public/system_prompt.txt` and `public/user_prompt.txt` form model inputs.
Network states, reference values and certificates are used exclusively for grading.

`case_id` is the unique task-prefixed, four-digit case identifier (for example,
`G1_0001` or `O1-S_0001`). `case_uid` is a unique 64-character hexadecimal
identifier. `case_dir` locates the files; its directory label is not an identifier.
The O1/X2/X3 pair table binds each task-specific root and truth file separately.

Q1 construction metadata records sampling parameters, physical-model settings,
seeds and spectrum perturbations. `input_generation` and `input_beam*_grade`
describe construction inputs and their diagnostics. Current-case certification
is recorded separately in the case metadata and oracle proof.
