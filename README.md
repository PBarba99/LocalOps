# LocalOps

[![Tests](https://github.com/PBarba99/LocalOps/actions/workflows/tests.yml/badge.svg)](https://github.com/PBarba99/LocalOps/actions/workflows/tests.yml)

LocalOps is a local AI assistant for inspecting a Linux home server. The
application runs on Windows, uses Llama 3.1 8B through Ollama, and retrieves
live server information over SSH through predefined read-only tools.

The configuration, restricted SSH boundary, three read-only inspection tools,
Ollama tool calling, and agent loop are implemented. LocalOps can answer a
natural-language question using live server data selected through a fixed,
immutable allowlist. An interactive command-line interface is available.

## Version 0.1 goal

Prove this end-to-end flow:

```text
User question
  -> local model selects a predefined tool
  -> Python runs a fixed read-only command over SSH
  -> real server output returns to the model
  -> model answers from that output
```

Initial tools:

- `get_system_info()`
- `get_memory_usage()`
- `get_disk_usage()`

The model will not receive arbitrary shell access.

## Structure

```text
src/localops/
  app.py              Command-line entry point
  agent.py            Model/tool orchestration
  config.py           Environment configuration
  ollama_client.py    Local model boundary
  ssh_client.py       Restricted SSH boundary
  prompts.py          Agent instructions
  tools/              Explicit read-only tools and registry
tests/
  unit/               Isolated behavior tests
  integration/        End-to-end flow tests
docs/                 Architecture and development notes
```

## Local setup

Copy `.env.example` to `.env` and fill in the local settings. The `.env` file and
private SSH keys must never be committed. The target server must already be in
the user's SSH `known_hosts`; unknown host keys are rejected rather than
accepted automatically.

Ollama must be running and the configured model must already be installed. The
VPN or local network route required to reach the server must also be active.

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
units and refusal of all server modifications.

## Interactive CLI

Start LocalOps from the project directory:

```powershell
.\.venv\Scripts\localops.exe
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe -m localops.app
```

Ask natural-language questions such as:

```text
You: How much storage is left on the server?
You: How much memory is currently available?
You: What operating system is the server running?
```

Enter `exit` or `quit` to stop. Expected connection, model, command, and tool
validation failures are displayed concisely and return to the prompt. `Ctrl+C`
and end-of-input exit cleanly.

Structured tool events are written to `.localops/localops.log` at the configured
`LOG_LEVEL`. Logs rotate locally and exclude user questions, server output, SSH
configuration, and private-key paths.

## Current status

- Environment configuration is loaded, validated, and immutable.
- Six reviewed read-only commands are represented by `CommandID` and stored in
  an immutable allowlist.
- The SSH client rejects raw command text, uses the configured private key, and
  returns stdout, stderr, and the remote exit code. Connection and command waits
  have bounded timeouts.
- System, memory, and disk tools execute only their assigned `CommandID` values.
  They fail immediately on a non-zero exit while preserving stdout and stderr
  for diagnosis.
- Unit tests cover command injection, connection failures, execution failures,
  command timeouts, non-zero exits, tool failure behavior, and cleanup.
- All three inspection tools have passed live smoke tests against the target
  server.
- Ollama receives only three zero-argument tool schemas. Model requests are
  strictly validated before invocation, and one corrective retry is allowed for
  an invalid request.
- The agent returns tool output to Ollama for a grounded final answer. Structured
  JSON logs record tool selection and outcomes without questions, command
  output, SSH settings, or private-key paths.
- The model instructions require quantities and units to be copied exactly from
  tool output. Requests to modify the server must be refused, including repeated
  requests, and unavailable commands or tool calls must not be suggested.
- The full question-to-answer flow has been verified live with system, memory,
  and disk questions.
- The interactive CLI constructs the complete application, accepts repeated
  questions, reports expected failures without a traceback, and exits cleanly.
- Llama 3.1 8B has passed live CLI checks for tool selection, grounded answers,
  response latency, and refusal of write operations. Qwen 3 4B remains available
  as a configuration-only fallback.

## License

LocalOps is available under the [MIT License](LICENSE).
