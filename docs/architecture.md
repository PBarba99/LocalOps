# Architecture notes

## Trust boundary

The model may select a named tool but must never construct or submit shell text.
Each tool maps to a reviewed command identifier inside the SSH layer, which owns
the fixed command allowlist.

The SSH client accepts `CommandID`, resolves it through the immutable allowlist,
and never accepts shell text as its execution input. Paramiko loads the user's
known host keys, rejects unknown hosts, and authenticates using the configured
private key. Results retain stdout, stderr, and the remote exit code.

Non-command decisions have a separate boundary. The only current control action
is `decline_unsupported_request`, whose response is stored in an immutable
application registry. It accepts no arguments and never reaches the SSH client.

## System flow

```text
User -> Agent -> Ollama -> one validated action
                         |-> inspection tool -> approved SSH command -> server
                         |   -> command result -> Ollama -> grounded answer
                         `-> decline unsupported request -> fixed local response
```

Ollama sees four zero-argument schemas: three inspection tools and one controlled
decline action. LocalOps requires exactly one request, validates its exact name
and empty arguments, and permits one corrective model retry after an invalid
request. A second invalid request fails closed; SSH, timeout, and remote command
failures are not retried through the model.

Inspection results return to Ollama for a grounded final answer. The decline
action instead returns fixed application-owned text immediately. This path does
not create an SSH connection and does not ask the model to compose or rewrite
the refusal.

The recommended model is `llama3.1:8b`, selected through `OLLAMA_MODEL` rather
than hard-coded into the agent. `qwen3:4b` remains a tested fallback and control
model. Changing the configured model cannot add tools or commands because both
registries are fixed and validated outside the model.

The system prompt requires final answers to copy reported quantities and units
exactly. It routes unsupported questions and every server modification request
to the controlled decline action, and prohibits claims that a change was or will
be performed. These instructions improve model selection; strict action
validation, the immutable response registry, and the command allowlist remain
the enforcement boundaries.

Each tool stops on the first non-zero command exit and raises a diagnostic error
retaining the command ID, stdout, stderr, and exit code. Structured JSON events
record tool names, attempts, validation decisions, execution outcomes, and
non-sensitive Ollama timing and token metrics. They exclude user questions,
model answers, tool output, SSH configuration, and exception messages from
operational failures.

## Interface

LocalOps currently uses an interactive terminal loop. It builds the model,
registry, and SSH client from one validated settings object, accepts repeated
questions, and keeps running after expected operational errors. Tool events are
written to a rotating local file under `.localops/`; conversational content
remains in the terminal and is not logged.

## Current non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework
