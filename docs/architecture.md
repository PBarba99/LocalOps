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

The command registry, restricted SSH client, and predefined tool portions of
this flow are implemented. Each tool stops on the first non-zero command exit
and raises a diagnostic error retaining the command ID, stdout, stderr, and exit
code. The Ollama and agent portions remain planned.

## Version 0.1 non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework
