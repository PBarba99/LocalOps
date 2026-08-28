# LocalOps

LocalOps is a planned local AI assistant for inspecting a Linux home server.
The application will run on Windows, use a small Qwen model through Ollama, and
retrieve live server information over SSH through predefined read-only tools.

The configuration, restricted SSH boundary, three read-only inspection tools,
Ollama tool calling, and agent loop are implemented. LocalOps can answer a
natural-language question using live server data selected through a fixed,
immutable allowlist. The command-line interface is not implemented yet.

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
- The full question-to-answer flow has been verified live with system, memory,
  and disk questions.
