# Model connection, generation and case selection

Run from `evaluation/` after installing `requirements.txt`. Copy
`config.example.json` to `config.json`. The example selects **one G1 case** and
is a starting point for a new run, not a specification of the paper's runs.

The example's optional top-level `_comment` object contains English field
explanations. `quick` ignores this block; keep or remove it as preferred.
The file remains valid JSON, so do not add `//` or `/* ... */` comments.

## One command

The configuration has three parts: connection, generation, and selection:

```json
{
  "model": "deepseek/deepseek-flash",
  "api_key_env": "DEEPSEEK_API_KEY",
  "generation": {"max_tokens": 8192},
  "selection": {"cases": ["G1_0001"]}
}
```

Set the named environment variable locally, never the key itself in JSON.
For Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY = "YOUR_API_KEY"
python evaluate.py quick --config config.json
```

On Linux/macOS use `export DEEPSEEK_API_KEY="YOUR_API_KEY"`, then the same Python
command. This makes paid requests, grades final answers and exports results.
Omitting selection is an error; it never implicitly runs the full dataset.

The default output is a unique timestamped folder under `runs/` next to the
configuration file. Use `--out runs/my_run` or `"output_dir": "runs/my_run"`
to choose a **new** folder. Existing outputs are never overwritten.

```shell
python evaluate.py quick --config config.json --dry-run --out runs/checked_plan
python evaluate.py quick --config config.json --offline --out runs/reference_check
```

Dry-run validates selected public inputs and saves a bound `plan.json` without
a key or a model request. Offline replays stored reference answers through the
existing graders, also without requests; it does not measure model performance.

## 1. Connection

| Field | Meaning |
|---|---|
| `model` | Inspect `provider/model_id`; generic compatible APIs use `openai-api/service/model_id` |
| `base_url` | Optional API base address, not a chat website or full `/chat/completions` URL |
| `api_key_env` | Optional environment variable **name** containing the key |
| `model_args` | Optional Inspect provider connection arguments |
| `datasets` | Optional nonempty list of roots; default `["../dataset"]`, relative to the config file |
| `max_samples` | Concurrent samples, default 1; not a requests-per-minute allowance |

In `quick`, omitted `base_url` uses official addresses for `openai`, `anthropic`
and `deepseek`. Other providers retain their Inspect defaults and environment
settings. The provider is not inferred from the model name:

| API service | Model string | Default key variable |
|---|---|---|
| DeepSeek official | `deepseek/deepseek-flash` | `DEEPSEEK_API_KEY` |
| OpenAI official | `openai/YOUR_MODEL_ID` | `OPENAI_API_KEY` |
| Anthropic official | `anthropic/YOUR_MODEL_ID` | `ANTHROPIC_API_KEY` |
| Google Gemini | `google/YOUR_MODEL_ID` | `GOOGLE_API_KEY` |
| OpenAI-compatible gateway/local API | `openai-api/custom/YOUR_SERVED_MODEL_ID`, with `base_url` | `CUSTOM_API_KEY` or your `api_key_env` |

Some native providers require optional dependencies, for example
`python -m pip install "inspect-ai[anthropic,google]==0.3.278"`. The standard
requirements include OpenAI and DeepSeek support. If `api_key_env` is omitted,
Inspect reads the provider's normal key variable.

Example for an OpenAI-compatible service:

```json
{
  "model": "openai-api/custom/YOUR_SERVED_MODEL_ID",
  "base_url": "https://YOUR_API_HOST/v1",
  "api_key_env": "MY_MODEL_API_KEY",
  "model_args": {"responses_api": false},
  "generation": {"max_tokens": 32768, "temperature": 0.6},
  "selection": {"tasks": ["X2"], "limit_per_task": 3}
}
```

Keys are resolved in memory, not copied into run configuration. Credential
fields and URLs containing credentials, query parameters or fragments are
rejected. Keep logs private if the service returns sensitive content in answers
or errors.

Use the generic `openai-api` adapter for gateways serving arbitrary model IDs;
native `openai` applies OpenAI-specific reasoning and message-role rules.

## 2. Generation and budgets

Every generation field is optional. Omit `generation` or use `{}` to retain
the pinned Inspect adapter and provider defaults. The evaluator does not insert
a temperature or output cap when omitted. Inspect/provider defaults can include
a model-dependent output limit; inspect the saved log configuration. The example
explicitly requests 8192 output tokens, which is not a universal default or a
guarantee that a case can finish.

| Option | Meaning |
|---|---|
| `max_tokens` | Positive output-token cap; 32K is 32768. Reasoning may share this cap, depending on the provider |
| `temperature` | Sampling temperature, 0–2; the service may support a narrower range |
| `top_p`, `top_k`, `seed`, `stop_seqs` | Optional sampling controls, when supported by the model |
| `frequency_penalty`, `presence_penalty` | Optional penalties, −2 to 2 |
| `reasoning_effort`, `reasoning_tokens`, `reasoning_mode` | Optional Inspect reasoning controls; model support varies |
| `timeout`, `attempt_timeout` | Positive request/attempt timeout in seconds |
| `max_retries` | Nonnegative Inspect transport retry limit; 0 disables these retries |
| `extra_body` | Documented provider settings, e.g. `{"thinking":{"type":"disabled"}}` |

Unknown fields, invalid values and `extra_body` overrides of prompts, model,
output format or standard generation controls are rejected. Service-specific
support is ultimately checked by that service. Structured output is not enabled
and prompts are not rewritten automatically.

**Context capacity belongs to the model service.** `max_tokens` changes requested
output, not the model's context window. Input plus reserved output must fit the
service's actual tokenizer and context window. There is no generic client option
to enlarge that window. Questions are never automatically truncated. Context
errors, output stop reasons and provider-reported usage remain in Inspect logs;
unknown usage stays unknown.

## 3. Cases and task batches

Use canonical IDs such as `X2_0001`, or full 64-character UIDs from the catalog.
Directory labels such as `X2_001` are not canonical IDs. Choose either exact
cases or tasks, never both:

```json
{"selection": {"cases": ["X2_0001", "X2_0002", "Q1_0001"]}}
```

All X2 cases:

```json
{"selection": {"tasks": ["X2"]}}
```

Ten cases in each selected task:

```json
{"selection": {"tasks": ["X2", "X3"], "limit_per_task": 10}}
```

Task selection also accepts `offset_per_task` (default 0), `scale` and `topology`
(exact topology ID or folder). Limit 0 means all matches. This follows catalog
order, not stratified random sampling. Each requested task must have a match.
Exact lists preserve request order and reject missing, ambiguous or duplicate
cases. Limits and filters cannot be combined with exact case lists.

`{"selection":{"case_file":"my_cases.txt"}}` reads one ID or UID per line;
blank lines and whole-line `#` comments are ignored. This path is relative to
the configuration file. CLI `--case-file` and `--out` paths are relative to the
current working directory. CLI case/task selectors replace configured selection;
CLI filters override corresponding configured filters:

