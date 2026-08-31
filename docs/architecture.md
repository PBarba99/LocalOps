# Architecture notes

## Trust boundary

The model may select a named tool but must never construct or submit shell text.
Each tool maps to a reviewed command identifier inside the SSH layer, which owns
the fixed command allowlist.

The SSH client accepts `CommandID`, resolves it through the immutable allowlist,
and never accepts shell text as its execution input. Paramiko loads the user's
known host keys, rejects unknown hosts, and authenticates using the configured
private key. Results retain stdout, stderr, and the remote exit code.

## System flow

```text
User -> Agent -> Ollama -> named tool -> registry
     -> predefined tool -> approved SSH command -> Linux server
     -> command result -> Ollama -> final answer
```

This flow is implemented through the final model answer. Ollama sees only three
zero-argument tool schemas. LocalOps requires exactly one request, validates its
exact name and empty arguments, and permits one corrective model retry after an
invalid request. A second invalid request fails closed; SSH, timeout, and remote
command failures are not retried through the model.

The recommended model is `llama3.1:8b`, selected through `OLLAMA_MODEL` rather
than hard-coded into the agent. `qwen3:4b` remains a tested fallback and control
model. Changing the configured model cannot add tools or commands because both
registries are fixed and validated outside the model.

The system prompt requires final answers to copy reported quantities and units
exactly. It also requires the model to refuse every server modification, never
claim that a change was or will be performed, and never imitate unavailable
commands or tool calls. These instructions improve user-facing behavior; the
registry and immutable allowlist remain the enforcement boundary.

Each tool stops on the first non-zero command exit and raises a diagnostic error
retaining the command ID, stdout, stderr, and exit code. Structured JSON events
record tool names, attempts, validation decisions, execution outcomes, and
non-sensitive Ollama timing and token metrics. They exclude user questions,
model answers, tool output, SSH configuration, and exception messages from
operational failures.

## Interface

Version 0.1 uses an interactive terminal loop. It builds the model, registry,
and SSH client from one validated settings object, accepts repeated questions,
and keeps running after expected operational errors. Tool events are written to
a rotating local file under `.localops/`; conversational content remains in the
terminal and is not logged.

## Version 0.1 non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework
