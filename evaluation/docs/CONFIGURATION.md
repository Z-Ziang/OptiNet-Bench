# Configuration

Copy `config.example.json` to `config.json`. Do not edit task graders to change
models. The default dataset location is `../dataset`; `_meta` stays inside it.

| Field | Purpose |
|---|---|
| datasets | Dataset roots, relative to the config file; the single-folder release uses ../dataset |
| model | Inspect provider/model string; an OpenAI-compatible endpoint uses openai/SERVED_MODEL_ID |
| base_url | Actual compatible API base URL, normally including /v1 |
| model_args | Provider connection options; responses_api=false selects Chat Completions in the example |
| generation.temperature | Frozen sampling setting |
| generation.max_tokens | Generation limit, not input size; reasoning-budget treatment is provider-specific |
| generation.timeout | Provider/Inspect request timeout |
| generation.max_retries | Transport retries, not repeated answer selection |
| generation.extra_body | Optional, explicitly confirmed platform settings; thinking keys are not guessed |
| max_samples | Inspect sample concurrency, not CPU workers or an RPM allowance |

Credentials are read from environment variables. Configuration rejects api_key,
authorization, access_token and password fields and credential-bearing URLs.
The program does not enable JSON Schema generation or change prompts by default.
If structured output is enabled by platform options, freeze and label that as a
separate experimental setting.

The example 8192-token generation limit is not guaranteed sufficient for all
Cases. Measure the actual service tokenizer, reserve output context, and report
truncation/context/service errors separately. Preserve unknown usage as unknown.
New computers should regenerate plans because plans bind absolute dataset paths.
