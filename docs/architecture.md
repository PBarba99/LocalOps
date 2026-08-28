# Architecture notes

## Trust boundary

The model may select a named tool but must never construct or submit shell text.
Each tool maps to a reviewed command identifier inside the SSH layer, which will
own the fixed command allowlist.

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

Each tool stops on the first non-zero command exit and raises a diagnostic error
retaining the command ID, stdout, stderr, and exit code. Structured JSON events
record tool names, attempts, validation decisions, and execution outcomes. They
exclude user questions, tool output, SSH configuration, and exception messages
from operational failures.

## Version 0.1 non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework
