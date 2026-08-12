# LocalOps

LocalOps is a planned local AI assistant for inspecting a Linux home server.
The application will run on Windows, use a small Qwen model through Ollama, and
retrieve live server information over SSH through predefined read-only tools.

This repository is currently only a project skeleton. The modules define the
intended boundaries, but no SSH connection, Ollama call, or remote command has
been implemented.

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

## Later setup

When implementation begins, copy `.env.example` to `.env`, fill in the local
settings, install the package in a virtual environment, and run `localops`.