```shell
python evaluate.py quick --config config.json --case X2_0001 --case X2_0002
python evaluate.py quick --config config.json --case-file my_cases.txt
python evaluate.py quick --config config.json --tasks X2 --limit-per-task 10
python evaluate.py quick --config config.json --tasks X2
```

## Outputs and existing commands

Live/offline runs save `plan.json`, `run_identity.json`, Inspect logs and an
`export/` directory. `answers_and_scores.jsonl` contains final answers, grades
and provider usage. `summary.json`/`summary.csv` aggregate counts and metrics;
`overall.csv` reports the eight-task aggregate when coverage permits. Inspect
logs retain stop reasons and generation settings. Failed samples are preserved
and cause exit code 2. Only public system/user prompts go to models; private
references are used locally by the unchanged graders. New runs do not alter
the published `results/` tables.

Existing `plan`, `preflight`, `run`, `offline`, `grade`, `export` and `retry`
commands remain available. `run --config ... --plan ... --out ...` uses its
explicit plan, ignoring `selection` and `output_dir`; its connection behavior
is the existing Inspect behavior. Official-address resolution and `api_key_env`
override described above belong to `quick`. Regenerate saved plans after moving
data because plans bind absolute roots.

References: [Inspect providers](https://inspect.aisi.org.uk/providers.html),
[Inspect GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig),
[DeepSeek model IDs and API address](https://api-docs.deepseek.com/quick_start/pricing/).
