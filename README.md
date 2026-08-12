# LocalOps

LocalOps is a planned local AI assistant for inspecting a Linux home server.
The application will run on Windows, use a small Qwen model through Ollama, and
retrieve live server information over SSH through predefined read-only tools.

The configuration and restricted SSH boundary are implemented. LocalOps can
connect with key-based authentication and execute commands selected from a
fixed, immutable allowlist. The read-only tools, Ollama integration, agent loop,
and command-line interface are not implemented yet.

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
  returns stdout, stderr, and the remote exit code.
- Unit tests cover command injection, connection failures, execution failures,
  non-zero exits, and connection cleanup.
- A live `HOSTNAME` command has been verified successfully against the target
  server.
