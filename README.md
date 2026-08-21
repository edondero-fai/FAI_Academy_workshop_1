# Workshop 1 — Municipal Front-Desk Assistant

This workshop builds the smallest runnable LLM application: one municipal question goes in
and one text response comes out. The application uses the OpenAI Responses API and records
enough diagnostic information to understand every model call.

The application code intentionally stays in one entrypoint, `main.py`, following the syntax
introduced in Lecture 2. Tests and smoke-test inputs remain in `tests/`.

## Project contents

```text
Workshop_1/
├── main.py                 # Complete application and CLI
├── .env.example            # Configuration template without a real secret
├── pyproject.toml          # Python requirement and dependencies
├── uv.lock                 # Locked dependency versions
├── tests/
│   ├── smoke_inputs.json   # Seven fixed municipal questions
│   └── test_smoke.py       # Optional live API smoke test
└── diagnostics/            # Created at runtime and ignored by Git
```

## Setup

You need Linux, macOS, or WSL/Ubuntu, Python 3.12, `uv`, and your own OpenAI API key.

From the project directory, create the environment from the committed lockfile:

```bash
uv sync --frozen
```

Create a local configuration file:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your own key:

```dotenv
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
```

The `.env` file is ignored by Git. Do not place the real key in source code, tests,
diagnostic files, screenshots, or commits.

## How `main.py` works

### 1. Imports and environment configuration

The first block loads `.env` before an OpenAI client is created. It then reads the model name,
prompt version, and diagnostic path from environment variables.

```python
load_dotenv()

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5-mini")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "municipal-assistant-v1")
```

### 2. Stable instructions

`INSTRUCTIONS` contains the application-controlled prompt. It tells the model how a municipal
front-desk assistant should behave. The resident's question is kept separate from these stable
instructions.

This creates the same request structure shown in the lecture:

```python
response = client.responses.create(
    model=MODEL_NAME,
    instructions=INSTRUCTIONS,
    input=query,
)
```

The model response is a structured SDK object. The application reads its text using:

```python
answer = response.output_text.strip()
```

### 3. Model call and diagnostics

`model_call()` performs the complete request-response operation. Before returning the answer,
it records a JSON-compatible event containing:

- request ID and timestamp;
- prompt version and complete input context;
- requested and resolved model;
- raw SDK response and token usage;
- output text and elapsed time; and
- success state or typed error information.

Events are appended to `diagnostics/model_calls.jsonl`. This directory is ignored by Git
because questions and answers may contain resident-provided information.

### 4. Expected failures

The OpenAI SDK exceptions introduced in the lecture are translated into readable states:

| SDK error | CLI state | Meaning |
|---|---|---|
| `AuthenticationError` | `authentication` | The API key was rejected |
| `RateLimitError` | `rate_limit` | Request or account quota was reached |
| `APIConnectionError` / `APITimeoutError` | `connection_or_timeout` | The API could not be reached |
| `BadRequestError` | `malformed_request` | A model or request parameter was rejected |
| Empty response text | `malformed_response` | The response contained no usable answer |

The technical error is retained in the diagnostic event. Any occurrence of the configured API
key is replaced with `[REDACTED]` before the event is written.

### 5. Tracing

`setup_tracing()` follows the lecture pattern: Phoenix registers an OpenTelemetry provider,
then `OpenAIInstrumentor` instruments Responses API calls.

```python
tracer_provider = register(
    project_name="municipal-front-desk",
    endpoint="http://localhost:6006/v1/traces",
)
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

`answer_question()` adds the municipal request ID, prompt version, and outcome to a manual
`municipal_front_desk.request` span.

### 6. Command-line entrypoint

`main()` reads the question and optional flags, starts tracing, calls `answer_question()`, and
prints either the answer or a readable error. The `if __name__ == "__main__"` guard ensures
that importing `main.py` in tests does not run the CLI or start Phoenix.

## Using the script

### Run without Phoenix

Use `--no-tracing` when only the local JSONL diagnostic record is needed:

```bash
uv run python main.py --no-tracing "How do I report a missed rubbish collection?"
```

The assistant prints one non-empty answer to the terminal.

### Supply a request ID

Attach an existing case or demonstration identifier:

```bash
uv run python main.py --no-tracing --request-id CASE-123 \
  "Where can I renew a resident parking permit?"
```

The same ID appears in the JSONL event and OpenTelemetry span, making the call easy to find.

### Run with Phoenix tracing

Start Phoenix in one terminal:

```bash
uv run phoenix serve
```

In another terminal, run the assistant without `--no-tracing`:

```bash
uv run python main.py --request-id DEMO-001 \
  "How can I request a copy of a birth certificate?"
```

Open <http://localhost:6006>, select the `municipal-front-desk` project, and inspect the trace.

### Inspect the local diagnostic event

```bash
rg 'DEMO-001' diagnostics/model_calls.jsonl
```

Each line is a complete JSON object for one model-call attempt.

## Configuration reference

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `OPENAI_API_KEY` | yes | none | OpenAI credential read by the SDK |
| `OPENAI_MODEL` | no | `gpt-5-mini` | Model sent to the Responses API |
| `PROMPT_VERSION` | no | `municipal-assistant-v1` | Prompt identifier in diagnostics |
| `DIAGNOSTICS_PATH` | no | `diagnostics/model_calls.jsonl` | Local event file |
| `PHOENIX_ENDPOINT` | no | `http://localhost:6006/v1/traces` | Phoenix trace endpoint |
| `PHOENIX_PROJECT` | no | `municipal-front-desk` | Phoenix project name |

## Tests

Run the seven fixed questions through the real API when a valid key, network connection and
local Phoenix server are available:

```bash
uv run pytest -v
```

The smoke test initializes Phoenix tracing and checks only that the application returns
non-empty text; it does not score the factual quality of the answers. This command makes seven
real, potentially billable API calls.

## Troubleshooting

- `Error [configuration]`: confirm that `.env` exists and contains `OPENAI_API_KEY`.
- `Error [authentication]`: replace an invalid, expired, or revoked API key.
- `Error [rate_limit]`: wait, check account quota, and try again.
- `Error [connection_or_timeout]`: check internet access, proxy settings, DNS, firewall rules,
  and access to `api.openai.com:443`.
- `Error [malformed_request]`: check `OPENAI_MODEL` and compare `.env` with `.env.example`.
- `ModuleNotFoundError`: run `uv sync --frozen` and use `uv run` for commands.
- Python version error: confirm Python 3.12 is available, then recreate the environment with
  `uv sync --frozen`.
