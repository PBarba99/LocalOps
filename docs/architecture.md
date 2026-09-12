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
User -> Agent -> Ollama -> validated action batch
                         |-> inspection tools -> approved SSH commands -> server
                         |   -> command results -> Ollama -> grounded answer
                         `-> decline unsupported request -> fixed local response
```

Ollama sees eight zero-argument schemas: seven inspection tools and one controlled
decline action. LocalOps accepts between one and six distinct requests, validates
the entire batch before running any command, rejects arguments and mixed decline
batches, and executes approved inspection tools sequentially. One corrective
model retry is permitted after an invalid request. A second invalid request
fails closed; SSH, timeout, and remote command failures are not retried through
the model.

Package-update inspection uses two fixed commands: a cached APT upgrade listing
and a read of `/var/lib/apt/periodic/update-stamp`. A missing stamp is reported
as "Unknown". The tool never refreshes metadata or installs packages. Its output
explicitly warns that the recorded periodic refresh does not guarantee all
repositories are current. Package-update selection and a combined update/disk
question have been validated against the live server.

Inspection results return to Ollama with an explicit final synthesis instruction
for a grounded answer. Tool schemas are omitted from this final request, so the
model cannot request additional structured tool calls after execution. The
decline action instead returns fixed application-owned text immediately. This
path does not create an SSH connection and does not ask the model to compose or
rewrite the refusal.

The recommended model is `llama3.1:8b`, selected through `OLLAMA_MODEL` rather
than hard-coded into the agent. `qwen3:4b` remains a tested fallback and control
model. Changing the configured model cannot add tools or commands because both
registries are fixed and validated outside the model.

The system prompt requires final answers to copy reported quantities and units
exactly. It routes unsupported questions and every server modification request
to the controlled decline action, and prohibits claims that a change was or will
be performed. Tool selection uses temperature `0` to reduce routing variance;
final-answer generation keeps the model's normal generation settings. These
instructions improve model behavior, while strict batch validation, the
immutable response registry, and the command allowlist remain the enforcement
boundaries.

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

Before displaying the first input prompt, the CLI asks the agent to warm the
model with the real system prompt and action schemas. Ollama evaluates that
stable prefix while the loading state is visible, generates at most one ignored
token, and never invokes the selected action. Chat requests keep the model
resident for the session; CLI shutdown sends a best-effort unload request.
Warm-up failures stop before user input rather than creating a broken session.

## Current non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework
