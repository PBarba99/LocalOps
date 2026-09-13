# LocalOps

[![Tests](https://github.com/PBarba99/LocalOps/actions/workflows/tests.yml/badge.svg)](https://github.com/PBarba99/LocalOps/actions/workflows/tests.yml)

LocalOps is a local AI assistant for inspecting a Linux home server. The
application runs on Windows, uses Llama 3.1 8B through Ollama, and retrieves
live server information over SSH through predefined read-only tools.

The configuration, restricted SSH boundary, eight read-only inspection tools,
Ollama tool calling, and agent loop are implemented. LocalOps can answer a
natural-language question using live server data selected through a fixed,
immutable allowlist. Unsupported requests are declined with fixed
application-owned text without connecting to the server. An interactive
command-line interface is available.

## Core flow

Prove this end-to-end flow:

```text
User question
  -> local model selects one or more predefined tools
  -> Python validates the complete request batch
  -> Python runs fixed read-only commands sequentially over SSH
  -> real server outputs return to the model
  -> model answers from those outputs without access to more tools
```

Inspection tools:

- `get_system_info()`
- `get_memory_usage()`
- `get_disk_usage()`
- `get_cpu_load()`
- `get_service_status()`
- `get_network_status()`
- `get_package_updates()`
- `get_temperature_readings()`

Package-update inspection reads cached APT metadata without refreshing it or
installing packages. It reports the last recorded periodic APT refresh, or
"Unknown" if the refresh stamp is missing. This timestamp is a freshness hint,
not a guarantee that every repository is current; stale metadata can miss new
updates.

Temperature inspection reads kernel thermal zones under `/sys/class/thermal/`
without requiring `lm-sensors` or changing thermal settings. Python converts
integer millidegrees to Celsius exactly and preserves kernel zone labels.
Unavailable or malformed readings remain visible without discarding valid
readings. These zones may not cover every component, and their readings are not
a hardware-health assessment.

The model will not receive arbitrary shell access.

## Structure

```text
src/localops/
  app.py              Command-line entry point
  agent.py            Model/tool orchestration
  config.py           Environment configuration
  ollama_client.py    Local model boundary
  request_policy.py   Fixed non-command decisions and responses
  ssh_client.py       Restricted SSH boundary
  prompts.py          Agent instructions
  tools/              Explicit read-only tools and registry
tests/
  unit/               Isolated behavior tests
  integration/        End-to-end flow tests
docs/                 Architecture and development notes
```

Release history is recorded in [CHANGELOG.md](CHANGELOG.md).

## Local setup

Copy `.env.example` to `.env` and fill in the local settings. The `.env` file and
private SSH keys must never be committed. The target server must already be in
the user's SSH `known_hosts`; unknown host keys are rejected rather than
accepted automatically.

Ollama must be running and the configured model must already be installed. The
VPN or local network route required to reach the server must also be active.

Ollama requests use a positive, finite SDK network timeout of 120 seconds by
default. Configure it in `.env`, increasing the value for slower CPU inference:

```dotenv
OLLAMA_TIMEOUT_SECONDS=120
```

This applies to loading, answering, and unload requests. It limits network
operations and periods of inactivity, not the total duration of a question
across model requests and SSH commands. Existing `.env` files do not need the
setting unless overriding the default.

From PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Model selection

The recommended model is `llama3.1:8b`. Install it before starting LocalOps:

```powershell
ollama pull llama3.1:8b
```

The model is selected with `OLLAMA_MODEL` in `.env`, so changing models does not
alter the application or its command restrictions. `qwen3:4b` remains a tested
fallback and control model. To use it, keep that model installed and set:

```dotenv
OLLAMA_MODEL=qwen3:4b
```

Llama 3.1 8B was selected after isolated and live CLI tests showed valid tool
selection, concise answers, no visible reasoning output, and substantially
lower response latency. The system prompt explicitly requires exact reported
units and refusal of all server modifications. Tool selection uses temperature
`0` for consistent routing; final-answer generation retains the model's normal
generation settings.

## Interactive CLI

Start LocalOps from the project directory:

```powershell
.\.venv\Scripts\localops.exe
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe -m localops.app
```

At startup, the CLI displays an ASCII banner and a model-loading status. It
loads the configured model and primes the stable system prompt and action
schemas before displaying the first `You:` prompt. The model remains resident
for the CLI session and an unload is attempted on exit. If warm-up fails,
LocalOps reports the problem without entering an unusable question loop.

Ask natural-language questions such as:

```text
You: How much storage is left on the server?
You: How much memory is currently available?
You: What operating system is the server running?
You: Summarize the server's CPU load, memory, disk space, and network status.
You: Are package updates available, and when was the metadata last refreshed?
You: What is the CPU package temperature, and what is the current CPU load?
```

Questions outside the available server inspection tools, such as a weather
question, receive a fixed explanation of the assistant's scope. Requests to
modify the server use the same controlled decline path. Neither case opens an
SSH connection.

Enter `exit` or `quit` to stop. Expected connection, model, command, and tool
validation failures are displayed concisely and return to the prompt. `Ctrl+C`
and end-of-input exit cleanly.

Empty final answers or unexpected final tool calls also produce a concise error
without closing the CLI. You can ask again; LocalOps does not automatically
repeat completed commands. Ollama timeouts during loading stop before input,
answer timeouts return to the prompt, and unload timeouts are ignored during
best-effort shutdown.

Structured tool events are written to `.localops/localops.log` at the configured
`LOG_LEVEL`. Logs rotate locally and exclude user questions, server output, SSH
configuration, and private-key paths.

## Current status

- Environment configuration is loaded, validated, and immutable.
- The CLI preloads and primes Ollama before accepting a question, keeps the
  model resident during the session, and attempts to unload it during shutdown.
- Fifteen reviewed read-only commands are represented by `CommandID` and stored in
  an immutable allowlist.
- The SSH client rejects raw command text, uses the configured private key, and
  returns stdout, stderr, and the remote exit code. Connection and command waits
  have bounded timeouts.
- The command-output collection deadline is enforced even while stdout or
  stderr remains continuously ready. Ollama requests use the configurable
  `OLLAMA_TIMEOUT_SECONDS` SDK network timeout.
- System, memory, disk, CPU-load, service-status, network-status, package-update,
  and temperature tools execute only their assigned `CommandID` values. They
  fail immediately on a non-zero command exit while preserving stdout and stderr
  for diagnosis. Individual unavailable thermal readings do not fail the report.
- Unit tests cover command injection, connection failures, execution failures,
  command timeouts, non-zero exits, tool failure behavior, and cleanup.
- All eight inspection tools have passed live smoke tests against the target
  server.
- Ollama receives nine zero-argument action schemas: eight inspection tools and
  `decline_unsupported_request`. The agent accepts at most six distinct calls,
  validates the complete batch before execution, and runs approved inspection
  tools sequentially. One corrective retry is allowed for an invalid request.
- Tool selection uses temperature `0`. After execution, the agent returns every
  tool output to Ollama with an explicit synthesis instruction and no tool
  schemas, so the final phase can only produce an answer. Structured JSON logs
  record tool selection and outcomes without questions, command output, SSH
  settings, or private-key paths.
- The model instructions require quantities and units to be copied exactly from
  tool output. Unsupported questions and requests to modify the server select an
  immutable application response without SSH or a second model call.
- The full question-to-answer flow has been verified live with system, memory,
  disk, CPU-load, systemd service, network, package-update, and temperature questions,
  including combined requests that select several tools. The per-question limit
  remains six calls, even though eight inspection tools are available.
- The interactive CLI constructs the complete application, accepts repeated
  questions, reports expected failures without a traceback, and exits cleanly.
- Llama 3.1 8B has passed live CLI checks for tool selection, grounded answers,
  response latency, unsupported general questions, and refusal of write
  operations. Qwen 3 4B remains available as a configuration-only fallback.

## License

LocalOps is available under the [MIT License](LICENSE).
